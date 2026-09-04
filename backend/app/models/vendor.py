"""
models/vendor.py
────────────────
Represents a vendor (payee/beneficiary) in our system.

A vendor maps to:
  - A Razorpay Contact (cont_xxx) on the payments side
  - A Zoho Books Contact/Vendor on the ERP side

The same real-world company has identities in both systems.
We keep them linked here so the agent can look up both from one record.
"""

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Vendor(Base):
    __tablename__ = "vendors"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # ── External system identifiers ───────────────────────────────────────────
    # Razorpay contact ID (cont_xxxx) — set when the contact exists in Razorpay
    razorpay_contact_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    # Zoho Books vendor/contact ID — set when vendor is looked up in Zoho
    zoho_vendor_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    # ── Vendor details ────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    # server_default uses the DB clock so timestamps are consistent
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    # back_populates must match the attribute name on the other model
    recovery_cases: Mapped[list["RecoveryCaseModel"]] = relationship(
        "RecoveryCaseModel", back_populates="vendor"
    )
    fund_accounts: Mapped[list["FundAccount"]] = relationship(
        "FundAccount", back_populates="vendor"
    )
    messages: Mapped[list["VendorMessage"]] = relationship(
        "VendorMessage", back_populates="vendor"
    )

    def __repr__(self) -> str:
        return f"<Vendor id={self.id} name={self.name!r}>"
