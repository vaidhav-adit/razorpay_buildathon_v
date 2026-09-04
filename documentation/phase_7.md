# Phase 7 Documentation: Zoho Books Integration (Sandbox)

## Overview

Phase 7 implements the Zoho Books Sandbox ERP client tools (`backend/app/services/zoho_client.py`) and the Zoho Webhook Ingestion API (`backend/app/api/zoho_webhooks.py`).

In accordance with our core architecture:
> **AI reasons. Deterministic code executes. Humans authorize money movement.**

The agent interacts with the ERP system (Zoho Books) strictly through strongly-typed tool interfaces. Level 1 tools execute autonomously to look up vendor records, bills, and bank accounts. Level 2 tools (modifying vendor bank accounts or updating bill status) are strictly gated by the Policy Engine and append tamper-evident records to the cryptographic audit ledger.

---

## What Was Built

### 1. OAuth 2.0 Token Manager (`backend/app/services/zoho_client.py`)
- **Lifecycle Management**: Automatic caching and token expiration tracking.
- **Auto-Refresh**: Automatically exchanges `refresh_token` for fresh access tokens prior to expiration.
- **Authorization Code Exchange**: Enables initial OAuth handshake (`exchange_authorization_code`).
- **Deterministic Simulation Fallback**: Falls back to mock sandbox responses when live credentials are not present, ensuring complete local test reproducibility.

### 2. Zoho Books Client & ERP Tools Suite (`backend/app/services/zoho_client.py`)
- **Tools Implemented**:
  1. `find_vendor(reference_id)` [Level 1 Autonomous]: Fetches vendor contact profile and existing bank accounts by reference or name.
  2. `find_invoice(invoice_id)` [Level 1 Autonomous]: Fetches invoice/bill total, balance, status, and due date.
  3. `get_vendor_bank_details(vendor_id)` [Level 1 Autonomous]: Retrieves configured bank account details for a vendor contact.
  4. `update_vendor_bank_details(vendor_id, bank_details)` [Level 2 Controlled Mutation]: Updates bank accounts in Zoho Books after penny-drop verification and vendor validation. Gated by Policy Engine.
  5. `update_invoice_status(invoice_id, status)` [Level 2 Controlled Mutation]: Updates bill/invoice payment status in Zoho Books upon payout confirmation. Gated by Policy Engine.
- **Audit Logging**: Every tool execution appends an `AuditEvent` with input and output hashes to the cryptographic audit trail.

### 3. Zoho Webhook Ingestion Pipeline (`backend/app/api/zoho_webhooks.py`)
- **Endpoint**: `POST /webhooks/zoho`
- Ingests bill approval and invoice lifecycle events from Zoho Books Sandbox to initiate exception resolution workflows.

---

## Unit Test Suite (`backend/tests/test_zoho.py`)

A comprehensive unit test suite covering:
1. `TestZohoOAuth`:
   - Valid token caching and direct retrieval.
   - Automatic token refresh upon expiration.
   - OAuth authorization code exchange.
2. `TestZohoTools`:
   - Level 1 tools (`find_vendor`, `find_invoice`, `get_vendor_bank_details`) autonomous execution and audit logging.
   - Level 2 tool `update_vendor_bank_details`: policy pass when data validated; policy block when unvalidated.
   - Level 2 tool `update_invoice_status`: policy pass on confirmed payout; policy block on blocked case state.
   - Cryptographic audit chain verification after tool execution.
3. `TestZohoWebhook`:
   - Valid bill approval webhook ingestion (HTTP 200).
   - Malformed payload rejection (HTTP 400).

---

## Verification

To run the Zoho Books integration tests:
```bash
pytest backend/tests/test_zoho.py -v
```

To run all test suites across Phases 2 through 7:
```bash
pytest backend/tests/ -v
```
