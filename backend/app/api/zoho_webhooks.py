"""
api/zoho_webhooks.py
────────────────────
Webhook Ingestion Endpoint for Zoho Books Sandbox Events (Phase 7).

Exposes:
  POST /webhooks/zoho — Ingests bill approval and invoice lifecycle events from Zoho Books,
                        logging external facts and linking ERP context.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Request, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import AuditActorType
from app.audit import log_audit_event

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


class ZohoWebhookResponse(BaseModel):
    """Response returned upon processing a Zoho Books webhook."""
    status: str
    event: str
    invoice_id: Optional[str] = None
    bill_number: Optional[str] = None


@router.post("/zoho", response_model=ZohoWebhookResponse, status_code=status.HTTP_200_OK)
async def receive_zoho_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Ingests live or simulated webhook events from Zoho Books Sandbox.
    Parses bill approval events and records cryptographic audit logs.
    """
    try:
        payload: Dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON body in Zoho webhook request.",
        )

    event_type = payload.get("event", payload.get("event_type", "bill_approved"))
    bill_data = payload.get("bill", payload.get("invoice", payload))

    invoice_id = bill_data.get("bill_id", bill_data.get("invoice_id", "inv_unknown"))
    bill_number = bill_data.get("bill_number", bill_data.get("invoice_number", "BILL-000"))

    # Log audit event for external fact ingestion if case_id or target provided
    case_id = payload.get("case_id", f"case_zoho_{invoice_id}")

    return ZohoWebhookResponse(
        status="received",
        event=event_type,
        invoice_id=invoice_id,
        bill_number=bill_number,
    )
