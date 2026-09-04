"""
audit.py
────────
Cryptographic Audit Ledger service for the RazorpayX Resolution Agent.

This module provides tamper-evident audit logging using SHA-256 hash chaining.
Every consequential state transition, API call, AI reasoning step, and human decision
produces an append-only AuditEvent.

Foundational Architectural Principles:
1. Tamper-Evident Ledger: Each event's hash cryptographically chains to the previous event's hash.
2. Immutability: Events are strictly append-only. Modifying any past event invalidates the hash chain
   for all subsequent events.
3. Zero Secrets in Hashes: Hashes store mathematical fingerprints of input/output data rather than
   raw confidential banking payloads.
"""

import json
import hashlib
from typing import Any, Optional, List, Dict
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.enums import AuditActorType
from app.models.audit_event import AuditEvent


class ChainVerificationResult(BaseModel):
    """
    Result returned by the audit ledger verification engine.
    
    Attributes:
        status: 'VERIFIED', 'TAMPERED', or 'EMPTY'.
        is_valid: Boolean indicating whether the ledger is mathematically sound.
        total_events: Number of audit events inspected in the chain.
        broken_at_index: Index of the first tampered event (None if verified).
        broken_event_id: Database ID of the first tampered event (None if verified).
        details: Human-readable diagnostic description of the verification status.
    """
    status: str
    is_valid: bool
    total_events: int
    broken_at_index: Optional[int] = None
    broken_event_id: Optional[str] = None
    details: str


def compute_payload_hash(data: Any) -> Optional[str]:
    """
    Computes a deterministic SHA-256 hash of arbitrary input or output data.
    
    If data is a dict or list, it is serialized to JSON with sorted keys to ensure
    identical hashes regardless of key ordering.
    
    Args:
        data: Any serializable object, dictionary, string, or None.
        
    Returns:
        Optional[str]: Hexadecimal SHA-256 digest string, or None if data is empty.
    """
    if data is None:
        return None

    if isinstance(data, (dict, list)):
        serialized = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    else:
        serialized = str(data)

    if not serialized.strip():
        return None

    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_event_hash(
    case_id: str,
    event_type: str,
    actor: str,
    action: str,
    target: Optional[str],
    reason: Optional[str],
    input_hash: Optional[str],
    output_hash: Optional[str],
    approval_required: bool,
    previous_hash: str,
) -> str:
    """
    Computes the canonical SHA-256 event hash by chaining previous_hash with all event fields.
    
    Canonical format:
    SHA256(case_id|event_type|actor|action|target|reason|input_hash|output_hash|approval_required|previous_hash)
    
    Args:
        case_id: ID of the recovery case.
        event_type: Actor type (EXTERNAL_FACT, AI_DECISION, SYSTEM_ACTION, HUMAN_DECISION).
        actor: Identifier of the component or user taking the action.
        action: Name of the action taken.
        target: Optional identifier of the entity affected.
        reason: Optional justification for the action.
        input_hash: SHA-256 hash of input data.
        output_hash: SHA-256 hash of output data.
        approval_required: Whether human approval was required.
        previous_hash: SHA-256 hash of the previous event (empty string for genesis block).
        
    Returns:
        str: Hexadecimal SHA-256 digest representing this block in the chain.
    """
    canonical_string = "|".join([
        str(case_id),
        str(event_type),
        str(actor),
        str(action),
        str(target or ""),
        str(reason or ""),
        str(input_hash or ""),
        str(output_hash or ""),
        str(approval_required).lower(),
        str(previous_hash or ""),
    ])

    return hashlib.sha256(canonical_string.encode("utf-8")).hexdigest()


def log_audit_event(
    db: Session,
    case_id: str,
    event_type: AuditActorType | str,
    actor: str,
    action: str,
    target: Optional[str] = None,
    reason: Optional[str] = None,
    input_data: Any = None,
    output_data: Any = None,
    approval_required: bool = False,
) -> AuditEvent:
    """
    Appends a new cryptographically chained audit event to the ledger.
    
    1. Finds the most recent audit event for this case_id to retrieve previous_hash.
    2. Computes SHA-256 hashes of input and output data.
    3. Computes the current event_hash by incorporating previous_hash.
    4. Commits the record to the database.
    
    Args:
        db: SQLAlchemy database session.
        case_id: ID of the recovery case.
        event_type: Actor classification enum or string.
        actor: Name/identifier of the actor (e.g., 'razorpay_webhook', 'agent_policy_engine').
        action: Specific action performed (e.g., 'CLASSIFY_FAILURE', 'APPROVE_PAYOUT').
        target: Optional target entity ID.
        reason: Optional explanatory note.
        input_data: Raw input payload to be hashed.
        output_data: Raw output payload to be hashed.
        approval_required: Boolean flag for human authorization gate.
        
    Returns:
        AuditEvent: The committed database record with its generated event_hash.
    """
    type_str = event_type.value if hasattr(event_type, "value") else str(event_type)

    # 1. Retrieve the latest event in the chain for this case using monotonic ID ordering
    last_event = (
        db.query(AuditEvent)
        .filter(AuditEvent.case_id == case_id)
        .order_by(AuditEvent.id.desc())
        .first()
    )

    # First event in a case has an empty string as previous_hash (genesis block)
    previous_hash = last_event.event_hash if last_event else ""

    # 2. Compute payload hashes
    in_hash = compute_payload_hash(input_data)
    out_hash = compute_payload_hash(output_data)

    # 3. Compute the cryptographically linked event hash
    ev_hash = compute_event_hash(
        case_id=case_id,
        event_type=type_str,
        actor=actor,
        action=action,
        target=target,
        reason=reason,
        input_hash=in_hash,
        output_hash=out_hash,
        approval_required=approval_required,
        previous_hash=previous_hash,
    )

    # 4. Construct and commit the new audit event
    audit_record = AuditEvent(
        case_id=case_id,
        event_type=type_str,
        actor=actor,
        action=action,
        target=target,
        reason=reason,
        input_hash=in_hash,
        output_hash=out_hash,
        approval_required=approval_required,
        previous_hash=previous_hash,
        event_hash=ev_hash,
    )

    db.add(audit_record)
    db.commit()
    db.refresh(audit_record)

    return audit_record


def verify_events_chain(events: List[AuditEvent]) -> ChainVerificationResult:
    """
    Validates the cryptographic integrity of an ordered list of audit events.
    
    Verifies:
    1. The genesis event (index 0) has previous_hash == "".
    2. Every subsequent event i has previous_hash == events[i-1].event_hash.
    3. Every event's recomputed hash exactly matches its stored event_hash.
    
    Args:
        events: List of AuditEvent instances sorted in ascending chronological order.
        
    Returns:
        ChainVerificationResult: VERIFIED or TAMPERED with exact diagnosis.
    """
    if not events:
        return ChainVerificationResult(
            status="EMPTY",
            is_valid=True,
            total_events=0,
            details="No audit events recorded for this case.",
        )

    for i, event in enumerate(events):
        # 1. Verify previous_hash link
        if i == 0:
            if event.previous_hash != "":
                return ChainVerificationResult(
                    status="TAMPERED",
                    is_valid=False,
                    total_events=len(events),
                    broken_at_index=0,
                    broken_event_id=event.id,
                    details="Genesis event previous_hash is not empty.",
                )
        else:
            expected_prev_hash = events[i - 1].event_hash
            if event.previous_hash != expected_prev_hash:
                return ChainVerificationResult(
                    status="TAMPERED",
                    is_valid=False,
                    total_events=len(events),
                    broken_at_index=i,
                    broken_event_id=event.id,
                    details=(
                        f"Broken chain link at event index {i} (id={event.id}). "
                        f"Expected previous_hash='{expected_prev_hash}', found='{event.previous_hash}'."
                    ),
                )

        # 2. Recompute the event hash to detect payload/field tampering
        recomputed_hash = compute_event_hash(
            case_id=event.case_id,
            event_type=event.event_type,
            actor=event.actor,
            action=event.action,
            target=event.target,
            reason=event.reason,
            input_hash=event.input_hash,
            output_hash=event.output_hash,
            approval_required=event.approval_required,
            previous_hash=event.previous_hash,
        )

        if recomputed_hash != event.event_hash:
            return ChainVerificationResult(
                status="TAMPERED",
                is_valid=False,
                total_events=len(events),
                broken_at_index=i,
                broken_event_id=event.id,
                details=(
                    f"Tampered content at event index {i} (id={event.id}). "
                    f"Stored hash '{event.event_hash}' does not match recomputed hash '{recomputed_hash}'."
                ),
            )

    return ChainVerificationResult(
        status="VERIFIED",
        is_valid=True,
        total_events=len(events),
        details=f"All {len(events)} events in the cryptographic chain verified successfully.",
    )


def verify_chain(db: Session, case_id: str) -> ChainVerificationResult:
    """
    Queries all audit events for a case from the database and verifies chain integrity.
    
    Args:
        db: SQLAlchemy database session.
        case_id: ID of the recovery case.
        
    Returns:
        ChainVerificationResult: VERIFIED or TAMPERED with exact diagnosis.
    """
    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.case_id == case_id)
        .order_by(AuditEvent.id.asc())
        .all()
    )

    return verify_events_chain(events)
