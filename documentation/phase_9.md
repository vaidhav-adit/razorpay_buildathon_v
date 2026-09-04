# Phase 9 Documentation: Vendor Communication Adapter

## Overview

Phase 9 implements the Vendor Communication Adapter (`backend/app/services/communication_adapter.py`) and its corresponding REST endpoints (`backend/app/api/vendor_communication.py`).

In accordance with our core architecture:
> **AI reasons. Deterministic code executes. Humans authorize money movement.**

The communication adapter provides a channel-agnostic messaging layer that supports both real communication APIs (e.g. WhatsApp Business API / Twilio) and demo simulator interfaces (Vendor Chat Simulator in the frontend). Every outbound inquiry sent by the agent and every inbound reply received from the vendor is persisted in PostgreSQL and logged as a cryptographically chained `AuditEvent`.

---

## What Was Built

### 1. Regex Extraction Engine (`extract_banking_details_from_text`)
- Scans unstructured vendor conversational responses for valid Indian banking credentials:
  - **IFSC Codes**: Matches standard 11-character format (`[A-Z]{4}0[A-Z0-9]{6}`).
  - **Bank Account Numbers**: Matches contiguous numeric sequences (9 to 18 digits).
- Populates the `extracted_data` JSON column automatically upon message ingestion.

### 2. Vendor Communication Adapter Service (`VendorCommunicationAdapter`)
- **`send_message(...)`** [Level 1 Autonomous]:
  - Emits outbound notifications to vendors (e.g. payout failure alerts, missing detail prompts).
  - Persists record with `direction = OUTBOUND`.
  - Emits `SYSTEM_ACTION` / `send_vendor_message` audit block.
- **`receive_message(...)`** [Level 1 Autonomous]:
  - Ingests inbound vendor responses.
  - Automatically parses banking credentials.
  - Persists record with `direction = INBOUND`.
  - Emits `EXTERNAL_FACT` / `receive_vendor_message` audit block.
- **`get_conversation_history(...)`**:
  - Retrieves chronological conversation history for a given case.

### 3. REST API Endpoints (`backend/app/api/vendor_communication.py`)
- `POST /vendor/message/send`: Sends an outbound agent inquiry.
- `POST /vendor/message/receive`: Simulates incoming reply from vendor/WhatsApp simulator.
- `GET /vendor/message/receive`: Polling endpoint returning recent messages for a case.
- `GET /vendor/messages/{case_id}`: Full chronological message thread for a case.

---

## Unit Test Suite (`backend/tests/test_communication.py`)

A comprehensive unit test suite covering:
1. `TestRegexExtraction`: Valid IFSC extraction, case normalization, account number matching, and blank/noise inputs.
2. `TestVendorCommunicationAdapter`:
   - Outbound message persistence and audit block creation.
   - Inbound message parsing, structured extraction, and audit chain verification.
   - Message chronological ordering.
3. `TestVendorCommunicationAPI`:
   - `POST /vendor/message/send` (HTTP 201).
   - `POST /vendor/message/receive` (HTTP 201).
   - `GET /vendor/message/receive?case_id=...` (HTTP 200).
   - `GET /vendor/messages/{case_id}` (HTTP 200).

---

## Verification

To run the Vendor Communication Adapter tests:
```bash
pytest backend/tests/test_communication.py -v
```

To run all test suites across Phases 2 through 9:
```bash
pytest backend/tests/ -v
```
