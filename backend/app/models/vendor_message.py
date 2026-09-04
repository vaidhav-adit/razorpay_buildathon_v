"""
models/vendor_message.py
────────────────────────
Records every message exchanged between the agent and the vendor.

OUTBOUND: messages the agent sends to the vendor requesting information.
INBOUND:  messages (or simulated responses) received from the vendor.

The extracted_data field stores the structured banking data the LLM parsed
out of an inbound message (account number, IFSC, account holder name). This
is a JSON column so we can store arbitrary extracted fields.

In the demo, inbound messages come from the Vendor Chat Simulator (the WhatsApp
panel in the dashboard). In production, they would come from WhatsApp Business API.
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, JSON, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import MessageDirection


class VendorMessage(Base):
    __tablename__ = "vendor_messages"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # ── Foreign keys ──────────────────────────────────────────────────────────
    case_id: Mapped[str] = mapped_column(
        String, ForeignKey("recovery_cases.id"), nullable=False, index=True
    )

    vendor_id: Mapped[str] = mapped_column(
        String, ForeignKey("vendors.id"), nullable=False
    )

    # ── Message details ───────────────────────────────────────────────────────
    # INBOUND (vendor -> agent) or OUTBOUND (agent -> vendor)
    direction: Mapped[str] = mapped_column(String, nullable=False)

    # The full message text
    body: Mapped[str] = mapped_column(Text, nullable=False)

    # Structured data extracted by the LLM from an INBOUND message.
    # Example: {"account_number": "...9876", "ifsc": "ICIC0001234", "account_holder_name": "..."}
    # None for OUTBOUND messages or INBOUND messages that were not yet parsed.
    extracted_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    case: Mapped["RecoveryCaseModel"] = relationship(
        "RecoveryCaseModel", back_populates="messages"
    )
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="messages")

    def __repr__(self) -> str:
        return (
            f"<VendorMessage case={self.case_id} "
            f"direction={self.direction!r} len={len(self.body)}>"
        )
