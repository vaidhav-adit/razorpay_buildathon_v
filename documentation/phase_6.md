# Phase 6 Documentation: RazorpayX Integration (Test Mode)

## Overview

Phase 6 implemented real RazorpayX Test Mode client tools (`backend/app/services/razorpay_client.py`) and the Webhook Ingestion API (`backend/app/api/webhooks.py`).

In accordance with the foundational architectural principle:
> **AI reasons. Deterministic code executes. Humans authorize money movement.**

The agent interacts with RazorpayX exclusively through typed tool functions. Each tool is gated by the Policy Engine (verifying authority level and risk limits) and produces an append-only AuditEvent in the cryptographic ledger. The webhook endpoint cryptographically verifies HMAC-SHA256 signatures, ingests payout failure events, instantiates Recovery Cases, and triggers deterministic root-cause classification.

---

## What Was Built

### 1. RazorpayX Client & Tool Suite (`backend/app/services/razorpay_client.py`)
- **HTTP Basic Authentication**: Interacts with `https://api.razorpay.com/v1` using `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET`. Includes robust simulation fallbacks for local offline testing.
- **HMAC-SHA256 Signature Verification (`verify_razorpay_signature`)**: Validates the cryptographic integrity of incoming webhook payloads using the shared `RAZORPAY_WEBHOOK_SECRET`.
- **Tools Implemented**:
  1. `get_payout(payout_id)` [Level 1 Autonomous]: Fetches payout status, mode, and `status_details`.
  2. `get_contact(contact_id)` [Level 1 Autonomous]: Fetches vendor contact profile.
  3. `get_fund_accounts(contact_id)` [Level 1 Autonomous]: Lists existing fund accounts for a vendor.
  4. `create_fund_account(...)` [Level 2 Controlled Mutation]: Creates a new immutable fund account when IFSC/data validation passes.
  5. `deactivate_fund_account(fund_account_id)` [Level 2 Controlled Mutation]: Deactivates faulty/failed fund accounts.
  6. `create_payout(...)` [Level 3 Financially Consequential]: Initiates a replacement payout. **Strictly protected by `is_human_authorized=True` check**.
- **Audit Logging**: Every tool execution appends an `AuditEvent` with input and output hashes to the tamper-evident ledger.

### 2. Webhook Ingestion Pipeline (`backend/app/api/webhooks.py`)
- **Endpoint**: `POST /webhooks/razorpay`
- **Security**: Validates `X-Razorpay-Signature` header.
- **Entity Ingestion**:
  - Automatically provisions or matches `Vendor` and `Payout` records in PostgreSQL.
  - Generates a unique `case_number` (e.g. `CASE-20260904-XXXXXX`).
  - Instantiates `RecoveryCase` in state `CASE_CREATED`.
  - Runs deterministic `classify_failure(source, reason)` to set `recovery_strategy`.
  - Logs the genesis `EXTERNAL_FACT` audit event.
  - Returns `HTTP 200 OK` with `{ "status": "received", "case_id": "...", "strategy": "..." }`.

---

## Unit Test Suite (`backend/tests/test_razorpay.py`)

A comprehensive unit test suite covering:
1. `TestWebhookSignatureVerification`: Valid HMAC-SHA256 calculation, invalid signature rejection, and missing parameter handling.
2. `TestWebhookIngestionEndpoint`:
   - Full ingestion of `payout.failed` event creating `Vendor`, `Payout`, `RecoveryCase`, and `AuditEvent`.
   - Verified genesis block cryptographic chain integrity for newly created cases.
   - Non-failure event filtering (`payout.processed` ignored).
   - Invalid signature rejection (HTTP 400).
3. `TestRazorpayTools`:
   - Level 1 tools (`get_payout`, `get_contact`, `get_fund_accounts`) autonomous execution and audit logging.
   - Level 2 tools (`create_fund_account`, `deactivate_fund_account`) policy-gated execution and unvalidated data rejection.
   - Level 3 tools (`create_payout`) human authorization enforcement.

---

## Verification

To run the Razorpay integration tests:
```bash
pytest backend/tests/test_razorpay.py -v
```
*(Or run all test suites across the application: `pytest backend/tests/ -v`)*
