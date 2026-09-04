"""
models/agent_action.py
──────────────────────
Records every tool call the agent makes during a recovery case.

This is a detailed operational log — separate from the audit ledger. The audit
ledger (audit_events) is the tamper-evident cryptographic chain for compliance.
This table is the raw agent activity log for debugging and transparency.

Every tool call goes through the policy engine. The policy_level and
policy_decision columns record exactly what the policy engine decided before
the tool was allowed to execute.
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Integer, JSON, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import PolicyLevel, PolicyDecision


class AgentAction(Base):
    __tablename__ = "agent_actions"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # ── Foreign key ───────────────────────────────────────────────────────────
    case_id: Mapped[str] = mapped_column(
        String, ForeignKey("recovery_cases.id"), nullable=False, index=True
    )

    # ── Tool call details ─────────────────────────────────────────────────────
    # Name of the tool the agent called (e.g. "create_fund_account")
    tool_name: Mapped[str] = mapped_column(String, nullable=False)

    # The actor — almost always "payout_recovery_agent"
    actor: Mapped[str] = mapped_column(
        String, nullable=False, default="payout_recovery_agent"
    )

    # The arguments the agent passed to the tool (as JSON)
    input_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # The result the tool returned (as JSON). None if the tool was blocked.
    output_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # ── Policy engine result ──────────────────────────────────────────────────
    # The authority level of this tool (1=autonomous, 2=controlled, 3=financial)
    policy_level: Mapped[int] = mapped_column(Integer, nullable=False)

    # What the policy engine decided: ALLOW, REQUIRE_APPROVAL, or BLOCK
    policy_decision: Mapped[str] = mapped_column(String, nullable=False)

    # ── Timestamps ────────────────────────────────────────────────────────────
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    case: Mapped["RecoveryCaseModel"] = relationship(
        "RecoveryCaseModel", back_populates="agent_actions"
    )

    def __repr__(self) -> str:
        return (
            f"<AgentAction case={self.case_id} tool={self.tool_name!r} "
            f"decision={self.policy_decision!r}>"
        )
