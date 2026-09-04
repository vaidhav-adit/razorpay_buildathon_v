"""
tests/test_state_machine.py
───────────────────────────
Unit tests for the pure Python state machine (Phase 2).

Tests:
1. Complete happy-path lifecycle progression.
2. Human review and policy branch progressions.
3. Escalation paths and recovery from escalation.
4. Terminal state enforcement (CASE_RESOLVED, BLOCKED).
5. Illegal transition rejection (InvalidStateTransitionError).
6. State machine helper function accuracy.
"""

import pytest
from app.enums import CaseState
from app.state_machine import (
    transition,
    can_transition,
    is_terminal_state,
    get_allowed_transitions,
    InvalidStateTransitionError,
    TerminalStateError,
    TERMINAL_STATES,
    ALLOWED_TRANSITIONS,
)


class TestStateMachineHappyPath:
    """Tests the standard full resolution workflow from failure to resolution."""

    def test_full_resolution_lifecycle(self):
        """Verify the complete step-by-step resolution lifecycle."""
        # 1. Payout failure received -> Case created
        state = transition(CaseState.PAYOUT_FAILED, CaseState.CASE_CREATED)
        assert state == CaseState.CASE_CREATED

        # 2. Case created -> Failure classified
        state = transition(state, CaseState.FAILURE_CLASSIFIED)
        assert state == CaseState.FAILURE_CLASSIFIED

        # 3. Failure classified -> Strategy selected
        state = transition(state, CaseState.RECOVERY_STRATEGY_SELECTED)
        assert state == CaseState.RECOVERY_STRATEGY_SELECTED

        # 4. Strategy selected -> Vendor contacted
        state = transition(state, CaseState.VENDOR_CONTACTED)
        assert state == CaseState.VENDOR_CONTACTED

        # 5. Vendor contacted -> Information received
        state = transition(state, CaseState.INFORMATION_RECEIVED)
        assert state == CaseState.INFORMATION_RECEIVED

        # 6. Information received -> Data validated
        state = transition(state, CaseState.DATA_VALIDATED)
        assert state == CaseState.DATA_VALIDATED

        # 7. Data validated -> Bank validated
        state = transition(state, CaseState.BANK_VALIDATED)
        assert state == CaseState.BANK_VALIDATED

        # 8. Bank validated -> Policy check
        state = transition(state, CaseState.POLICY_CHECK)
        assert state == CaseState.POLICY_CHECK

        # 9. Policy check -> Payout ready (pre-approval staging)
        state = transition(state, CaseState.PAYOUT_READY)
        assert state == CaseState.PAYOUT_READY

        # 10. Payout ready -> Human approval (approval card surfaced)
        state = transition(state, CaseState.HUMAN_APPROVAL)
        assert state == CaseState.HUMAN_APPROVAL

        # 11. Human approval -> Payout executed
        state = transition(state, CaseState.PAYOUT_EXECUTED)
        assert state == CaseState.PAYOUT_EXECUTED

        # 12. Payout executed -> Payout confirmed
        state = transition(state, CaseState.PAYOUT_CONFIRMED)
        assert state == CaseState.PAYOUT_CONFIRMED

        # 13. Payout confirmed -> Case resolved
        state = transition(state, CaseState.CASE_RESOLVED)
        assert state == CaseState.CASE_RESOLVED
        assert is_terminal_state(state) is True


class TestAlternativeWorkflowPaths:
    """Tests alternative recovery branches and intermediate review states."""

    def test_human_review_branch_from_bank_validated(self):
        """Test routing through Human Review when name match or policy requires inspection."""
        state = transition(CaseState.BANK_VALIDATED, CaseState.HUMAN_REVIEW)
        assert state == CaseState.HUMAN_REVIEW

        # Human moves case to final approval
        state = transition(state, CaseState.HUMAN_APPROVAL)
        assert state == CaseState.HUMAN_APPROVAL

    def test_human_review_branch_from_policy_check(self):
        """Test routing from Policy Check directly to Human Review."""
        state = transition(CaseState.POLICY_CHECK, CaseState.HUMAN_REVIEW)
        assert state == CaseState.HUMAN_REVIEW

    def test_direct_human_approval_from_policy_check(self):
        """Test routing from Policy Check straight to Human Approval."""
        state = transition(CaseState.POLICY_CHECK, CaseState.HUMAN_APPROVAL)
        assert state == CaseState.HUMAN_APPROVAL

    def test_vendor_recontact_loop(self):
        """Test vendor re-contact loops when validation fails or clarifications are needed."""
        # Follow-up message sent while in VENDOR_CONTACTED
        state = transition(CaseState.VENDOR_CONTACTED, CaseState.VENDOR_CONTACTED)
        assert state == CaseState.VENDOR_CONTACTED

        # Data invalid -> re-contact vendor
        state = transition(CaseState.DATA_VALIDATED, CaseState.VENDOR_CONTACTED)
        assert state == CaseState.VENDOR_CONTACTED

        # Bank validation failed -> re-contact vendor
        state = transition(CaseState.BANK_VALIDATED, CaseState.VENDOR_CONTACTED)
        assert state == CaseState.VENDOR_CONTACTED

    def test_replacement_payout_failure_loop(self):
        """Test case when a replacement payout also fails."""
        state = transition(CaseState.PAYOUT_EXECUTED, CaseState.PAYOUT_FAILED)
        assert state == CaseState.PAYOUT_FAILED


class TestEscalationPaths:
    """Tests case escalations and administrative resolution workflows."""

    @pytest.mark.parametrize(
        "source_state",
        [
            CaseState.PAYOUT_FAILED,
            CaseState.CASE_CREATED,
            CaseState.FAILURE_CLASSIFIED,
            CaseState.RECOVERY_STRATEGY_SELECTED,
            CaseState.VENDOR_CONTACTED,
            CaseState.INFORMATION_RECEIVED,
            CaseState.DATA_VALIDATED,
            CaseState.BANK_VALIDATED,
            CaseState.POLICY_CHECK,
            CaseState.PAYOUT_READY,
            CaseState.HUMAN_REVIEW,
            CaseState.HUMAN_APPROVAL,
            CaseState.PAYOUT_EXECUTED,
            CaseState.PAYOUT_CONFIRMED,
        ],
    )
    def test_states_can_escalate(self, source_state: CaseState):
        """Verify that all active operational states can transition to ESCALATED."""
        assert can_transition(source_state, CaseState.ESCALATED) is True
        state = transition(source_state, CaseState.ESCALATED)
        assert state == CaseState.ESCALATED

    def test_recovery_from_escalated(self):
        """Verify that an escalated case can be triaged back into the workflow or resolved."""
        # To Human Review
        assert transition(CaseState.ESCALATED, CaseState.HUMAN_REVIEW) == CaseState.HUMAN_REVIEW
        # Re-contact vendor
        assert transition(CaseState.ESCALATED, CaseState.VENDOR_CONTACTED) == CaseState.VENDOR_CONTACTED
        # Manual administrative resolution
        assert transition(CaseState.ESCALATED, CaseState.CASE_RESOLVED) == CaseState.CASE_RESOLVED
        # Administrative block
        assert transition(CaseState.ESCALATED, CaseState.BLOCKED) == CaseState.BLOCKED


class TestTerminalStates:
    """Tests strict enforcement of terminal state behavior."""

    def test_terminal_state_detection(self):
        """Ensure only CASE_RESOLVED and BLOCKED are marked as terminal."""
        assert is_terminal_state(CaseState.CASE_RESOLVED) is True
        assert is_terminal_state(CaseState.BLOCKED) is True

        for state in CaseState:
            if state not in {CaseState.CASE_RESOLVED, CaseState.BLOCKED}:
                assert is_terminal_state(state) is False

    def test_transition_out_of_case_resolved_raises_error(self):
        """Ensure no transitions out of CASE_RESOLVED are permitted."""
        for target_state in CaseState:
            assert can_transition(CaseState.CASE_RESOLVED, target_state) is False
            with pytest.raises(TerminalStateError) as exc_info:
                transition(CaseState.CASE_RESOLVED, target_state)
            assert "Cannot transition out of terminal state 'CASE_RESOLVED'" in str(exc_info.value)

    def test_transition_out_of_blocked_raises_error(self):
        """Ensure no transitions out of BLOCKED are permitted."""
        for target_state in CaseState:
            assert can_transition(CaseState.BLOCKED, target_state) is False
            with pytest.raises(TerminalStateError) as exc_info:
                transition(CaseState.BLOCKED, target_state)
            assert "Cannot transition out of terminal state 'BLOCKED'" in str(exc_info.value)


class TestInvalidTransitions:
    """Tests that any illegal state skips raise InvalidStateTransitionError."""

    def test_cannot_skip_directly_from_failed_to_executed(self):
        """Critical financial guard: cannot skip from failure directly to execution."""
        assert can_transition(CaseState.PAYOUT_FAILED, CaseState.PAYOUT_EXECUTED) is False
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            transition(CaseState.PAYOUT_FAILED, CaseState.PAYOUT_EXECUTED)
        assert exc_info.value.current_state == CaseState.PAYOUT_FAILED
        assert exc_info.value.target_state == CaseState.PAYOUT_EXECUTED

    def test_cannot_skip_from_failed_directly_to_resolved(self):
        """Cannot resolve a case immediately upon failure receipt."""
        assert can_transition(CaseState.PAYOUT_FAILED, CaseState.CASE_RESOLVED) is False
        with pytest.raises(InvalidStateTransitionError):
            transition(CaseState.PAYOUT_FAILED, CaseState.CASE_RESOLVED)

    def test_cannot_skip_validation_to_payout_ready(self):
        """Cannot skip bank validation straight to payout ready."""
        assert can_transition(CaseState.DATA_VALIDATED, CaseState.PAYOUT_READY) is False
        with pytest.raises(InvalidStateTransitionError):
            transition(CaseState.DATA_VALIDATED, CaseState.PAYOUT_READY)

    def test_cannot_skip_approval_straight_to_confirmed(self):
        """Cannot mark payout confirmed directly from human approval."""
        assert can_transition(CaseState.HUMAN_APPROVAL, CaseState.PAYOUT_CONFIRMED) is False
        with pytest.raises(InvalidStateTransitionError):
            transition(CaseState.HUMAN_APPROVAL, CaseState.PAYOUT_CONFIRMED)


class TestStateMachineCoverage:
    """Tests completeness of the state machine definition."""

    def test_all_enum_states_are_covered_in_transition_table(self):
        """Every single CaseState enum member must exist in the transition matrix."""
        for state in CaseState:
            assert state in ALLOWED_TRANSITIONS, f"State {state.value} missing from ALLOWED_TRANSITIONS"

    def test_get_allowed_transitions_returns_copy_or_set(self):
        """get_allowed_transitions returns valid set for all states."""
        for state in CaseState:
            allowed = get_allowed_transitions(state)
            assert isinstance(allowed, set)
            if state in TERMINAL_STATES:
                assert len(allowed) == 0
