"""
api/cases.py
────────────
Case Management & Human Approval API (Phase 11).

Exposes endpoints for the internal finance operations controller:
  POST /cases/{case_id}/approve  — Authorizes and triggers Level 3 replacement payout execution.
  POST /cases/{case_id}/reject   — Rejects proposed recovery and transitions case to terminal BLOCKED.
  GET  /cases/{case_id}          — Returns full case detail, context tabs, and verification status.
  GET  /cases                    — Returns paginated/filtered list of recovery cases.

Foundational Architectural Principles:
1. Human Gate Enforcement: Money NEVER moves without explicit human authorization.
2. State Machine Validation: Approve only allowed from HUMAN_APPROVAL. Reject allowed from HUMAN_APPROVAL/HUMAN_REVIEW.
3. Cryptographic Audit Logging: Every decision is recorded with actor = 'finance_controller' and event_type = HUMAN_DECISION.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.enums import CaseState, ApprovalDecision, AuditActorType, PolicyLevel, PolicyDecision
from app.models.recovery_case import RecoveryCaseModel
from app.models.approval import Approval
from app.models.payout import Payout
from app.models.vendor import Vendor
from app.models.fund_account import FundAccount
from app.models.agent_action import AgentAction
from app.state_machine import transition_state
from app.classifier import classify_failure
from app.audit import log_audit_event, verify_chain
from app.services.razorpay_client import razorpay_client
from app.agent.orchestrator import run_agent_for_case

router = APIRouter(prefix="/cases", tags=["Cases & Human Approvals"])


# ─────────────────────────────────────────────────────────────────────────────
# Request and Response Schemas
# ─────────────────────────────────────────────────────────────────────────────

class ApproveCaseRequest(BaseModel):
    """Payload provided by the human controller approving a payout execution."""
    model_config = ConfigDict(extra="ignore")
    decided_by: str = Field(default="finance_controller", description="Identifier of the approver")
    notes: Optional[str] = Field(default=None, description="Optional operational notes")


class RejectCaseRequest(BaseModel):
    """Payload provided by the human controller rejecting a payout recovery proposal."""
    model_config = ConfigDict(extra="ignore")
    reason: str = Field(..., description="Mandatory reason for rejecting the recovery")
    decided_by: str = Field(default="finance_controller", description="Identifier of the approver")


class ApprovalActionResponse(BaseModel):
    """Response returned upon approving or rejecting a case."""
    case_id: str
    case_number: str
    decision: str
    state: str
    payout_id: Optional[str] = None
    message: str


class CaseListItemResponse(BaseModel):
    """Summary item for the case list view."""
    id: str
    case_number: str
    payout_id: str
    vendor_id: Optional[str] = None
    vendor_name: Optional[str] = None
    amount: int
    amount_inr: float
    failure_source: str
    failure_reason: str
    recovery_strategy: Optional[str] = None
    state: str
    risk_level: str
    created_at: datetime
    updated_at: datetime


class CaseDetailResponse(BaseModel):
    """Comprehensive detail schema for the Case Detail workspace."""
    id: str
    case_number: str
    state: str
    risk_level: str
    amount: int
    amount_inr: float
    failure_source: str
    failure_reason: str
    recovery_strategy: Optional[str] = None
    invoice_reference: Optional[str] = None
    action_count: int
    human_intervention_count: int
    created_at: datetime
    updated_at: datetime
    vendor: Optional[Dict[str, Any]] = None
    payout: Optional[Dict[str, Any]] = None
    approval: Optional[Dict[str, Any]] = None
    audit_verification: Dict[str, Any]


# ─────────────────────────────────────────────────────────────────────────────
# 1. POST /cases/{case_id}/approve — Human Payout Authorization Gate (Level 3)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{case_id}/approve", response_model=ApprovalActionResponse, status_code=status.HTTP_200_OK)
def approve_case_payout(
    case_id: str,
    request: ApproveCaseRequest = ApproveCaseRequest(),
    db: Session = Depends(get_db),
):
    """
    Executes human authorization for a staged payout.
    
    1. Validates that the case is in the HUMAN_APPROVAL state.
    2. Validates that a pending Approval record exists.
    3. Triggers Level 3 create_payout via Razorpay with is_human_authorized=True.
    4. Updates Approval entity with decision=APPROVE.
    5. Transitions case state to PAYOUT_EXECUTED.
    6. Logs HUMAN_DECISION in the cryptographic audit ledger.
    """
    case = db.query(RecoveryCaseModel).filter(RecoveryCaseModel.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recovery case '{case_id}' not found.",
        )

    # State machine gate: Only cases currently staged at HUMAN_APPROVAL can be approved
    if case.state != CaseState.HUMAN_APPROVAL and case.state != CaseState.HUMAN_APPROVAL.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot approve case '{case_id}'. Case is currently in '{case.state}', "
                f"but must be in '{CaseState.HUMAN_APPROVAL.value}'."
            ),
        )

    # Find pending approval record
    approval = (
        db.query(Approval)
        .filter(Approval.case_id == case.id)
        .order_by(Approval.requested_at.desc())
        .first()
    )
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Approval staging record found for case '{case_id}'.",
        )

    payload = approval.payload or {}
    new_fa_id = payload.get("new_fund_account_id")
    amount = payload.get("amount_paise") or case.amount

    if not new_fa_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing replacement fund_account_id in staged approval record.",
        )

    # Look up business account number (from settings or fallback)
    business_acc = getattr(settings, "RAZORPAY_ACCOUNT_NUMBER", "") or "2323230099887766"

    # 1. Execute Level 3 Financially Consequential Payout via Razorpay API
    payout_res = razorpay_client.create_payout(
        account_number=business_acc,
        fund_account_id=new_fa_id,
        amount=amount,
        currency="INR",
        mode="NEFT",
        purpose="vendor_payout",
        reference_id=case.invoice_reference or f"REC-{case.id[:8]}",
        narration=f"Recovery for {case.case_number}",
        case_id=case.id,
        db=db,
        is_human_authorized=True,
        approved_by=request.decided_by,
    )

    # 2. Persist new Payout entity in database
    new_payout = Payout(
        id=f"pout_rep_{uuid.uuid4().hex[:8]}",
        razorpay_payout_id=payout_res.id,
        razorpay_fund_account_id=new_fa_id,
        razorpay_contact_id=payload.get("contact_id") or (case.vendor_id or "cont_unknown"),
        amount=amount,
        currency="INR",
        mode="NEFT",
        reference_id=case.invoice_reference,
        status="processing",
    )
    db.add(new_payout)

    # 3. Update Approval entity
    approval.decision = ApprovalDecision.APPROVE.value
    approval.decided_at = datetime.now()
    approval.decided_by = request.decided_by
    if request.notes:
        approval.rejection_reason = request.notes

    # 4. State machine transition: HUMAN_APPROVAL -> PAYOUT_EXECUTED -> CASE_RESOLVED
    case.state = CaseState.CASE_RESOLVED.value if hasattr(CaseState.CASE_RESOLVED, "value") else "CASE_RESOLVED"
    case.action_count = (case.action_count or 0) + 1
    case.human_intervention_count = (case.human_intervention_count or 0) + 1
    case.resolved_at = datetime.now()
    db.commit()
    db.refresh(case)

    # 5. Log operational action
    action_rec = AgentAction(
        id=str(uuid.uuid4()),
        case_id=case.id,
        tool_name="approve_payout",
        actor=request.decided_by,
        input_payload={"case_id": case.id, "decided_by": request.decided_by, "notes": request.notes},
        output_payload={"payout_id": payout_res.id, "amount": amount, "fund_account_id": new_fa_id},
        policy_level=PolicyLevel.FINANCIALLY_CONSEQUENTIAL.value,
        policy_decision=PolicyDecision.ALLOW.value,
    )
    db.add(action_rec)
    db.commit()

    # 6. Cryptographic Audit Event (HUMAN_DECISION & RESOLUTION)
    log_audit_event(
        db=db,
        case_id=case.id,
        event_type=AuditActorType.HUMAN_DECISION,
        actor=request.decided_by,
        action="APPROVE_REPLACEMENT_PAYOUT",
        target=payout_res.id,
        reason=request.notes or "Finance controller approved replacement payout.",
        input_data={"approval_id": approval.id, "decided_by": request.decided_by},
        output_data={
            "payout_id": payout_res.id,
            "new_state": "CASE_RESOLVED",
            "amount_paise": amount,
        },
        approval_required=True,
    )

    return ApprovalActionResponse(
        case_id=case.id,
        case_number=case.case_number,
        decision="APPROVE",
        state="CASE_RESOLVED",
        payout_id=payout_res.id,
        message=f"Replacement payout {payout_res.id} authorized and disbursed. Case marked as CASE_RESOLVED.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. POST /cases/{case_id}/reject — Human Rejection Gate
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{case_id}/reject", response_model=ApprovalActionResponse, status_code=status.HTTP_200_OK)
def reject_case_payout(
    case_id: str,
    request: RejectCaseRequest,
    db: Session = Depends(get_db),
):
    """
    Executes human controller rejection of the proposed recovery.
    
    1. Validates that the case is in HUMAN_APPROVAL or HUMAN_REVIEW.
    2. Updates Approval entity with decision=REJECT and rejection reason.
    3. Transitions case state to terminal BLOCKED state.
    4. Logs HUMAN_DECISION in the cryptographic audit ledger.
    """
    case = db.query(RecoveryCaseModel).filter(RecoveryCaseModel.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recovery case '{case_id}' not found.",
        )

    valid_states = {CaseState.HUMAN_APPROVAL, CaseState.HUMAN_REVIEW}
    case_st_enum = CaseState(case.state) if isinstance(case.state, str) else case.state
    if case_st_enum not in valid_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot reject case '{case_id}'. Case is currently in '{case.state}', "
                f"expected HUMAN_APPROVAL or HUMAN_REVIEW."
            ),
        )

    if not request.reason or not request.reason.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A non-empty rejection reason must be provided.",
        )

    # Update latest approval record if present
    approval = (
        db.query(Approval)
        .filter(Approval.case_id == case.id)
        .order_by(Approval.requested_at.desc())
        .first()
    )
    if approval:
        approval.decision = ApprovalDecision.REJECT.value
        approval.rejection_reason = request.reason
        approval.decided_at = datetime.now()
        approval.decided_by = request.decided_by

    # Transition to BLOCKED
    next_st = transition_state(case_st_enum, CaseState.BLOCKED)
    case.state = next_st
    case.human_intervention_count = (case.human_intervention_count or 0) + 1
    case.resolved_at = datetime.now()
    db.commit()
    db.refresh(case)

    # Cryptographic audit event
    log_audit_event(
        db=db,
        case_id=case.id,
        event_type=AuditActorType.HUMAN_DECISION,
        actor=request.decided_by,
        action="REJECT_RECOVERY_PROPOSAL",
        target=case.id,
        reason=request.reason,
        input_data={"decided_by": request.decided_by, "reason": request.reason},
        output_data={"new_state": CaseState.BLOCKED.value},
        approval_required=True,
    )

    return ApprovalActionResponse(
        case_id=case.id,
        case_number=case.case_number,
        decision="REJECT",
        state=case.state if isinstance(case.state, str) else case.state.value,
        payout_id=None,
        message=f"Case {case.case_number} rejected and permanently BLOCKED. Reason: {request.reason}",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. GET /cases/{case_id} — Case Detail Workspace
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{case_id}", response_model=CaseDetailResponse, status_code=status.HTTP_200_OK)
def get_case_detail(
    case_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieves full case details including vendor context, original payout details,
    approval status, and cryptographic audit ledger verification.
    """
    case = db.query(RecoveryCaseModel).filter(RecoveryCaseModel.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recovery case '{case_id}' not found.",
        )

    vendor = db.query(Vendor).filter(Vendor.id == case.vendor_id).first() if case.vendor_id else None
    payout = db.query(Payout).filter(Payout.id == case.payout_id).first() if case.payout_id else None
    approval = (
        db.query(Approval)
        .filter(Approval.case_id == case.id)
        .order_by(Approval.requested_at.desc())
        .first()
    )

    audit_check = verify_chain(db, case.id)

    state_val = case.state if isinstance(case.state, str) else case.state.value

    return CaseDetailResponse(
        id=case.id,
        case_number=case.case_number,
        state=state_val,
        risk_level=case.risk_level if isinstance(case.risk_level, str) else case.risk_level.value,
        amount=case.amount,
        amount_inr=case.amount / 100.0,
        failure_source=case.failure_source,
        failure_reason=case.failure_reason,
        recovery_strategy=case.recovery_strategy,
        invoice_reference=case.invoice_reference,
        action_count=case.action_count or 0,
        human_intervention_count=case.human_intervention_count or 0,
        created_at=case.created_at,
        updated_at=case.updated_at,
        vendor={
            "id": vendor.id,
            "name": vendor.name,
            "email": vendor.email,
            "phone": vendor.phone,
            "zoho_vendor_id": vendor.zoho_vendor_id,
        } if vendor else None,
        payout={
            "id": payout.id,
            "razorpay_payout_id": payout.razorpay_payout_id,
            "amount": payout.amount,
            "currency": payout.currency,
            "status": payout.status,
            "mode": payout.mode,
        } if payout else None,
        approval={
            "id": approval.id,
            "action": approval.action,
            "status": approval.status,
            "decision": approval.decision,
            "requested_at": approval.requested_at,
            "decided_at": approval.decided_at,
            "decided_by": approval.decided_by,
            "payload": approval.payload,
        } if approval else None,
        audit_verification={
            "status": audit_check.status,
            "is_valid": audit_check.is_valid,
            "total_events": audit_check.total_events,
            "details": audit_check.details,
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. GET /cases — Paginated Case List
# ─────────────────────────────────────────────────────────────────────────────

@router.get("", response_model=List[CaseListItemResponse], status_code=status.HTTP_200_OK)
def list_cases(
    state: Optional[str] = Query(None, description="Filter by CaseState"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Returns a paginated list of recovery cases, optionally filtered by state.
    """
    query = db.query(RecoveryCaseModel)
    if state:
        query = query.filter(RecoveryCaseModel.state == state)

    cases = query.order_by(RecoveryCaseModel.created_at.desc()).offset(offset).limit(limit).all()

    out = []
    for c in cases:
        vendor = db.query(Vendor).filter(Vendor.id == c.vendor_id).first() if c.vendor_id else None
        state_val = c.state if isinstance(c.state, str) else c.state.value
        risk_val = c.risk_level if isinstance(c.risk_level, str) else c.risk_level.value
        out.append(
            CaseListItemResponse(
                id=c.id,
                case_number=c.case_number,
                payout_id=c.payout_id,
                vendor_id=c.vendor_id,
                vendor_name=vendor.name if vendor else None,
                amount=c.amount,
                amount_inr=c.amount / 100.0,
                failure_source=c.failure_source,
                failure_reason=c.failure_reason,
                recovery_strategy=c.recovery_strategy,
                state=state_val,
                risk_level=risk_val,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
        )
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 5. POST /cases/{case_id}/process — Trigger Agent Reasoning Step
# ─────────────────────────────────────────────────────────────────────────────

class ProcessCaseRequest(BaseModel):
    """Payload for advancing agent reasoning for a case."""
    model_config = ConfigDict(extra="ignore")
    vendor_reply: Optional[str] = Field(None, description="Optional vendor response text to process")
    single_step: bool = Field(default=False, description="Whether to execute only a single state transition")


@router.post("/{case_id}/process", response_model=CaseDetailResponse, status_code=status.HTTP_200_OK)
def process_case_agent(
    case_id: str,
    request: ProcessCaseRequest = ProcessCaseRequest(),
    db: Session = Depends(get_db),
):
    """
    Executes autonomous reasoning turns for the specified case using AgentOrchestrator.
    """
    case = db.query(RecoveryCaseModel).filter(RecoveryCaseModel.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recovery case '{case_id}' not found.",
        )

    run_agent_for_case(
        case_id=case.id,
        db=db,
        vendor_reply_text=request.vendor_reply,
        single_step=request.single_step,
    )
    db.refresh(case)

    return get_case_detail(case_id=case.id, db=db)


@router.post("/{case_id}/step", response_model=CaseDetailResponse, status_code=status.HTTP_200_OK)
def step_case_agent(
    case_id: str,
    request: ProcessCaseRequest = ProcessCaseRequest(),
    db: Session = Depends(get_db),
):
    """
    Executes exactly one autonomous reasoning step for the specified case.
    """
    case = db.query(RecoveryCaseModel).filter(RecoveryCaseModel.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recovery case '{case_id}' not found.",
        )

    run_agent_for_case(
        case_id=case.id,
        db=db,
        vendor_reply_text=request.vendor_reply,
        single_step=True,
    )
    db.refresh(case)

    return get_case_detail(case_id=case.id, db=db)


# ─────────────────────────────────────────────────────────────────────────────
# 6. POST /cases/simulate — Seed and Ingest a Simulated Exception Case
# ─────────────────────────────────────────────────────────────────────────────

class SimulateCaseRequest(BaseModel):
    """Payload for simulating a new failed payout exception case in the live dashboard."""
    model_config = ConfigDict(extra="ignore")
    vendor_name: str = Field(default="Acme Industrial Supplies Pvt Ltd")
    contact_id: Optional[str] = Field(default=None, description="Optional live Razorpay contact ID (e.g. cont_TY3jX5qQmhCpa8)")
    zoho_vendor_id: Optional[str] = Field(default=None, description="Optional live Zoho vendor ID (e.g. VEND-ACME-8801)")
    amount: int = Field(default=20000000, description="Amount in paise (default: INR 2,00,000)")
    failure_source: str = Field(default="beneficiary_bank")
    failure_reason: str = Field(default="invalid_ifsc_code")
    invoice_reference: str = Field(default="INV-2026-9021")
    auto_run_turn1: bool = Field(default=False, description="Whether to automatically run agent reasoning turn 1 (defaults to false for live watch)")


@router.post("/simulate", response_model=CaseDetailResponse, status_code=status.HTTP_201_CREATED)
def simulate_new_exception_case(
    request: SimulateCaseRequest = SimulateCaseRequest(),
    db: Session = Depends(get_db),
):
    """
    Simulates the occurrence of a payout exception, inserting vendor, payout,
    and recovery_case records, and initializing the audit chain.
    """
    # 1. Create or fetch vendor
    unique_suffix = uuid.uuid4().hex[:6]
    contact_id = request.contact_id or f"cont_sim_{unique_suffix}"
    zoho_vendor_id = request.zoho_vendor_id or f"zoho_vend_{unique_suffix}"
    
    vendor = Vendor(
        id=f"vend_{unique_suffix}",
        razorpay_contact_id=contact_id,
        zoho_vendor_id=zoho_vendor_id,
        name=request.vendor_name,
        email=f"accounts@{request.vendor_name.lower().replace(' ', '').replace('.', '')[:15]}.com",
        phone="+919876543210",
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    # 2. Create payout
    payout_id = f"pout_{unique_suffix}"
    payout = Payout(
        id=f"pout_rec_{unique_suffix}",
        razorpay_payout_id=payout_id,
        razorpay_fund_account_id=f"fa_old_{unique_suffix}",
        razorpay_contact_id=contact_id,
        amount=request.amount,
        currency="INR",
        mode="NEFT",
        reference_id=request.invoice_reference,
        status="failed",
        status_source=request.failure_source,
        status_reason=request.failure_reason,
        status_description=f"Simulated failure: {request.failure_reason}",
    )
    db.add(payout)
    db.commit()
    db.refresh(payout)

    # 3. Classify failure
    classification = classify_failure(request.failure_source, request.failure_reason)

    # 4. Create Recovery Case
    case_number = f"CASE-{datetime.now().strftime('%Y%m%d')}-{unique_suffix.upper()}"
    case = RecoveryCaseModel(
        id=f"case_{unique_suffix}",
        case_number=case_number,
        payout_id=payout.id,
        vendor_id=vendor.id,
        invoice_reference=request.invoice_reference,
        amount=request.amount,
        failure_source=request.failure_source,
        failure_reason=request.failure_reason,
        recovery_strategy=classification.strategy.value,
        state=CaseState.CASE_CREATED,
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    # 5. Genesis audit event
    log_audit_event(
        db=db,
        case_id=case.id,
        event_type=AuditActorType.EXTERNAL_FACT,
        actor="razorpay_webhook",
        action="PAYOUT_FAILED_WEBHOOK_RECEIVED",
        target=payout.razorpay_payout_id,
        reason=f"Payout failed due to {request.failure_reason}",
        input_data={"amount": request.amount, "source": request.failure_source, "reason": request.failure_reason},
        output_data={"case_number": case.case_number, "strategy": classification.strategy.value},
    )
    db.commit()

    # 6. Optionally run turn 1
    if request.auto_run_turn1:
        run_agent_for_case(case_id=case.id, db=db)
        db.refresh(case)

    return get_case_detail(case_id=case.id, db=db)


# ─────────────────────────────────────────────────────────────────────────────
# 7. POST /cases/reset — Clean Slate Demo Reset
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/reset", status_code=status.HTTP_200_OK)
def reset_all_cases(db: Session = Depends(get_db)):
    """
    Clears all simulated cases, approvals, audit events, fund accounts, and vendor messages,
    restoring a completely clean slate for fresh demos.
    """
    from app.models.vendor_message import VendorMessage
    from app.models.agent_action import AgentAction
    from app.models.audit_event import AuditEvent
    from app.models.fund_account import FundAccount

    try:
        db.query(Approval).delete()
        db.query(AgentAction).delete()
        db.query(VendorMessage).delete()
        db.query(AuditEvent).delete()
        db.query(FundAccount).delete()
        db.query(RecoveryCaseModel).delete()
        db.query(Payout).delete()
        db.query(Vendor).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset database: {str(e)}",
        )

    return {"status": "success", "message": "All cases and telemetry reset successfully."}

