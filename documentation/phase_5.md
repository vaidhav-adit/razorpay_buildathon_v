# Phase 5 Documentation: Cryptographic Audit Ledger

## Overview

Phase 5 implemented the Cryptographic Audit Ledger (`backend/app/audit.py`) and its audit trail endpoint (`backend/app/api/audit.py`).

In accordance with the foundational architectural principle:
> **AI reasons. Deterministic code executes. Humans authorize money movement.**

The audit ledger provides a tamper-evident audit trail for every action, decision, API call, and state transition. It uses SHA-256 cryptographic hash chaining (similar in concept to git commit history or blockchain blocks, without the bloat of distributed consensus). Modifying any past event or payload breaks the hash chain for all subsequent events, allowing instant mathematical verification.

---

## What Was Built

### 1. Cryptographic Chaining Engine (`backend/app/audit.py`)
- **Deterministic Payload Fingerprinting (`compute_payload_hash`)**:
  - Computes SHA-256 digests of input and output data.
  - Dicts/JSON objects are serialized with sorted keys to ensure consistent hashes regardless of dictionary ordering.
  - Keeps raw confidential banking details out of hashes while preserving verifiable proof of data integrity.
- **Block Chaining (`compute_event_hash`)**:
  - Computes the canonical block hash:
    `SHA256(case_id | event_type | actor | action | target | reason | input_hash | output_hash | approval_required | previous_hash)`
- **Append-Only Logging (`log_audit_event`)**:
  - Automatically retrieves the preceding event's `event_hash` to set as `previous_hash`.
  - Sets `previous_hash = ""` for the initial genesis event in a case.
  - Inserts and commits the new event into the `audit_events` table.
- **Verification Engine (`verify_chain` / `verify_events_chain`)**:
  - Walks the chronological event sequence for a case.
  - Validates that the genesis block has an empty `previous_hash`.
  - Validates that each block's `previous_hash` matches the preceding block's `event_hash`.
  - Recomputes the SHA-256 hash of each block and compares with stored `event_hash`.
  - Returns `ChainVerificationResult` (`VERIFIED`, `TAMPERED`, or `EMPTY`) with the exact `broken_at_index` and `broken_event_id` upon any discrepancy.

### 2. Audit API Router (`backend/app/api/audit.py`)
- Endpoint: `GET /cases/{case_id}/audit`
- Returns:
  - `case_id`: The requested case ID.
  - `verification`: Mathematical integrity result (`status: "VERIFIED" | "TAMPERED" | "EMPTY"`, `total_events`, `is_valid`).
  - `events`: Array of all audit events in chronological order with timestamps and hashes.

---

## Unit Test Suite (`backend/tests/test_audit.py`)

A comprehensive unit test suite covering:
1. `TestPayloadHashing`: Verified key-ordering independence in JSON payloads and string hashing.
2. `TestChainVerificationInMemory`:
   - Empty chain handling.
   - Genesis block verification.
   - Multi-event chain verification.
   - Content tampering detection (modified actor/action/reason/payload).
   - Broken link detection (forged or modified `previous_hash`).
3. `TestAuditDatabaseIntegration`: Validated sequential chaining and verification against a SQLite database session.
4. `TestAuditAPIEndpoint`: Validated `GET /cases/{case_id}/audit` HTTP response schema.

---

## Verification

To run the audit ledger tests:
```bash
pytest backend/tests/test_audit.py -v
```
*(Or run all test suites: `pytest backend/tests/ -v`)*
