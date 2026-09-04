# Implementation Plan — RazorpayX Payout Exception Resolution Agent

Backend first. Phase by phase. Each phase is independently testable and committable to git before moving on. UI comes only after the backend is solid and all test scenarios are passing.

---

## Git Workflow and Code Style Rules

These apply to every phase without exception.

Git:
    - Each phase ends with a git commit. The commit message must clearly name the phase (e.g. "Phase 1: project scaffold and database models").
    - Before the very first commit, create the GitHub repo and set it as the remote origin.
    - Before every commit, update README.md to reflect what has been built in that phase, how to set it up locally, and what the next phase is.
    - Never push broken or untested code. Each phase must be working before commit.

Code style:
    - Comment all non-obvious lines and every function or class with a brief docstring.
    - Keep functions small, focused, and single-purpose.
    - Use descriptive names for variables, functions, and classes. No single-letter names except loop counters.
    - Prefer explicit over implicit. A new engineer reading the code should understand it without asking anyone.
    - No dead code, no commented-out blocks, no TODO notes left in production files.

---

## Agent Framework Decision

### Outer layer: Custom Python State Machine

The state machine is a financial control boundary, not just an orchestration convenience. The LLM must not be able to skip DATA_VALIDATED and jump to PAYOUT_EXECUTED. That constraint must hold regardless of what the model outputs. This requires a hard-coded transition table owned entirely by our code, independently testable with zero LLM involvement, and with every transition logged to the audit ledger.

### Inner layer: LangGraph (inside state nodes)

Within a given state node (for example the VENDOR_CONTACTED node), the agent needs to sequence tool calls, parse responses, and decide what to do next based on partial information. This is exactly where LangGraph earns its place: tool-call sequencing, conditional branching on tool outputs, and resumability. LangGraph sits inside the agent reasoning loop within a node, not as the outer state machine controlling financial transitions.

Summary:
- Custom state machine: controls which financial stage the case is in and what transitions are legal.
- LangGraph: handles the agent's internal reasoning and tool-call sequencing within a stage.

---

## Phase 1 — Project Scaffold and Database

Set up the FastAPI project directory structure. Define all PostgreSQL tables using SQLAlchemy models. Write Alembic migrations. No business logic yet.

Tables to create:
    vendors
    payouts
    recovery_cases
    fund_accounts
    vendor_messages
    agent_actions
    approvals
    audit_events

Deliverable: running FastAPI server, all tables created, basic health-check endpoint at GET /health. Commit to git.

---

## Phase 2 — State Machine (no LLM, no Razorpay)

Write the pure Python state machine. Define all states as a Python enum. Define all legal transitions in a transition table. Write a transition function that takes (current_state, event) and returns new_state or raises an error for illegal transitions.

States:
    PAYOUT_FAILED
    CASE_CREATED
    FAILURE_CLASSIFIED
    RECOVERY_STRATEGY_SELECTED
    VENDOR_CONTACTED
    INFORMATION_RECEIVED
    DATA_VALIDATED
    BANK_VALIDATED
    POLICY_CHECK
    PAYOUT_READY
    HUMAN_REVIEW
    HUMAN_APPROVAL
    PAYOUT_EXECUTED
    PAYOUT_CONFIRMED
    CASE_RESOLVED
    ESCALATED
    BLOCKED

Write unit tests for every transition. Illegal transitions must raise, not silently fail.

Deliverable: state machine module, fully tested, zero LLM dependency. Commit to git.

---

## Phase 3 — Failure Classifier (deterministic code)

Write the hard-coded mapping from (source, reason) pairs to recovery strategies. This is a plain Python dictionary lookup, not an LLM call.

Mappings:
    beneficiary_bank / invalid_ifsc_code                => vendor_remediation
    beneficiary_bank / bank_account_closed              => vendor_remediation
    beneficiary_bank / bank_account_invalid             => vendor_remediation
    beneficiary_bank / bank_account_frozen              => human_escalation
    beneficiary_bank / beneficiary_bank_offline         => schedule_retry
    beneficiary_bank / beneficiary_bank_technical_error => schedule_retry
    beneficiary_bank / npci_beneficiary_timeout         => schedule_retry
    beneficiary_bank / imps_not_allowed                 => internal_workflow_decision
    business / insufficient_funds                       => finance_escalation
    gateway / timeout                                   => retry_logic
    validation / low_name_match                         => human_review
    validation / inactive_account                       => block

Write unit tests for every mapping. Any unknown (source, reason) pair must return an explicit UNKNOWN_FAILURE strategy and escalate, not crash.

Deliverable: classifier module, fully tested. Commit to git.

---

## Phase 4 — Policy Engine

Write the authority/policy engine. Given an action name and current case context (state, risk_level, amount), it returns one of: ALLOW, REQUIRE_APPROVAL, or BLOCK.

Policy levels:
    Level 1 (Autonomous): read operations, classify failure, send vendor message, create case, parse response.
    Level 2 (Controlled Mutation): create fund account, deactivate fund account, update ERP, initiate validation.
    Level 3 (Financially Consequential): execute payout, override validation, override risk policy.

Rules:
    All Level 1 actions => ALLOW always.
    Level 2 actions => ALLOW if all policy conditions pass (data validated, vendor identity verified, within thresholds). Otherwise => REQUIRE_APPROVAL.
    All Level 3 actions => REQUIRE_APPROVAL always, no exceptions.
    Any action in BLOCKED or ESCALATED state => BLOCK.

Write unit tests for every rule including edge cases and boundary thresholds.

Deliverable: policy engine module, fully tested. Commit to git.

---

## Phase 5 — Cryptographic Audit Ledger

Write the audit event system. Every call to log_audit_event appends a row to the audit_events table.

Each event stores:
    event_id, case_id, event_type, actor, action, target,
    input_hash, output_hash, approval_required,
    previous_hash, event_hash, timestamp

event_hash = SHA256(event_content_string + previous_hash)

Write a verify_chain(case_id) function that walks all events for a case in order and confirms each event_hash is correct. Returns VERIFIED or TAMPERED with the index of the first broken link.

Write unit tests:
    Chain verifies correctly for untampered events.
    Modifying any event payload breaks the chain from that point forward.
    The first event (with no previous_hash) is correctly anchored.

Expose GET /cases/:id/audit endpoint that returns the full event chain plus verification result.

Deliverable: audit ledger module + endpoint, fully tested. Commit to git.

---

## Phase 6 — Razorpay Integration (Test Mode)

Wire up real Razorpay Test Mode API calls. Implement all Razorpay tools as functions. Each function must:
    1. Go through the policy engine before executing.
    2. Log an audit event after executing.
    3. Return a typed Pydantic response object.

Tools to implement:
    get_payout(payout_id)            GET /v1/payouts/:id
    get_contact(contact_id)          GET /v1/contacts/:id
    get_fund_accounts(contact_id)    GET /v1/fund_accounts?contact_id=:id
    create_fund_account(...)         POST /v1/fund_accounts       [Level 2]
    deactivate_fund_account(...)     PATCH /v1/fund_accounts/:id  [Level 2]
    create_payout(...)               POST /v1/payouts             [Level 3]

Implement the webhook ingestion endpoint:
    POST /webhooks/razorpay
    Verify HMAC-SHA256 signature from the razorpay-signature header.
    Store raw event.
    Create a Recovery Case record.
    Run the failure classifier.
    Transition state machine to CASE_CREATED.
    Return HTTP 200 immediately (agent runs asynchronously).

Deliverable: you can trigger a payout in Razorpay Test Mode, watch it fail, and see the webhook create a Recovery Case in the database. Commit to git.

---

## Phase 7 — Zoho Books Integration (Sandbox)

Implement OAuth 2.0 token exchange and refresh for Zoho Books Sandbox. Implement all ERP tools:
    find_vendor(reference_id)                  GET /books/v3/contacts
    find_invoice(invoice_id)                   GET /books/v3/bills/:id
    get_vendor_bank_details(vendor_id)         GET /books/v3/contacts/:id/bankaccounts
    update_vendor_bank_details(vendor_id, ...) PUT /books/v3/contacts/:id/bankaccounts  [Level 2]
    update_invoice_status(invoice_id, status)  PUT /books/v3/bills/:id                  [Level 2]

Implement Zoho webhook endpoint:
    POST /webhooks/zoho
    Receives bill approval events.
    Triggers initial payout creation via Razorpay.

Deliverable: agent can look up vendor and invoice context from Zoho and write back after case resolution. Commit to git.

---

## Phase 8 — Mock Account Validation Service

Write a local mock for POST /v1/fund_accounts/validations. This endpoint is unavailable in Razorpay Test Mode.

The mock must:
    Accept a fund_account_id.
    Return a configurable response: account_status, registered_name, name_match_score.
    Support scenario overrides so tests can dial name_match_score to any value.
    Label its responses with a SIMULATED flag so the UI can display it honestly.

Deterministic code (not the LLM) evaluates the result:
    account_status != active  =>  STOP, transition to BLOCKED
    name_match_score < threshold  =>  transition to HUMAN_REVIEW
    both pass  =>  continue to POLICY_CHECK

Deliverable: mock validation service, configurable per test scenario. Commit to git.

---

## Phase 9 — Vendor Communication Adapter

Write the Communication Adapter with a demo backend. At this stage it is purely an API with no UI.

Endpoints:
    POST /vendor/message/send      Accepts case_id, vendor_id, message_body. Stores to vendor_messages table.
    GET  /vendor/message/receive   Polls for inbound messages from vendor for a given case.

The adapter is designed so that in production it would swap the demo backend for WhatsApp Business API. For now, an internal test client can POST fake vendor replies to simulate responses.

Deliverable: message adapter API. Commit to git.

---

## Phase 10 — LLM Agent (wired into the state machine via LangGraph)

Now and only now add the LLM.

Architecture:
    The outer custom state machine controls which stage the case is in.
    When the state machine enters a node that requires reasoning (e.g. VENDOR_CONTACTED, INFORMATION_RECEIVED), it hands control to a LangGraph agent graph for that node.
    The LangGraph graph defines the tool-call loop: call tool, observe result, decide next tool or decide to exit node.
    When the LangGraph loop exits, it returns a structured output to the state machine.
    The state machine then decides the next legal transition based on that output.

Tool schemas to define for the LLM (as LangGraph tool nodes):
    get_payout, get_contact, get_fund_accounts
    find_vendor, find_invoice, get_vendor_bank_details
    send_vendor_message, read_vendor_response, request_missing_information
    create_fund_account, deactivate_fund_account, validate_fund_account
    update_vendor_bank_details, update_invoice_status
    prepare_replacement_payout, request_human_approval

All tool executions still go through the policy engine. The LLM does not bypass it.

Data extraction: the LLM parses vendor replies and outputs a strict Pydantic schema (account_holder_name, account_number, ifsc). Deterministic code validates the schema before any fund account creation.

Deliverable: full golden path working end-to-end (invalid_ifsc_code from webhook to HUMAN_APPROVAL state) without any UI. Test by manually calling POST /cases/:id/approve after the agent halts. Commit to git.

---

## Phase 11 — Human Approval API

Implement the approval endpoints:
    POST /cases/:id/approve   Validates the case is in HUMAN_APPROVAL state. Calls create_payout. Logs audit event with actor = finance_controller and human decision = APPROVE.
    POST /cases/:id/reject    Transitions case to CASE_RESOLVED with rejection note. Logs audit event.

When the subsequent payout.processed webhook arrives from Razorpay, the system:
    Calls update_invoice_status in Zoho.
    Transitions state to PAYOUT_CONFIRMED then CASE_RESOLVED.
    Logs final audit event.
    Verifies chain integrity.

Deliverable: full end-to-end golden path including payout execution and reconciliation. Commit to git.

---

## Phase 12 — Test Case Engine and Evaluation Harness

Build a scenario runner. Ten predefined test scenarios covering the full decision space.

    CASE 001: invalid_ifsc_code                => vendor_remediation (golden path)
    CASE 002: bank_account_closed              => vendor provides entirely new account
    CASE 003: bank_account_invalid             => re-verification with vendor
    CASE 004: beneficiary_bank_offline         => controlled retry, no vendor contact
    CASE 005: beneficiary_bank_technical_error => retry
    CASE 006: insufficient_funds               => finance escalation, no vendor contact
    CASE 007: low_name_match_score             => human review triggered
    CASE 008: vendor gives incomplete details  => agent sends targeted follow-up
    CASE 009: vendor gives contradictory details => escalate
    CASE 010: possible impersonation           => BLOCK immediately

Evaluation metrics reported per run:
    Correct failure diagnosis          (target: 95% or above)
    Correct recovery strategy          (target: 95% or above)
    Correct tool calls                 (target: 95% or above)
    Data extraction accuracy           (target: 97% or above)
    Policy compliance                  (target: 100%)
    Unnecessary escalations            (target: below 5%)
    Authorized financial actions       (target: 100% human-approved)
    Unauthorized financial actions     (target: 0, hard requirement)

Deliverable: pytest command that runs all 10 scenarios and prints the evaluation report. All metrics must pass before any frontend work begins. Commit to git.

---

## Phase 13 — Frontend Dashboard (Next.js + TypeScript)

Only after Phase 12 is passing.

See the UI section below for the full design.

---

## Phase 14 — Demo Polish and Adversarial Testing

Run adversarial cases against the fully integrated system. Fix any gaps. Prepare the cinematic golden-path demo flow. Add the SIMULATED labels to the UI for mocked components. Final git tag.

---

## UI Dashboard Design — Internal Audit and Finance Team

The product is positioned as a mission control room for the internal finance and audit team. The screen is always live. Cases flow in, work through stages, and exit as resolved or escalated. The agent is visible doing its work in real time.

### Overall Layout

Three top-level views accessible from the top navigation bar:
    Active Cases       (default view, described below)
    Closed Cases       (resolved and rejected cases, searchable)
    Evaluation         (test case launcher and metrics table)

### Active Cases View

Left sidebar: case list. Each card shows vendor name, amount, failure reason, current state as a colour-coded badge, and time elapsed. Clicking a card opens the case in the main area.

Main area: case detail view. This is the primary working surface.

    Top strip: case metadata. Case ID, payout ID, vendor name, amount, failure reason, current state badge, risk level badge.

    Agent Action Terminal: a live-scrolling feed of every step the agent has taken, timestamped. Each line shows what happened, who did it (AI, system, or human), and whether it was a read or a write action. This is the brain-visible element. The audit team can see the agent reasoning in real time.

    Cryptographic Audit Timeline: same events in a more structured table. Columns: timestamp, actor type (External Fact / AI Decision / System Action / Human Decision), action, result. A VERIFIED badge anchors the table header. If the chain is tampered, it turns red with TAMPERED.

Right side panel: context drawer with tabs.
    Payout tab: original payout details pulled from Razorpay.
    Vendor tab: vendor record from Zoho Books.
    Bank Validation tab: validation result including account_status, registered_name, name_match_score. Labelled SIMULATED (DEMO ENVIRONMENT) in the demo.

Bottom strip: Vendor Communication entry point. A compact bar at the bottom with a WhatsApp-style logo icon and a label showing the vendor name. When clicked, a chat panel slides up from the bottom (occupying the lower quarter of the screen). The simulated WhatsApp conversation between the agent and the vendor is displayed here in bubble format, agent messages on one side and vendor replies on the other. This panel is read-only for the audit team (they observe but do not intervene). The panel is dismissible by clicking the icon again.

Floating approval card: when a Level 3 action is triggered (replacement payout ready for execution), a prominent card slides in from the top-right of the screen like a notification. It shows: vendor, amount, original failure, old account (deactivated), new account (validated), bank validation result, name match score, ERP updated status. Two buttons: APPROVE and REJECT. These are inline — the team does not navigate to a new page. On approval or rejection, the card dismisses and the Agent Action Terminal updates immediately.

### Evaluation View

A test case launcher with a grid of the 10 predefined scenarios. Each can be triggered individually or all run as a batch. Results populate a metrics table live. The most prominent metric displayed is Unauthorized Financial Actions which should always read 0.

---

## Files Accessed and Why

- antigrav_plan.md: Referenced to ensure this implementation plan is consistent with and extends the overall architecture documented there.
