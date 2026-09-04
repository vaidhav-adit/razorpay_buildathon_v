# Phase 3 Documentation: Deterministic Failure Classifier

## Overview

Phase 3 implemented the deterministic Failure Classifier module (`backend/app/classifier.py`).

In accordance with the foundational architectural principle:
> **AI reasons. Deterministic code executes. Humans authorize money movement.**

The failure classifier maps Razorpay webhook `status_details` (`source`, `reason`) directly to standard `RecoveryStrategy` outcomes through a deterministic dictionary lookup rather than an LLM prompt. This guarantees predictable, reproducible, and instantaneous classification across all failure modes.

---

## What Was Built

### 1. Classification Engine (`backend/app/classifier.py`)
- **`ClassificationResult` Schema**: A structured Pydantic model containing:
  - `strategy`: `RecoveryStrategy` enum value.
  - `source` and `reason`: Normalized (lowercase, stripped) strings.
  - `description`: Plain English explanation of the failure.
  - `is_retryable`: Boolean indicating if the failure is transient.
  - `requires_vendor_contact`: Boolean indicating if updated banking info is required.
  - `requires_human_attention`: Boolean indicating if human operations must intervene.
  - `suggested_action`: Actionable next step guidance.
- **`FAILURE_CLASSIFICATION_MAP`**: Complete mapping matrix:
  - `beneficiary_bank / invalid_ifsc_code` -> `VENDOR_REMEDIATION`
  - `beneficiary_bank / bank_account_closed` -> `VENDOR_REMEDIATION`
  - `beneficiary_bank / bank_account_invalid` -> `VENDOR_REMEDIATION`
  - `beneficiary_bank / bank_account_frozen` -> `HUMAN_ESCALATION`
  - `beneficiary_bank / beneficiary_bank_offline` -> `SCHEDULE_RETRY`
  - `beneficiary_bank / beneficiary_bank_technical_error` -> `SCHEDULE_RETRY`
  - `beneficiary_bank / npci_beneficiary_timeout` -> `SCHEDULE_RETRY`
  - `beneficiary_bank / imps_not_allowed` -> `INTERNAL_WORKFLOW`
  - `business / insufficient_funds` -> `FINANCE_ESCALATION`
  - `gateway / timeout` -> `RETRY_LOGIC`
  - `validation / low_name_match` -> `HUMAN_ESCALATION`
  - `validation / inactive_account` -> `BLOCK`
- **Graceful Fallback**: Unknown or unrecognized `(source, reason)` pairs safely return `UNKNOWN_FAILURE` with `requires_human_attention=True` without crashing.

---

## Unit Test Suite (`backend/tests/test_classifier.py`)

A comprehensive unit test suite covering:
1. `TestFailureClassifierKnownMappings`: Verified all 12 defined mappings against expected recovery strategy, retry flags, and vendor contact requirements.
2. `TestFailureClassifierNormalization`: Tested resilience against uppercase, mixed case, and extra whitespace.
3. `TestFailureClassifierUnknownAndEdgeCases`: Tested unmapped error codes, unexpected gateway codes, `None` inputs, and empty string handling.
4. `TestFailureClassifierCoverage`: Verified all entries in the classification table are well-formed.

---

## Verification

To run all tests including the classifier:
```bash
pytest backend/tests/ -v
```
