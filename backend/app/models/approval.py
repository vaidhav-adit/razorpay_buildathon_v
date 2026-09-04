"""
models/approval.py
──────────────────
Records human approval requests and decisions.

When the policy engine returns REQUIRE_APPROVAL for an agent action, the system
creates an Approval record and surfaces it in the dashboard for the finance
controller to act on. The agent is paused until a decision is made.

The payload field stores everything the human needs to make an informed decision:
the full recovery summary, validation results, old and new fund account details,
ERP status, etc. This is what populates the floating approval card in the UI.

Only Level 3 (financially consequential) actions always require approval.
Level 2 actions may require approval depending on policy configuration.
"""

import uuid
from datetime import datetime

from sqlalchemy import String, JSON, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import ApprovalDecision


class Approval(Base):
    __tablename__ = "approvals"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # ── Foreign key ───────────────────────────────────────────────────────────
    case_id: Mapped[str] = mapped_column(
        String, ForeignKey("recovery_cases.id"), nullable=False, index=True
    )

    # ── What is being approved ────────────────────────────────────────────────
    # Human-readable description of what action requires approval
    action_description: Mapped[str] = mapped_column(String, nullable=False)

    # Full context for the approver — populated from case, payout, vendor, validation
    # This is what the dashboard approval card displays
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    # ── Decision ──────────────────────────────────────────────────────────────
    # When the approval request was created and surfaced to the UI
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # When the human made their decision (None if still pending)
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Name or email of the person who decided (from session/auth, Phase 13+)
    decided_by: Mapped[str | None] = mapped_column(String, nullable=True)

    # APPROVE or REJECT (None if still pending)
    decision: Mapped[str | None] = mapped_column(String, nullable=True)

    # Required if decision is REJECT — the human must provide a reason
    rejection_reason: Mapped[str | None] = mapped_column(String, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    case: Mapped["RecoveryCaseModel"] = relationship(
        "RecoveryCaseModel", back_populates="approvals"
    )

    def __repr__(self) -> str:
        return (
            f"<Approval case={self.case_id} "
            f"decision={self.decision!r} pending={self.decided_at is None}>"
        )
