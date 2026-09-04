# Phase 11 Documentation: Human Approval API & Reconciliation

## Overview

Phase 11 implements the **Human Approval API** and end-to-end payment reconciliation endpoints (`backend/app/api/cases.py`).

In strict alignment with the core architecture:
> **AI reasons. Deterministic code executes. Humans authorize money movement.**

The system enforces a non-bypassable human gate before executing any replacement payout:
1. **Level 3 Action Gate**: Replacement payout creation is a Financially Consequential action that is blocked from autonomous execution.
2. **Approval Card Context**: The approval payload surfaces the vendor profile, invoice reference, old defunct account, new penny-drop-validated account, name match score, and ERP update status.
3. **Audit Ledger Immutability**: Every approval and rejection action records an immutable `HUMAN_DECISION` audit event with the decider's identity (`decided_by`).
4. **Subsequent Webhook Reconciliation**: When the replacement payout is processed on RazorpayX, the system ingests `payout.processed`, reconciles the invoice in Zoho Books as paid, advances the case through `PAYOUT_CONFIRMED` to terminal `CASE_RESOLVED`, and cryptographically seals the audit ledger.

---

## Endpoints Implemented

### 1. `POST /cases/{case_id}/approve`
- **Purpose**: Authorizes and dispatches a replacement payout.
- **Preconditions**: Case must be in `HUMAN_APPROVAL` state with a staged `Approval` record.
- **Workflow**:
  1. Validates case state and presence of replacement fund account ID.
  2. Invokes `razorpay_client.create_payout` with `is_human_authorized=True`.
  3. Updates `Approval` record (`decision="APPROVE"`).
  4. Advances case state: `HUMAN_APPROVAL` &rarr; `PAYOUT_EXECUTED`.
  5. Records `AgentAction` and logs cryptographic `AuditEvent` (`event_type="HUMAN_DECISION"`, `actor="finance_controller"`).

### 2. `POST /cases/{case_id}/reject`
- **Purpose**: Rejects a proposed recovery and marks the case as permanently blocked.
- **Preconditions**: Case must be in `HUMAN_APPROVAL` or `HUMAN_REVIEW` state.
- **Workflow**:
  1. Validates non-empty rejection reason.
  2. Updates `Approval` record (`decision="REJECT"`, `rejection_reason`).
  3. Advances case state to terminal `BLOCKED`.
  4. Logs cryptographic `AuditEvent` (`event_type="HUMAN_DECISION"`).

### 3. `GET /cases/{case_id}`
- **Purpose**: Workspace detail endpoint returning full case metadata, vendor profile, payout details, approval context, and cryptographic audit ledger verification result (`verify_chain`).

### 4. `GET /cases`
- **Purpose**: Paginated case list endpoint with state filter (`?state=...`).

### 5. `POST /webhooks/razorpay` (`payout.processed`)
- **Purpose**: Ingests subsequent payout confirmation webhook.
- **Workflow**:
  1. Matches executed case by payout ID or invoice reference.
  2. Updates Zoho Books invoice status to `paid`.
  3. Advances state: `PAYOUT_EXECUTED` &rarr; `PAYOUT_CONFIRMED` &rarr; `CASE_RESOLVED`.
  4. Logs final `EXTERNAL_FACT` audit event and verifies chain integrity.

---

## Unit Test Suite (`backend/tests/test_approval.py`)

The test suite covers:
1. `TestHumanApprovalEndpoints`:
   - `test_approve_payout_golden_path`: Successful payout dispatch, state advance to `PAYOUT_EXECUTED`, approval update, audit ledger logging.
   - `test_approve_payout_rejected_when_not_in_human_approval_state`: 400 Bad Request if case is in another state.
   - `test_approve_payout_nonexistent_case`: 404 Not Found handling.
2. `TestHumanRejectionEndpoints`:
   - `test_reject_payout_transitions_case_to_blocked`: Rejection reason recorded, transition to `BLOCKED`.
   - `test_reject_payout_empty_reason_rejected`: 422 validation error on empty reason string.
3. `TestSubsequentWebhookReconciliation`:
   - `test_subsequent_payout_processed_reconciles_and_resolves_case`: Full reconciliation flow, ERP update, transition to `CASE_RESOLVED`, audit chain verification.
4. `TestCaseQueryEndpoints`:
   - `test_get_case_detail_workspace`: Detailed workspace response with audit status.
   - `test_list_cases_with_filter`: State filtering and pagination.

---

## Verification

Run the Phase 11 test suite:
```bash
pytest backend/tests/test_approval.py -v
```

Run all unit tests across all 11 phases:
```bash
pytest backend/tests/ -v
```
