# Phase 8 Documentation: Mock Account Validation Service

## Overview

Phase 8 implements the Mock Account Validation Service (`backend/app/services/validation_service.py`), which simulates penny-drop verification (`POST /v1/fund_accounts/validations`) for B2B bank accounts. Since penny-drop verification is not available in Razorpay Test Mode, this service provides an honest, configurable simulation engine for local development, evaluation harnesses, and test automation.

In accordance with our core architecture:
> **AI reasons. Deterministic code executes. Humans authorize money movement.**

The evaluation of penny-drop results is 100% deterministic:
- **Fatal Status** (`account_status != "active"`): Immediately transitions the state machine to `BLOCKED`.
- **Low Name-Match Score** (`name_match_score < threshold`): Transitions the state machine to `HUMAN_REVIEW` for manual verification.
- **Passing Result** (`account_status == "active"` and `name_match_score >= threshold`): Transitions to `POLICY_CHECK`.

---

## What Was Built

### 1. Fuzzy Name Matching Algorithm (`compute_name_match_score`)
- Normalizes B2B company and vendor names (removing punctuation and common noise terms such as `pvt`, `ltd`, `private limited`, `llp`, `logistics`, `enterprises`).
- Performs token overlap and containment analysis to compute a deterministic similarity score between 0 and 100.
- Identical names score 100; minor corporate suffix differences score >= 90; completely unrelated names score < 40.

### 2. Scenario Overrides Engine
- Allows evaluation tests and adversarial test harnesses to dial the exact validation response:
  - `set_override(fund_account_id, name_match_score=60, account_status="frozen")`
  - `clear_overrides()`
- Explicitly flags all responses with `is_simulated = True` for transparent UI presentation.

### 3. Deterministic Evaluator (`evaluate_validation_result`)
- Evaluates account status and name match score against configured thresholds (default: 85%).
- Returns `ValidationEvaluationResult` with `next_state` routing (`BLOCKED`, `HUMAN_REVIEW`, or `POLICY_CHECK`).

### 4. Gated Tool Method (`validate_fund_account`)
- Gated as a Level 2 Controlled Mutation via the Policy Engine.
- Produces an append-only, tamper-evident `AuditEvent` in the cryptographic ledger.

---

## Unit Test Suite (`backend/tests/test_validation.py`)

A comprehensive unit test suite covering:
1. `TestNameMatching`: Exact matches (100), normalized corporate suffixes (>= 90), distinct entity names (< 40), and blank/None edge cases.
2. `TestScenarioOverrides`: Setting custom match scores, setting fatal bank statuses (e.g. `frozen`), and clearing overrides.
3. `TestDeterministicEvaluator`:
   - Active status + score >= 85 -> `POLICY_CHECK` (Valid).
   - Active status + score < 85 -> `HUMAN_REVIEW` (Invalid).
   - Non-active status -> `BLOCKED` (Invalid).
   - Configurable threshold support.
4. `TestValidationServiceExecution`:
   - Level 2 policy engine gating.
   - Transparent `is_simulated=True` flag verification.
   - Cryptographic audit ledger logging and chain verification.
   - Policy rejection when case is in terminal `CASE_RESOLVED` state.

---

## Verification

To run the Mock Account Validation Service tests:
```bash
pytest backend/tests/test_validation.py -v
```

To run all test suites across Phases 2 through 8:
```bash
pytest backend/tests/ -v
```
