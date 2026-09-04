"""
models/audit_event.py
─────────────────────
The cryptographic audit ledger — the most important table in the system.

Every consequential action produces an append-only audit event. Events are
chained using SHA-256: each event's hash includes the previous event's hash,
forming a tamper-evident chain. Modifying any event breaks all subsequent hashes.

Design:
  - Events are NEVER updated or deleted — the table is append-only.
  - The event_hash column is computed by the application, not the database.
  - The previous_hash of the first event in a case is an empty string.
  - The verify_chain() function in the audit service walks all events for
    a case in timestamp order and recomputes each hash to verify integrity.

Actor types (from AuditActorType enum):
  - EXTERNAL_FACT:  something Razorpay or the banking system told us
  - AI_DECISION:    something the LLM classified or recommended
  - SYSTEM_ACTION:  an API call or state transition our code made
  - HUMAN_DECISION: a human approved, rejected, or overrode something

The input_hash and output_hash columns store SHA-256 hashes of the raw
input and output payloads — not the payloads themselves — to keep the
audit table lean while still being verifiable.
"""

import uuid
import time
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def generate_audit_id() -> str:
    """Generate a monotonically sortable unique ID for audit ledger events."""
    now_ns = time.time_ns()
    return f"{now_ns:020d}_{uuid.uuid4().hex[:8]}"


class AuditEvent(Base):
    __tablename__ = "audit_events"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=generate_audit_id
    )

    # ── Foreign key ───────────────────────────────────────────────────────────
    case_id: Mapped[str] = mapped_column(
        String, ForeignKey("recovery_cases.id"), nullable=False, index=True
    )

    # ── Event classification ──────────────────────────────────────────────────
    # One of: EXTERNAL_FACT, AI_DECISION, SYSTEM_ACTION, HUMAN_DECISION
    event_type: Mapped[str] = mapped_column(String, nullable=False)

    # Who or what produced this event (e.g. "razorpay", "payout_recovery_agent", "finance_controller")
    actor: Mapped[str] = mapped_column(String, nullable=False)

    # What happened (e.g. "CREATE_FUND_ACCOUNT", "PAYOUT_FAILED", "APPROVE_PAYOUT")
    action: Mapped[str] = mapped_column(String, nullable=False)

    # The entity affected (e.g. "fa_789", "pout_123"). Optional for events with no target.
    target: Mapped[str | None] = mapped_column(String, nullable=True)

    # Human-readable explanation of why this action was taken
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Payload fingerprints ──────────────────────────────────────────────────
    # SHA-256 hash of the input data. Verifiable but does not expose the raw data.
    input_hash: Mapped[str | None] = mapped_column(String, nullable=True)

    # SHA-256 hash of the output/result data.
    output_hash: Mapped[str | None] = mapped_column(String, nullable=True)

    # Whether this action required human approval before it could execute
    approval_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Hash chain ────────────────────────────────────────────────────────────
    # Hash of the immediately preceding event for this case (empty string for the first event)
    previous_hash: Mapped[str] = mapped_column(String, nullable=False, default="")

    # SHA-256(event_id + case_id + event_type + actor + action + target +
    #          reason + input_hash + output_hash + previous_hash + timestamp)
    # Computed and stored by the application at event creation time.
    event_hash: Mapped[str] = mapped_column(String, nullable=False)

    # ── Timestamp ─────────────────────────────────────────────────────────────
    # The DB clock is used for consistency — application timestamps can drift
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    case: Mapped["RecoveryCaseModel"] = relationship(
        "RecoveryCaseModel", back_populates="audit_events"
    )

    def __repr__(self) -> str:
        return (
            f"<AuditEvent case={self.case_id} actor={self.actor!r} "
            f"action={self.action!r}>"
        )
