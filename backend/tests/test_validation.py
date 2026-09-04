"""
tests/test_validation.py
────────────────────────
Unit tests for the Mock Account Validation Service (Phase 8).

Tests:
1. Name matching algorithm:
   - Exact string matches return 100.
   - Normalized noise-word variations (Pvt Ltd, India, Corp) return >= 90.
   - Completely different entity names return < 40.
   - Empty/None inputs return 0 safely.
2. Scenario overrides:
   - Dialing custom name_match_score (e.g., 65).
   - Simulating fatal bank statuses (e.g., closed, frozen, invalid).
   - Clearing overrides.
3. Deterministic evaluation rules:
   - Active account + score >= threshold (85) -> POLICY_CHECK (Valid).
   - Active account + score < threshold (85) -> HUMAN_REVIEW (Invalid).
   - Inactive/closed/frozen account -> BLOCKED (Invalid).
   - Custom threshold configuration.
4. Tool execution with policy engine gating and cryptographic audit logging:
   - Verified audit event creation and chain integrity.
   - Honest labeling with is_simulated=True.
   - Policy rejection on blocked/resolved cases.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.enums import CaseState, RiskLevel
from app.models.vendor import Vendor
from app.models.payout import Payout
from app.models.recovery_case import RecoveryCaseModel
from app.models.fund_account import FundAccount
from app.models.vendor_message import VendorMessage
from app.models.agent_action import AgentAction
from app.models.approval import Approval
from app.models.audit_event import AuditEvent
from app.policy_engine import PolicyContext
from app.audit import verify_chain
from app.services.validation_service import (
    validation_service,
    compute_name_match_score,
    evaluate_validation_result,
    FundAccountValidationResponse,
    ValidationEvaluationResult,
)


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
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def clean_overrides():
    """Ensures scenario overrides are cleared before and after each test."""
    validation_service.clear_overrides()
    yield
    validation_service.clear_overrides()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Name Matching Algorithm Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestNameMatching:
    """Tests fuzzy string comparison and noise-word normalization."""

    def test_exact_name_match_returns_100(self):
        """Identical names score 100."""
        score = compute_name_match_score("Acme Logistics", "Acme Logistics")
        assert score == 100

    def test_normalized_name_match_high_score(self):
        """Names with legal entity suffix variations score >= 90."""
        score = compute_name_match_score(
            "Acme Industrial Logistics Pvt Ltd",
            "Acme Industrial Logistics Private Limited India",
        )
        assert score >= 90

    def test_different_names_low_score(self):
        """Unrelated vendor and beneficiary names score < 40."""
        score = compute_name_match_score(
            "Acme Logistics",
            "Sharma Global Enterprises",
        )
        assert score < 40

    def test_empty_or_none_name_returns_0(self):
        """Missing or blank names safely evaluate to 0."""
        assert compute_name_match_score("", "Acme Logistics") == 0
        assert compute_name_match_score("Acme Logistics", "") == 0
        assert compute_name_match_score(None, None) == 0


# ─────────────────────────────────────────────────────────────────────────────
# 2. Scenario Overrides Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestScenarioOverrides:
    """Tests the ability to dial validation responses for deterministic test harnesses."""

    def test_scenario_override_custom_score(self):
        """Configuring score override returns exact dialed score."""
        fa_id = "fa_override_score_test"
        validation_service.set_override(fa_id, name_match_score=68)

        res = validation_service.validate_fund_account(
            fund_account_id=fa_id,
            vendor_name="Acme Logistics",
            registered_name="Acme Logistics",
        )
        assert res.name_match_score == 68
        assert res.is_simulated is True

    def test_scenario_override_inactive_status(self):
        """Configuring fatal account status override returns specified status."""
        fa_id = "fa_override_status_test"
        validation_service.set_override(fa_id, account_status="frozen", name_match_score=95)

        res = validation_service.validate_fund_account(
            fund_account_id=fa_id,
            vendor_name="Acme Logistics",
        )
        assert res.account_status == "frozen"
        assert res.name_match_score == 95

    def test_clear_overrides_restores_default(self):
        """Clearing overrides restores dynamic algorithm evaluation."""
        fa_id = "fa_clear_test"
        validation_service.set_override(fa_id, name_match_score=40)
        validation_service.clear_overrides()

        res = validation_service.validate_fund_account(
            fund_account_id=fa_id,
            vendor_name="Acme Logistics",
            registered_name="Acme Logistics",
        )
        assert res.name_match_score == 100


# ─────────────────────────────────────────────────────────────────────────────
# 3. Deterministic Evaluation Rules Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDeterministicEvaluator:
    """Tests state routing decisions based on penny-drop validation outcomes."""

    def test_evaluate_active_high_score_transitions_to_policy_check(self):
        """Active account with score >= 85 transitions to POLICY_CHECK."""
        val_res = FundAccountValidationResponse(
            fund_account_id="fa_pass_01",
            account_status="active",
            registered_name="Acme Logistics",
            name_match_score=92,
        )
        outcome = evaluate_validation_result(val_res, threshold=85)
        assert outcome.is_valid is True
        assert outcome.next_state == CaseState.POLICY_CHECK
        assert "validation successful" in outcome.reason

    def test_evaluate_low_score_transitions_to_human_review(self):
        """Active account with score < 85 transitions to HUMAN_REVIEW."""
        val_res = FundAccountValidationResponse(
            fund_account_id="fa_review_01",
            account_status="active",
            registered_name="Sharma Logistics",
            name_match_score=72,
        )
        outcome = evaluate_validation_result(val_res, threshold=85)
        assert outcome.is_valid is False
        assert outcome.next_state == CaseState.HUMAN_REVIEW
        assert "below the safety threshold" in outcome.reason

    def test_evaluate_inactive_account_transitions_to_blocked(self):
        """Non-active account (e.g., closed) transitions immediately to BLOCKED."""
        val_res = FundAccountValidationResponse(
            fund_account_id="fa_blocked_01",
            account_status="closed",
            registered_name="Acme Logistics",
            name_match_score=100,
        )
        outcome = evaluate_validation_result(val_res, threshold=85)
        assert outcome.is_valid is False
        assert outcome.next_state == CaseState.BLOCKED
        assert "permanently BLOCKED" in outcome.reason

    def test_custom_threshold_override(self):
        """Custom threshold (e.g. 70) allows score 75 to pass."""
        val_res = FundAccountValidationResponse(
            fund_account_id="fa_custom_01",
            account_status="active",
            registered_name="Acme Corp",
            name_match_score=75,
        )
        outcome = evaluate_validation_result(val_res, threshold=70)
        assert outcome.is_valid is True
        assert outcome.next_state == CaseState.POLICY_CHECK


# ─────────────────────────────────────────────────────────────────────────────
# 4. Tool Execution & Audit Logging Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestValidationServiceExecution:
    """Tests tool execution, policy gating, and cryptographic audit log emission."""

    def test_validation_service_success_and_audit_logging(self, test_db_session):
        """validate_fund_account passes policy, returns simulated response, and logs audit event."""
        case_id = "case_val_audit_test_01"
        valid_context = PolicyContext(
            case_state=CaseState.INFORMATION_RECEIVED,
            data_validated=True,
            vendor_verified=True,
            risk_level=RiskLevel.LOW,
        )

        res = validation_service.validate_fund_account(
            fund_account_id="fa_audit_01",
            vendor_name="Acme Industrial Logistics",
            registered_name="Acme Industrial Logistics Pvt Ltd",
            case_id=case_id,
            db=test_db_session,
            context=valid_context,
        )

        assert isinstance(res, FundAccountValidationResponse)
        assert res.is_simulated is True
        assert res.account_status == "active"
        assert res.name_match_score >= 90

        # Verify audit event in ledger
        audit_check = verify_chain(test_db_session, case_id)
        assert audit_check.status == "VERIFIED"
        assert audit_check.is_valid is True
        assert audit_check.total_events == 1

    def test_validation_service_policy_block_on_resolved_case(self, test_db_session):
        """validate_fund_account is BLOCKED by policy if case is already CASE_RESOLVED."""
        case_id = "case_val_audit_test_02"
        resolved_context = PolicyContext(case_state=CaseState.CASE_RESOLVED)

        with pytest.raises(PermissionError) as exc_info:
            validation_service.validate_fund_account(
                fund_account_id="fa_resolved_01",
                vendor_name="Acme Logistics",
                case_id=case_id,
                db=test_db_session,
                context=resolved_context,
            )
        assert "Policy Engine BLOCKED" in str(exc_info.value)
        assert "CASE_RESOLVED" in str(exc_info.value)
