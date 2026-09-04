# Phase 10 Documentation: LLM Agent & State Machine Orchestration

## Overview

Phase 10 implements the AI Reasoning Agent and integrates it with the outer deterministic State Machine (`backend/app/agent/`).

In accordance with our core architecture:
> **AI reasons. Deterministic code executes. Humans authorize money movement.**

The system strictly separates macro financial state governance from micro internal reasoning:
1. **Outer Layer (Custom State Machine)**: Strictly controls macro financial stages (`CASE_CREATED`, `VENDOR_CONTACTED`, `BANK_VALIDATED`, `HUMAN_APPROVAL`, etc.) and determines which state transitions are legally permitted.
2. **Inner Layer (Reasoning Agent & Tool Loop)**: Handles context gathering, prompt generation, LLM banking data extraction, and tool sequencing inside each stage.
3. **Hard Human Boundary**: The agent has Level 1 (autonomous read) and Level 2 (controlled mutation) permissions, but **NEVER executes Level 3 payouts autonomously**. The agent prepares the replacement payout payload and pauses at `HUMAN_APPROVAL` awaiting a human financial controller's decision.

---

## What Was Built

### 1. LLM Provider Layer (`backend/app/agent/llm.py`)
- **Multi-Provider Support**: Supports Google Gemini (Free Tier via `GEMINI_API_KEY`), OpenAI (`OPENAI_API_KEY`), and deterministic regex/heuristic fallback.
- **Structured Extraction (`extract_banking_data`)**: Extracts `account_holder_name`, `account_number`, and `ifsc` into strict Pydantic models with automated regex syntax validation.
- **Vendor Outreach Generation (`generate_vendor_message`)**: Drafts polite and context-aware payout failure remediation messages.

### 2. Tool Wrappers (`backend/app/agent/tools.py`)
- Standardized tool calling functions that wrap Razorpay, Zoho Books, Account Validation, and Communication services:
  - Policy engine permission checks on every call.
  - Recording operational actions in `agent_actions`.
  - Logging append-only cryptographic records in `audit_events`.

### 3. Reasoning Nodes (`backend/app/agent/graph.py`)
- Node handlers corresponding to state machine stages:
  - `run_case_classification_node`: Failure classification & strategy selection.
  - `run_vendor_contact_node`: Vendor context gathering & outreach dispatch.
  - `run_information_extraction_node`: Inbound reply parsing & syntax validation.
  - `run_bank_validation_node`: Fund account provisioning & penny-drop validation.
  - `run_policy_and_payout_prep_node`: Policy checks, old account deactivation, ERP update, and approval preparation.

### 4. Agent Orchestrator (`backend/app/agent/orchestrator.py`)
- Top-level workflow runner coordinating legal state machine transitions with inner reasoning outputs.
- Ensures safe halting at `HUMAN_APPROVAL`, `HUMAN_REVIEW`, `BLOCKED`, or while awaiting vendor replies.

---

## Challenges Faced, Errors Encountered, and How We Fixed Them

During end-to-end integration and adversarial testing, we encountered several architectural and implementation challenges. Here is a detailed breakdown of each error and its resolution:

### 1. SQLAlchemy Binding Error with Dataclass Objects
- **Error**: `sqlalchemy.exc.ProgrammingError: (sqlite3.ProgrammingError) Error binding parameter 1: type 'ClassificationResult' is not supported`.
- **Root Cause**: `classify_failure()` returns a `ClassificationResult` Pydantic model/dataclass containing the strategy, descriptions, and action flags. In `run_case_classification_node`, `case.recovery_strategy = strategy` assigned the entire object instead of the enum string.
- **Fix**: Updated `graph.py` to assign the exact enum: `case.recovery_strategy = strategy_result.strategy`.

---

### 2. Direct Indexing KeyError on Extracted Banking Details
- **Error**: `KeyError: 'account_number'` in `run_bank_validation_node`.
- **Root Cause**: When tests initialized cases directly at `DATA_VALIDATED` (skipping `VENDOR_CONTACTED`), `extracted_banking_data` in the orchestrator's local loop was empty `{}`. `run_bank_validation_node` attempted direct indexing `banking_data["account_number"]`.
- **Fix**:
  1. Updated `orchestrator.py` to parse `vendor_reply_text` or fetch the latest inbound message if starting at `DATA_VALIDATED` with an empty extraction cache.
  2. In `graph.py` (`run_bank_validation_node`), used safe getters `.get("account_number")` with fallback to vendor profile details.

---

### 3. Missing `is_valid` Property on `ExtractedBankingData`
- **Error**: `AttributeError: 'ExtractedBankingData' object has no attribute 'is_valid'`.
- **Root Cause**: The orchestrator checked `extracted.is_valid` to determine whether extracted credentials satisfied Indian banking formats (IFSC code and account number regexes), but `ExtractedBankingData` lacked the property.
- **Fix**: Added a property to `ExtractedBankingData` in `backend/app/agent/llm.py`:
  ```python
  @property
  def is_valid(self) -> bool:
      if not self.account_number or not self.ifsc:
          return False
      ifsc_valid = bool(re.match(r"^[A-Z]{4}0[A-Z0-9]{6}$", self.ifsc.upper()))
      acc_valid = bool(re.match(r"^\d{9,18}$", str(self.account_number).strip()))
      return ifsc_valid and acc_valid
  ```

---

### 4. String vs Enum `.value` AttributeErrors in Audit Logging and State Machine
- **Error**: `AttributeError: 'str' object has no attribute 'value'`.
- **Root Cause**: In SQLAlchemy models, `case.state` is persisted as a plain `str`. When `_apply_transition` and `InvalidStateTransitionError` accessed `.value` directly on `current_state`, it threw an AttributeError whenever the state was passed as a raw string instead of a `CaseState` enum.
- **Fix**: Replaced all direct `.value` lookups with safe attribute checks:
  ```python
  cur_name = current_state.value if hasattr(current_state, "value") else str(current_state)
  ```

---

### 5. State Transition Skipping & Strict Matrix Compliance
- **Error 1**: `InvalidStateTransitionError: Invalid state transition from 'CASE_CREATED' to 'RECOVERY_STRATEGY_SELECTED'`.
- **Error 2**: `InvalidStateTransitionError: Invalid state transition from 'VENDOR_CONTACTED' to 'DATA_VALIDATED'`.
- **Root Cause**:
  - The deterministic state machine matrix explicitly requires sequential state transitions:
    - `CASE_CREATED` -> `FAILURE_CLASSIFIED` -> `RECOVERY_STRATEGY_SELECTED`
    - `VENDOR_CONTACTED` -> `INFORMATION_RECEIVED` -> `DATA_VALIDATED`
  - Some graph nodes were attempting to jump directly across multiple states in a single return statement.
- **Fix**:
  1. In `orchestrator.py`, enforced strict sequential stepping: `CASE_CREATED` first transitions to `FAILURE_CLASSIFIED` before entering `RECOVERY_STRATEGY_SELECTED`.
  2. In `graph.py`, updated `run_information_extraction_node` to return `next_state=CaseState.INFORMATION_RECEIVED`. The orchestrator then validates syntax at `INFORMATION_RECEIVED` and advances to `DATA_VALIDATED`.

---

### 6. Missing `HUMAN_REVIEW` Transition from `DATA_VALIDATED`
- **Error**: `InvalidStateTransitionError: Invalid state transition from 'DATA_VALIDATED' to 'HUMAN_REVIEW'. Allowed next states: BANK_VALIDATED, BLOCKED, ESCALATED, VENDOR_CONTACTED`.
- **Root Cause**: Penny-drop bank account validation executes at the `DATA_VALIDATED` node. When the penny-drop service returns a name match score below threshold (e.g. 62%), the policy engine diverts the case to `HUMAN_REVIEW`. However, `CaseState.HUMAN_REVIEW` was missing from `ALLOWED_TRANSITIONS[CaseState.DATA_VALIDATED]`.
- **Fix**: Added `CaseState.HUMAN_REVIEW` to `ALLOWED_TRANSITIONS[CaseState.DATA_VALIDATED]` in `backend/app/state_machine.py`.

---

### 7. SQLAlchemy `Approval` Model Kwarg Mismatch
- **Error**: `TypeError: 'action' is an invalid keyword argument for Approval`.
- **Root Cause**: The SQLAlchemy `Approval` model column is named `action_description` (and stores `payload` and `decision`), but `tool_prepare_replacement_payout` passed `action="execute_replacement_payout"` and `status="PENDING"`.
- **Fix**:
  1. In `backend/app/agent/tools.py`, updated `Approval` instantiation to pass `action_description="execute_replacement_payout"` and `decision=None`.
  2. In `backend/app/models/approval.py`, added `@property def action(self)` and `@property def status(self)` accessors so API callers can query `.action` and `.status` (which evaluates to `"PENDING"` while pending decision).

---

## Unit Test Suite (`backend/tests/test_agent.py`)

A comprehensive unit test suite covering:
1. `TestAgentGoldenPath`:
   - End-to-end golden path execution from `CASE_CREATED` through `VENDOR_CONTACTED`, `INFORMATION_RECEIVED`, `DATA_VALIDATED`, `BANK_VALIDATED`, `POLICY_CHECK`, and safely halting at `HUMAN_APPROVAL`.
   - Verification of `Approval` record generation (`execute_replacement_payout` pending).
   - Operational log verification in `AgentAction` (all 7 tool calls logged).
   - Complete cryptographic audit chain verification (`verify_chain` -> `VERIFIED`, 0 tampering).
2. `TestAgentAlternativePaths`:
   - Name match score mismatch (< 85%) diverting to `HUMAN_REVIEW`.
   - Inactive/frozen bank account status diverting to `BLOCKED`.

---

## Verification

To run the Agent Orchestrator tests:
```bash
pytest backend/tests/test_agent.py -v
```

To run all 143 unit tests across all 10 completed phases:
```bash
pytest backend/tests/ -v
```
