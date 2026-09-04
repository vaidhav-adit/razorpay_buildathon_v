"""
tests/test_policy_engine.py
───────────────────────────
Unit tests for the deterministic Policy and Authority Engine (Phase 4).

Tests:
1. Level 1 (Autonomous) actions are always ALLOWED.
2. Level 2 (Controlled Mutation) actions are ALLOWED when thresholds pass,
   REQUIRE_APPROVAL on high risk / low match / unverified data, and BLOCKED on inactive accounts.
3. Level 3 (Financially Consequential) actions ALWAYS REQUIRE_APPROVAL (zero autonomous money movement).
4. State guards (BLOCKED, CASE_RESOLVED, ESCALATED).
5. Unknown/unregistered action safety fallbacks.
"""

import pytest
from app.enums import CaseState, RiskLevel, PolicyDecision, PolicyLevel
from app.policy_engine import (
    evaluate_policy,
    get_action_policy_level,
    PolicyContext,
    PolicyEvaluationResult,
    ACTION_REGISTRY,
)


class TestPolicyEngineLevel1Autonomous:
    """Tests that Level 1 read and autonomous operations are allowed."""

    @pytest.mark.parametrize(
        "action_name",
        [
            "get_payout",
            "read_payout",
            "get_contact",
            "read_vendor",
            "get_fund_accounts",
            "classify_failure",
            "send_vendor_message",
            "create_recovery_case",
            "parse_vendor_response",
            "query_status",
            "log_audit_event",
        ],
    )
    def test_level_1_actions_are_allowed(self, action_name: str):
        """All registered Level 1 actions must return ALLOW."""
        result = evaluate_policy(action_name)
        assert result.decision == PolicyDecision.ALLOW
        assert result.level == PolicyLevel.AUTONOMOUS
        assert result.requires_human is False


class TestPolicyEngineLevel2ControlledMutation:
    """Tests conditional authorization for Level 2 mutation operations."""

    @pytest.mark.parametrize(
        "action_name",
        [
            "create_fund_account",
            "deactivate_fund_account",
            "update_erp_vendor",
            "initiate_account_validation",
            "update_case_state",
            "schedule_retry",
        ],
    )
    def test_level_2_allowed_when_all_conditions_pass(self, action_name: str):
        """Level 2 actions pass when data is validated, vendor verified, and risk is normal."""
        context = PolicyContext(
            case_state=CaseState.DATA_VALIDATED,
            risk_level=RiskLevel.LOW,
            name_match_score=95,
            is_account_active=True,
            vendor_verified=True,
            data_validated=True,
        )
        result = evaluate_policy(action_name, context)
        assert result.decision == PolicyDecision.ALLOW
        assert result.level == PolicyLevel.CONTROLLED_MUTATION
        assert result.requires_human is False

    def test_level_2_requires_approval_when_data_not_validated(self):
        """Unvalidated data mutations require human approval."""
        context = PolicyContext(data_validated=False)
        result = evaluate_policy("create_fund_account", context)
        assert result.decision == PolicyDecision.REQUIRE_APPROVAL
        assert result.requires_human is True
        assert "validation has not passed" in result.reason

    def test_level_2_requires_approval_when_vendor_unverified(self):
        """Unverified vendor identity requires human approval."""
        context = PolicyContext(vendor_verified=False)
        result = evaluate_policy("update_erp_vendor", context)
        assert result.decision == PolicyDecision.REQUIRE_APPROVAL
        assert result.requires_human is True
        assert "Vendor identity is not confirmed" in result.reason

    def test_level_2_requires_approval_on_low_name_match(self):
        """Name match below 85% requires human review."""
        context = PolicyContext(name_match_score=72)
        result = evaluate_policy("create_fund_account", context)
        assert result.decision == PolicyDecision.REQUIRE_APPROVAL
        assert result.requires_human is True
        assert "below the auto-approval threshold" in result.reason

    def test_level_2_allows_on_boundary_name_match(self):
        """Exact 85% threshold passes auto-approval."""
        context = PolicyContext(name_match_score=85, data_validated=True, vendor_verified=True)
        result = evaluate_policy("create_fund_account", context)
        assert result.decision == PolicyDecision.ALLOW
        assert result.requires_human is False

    def test_level_2_requires_approval_on_high_risk(self):
        """High risk cases gate mutations behind human review."""
        context = PolicyContext(risk_level=RiskLevel.HIGH)
        result = evaluate_policy("create_fund_account", context)
        assert result.decision == PolicyDecision.REQUIRE_APPROVAL
        assert result.requires_human is True
        assert "High-risk case requires human approval" in result.reason

    def test_level_2_blocks_inactive_account(self):
        """Dormant or inactive accounts are blocked from mutation."""
        context = PolicyContext(is_account_active=False)
        result = evaluate_policy("create_fund_account", context)
        assert result.decision == PolicyDecision.BLOCK
        assert result.requires_human is False
        assert "inactive or dormant" in result.reason


class TestPolicyEngineLevel3FinanciallyConsequential:
    """Tests strict human authorization requirement for Level 3 actions."""

    @pytest.mark.parametrize(
        "action_name",
        [
            "execute_payout",
            "execute_replacement_payout",
            "override_validation",
            "override_risk_policy",
            "approve_large_transaction",
        ],
    )
    def test_level_3_always_requires_human_approval(self, action_name: str):
        """Level 3 actions must ALWAYS require approval, even with perfect scores."""
        perfect_context = PolicyContext(
            case_state=CaseState.PAYOUT_READY,
            risk_level=RiskLevel.LOW,
            name_match_score=100,
            is_account_active=True,
            vendor_verified=True,
            data_validated=True,
            amount_in_paise=10000,
        )
        result = evaluate_policy(action_name, perfect_context)
        assert result.decision == PolicyDecision.REQUIRE_APPROVAL
        assert result.level == PolicyLevel.FINANCIALLY_CONSEQUENTIAL
        assert result.requires_human is True
        assert "strictly require human authorization" in result.reason


class TestPolicyEngineStateGuards:
    """Tests policy enforcement on blocked, resolved, and escalated cases."""

    def test_blocked_case_blocks_mutations(self):
        """Mutations on BLOCKED cases are strictly blocked."""
        context = PolicyContext(case_state=CaseState.BLOCKED)
        result = evaluate_policy("create_fund_account", context)
        assert result.decision == PolicyDecision.BLOCK
        assert "in BLOCKED state" in result.reason

    def test_blocked_case_allows_read_operations(self):
        """Read/audit operations are permitted on BLOCKED cases."""
        context = PolicyContext(case_state=CaseState.BLOCKED)
        result = evaluate_policy("read_payout", context)
        assert result.decision == PolicyDecision.ALLOW

    def test_resolved_case_blocks_mutations(self):
        """Mutations on CASE_RESOLVED cases are blocked."""
        context = PolicyContext(case_state=CaseState.CASE_RESOLVED)
        result = evaluate_policy("execute_payout", context)
        assert result.decision == PolicyDecision.BLOCK
        assert "already CASE_RESOLVED" in result.reason

    def test_escalated_case_requires_human_approval(self):
        """Mutations on ESCALATED cases require human triage."""
        context = PolicyContext(case_state=CaseState.ESCALATED)
        result = evaluate_policy("create_fund_account", context)
        assert result.decision == PolicyDecision.REQUIRE_APPROVAL
        assert result.requires_human is True


class TestPolicyEngineSafetyFallbacks:
    """Tests handling of unregistered actions and case-insensitivity."""

    def test_unknown_action_defaults_to_level_3(self):
        """Unregistered dangerous actions default to Level 3 / REQUIRE_APPROVAL."""
        result = evaluate_policy("unregistered_arbitrary_transfer")
        assert result.level == PolicyLevel.FINANCIALLY_CONSEQUENTIAL
        assert result.decision == PolicyDecision.REQUIRE_APPROVAL
        assert result.requires_human is True

    def test_case_insensitive_action_lookup(self):
        """Action names are normalized properly."""
        result = evaluate_policy("  CREATE_FUND_ACCOUNT  ")
        assert result.level == PolicyLevel.CONTROLLED_MUTATION
