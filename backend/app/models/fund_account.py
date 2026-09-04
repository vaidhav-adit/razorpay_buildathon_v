"""
models/fund_account.py
──────────────────────
Tracks Razorpay fund accounts (fa_xxxx) associated with a vendor/contact.

Key design points from the architecture:
  - Fund accounts in Razorpay are IMMUTABLE. You cannot edit the bank details
    of an existing fund account. The correct approach is to deactivate the old
    one and create a new one with corrected details.
  - We track both old and new fund accounts here. The old one is deactivated
    (is_active=False), the new one is active. The full history is preserved.
  - Account numbers are stored masked (last 4 digits only) for security.
  - is_simulated_validation flags accounts where the bank validation result
    came from our mock service rather than the real Razorpay API (Test Mode
    limitation). The UI displays a SIMULATED label for these.
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import ValidationStatus


class FundAccount(Base):
    __tablename__ = "fund_accounts"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # ── Razorpay identifiers ──────────────────────────────────────────────────
    # The Razorpay fund account ID (fa_xxxx) — unique in Razorpay
    razorpay_fund_account_id: Mapped[str] = mapped_column(
        String, unique=True, nullable=False, index=True
    )

    # The Razorpay contact (cont_xxxx) this fund account belongs to
    razorpay_contact_id: Mapped[str] = mapped_column(String, nullable=False)

    # ── Foreign keys ──────────────────────────────────────────────────────────
    vendor_id: Mapped[str] = mapped_column(
        String, ForeignKey("vendors.id"), nullable=False
    )

    # Which recovery case created or discovered this fund account
    recovery_case_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("recovery_cases.id"), nullable=True
    )

    # ── Bank details ──────────────────────────────────────────────────────────
    bank_name: Mapped[str | None] = mapped_column(String, nullable=True)

    # Masked account number — we store ONLY the last 4 digits (e.g. "XXXX9876")
    # Full account numbers must never be stored in our database
    account_number_masked: Mapped[str | None] = mapped_column(String, nullable=True)

    ifsc: Mapped[str | None] = mapped_column(String, nullable=True)

    account_holder_name: Mapped[str | None] = mapped_column(String, nullable=True)

    # ── Status ────────────────────────────────────────────────────────────────
    # Whether Razorpay considers this fund account active
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── Bank validation results ───────────────────────────────────────────────
    # Result of POST /v1/fund_accounts/validations
    validation_status: Mapped[str] = mapped_column(
        String, default=ValidationStatus.PENDING, nullable=False
    )

    # The registered account holder name returned by the bank validation API
    validated_name: Mapped[str | None] = mapped_column(String, nullable=True)

    # Name match score (0-100) from bank validation. Compared to MIN_NAME_MATCH_SCORE.
    name_match_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # True if the validation result came from our mock service (not real Razorpay API)
    # The UI must display "SIMULATED" when this is True
    is_simulated_validation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Set when deactivate_fund_account() is called
    deactivated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="fund_accounts")
    recovery_case: Mapped["RecoveryCaseModel | None"] = relationship(
        "RecoveryCaseModel", back_populates="fund_accounts"
    )

    def __repr__(self) -> str:
        return (
            f"<FundAccount razorpay_id={self.razorpay_fund_account_id!r} "
            f"active={self.is_active} ifsc={self.ifsc!r}>"
        )
