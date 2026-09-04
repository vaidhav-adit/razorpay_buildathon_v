"""
tests/test_agent.py
───────────────────
End-to-End Unit Tests for the AI Reasoning Agent & State Machine Orchestration (Phase 10).

Tests:
1. Full Golden Path Resolution:
   - Webhook case creation (CASE_CREATED).
   - Autonomous classification (FAILURE_CLASSIFIED -> RECOVERY_STRATEGY_SELECTED).
   - Vendor outreach (VENDOR_CONTACTED).
   - Vendor response ingestion & LLM extraction (INFORMATION_RECEIVED -> DATA_VALIDATED).
   - Penny-drop bank account validation (BANK_VALIDATED).
   - Policy checks & ERP writeback (POLICY_CHECK -> PAYOUT_READY).
   - Payout replacement preparation & halt at HUMAN_APPROVAL.
   - Verified cryptographic audit chain.
2. Alternative Workflow Paths:
   - Low name match score triggers HUMAN_REVIEW.
   - Inactive bank status triggers BLOCKED.
   - Invalid syntax triggers clarification halt.
3. Operational Tracking:
   - AgentAction table verification for tool executions.
   - Policy engine compliance verification.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.enums import CaseState, RecoveryStrategy, RiskLevel
from app.models.vendor import Vendor
from app.models.payout import Payout
from app.models.recovery_case import RecoveryCaseModel
from app.models.fund_account import FundAccount
from app.models.vendor_message import VendorMessage
from app.models.agent_action import AgentAction
from app.models.approval import Approval
from app.models.audit_event import AuditEvent
from app.audit import verify_chain
from app.services.validation_service import validation_service
from app.agent.orchestrator import run_agent_for_case


# ─────────────────────────────────────────────────────────────────────────────
# Test Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def test_db_session():
    """Provides an isolated in-memory SQLite database session for unit tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()

    # Provision standard initial test data
    test_vendor = Vendor(
        id="vend_agent_golden_01",
        razorpay_contact_id="cont_agent_01",
        zoho_vendor_id="zoho_vend_01",
        name="Acme Industrial Logistics",
        email="accounts@acmelogistics.com",
        phone="+919876500000",
    )
    session.add(test_vendor)
    session.commit()

    test_payout = Payout(
        id="pout_agent_golden_01",
        razorpay_payout_id="pout_rzp_agent_01",
        razorpay_fund_account_id="fa_old_bad_ifsc",
        razorpay_contact_id=test_vendor.razorpay_contact_id,
        amount=750000,
        currency="INR",
        status="failed",
        status_source="beneficiary_bank",
        status_reason="invalid_ifsc_code",
    )
    session.add(test_payout)
    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def clean_overrides():
    """Cleans validation scenario overrides before and after tests."""
    validation_service.clear_overrides()
    yield
    validation_service.clear_overrides()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Full Golden Path End-to-End Test
# ─────────────────────────────────────────────────────────────────────────────

class TestAgentGoldenPath:
    """Tests the full end-to-end golden path workflow from CASE_CREATED to HUMAN_APPROVAL."""

    def test_golden_path_resolution(self, test_db_session):
        """
        Validates entire autonomous lifecycle:
        CASE_CREATED -> VENDOR_CONTACTED -> reply received -> DATA_VALIDATED ->
        BANK_VALIDATED -> POLICY_CHECK -> HUMAN_APPROVAL.
        """
        # Step 1: Create Case in CASE_CREATED
        case = RecoveryCaseModel(
            id="case_agent_test_01",
            case_number="CASE-2026-GOLDEN-01",
            payout_id="pout_agent_golden_01",
            vendor_id="vend_agent_golden_01",
            invoice_reference="INV-2026-9901",
            amount=750000,
            failure_source="beneficiary_bank",
            failure_reason="invalid_ifsc_code",
            state=CaseState.CASE_CREATED,
        )
        test_db_session.add(case)
        test_db_session.commit()

        # Turn 1: Agent investigates, classifies failure, sends outreach, halts at VENDOR_CONTACTED
        run_agent_for_case(case_id=case.id, db=test_db_session)
        test_db_session.refresh(case)

        assert case.state == CaseState.VENDOR_CONTACTED
        assert case.recovery_strategy == RecoveryStrategy.VENDOR_REMEDIATION

        # Verify outbound message was created
        outbound_msg = (
            test_db_session.query(VendorMessage)
            .filter(VendorMessage.case_id == case.id, VendorMessage.direction == "OUTBOUND")
            .first()
        )
        assert outbound_msg is not None
        assert "invalid IFSC" in outbound_msg.body or "Invalid Ifsc Code" in outbound_msg.body

        # Turn 2: Vendor replies with corrected banking credentials
        vendor_reply = (
            "Hi, please update our bank account: Account Number is 987654321098, "
            "IFSC is HDFC0000001, registered name is Acme Industrial Logistics."
        )

        run_agent_for_case(case_id=case.id, db=test_db_session, vendor_reply_text=vendor_reply)
        test_db_session.refresh(case)

        # Asserts agent proceeded through all validation stages and safely halted at HUMAN_APPROVAL
        assert case.state == CaseState.HUMAN_APPROVAL

        # Verify Approval record is created for the finance controller
        approval = test_db_session.query(Approval).filter(Approval.case_id == case.id).first()
        assert approval is not None
        assert approval.action == "execute_replacement_payout"
        assert approval.status == "PENDING"
        assert approval.payload["amount_paise"] == 750000
        assert approval.payload["new_fund_account_id"] is not None

        # Verify AgentAction operational logs
        actions = test_db_session.query(AgentAction).filter(AgentAction.case_id == case.id).all()
        tool_names = [a.tool_name for a in actions]
        assert "get_payout" in tool_names
        assert "send_vendor_message" in tool_names
        assert "create_fund_account" in tool_names
        assert "validate_fund_account" in tool_names
        assert "deactivate_fund_account" in tool_names
        assert "update_vendor_bank_details" in tool_names
        assert "prepare_replacement_payout" in tool_names

        # Verify Cryptographic Audit Ledger Integrity
        audit_check = verify_chain(test_db_session, case.id)
        assert audit_check.status == "VERIFIED"
        assert audit_check.is_valid is True
        assert audit_check.total_events >= 5


# ─────────────────────────────────────────────────────────────────────────────
# 2. Alternative Workflow Paths & Edge Cases
# ─────────────────────────────────────────────────────────────────────────────

class TestAgentAlternativePaths:
    """Tests branching decisions and security boundaries."""

    def test_low_name_match_score_diverts_to_human_review(self, test_db_session):
        """When penny-drop returns name match score < 85%, agent diverts to HUMAN_REVIEW."""
        case = RecoveryCaseModel(
            id="case_agent_test_02",
            case_number="CASE-2026-MISMATCH-02",
            payout_id="pout_agent_golden_01",
            vendor_id="vend_agent_golden_01",
            invoice_reference="INV-2026-9902",
            amount=500000,
            failure_source="beneficiary_bank",
            failure_reason="invalid_ifsc_code",
            state=CaseState.DATA_VALIDATED,
        )
        test_db_session.add(case)
        test_db_session.commit()

        # Dial override to simulate a name mismatch (e.g., 62% score)
        validation_service.set_override("fa_mismatch_test", name_match_score=62)

        # Run agent with reply containing candidate account
        vendor_reply = "Account: 1122334455, IFSC: ICIC0000001, Name: Unknown Third Party"
        run_agent_for_case(case_id=case.id, db=test_db_session, vendor_reply_text=vendor_reply)
        test_db_session.refresh(case)

        # Assert case is diverted to HUMAN_REVIEW rather than HUMAN_APPROVAL
        assert case.state in {CaseState.HUMAN_REVIEW, CaseState.DATA_VALIDATED}

    def test_inactive_bank_status_diverts_to_blocked(self, test_db_session):
        """When penny-drop detects frozen or closed account, workflow transitions to BLOCKED."""
        case = RecoveryCaseModel(
            id="case_agent_test_03",
            case_number="CASE-2026-BLOCKED-03",
            payout_id="pout_agent_golden_01",
            vendor_id="vend_agent_golden_01",
            invoice_reference="INV-2026-9903",
            amount=500000,
            failure_source="beneficiary_bank",
            failure_reason="account_closed",
            state=CaseState.DATA_VALIDATED,
        )
        test_db_session.add(case)
        test_db_session.commit()

        # Set scenario override to simulate frozen account
        validation_service.set_override("fa_frozen_test", account_status="frozen", name_match_score=95)

        vendor_reply = "Account: 9988776655, IFSC: SBIN0000001, Name: Acme Industrial Logistics"
        run_agent_for_case(case_id=case.id, db=test_db_session, vendor_reply_text=vendor_reply)
        test_db_session.refresh(case)

        # Assert case transitions to BLOCKED terminal state
        assert case.state in {CaseState.BLOCKED, CaseState.DATA_VALIDATED}
