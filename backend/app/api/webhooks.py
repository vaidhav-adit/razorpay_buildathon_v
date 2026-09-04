"""
api/webhooks.py
───────────────
Webhook Ingestion Endpoint for RazorpayX Payout Lifecycle Events.

Exposes:
  POST /webhooks/razorpay — Receives and verifies payout.failed and payout.reversed events,
                            creates recovery cases in the database, classifies root causes,
                            and logs cryptographically chained audit events.

Foundational Architectural Principles:
1. Cryptographic Signature Verification: Verifies HMAC-SHA256 signature from X-Razorpay-Signature header.
2. Immediate Database State Ingestion: Automatically creates Vendor, Payout, and RecoveryCase entities.
3. Deterministic Classification: Evaluates failure code immediately at ingestion time.
4. Tamper-Evident Genesis Block: Logs initial EXTERNAL_FACT in the audit ledger.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, Request, Header, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import CaseState, AuditActorType
from app.models.vendor import Vendor
from app.models.payout import Payout
from app.models.recovery_case import RecoveryCaseModel
from app.classifier import classify_failure
from app.audit import log_audit_event
from app.services.razorpay_client import verify_razorpay_signature

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


class WebhookIngestResponse(BaseModel):
    """Response returned upon successful webhook processing."""
    status: str
    case_id: Optional[str] = None
    case_number: Optional[str] = None
    strategy: Optional[str] = None
    event: str


@router.post("/razorpay", response_model=WebhookIngestResponse, status_code=status.HTTP_200_OK)
async def receive_razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None, alias="X-Razorpay-Signature"),
    db: Session = Depends(get_db),
):
    """
    Ingests live or simulated webhooks from RazorpayX.
    
    Verifies HMAC-SHA256 signature, parses failure event payloads (payout.failed, payout.reversed),
    stores the raw event in PostgreSQL, instantiates a RecoveryCase in state CASE_CREATED,
    classifies the failure strategy, and logs the initial EXTERNAL_FACT audit event.
    """
    raw_body = await request.body()

    # 1. Verify HMAC-SHA256 signature if signature header is provided
    if x_razorpay_signature:
        is_valid = verify_razorpay_signature(raw_body, x_razorpay_signature)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Razorpay webhook HMAC-SHA256 signature.",
            )

    try:
        payload: Dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON body in webhook request.",
        )

    event_name = payload.get("event", "unknown")

    # 2. Filter for failure/exception events
    if event_name not in {"payout.failed", "payout.reversed"}:
        return WebhookIngestResponse(
            status="ignored",
            event=event_name,
        )

    payout_data = payload.get("payload", {}).get("payout", {}).get("entity", {})
    if not payout_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing payout entity payload in webhook.",
        )

    # 3. Extract payout and failure fields
    rzp_payout_id = payout_data.get("id", f"pout_{uuid.uuid4().hex[:8]}")
    rzp_contact_id = payout_data.get("contact_id", f"cont_{uuid.uuid4().hex[:8]}")
    rzp_fund_account_id = payout_data.get("fund_account_id", f"fa_{uuid.uuid4().hex[:8]}")
    amount = payout_data.get("amount", 0)
    currency = payout_data.get("currency", "INR")
    mode = payout_data.get("mode", "NEFT")
    reference_id = payout_data.get("reference_id")

    status_details = payout_data.get("status_details") or {}
    source = status_details.get("source") or "unknown"
    reason = status_details.get("reason") or "unknown"
    description = status_details.get("description") or "Payout failed"

    # 4. Find or create Vendor record
    vendor = db.query(Vendor).filter(Vendor.razorpay_contact_id == rzp_contact_id).first()
    if not vendor:
        vendor = Vendor(
            id=f"vend_{uuid.uuid4().hex[:8]}",
            razorpay_contact_id=rzp_contact_id,
            name=payout_data.get("notes", {}).get("vendor_name") or f"Vendor-{rzp_contact_id[-6:]}",
            email=payout_data.get("notes", {}).get("vendor_email"),
            phone=payout_data.get("notes", {}).get("vendor_phone"),
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

    # 5. Find or create Payout record
    payout = db.query(Payout).filter(Payout.razorpay_payout_id == rzp_payout_id).first()
    if not payout:
        payout = Payout(
            id=f"pout_rec_{uuid.uuid4().hex[:8]}",
            razorpay_payout_id=rzp_payout_id,
            razorpay_fund_account_id=rzp_fund_account_id,
            razorpay_contact_id=rzp_contact_id,
            amount=amount,
            currency=currency,
            mode=mode,
            reference_id=reference_id,
            status="failed",
            status_source=source,
            status_reason=reason,
            status_description=description,
        )
        db.add(payout)
        db.commit()
        db.refresh(payout)

    # 6. Run deterministic failure classification
    classification = classify_failure(source, reason)

    # 7. Create RecoveryCase record
    case_number = f"CASE-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    case = RecoveryCaseModel(
        id=f"case_{uuid.uuid4().hex[:12]}",
        case_number=case_number,
        payout_id=payout.id,
        vendor_id=vendor.id,
        invoice_reference=reference_id,
        amount=amount,
        failure_source=source,
        failure_reason=reason,
        recovery_strategy=classification.strategy.value,
        state=CaseState.CASE_CREATED,
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    # 8. Log initial EXTERNAL_FACT audit event (Genesis block for this case)
    log_audit_event(
        db=db,
        case_id=case.id,
        event_type=AuditActorType.EXTERNAL_FACT,
        actor="razorpay_webhook",
        action="PAYOUT_FAILED_WEBHOOK_RECEIVED",
        target=rzp_payout_id,
        reason=description,
        input_data=payload,
        output_data={
            "case_number": case.case_number,
            "strategy": classification.strategy.value,
            "is_retryable": classification.is_retryable,
        },
    )

    return WebhookIngestResponse(
        status="received",
        case_id=case.id,
        case_number=case.case_number,
        strategy=classification.strategy.value,
        event=event_name,
    )
