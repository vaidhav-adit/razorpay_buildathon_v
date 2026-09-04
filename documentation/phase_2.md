# Phase 2 Documentation: Pure Python Deterministic State Machine

## Overview

Phase 2 implemented the core finite state machine (`backend/app/state_machine.py`) governing the entire lifecycle of a recovery case.

In accordance with the foundational architectural principle:
> **AI reasons. Deterministic code executes. Humans authorize money movement.**

The state machine is implemented as a strict, non-bypassable Python module with zero external API or LLM dependencies. Any state transition not explicitly registered in the transition matrix raises a descriptive `InvalidStateTransitionError`. Once a case enters a terminal state (`CASE_RESOLVED` or `BLOCKED`), `TerminalStateError` prevents any further mutations.

---

## What Was Built

### 1. State Machine Engine (`backend/app/state_machine.py`)
- **Complete Transition Table (`ALLOWED_TRANSITIONS`)**: Defines all valid transitions across all 17 `CaseState` enum members:
  - `PAYOUT_FAILED`: Initial webhook failure ingestion.
  - `CASE_CREATED`: Case initialized in PostgreSQL.
  - `FAILURE_CLASSIFIED`: Deterministic mapping from failure code to strategy.
  - `RECOVERY_STRATEGY_SELECTED`: Routing to remediation, retry, escalation, or block.
  - `VENDOR_CONTACTED`: Outbound notification dispatched.
  - `INFORMATION_RECEIVED`: Inbound vendor response received.
  - `DATA_VALIDATED`: Account & IFSC syntax/format checked.
  - `BANK_VALIDATED`: Bank verification / penny-drop verified.
  - `POLICY_CHECK`: Policy engine evaluation of rules, limits, and risk thresholds.
  - `PAYOUT_READY`: Replacement payout staged.
  - `HUMAN_REVIEW`: Internal controller inspection for ambiguous or high-risk cases.
  - `HUMAN_APPROVAL`: Mandatory human authorization gate for money movement.
  - `PAYOUT_EXECUTED`: Replacement payout API initiated.
  - `PAYOUT_CONFIRMED`: Payout settled successfully.
  - `CASE_RESOLVED`: Terminal state — ERP updated, audit ledger sealed.
  - `ESCALATED`: Operational / administrative triage state.
  - `BLOCKED`: Terminal state — hard block or rejection.
- **Terminal States Guard**: `TERMINAL_STATES` set containing `CASE_RESOLVED` and `BLOCKED`.
- **Custom Exceptions**:
  - `InvalidStateTransitionError`: Lists current state, attempted target, and all valid next states.
  - `TerminalStateError`: Enforces immutability for resolved and blocked cases.
- **Helper Query Functions**:
  - `transition(current_state, target_state)`: Executes validated state transition.
  - `can_transition(current_state, target_state)`: Boolean capability check.
  - `is_terminal_state(state)`: Boolean terminal state check.
  - `get_allowed_transitions(state)`: Set of legal next states.

---

## Unit Test Suite (`backend/tests/test_state_machine.py`)

A comprehensive unit test suite covering 100% of state transitions and edge cases:
1. `TestStateMachineHappyPath`: Full 13-step sequential lifecycle from `PAYOUT_FAILED` to `CASE_RESOLVED`.
2. `TestAlternativeWorkflowPaths`: Human review branches, vendor re-contact loops, and replacement payout failure loops.
3. `TestEscalationPaths`: Validated that all 14 active operational states can transition to `ESCALATED`, and that `ESCALATED` can be triaged back into review, vendor contact, resolution, or block.
4. `TestTerminalStates`: Verified that `CASE_RESOLVED` and `BLOCKED` cannot be transitioned out of under any circumstances.
5. `TestInvalidTransitions`: Verified that illegal skips (e.g. `PAYOUT_FAILED` directly to `PAYOUT_EXECUTED` or `CASE_RESOLVED`) raise `InvalidStateTransitionError`.
6. `TestStateMachineCoverage`: Verified all 17 enum members exist in the transition matrix.

---

## Verification

To run the unit tests:
```bash
pytest backend/tests/test_state_machine.py -v
```
