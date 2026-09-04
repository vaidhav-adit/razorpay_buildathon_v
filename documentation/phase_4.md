# Phase 4 Documentation: Policy and Authority Engine

## Overview

Phase 4 implemented the deterministic Policy and Authority Engine (`backend/app/policy_engine.py`).

In accordance with the foundational architectural principle:
> **AI reasons. Deterministic code executes. Humans authorize money movement.**

The policy engine acts as the gatekeeper between proposed AI tool invocations and execution. Every action is assigned a strict `PolicyLevel` (Level 1 Autonomous, Level 2 Controlled Mutation, Level 3 Financially Consequential). The policy engine evaluates proposed actions against case state, risk level, name match thresholds, and validation flags to return `ALLOW`, `REQUIRE_APPROVAL`, or `BLOCK`.

---

## What Was Built

### 1. Authority Level Hierarchy (`ACTION_REGISTRY`)
- **Level 1 — Autonomous (Green)**:
  - Actions: `get_payout`, `read_payout`, `get_contact`, `read_vendor`, `get_fund_accounts`, `classify_failure`, `send_vendor_message`, `create_recovery_case`, `parse_vendor_response`, `query_status`, `log_audit_event`.
  - Rule: `ALLOW` always (unless case is in a terminal state).
- **Level 2 — Controlled Mutation (Yellow)**:
  - Actions: `create_fund_account`, `deactivate_fund_account`, `update_erp_vendor`, `initiate_account_validation`, `update_case_state`, `schedule_retry`.
  - Rule: `ALLOW` if:
    - Data format/IFSC validation passed (`data_validated=True`).
    - Vendor identity confirmed (`vendor_verified=True`).
    - Name match score meets or exceeds minimum threshold (`name_match_score >= 85`).
    - Risk is not `HIGH`.
    - Target account is active (`is_account_active != False`).
    - Otherwise returns `REQUIRE_APPROVAL` or `BLOCK`.
- **Level 3 — Financially Consequential (Red)**:
  - Actions: `execute_payout`, `execute_replacement_payout`, `override_validation`, `override_risk_policy`, `approve_large_transaction`.
  - Rule: `REQUIRE_APPROVAL` ALWAYS without exception. Zero LLM autonomy over movement of funds.

### 2. State & Safety Guards
- **`BLOCKED` & `CASE_RESOLVED`**: All mutation actions are returned as `BLOCK`. Read operations remain `ALLOW` for auditing.
- **`ESCALATED`**: Mutations return `REQUIRE_APPROVAL` for operational triage.
- **Unregistered Actions**: Any unmapped or unknown action defaults safely to Level 3 (`REQUIRE_APPROVAL`).

---

## Unit Test Suite (`backend/tests/test_policy_engine.py`)

A comprehensive unit test suite covering:
1. `TestPolicyEngineLevel1Autonomous`: All 11 registered Level 1 actions return `ALLOW`.
2. `TestPolicyEngineLevel2ControlledMutation`: Verified conditional gating:
   - Passes with valid data and scores >= 85.
   - Gated behind approval on unvalidated data, unverified vendor, low name match (<85), or high risk.
   - Blocked on inactive accounts.
3. `TestPolicyEngineLevel3FinanciallyConsequential`: Tested all 5 Level 3 actions strictly require approval regardless of context.
4. `TestPolicyEngineStateGuards`: Verified immutability of `BLOCKED` and `CASE_RESOLVED` states, while permitting read access.
5. `TestPolicyEngineSafetyFallbacks`: Verified unregistered actions default to Level 3 and normalize string casing.

---

## Verification

To run the policy engine tests:
```bash
pytest backend/tests/test_policy_engine.py -v
```
*(Or run the full test suite: `pytest backend/tests/ -v`)*
