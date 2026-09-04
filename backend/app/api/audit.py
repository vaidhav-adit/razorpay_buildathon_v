"""
api/audit.py
────────────
API router for the Cryptographic Audit Ledger.

Exposes:
  GET /cases/{case_id}/audit — returns all audit events for a recovery case
                               along with cryptographic chain verification status.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit_event import AuditEvent
from app.audit import verify_chain, ChainVerificationResult

router = APIRouter(prefix="/cases", tags=["Audit Ledger"])


class AuditEventResponse(BaseModel):
    """Schema representing a single audit ledger event."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    event_type: str
    actor: str
    action: str
    target: Optional[str] = None
    reason: Optional[str] = None
    input_hash: Optional[str] = None
    output_hash: Optional[str] = None
    approval_required: bool
    previous_hash: str
    event_hash: str
    timestamp: Optional[datetime] = None


class AuditChainResponse(BaseModel):
    """Schema representing the full audit chain and its cryptographic verification status."""
    case_id: str
    verification: ChainVerificationResult
    events: List[AuditEventResponse]


@router.get("/{case_id}/audit", response_model=AuditChainResponse)
def get_case_audit_trail(case_id: str, db: Session = Depends(get_db)):
    """
    Retrieve the complete tamper-evident audit trail for a recovery case.
    
    Walks all audit events for the given case_id in chronological order, verifies
    the cryptographic SHA-256 hash chain, and returns both the verification outcome
    and the event history.
    """
    # 1. Run cryptographic verification over the case's audit chain
    verification = verify_chain(db, case_id)

    # 2. Fetch all events for display
    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.case_id == case_id)
        .order_by(AuditEvent.id.asc())
        .all()
    )

    return AuditChainResponse(
        case_id=case_id,
        verification=verification,
        events=[AuditEventResponse.model_validate(ev) for ev in events],
    )
