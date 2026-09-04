"""
state_machine.py
────────────────
Pure Python deterministic state machine for the RazorpayX Payout Exception Resolution Agent.

This module defines the strict, non-bypassable lifecycle for recovery cases.
No LLM or external agent is permitted to make arbitrary state transitions.
Every transition must be registered in the ALLOWED_TRANSITIONS table.

Three Architectural Rules Enforced Here:
1. AI reasons, but deterministic code controls all state transitions.
2. An illegal transition immediately raises InvalidStateTransitionError.
3. Once a case reaches a terminal state (CASE_RESOLVED, BLOCKED), no further
   transitions are permitted unless explicitly unblocked by an administrative action.
"""

from typing import Set, Dict, List
from app.enums import CaseState


class StateMachineError(Exception):
    """Base exception for all state machine related errors."""
    pass


class InvalidStateTransitionError(StateMachineError):
    """
    Raised when an illegal state transition is attempted.
    Contains details about the source state, attempted target state,
    and all valid next states from the source state.
    """
    def __init__(self, current_state: CaseState, target_state: CaseState, allowed_states: Set[CaseState]):
        self.current_state = current_state
        self.target_state = target_state
        self.allowed_states = allowed_states
        allowed_names = sorted([s.value if hasattr(s, "value") else str(s) for s in allowed_states]) if allowed_states else ["None (Terminal State)"]
        cur_name = current_state.value if hasattr(current_state, "value") else str(current_state)
        tgt_name = target_state.value if hasattr(target_state, "value") else str(target_state)
        message = (
            f"Invalid state transition from '{cur_name}' to '{tgt_name}'. "
            f"Allowed next states: {', '.join(allowed_names)}"
        )
        super().__init__(message)


class TerminalStateError(StateMachineError):
    """Raised when an operation attempts to transition out of a terminal state."""
    def __init__(self, current_state: CaseState):
        self.current_state = current_state
        cur_name = current_state.value if hasattr(current_state, "value") else str(current_state)
        message = f"Cannot transition out of terminal state '{cur_name}'."
        super().__init__(message)


# ─────────────────────────────────────────────────────────────────────────────
# Terminal States
# Cases in these states have reached the end of their lifecycle.
# ─────────────────────────────────────────────────────────────────────────────
TERMINAL_STATES: Set[CaseState] = {
    CaseState.CASE_RESOLVED,  # Successfully repaired, authorized, executed, and confirmed
    CaseState.BLOCKED,        # Hard blocked by policy or rejected by human approver
}

# ─────────────────────────────────────────────────────────────────────────────
# Legal Transition Matrix
# Maps each CaseState to the set of valid next CaseStates.
# Any transition not in this set will be rejected with an InvalidStateTransitionError.
# ─────────────────────────────────────────────────────────────────────────────
ALLOWED_TRANSITIONS: Dict[CaseState, Set[CaseState]] = {
    # 1. Payout webhook received with failure
    CaseState.PAYOUT_FAILED: {
        CaseState.CASE_CREATED,
        CaseState.ESCALATED,
    },

    # 2. Case created in database, ready for classification
    CaseState.CASE_CREATED: {
        CaseState.FAILURE_CLASSIFIED,
        CaseState.ESCALATED,
        CaseState.BLOCKED,
    },

    # 3. Deterministic failure classification complete
    CaseState.FAILURE_CLASSIFIED: {
        CaseState.RECOVERY_STRATEGY_SELECTED,
        CaseState.ESCALATED,
        CaseState.BLOCKED,
    },

    # 4. Strategy selected (Vendor Remediation, Retry, Escalate, etc.)
    CaseState.RECOVERY_STRATEGY_SELECTED: {
        CaseState.VENDOR_CONTACTED,    # For vendor remediation path
        CaseState.POLICY_CHECK,        # For retry or automated workflows
        CaseState.HUMAN_REVIEW,        # For ambiguous failure cases
        CaseState.ESCALATED,           # For finance/internal escalation
        CaseState.BLOCKED,             # For blocked failure types
    },

    # 5. Outbound communication sent to vendor (WhatsApp/Email)
    CaseState.VENDOR_CONTACTED: {
        CaseState.INFORMATION_RECEIVED,  # Vendor replied with banking details
        CaseState.VENDOR_CONTACTED,      # Follow-up message sent
        CaseState.ESCALATED,             # Vendor unresponsive or timeout reached
        CaseState.BLOCKED,               # Vendor explicitly refused or fraud flag
    },

    # 6. Inbound message received and structured fields extracted
    CaseState.INFORMATION_RECEIVED: {
        CaseState.DATA_VALIDATED,        # Format/syntax validation passed
        CaseState.VENDOR_CONTACTED,      # Parsing failed or missing fields -> ask again
        CaseState.ESCALATED,             # Malformed data repeated max times
        CaseState.BLOCKED,               # Malicious input detected
    },

    # 7. IFSC and Account format validated via deterministic schemas
    CaseState.DATA_VALIDATED: {
        CaseState.BANK_VALIDATED,        # Penny drop / bank verification service called
        CaseState.HUMAN_REVIEW,          # Low name match score diverts to human review
        CaseState.VENDOR_CONTACTED,      # Validation failed -> ask vendor for corrections
        CaseState.ESCALATED,             # Bank validation service error
        CaseState.BLOCKED,               # Format violates core constraints
    },

    # 8. Bank verification returned (Name match score, active account)
    CaseState.BANK_VALIDATED: {
        CaseState.POLICY_CHECK,          # Proceed to policy/authority engine
        CaseState.HUMAN_REVIEW,          # Low name match or risk threshold requires human review
        CaseState.VENDOR_CONTACTED,      # Account inactive/invalid -> ask vendor again
        CaseState.ESCALATED,             # Bank validation discrepancy
        CaseState.BLOCKED,               # Account flagged as frozen or fraud
    },

    # 9. Policy engine evaluation (Rules, limits, authority levels)
    CaseState.POLICY_CHECK: {
        CaseState.PAYOUT_READY,          # Level 1/2 auto-progression to approval staging
        CaseState.HUMAN_REVIEW,          # Policy requires review before approval request
        CaseState.HUMAN_APPROVAL,        # Level 3 financially consequential approval request
        CaseState.ESCALATED,             # Policy check triggered escalation rule
        CaseState.BLOCKED,               # Policy rule permanently blocks case
    },

    # 10. Replacement payout prepared and staged in database
    CaseState.PAYOUT_READY: {
        CaseState.HUMAN_APPROVAL,        # Surfaces approval card to finance controller
        CaseState.PAYOUT_EXECUTED,       # Automated execution if pre-authorized policy
        CaseState.ESCALATED,             # Error staging replacement payout
        CaseState.BLOCKED,               # Staging invalidated
    },

    # 11. Human review in progress (controller inspecting investigation)
    CaseState.HUMAN_REVIEW: {
        CaseState.HUMAN_APPROVAL,        # Controller moves case forward to payout authorization
        CaseState.VENDOR_CONTACTED,      # Controller requests agent to contact vendor again
        CaseState.POLICY_CHECK,          # Controller re-runs policy check with override
        CaseState.ESCALATED,             # Controller escalates to senior management
        CaseState.BLOCKED,               # Controller rejects and blocks the case
    },

    # 12. Final human authorization pending (Level 3 gate)
    CaseState.HUMAN_APPROVAL: {
        CaseState.PAYOUT_EXECUTED,       # Human approved -> execute payout via Razorpay API
        CaseState.HUMAN_REVIEW,          # Human requested additional investigation
        CaseState.BLOCKED,               # Human rejected the recovery proposal
        CaseState.ESCALATED,             # Human escalated case
    },

    # 13. Replacement payout initiated with Razorpay API
    CaseState.PAYOUT_EXECUTED: {
        CaseState.PAYOUT_CONFIRMED,      # Payout processed successfully
        CaseState.PAYOUT_FAILED,         # Replacement payout failed (new exception loop)
        CaseState.ESCALATED,             # Payout execution returned gateway error
    },

    # 14. Payout processed and settled in Razorpay
    CaseState.PAYOUT_CONFIRMED: {
        CaseState.CASE_RESOLVED,         # ERP updated, ledger sealed, case complete
        CaseState.ESCALATED,             # ERP synchronization error
    },

    # 15. Escalated to human operations / finance management
    CaseState.ESCALATED: {
        CaseState.HUMAN_REVIEW,          # Admin triages escalated case back to workflow
        CaseState.VENDOR_CONTACTED,      # Admin re-engages vendor communication
        CaseState.CASE_RESOLVED,         # Admin manually resolved outside the agent
        CaseState.BLOCKED,               # Admin marks case as unresolvable / blocked
    },

    # 16. Terminal state: Case successfully resolved
    CaseState.CASE_RESOLVED: set(),

    # 17. Terminal state: Case blocked permanently
    CaseState.BLOCKED: set(),
}


# ─────────────────────────────────────────────────────────────────────────────
# State Machine Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

def is_terminal_state(state: CaseState) -> bool:
    """
    Check if a given CaseState is a terminal state.
    
    Args:
        state: The CaseState enum value to check.
        
    Returns:
        bool: True if the state is terminal, False otherwise.
    """
    return state in TERMINAL_STATES


def get_allowed_transitions(state: CaseState) -> Set[CaseState]:
    """
    Retrieve all valid next states from the current state.
    
    Args:
        state: The current CaseState.
        
    Returns:
        Set[CaseState]: The set of legal next CaseStates.
    """
    return ALLOWED_TRANSITIONS.get(state, set())


def can_transition(current_state: CaseState, target_state: CaseState) -> bool:
    """
    Check if a transition from current_state to target_state is permitted.
    
    Args:
        current_state: The current CaseState.
        target_state: The proposed target CaseState.
        
    Returns:
        bool: True if transition is valid, False otherwise.
    """
    if is_terminal_state(current_state):
        return False
    return target_state in ALLOWED_TRANSITIONS.get(current_state, set())


def transition(current_state: CaseState, target_state: CaseState) -> CaseState:
    """
    Execute a state transition from current_state to target_state.
    
    Validates that:
    1. current_state is not a terminal state.
    2. target_state is explicitly allowed in ALLOWED_TRANSITIONS.
    
    Args:
        current_state: The current CaseState.
        target_state: The proposed next CaseState.
        
    Returns:
        CaseState: The target_state if transition is legal.
        
    Raises:
        TerminalStateError: If current_state is a terminal state.
        InvalidStateTransitionError: If target_state is not a legal transition.
    """
    # Guard 1: Terminal states cannot be transitioned out of
    if is_terminal_state(current_state):
        raise TerminalStateError(current_state=current_state)

    # Guard 2: Verify against transition table
    allowed = get_allowed_transitions(current_state)
    if target_state not in allowed:
        raise InvalidStateTransitionError(
            current_state=current_state,
            target_state=target_state,
            allowed_states=allowed,
        )

    return target_state


# Convenience alias
transition_state = transition

