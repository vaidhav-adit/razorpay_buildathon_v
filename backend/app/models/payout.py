"""
models/payout.py
────────────────
Records a Razorpay payout that has entered our system.

We only create a payout record when Razorpay sends us a payout.failed or
payout.reversed webhook — we are not tracking successful payouts (those are
Razorpay's concern). This table is the entry point for the entire recovery flow.

Amount is stored in the smallest currency unit (paise for INR) to avoid
floating-point arithmetic issues — never store money as a float.
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import PayoutStatus


class Payout(Base):
    __tablename__ = "payouts"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # ── Razorpay identifiers ──────────────────────────────────────────────────
    # The Razorpay payout ID (pout_xxxx) — unique across Razorpay
    razorpay_payout_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)

    # The fund account used for this payout (fa_xxxx)
    razorpay_fund_account_id: Mapped[str] = mapped_column(String, nullable=False)

    # The contact associated with this payout (cont_xxxx)
    razorpay_contact_id: Mapped[str] = mapped_column(String, nullable=False)

    # ── Payment details ───────────────────────────────────────────────────────
    # Amount in paise (1 INR = 100 paise) — integer to avoid float precision issues
    amount: Mapped[int] = mapped_column(Integer, nullable=False)

    currency: Mapped[str] = mapped_column(String, default="INR", nullable=False)

    # Payment mode: IMPS, NEFT, RTGS, UPI, etc.
    mode: Mapped[str | None] = mapped_column(String, nullable=True)

    # Reference ID provided when the payout was created (usually an invoice ID)
    reference_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    # ── Failure details (from Razorpay status_details) ───────────────────────
    status: Mapped[str] = mapped_column(String, nullable=False)  # e.g. "failed"

    # Source of the failure: beneficiary_bank, business, gateway
    status_source: Mapped[str | None] = mapped_column(String, nullable=True)

    # Machine-readable reason code: invalid_ifsc_code, insufficient_funds, etc.
    status_reason: Mapped[str | None] = mapped_column(String, nullable=True)

    # Human-readable description from Razorpay
    status_description: Mapped[str | None] = mapped_column(String, nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    # When Razorpay says the payout was created (from webhook payload)
    razorpay_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # When our system first recorded this payout
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    recovery_cases: Mapped[list["RecoveryCaseModel"]] = relationship(
        "RecoveryCaseModel", back_populates="payout"
    )

    def __repr__(self) -> str:
        return (
            f"<Payout razorpay_id={self.razorpay_payout_id!r} "
            f"amount={self.amount} status={self.status!r}>"
        )
