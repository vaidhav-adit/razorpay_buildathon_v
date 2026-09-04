# RazorpayX Payout Exception Resolution Agent — Engineering Plan

Last updated to include: agent framework decision (custom state machine + LangGraph) and UI dashboard design for the internal audit team.

---

## What We Are Building

Product name: RazorpayX Autonomous Payout Exception Resolution Agent
Tagline: Self-healing payouts, with humans in control.

This is not an AI chatbot. It is not a retry cron job. It is a hybrid AI and deterministic financial-control system that wakes up when a B2B vendor payout fails or is reversed, investigates the root cause, communicates with the vendor when needed, repairs the underlying data, validates the fix, and prepares a replacement payout for human authorization.

The system never autonomously moves money. The human is the final authority over the actual financial transaction.

---

## Core Architecture Principle

There are three layers of authority and this governs every design decision:

    AI reasons.
    Deterministic code executes.
    Humans authorize the movement of money.

---

## The Three Layers Explained

### Layer 1 — AI Agent (Brain)

The LLM handles:

- Understanding failure context
- Choosing the correct recovery strategy given a failure code
- Generating vendor-facing communication messages
- Parsing and extracting structured banking data from unstructured vendor replies
- Deciding what information is still missing
- Determining whether a case should be escalated or blocked

The LLM does NOT:

- Invent or hallucinate banking information
- Make the final financial decision
- Override validation thresholds
- Access Razorpay APIs directly (it calls tools; tools call APIs)
- Invent its own state transitions outside the state machine

### Layer 2 — Deterministic Code (Nervous System)

Code handles:

- Webhook receipt and HMAC-SHA256 signature verification
- State machine transitions
- Failure code classification (deterministic mapping)
- Pydantic schema validation of all extracted banking fields
- IFSC format validation
- Account number format validation
- Threshold evaluation (name match score, account status)
- Idempotency key generation
- API execution against Razorpay and Zoho
- Policy/authority engine decisions (allow vs. require approval vs. block)
- Audit event creation and hash chaining
- Financial calculations (amount, fees)

### Layer 3 — Human (Authority)

Humans control:

- Final authorization to execute the replacement payout (Level 3 action)
- Any case where the policy engine flags ambiguity or risk
- Override of the agent in adversarial scenarios
- Rejection of the recovery case if they disagree

---

## Authority Level Model

Every action the agent proposes goes through the policy engine and is assigned one of three levels.

Level 1 — Autonomous (Green): No human needed.
Examples: read payout, read vendor, classify failure, send vendor message, create recovery case, parse vendor response, retry transient error.

Level 2 — Controlled Mutation (Yellow): Requires policy check, may require human.
Examples: create new fund account, deactivate old fund account, update ERP vendor details, initiate account validation, change workflow state.

Level 3 — Financially Consequential (Red): Always requires human authorization.
Examples: execute replacement payout, approve large transaction, override validation, override risk policy.

---

## The State Machine

This is the backbone of the entire system. The LLM operates inside this state machine and cannot invent arbitrary transitions.

    PAYOUT_FAILED
          |
    CASE_CREATED
          |
    FAILURE_CLASSIFIED
          |
    RECOVERY_STRATEGY_SELECTED
          |
      [branch on strategy]
          |
    +-------------------+----------------------+
    |                   |                      |
  TRANSIENT          INTERNAL            VENDOR_DATA
  (retry)            (escalate)          (contact vendor)
                                               |
                                         VENDOR_CONTACTED
                                               |
                                      INFORMATION_RECEIVED
                                               |
                                         DATA_VALIDATED
                                               |
                                        BANK_VALIDATED
                                               |
                                         POLICY_CHECK
                                               |
                         +--------------------+--------------------+
                         |                    |                    |
                       ALLOW               ESCALATE             BLOCK
                         |                    |
                    PAYOUT_READY         HUMAN_REVIEW
                         |
                   HUMAN_APPROVAL
                         |
                 +-------+--------+
                 |                |
              APPROVE           REJECT
                 |
          PAYOUT_EXECUTED
                 |
          PAYOUT_CONFIRMED
                 |
           CASE_RESOLVED

---

## Failure Classification Map (Deterministic Code)

This is NOT an LLM reasoning task. These mappings are hard-coded:

    beneficiary_bank
        invalid_ifsc_code                  => vendor_remediation
        bank_account_closed                => vendor_remediation
        bank_account_invalid               => vendor_remediation
        bank_account_frozen                => human_escalation
        beneficiary_bank_offline           => schedule_retry
        beneficiary_bank_technical_error   => schedule_retry
        npci_beneficiary_timeout           => schedule_retry
        imps_not_allowed                   => internal_workflow_decision

    business
        insufficient_funds                 => finance_escalation

    gateway
        timeout                            => retry_logic

    validation
        low_name_match                     => human_review
        inactive_account                   => block

---

## Full Tool Set

The agent calls tools. Tools call APIs. The policy engine sits between the agent and the tools.

### Razorpay Tools

    get_payout(payout_id)
        GET /v1/payouts/:id
        Returns full payout object including status_details

    get_contact(contact_id)
        GET /v1/contacts/:id
        Returns vendor contact record

    get_fund_accounts(contact_id)
        GET /v1/fund_accounts?contact_id=:id
        Returns all fund accounts for a contact

    create_fund_account(contact_id, bank_details)
        POST /v1/fund_accounts
        Creates a new immutable fund account
        Policy level: Level 2

    deactivate_fund_account(fund_account_id)
        PATCH /v1/fund_accounts/:id
        Sets is_active = false
        Policy level: Level 2

    validate_fund_account(fund_account_id)
        POST /v1/fund_accounts/validations
        Returns account_status, registered_name, name_match_score
        NOTE: MOCKED in demo (Account Validation unavailable in Razorpay Test Mode)
        Policy level: Level 2

    create_payout(fund_account_id, amount, currency, mode, idempotency_key)
        POST /v1/payouts
        ONLY called after human approval
        Policy level: Level 3

### Zoho Books (ERP) Tools

    find_vendor(reference_id)
        GET /books/v3/contacts
        Looks up vendor by invoice reference

    find_invoice(invoice_id)
        GET /books/v3/bills/:id
        Returns full invoice including amount, vendor ID

    get_vendor_bank_details(vendor_id)
        GET /books/v3/contacts/:id/bankaccounts
        Returns current bank account on file in ERP

    update_vendor_bank_details(vendor_id, new_bank_details)
        PUT /books/v3/contacts/:id/bankaccounts
        Updates ERP vendor record after validated correction
        Policy level: Level 2

    update_invoice_status(invoice_id, status)
        PUT /books/v3/bills/:id
        Marks invoice PAID after payout confirmed
        Policy level: Level 2

### Vendor Communication Tools

    send_vendor_message(vendor_id, message_body)
        Sends via Communication Adapter (demo: Vendor Chat Simulator)
        Policy level: Level 1

    read_vendor_response(vendor_id)
        Reads incoming vendor message from queue
        Policy level: Level 1

    request_missing_information(vendor_id, missing_fields)
        Generates a targeted follow-up request for specific missing fields
        Policy level: Level 1

### Control / Orchestration Tools

    create_recovery_case(payout_id, failure_details)
        Creates a new Recovery Case in PostgreSQL
        Policy level: Level 1

    update_case_state(case_id, new_state, reason)
        Transitions the state machine
        Policy level: Level 1

    request_human_approval(case_id, approval_payload)
        Creates an approval request and surfaces it to the dashboard
        Policy level: Level 3 trigger

    log_audit_event(case_id, actor, action, payload, previous_hash)
        Appends a cryptographically chained event to the audit ledger
        Called internally by every tool, not directly by the agent

---

## Razorpay APIs — Real vs. Mocked

    Razorpay payout creation              REAL (Test Mode)
    Razorpay payout failure               REAL (Test Mode)
    Razorpay payout.failed webhook        REAL
    Failure reason / status_details       REAL
    Payout retrieval (GET)                REAL (Test Mode)
    Contact/vendor APIs                   REAL (Test Mode)
    Fund account creation                 REAL (Test Mode)
    Fund account deactivation             REAL (Test Mode)
    Account validation                    MOCKED (unavailable in Test Mode)
    Zoho Books vendor/invoice             REAL (Zoho Sandbox)
    Zoho Books webhook                    REAL (Zoho Sandbox)
    Vendor communication                  SIMULATED (Vendor Chat Simulator)
    AI reasoning                          REAL
    Policy engine                         REAL
    Human approval UI                     REAL
    Audit ledger                          REAL

---

## Tech Stack

    Layer                  Technology
    -------------------------------------------------------
    Frontend               Next.js + React + TypeScript
    Backend                Python + FastAPI
    Data validation        Pydantic
    Database               PostgreSQL
    Agent LLM              OpenAI or Gemini with structured tool calling
    Agent orchestration    Two-layer model — see Agent Framework section below
    Policy engine          Python policy module (not LLM)
    Audit system           PostgreSQL + SHA-256 hash chaining
    ERP integration        Zoho Books Sandbox via OAuth 2.0
    Payment integration    Razorpay Test Mode
    Webhook ingestion      FastAPI endpoint (Razorpay + Zoho)
    Vendor communication   Simulated WhatsApp-style chat interface
    Account validation     Mocked service with real response schema
    Testing                pytest + custom scenario/evaluation harness
    Dev environment        Antigravity

Not using: Kafka, Kubernetes, blockchain, microservices, vector databases, complex ML models.

---

## Agent Framework Decision

### Outer layer: Custom Python State Machine

The state machine is a financial control boundary, not just an orchestration convenience. The LLM must not be able to skip DATA_VALIDATED and jump to PAYOUT_EXECUTED regardless of what it outputs. This requires a hard-coded transition table owned entirely by our code, independently testable with zero LLM involvement, and with every transition logged to the audit ledger.

### Inner layer: LangGraph (inside state nodes)

Within a given state node (for example the VENDOR_CONTACTED node), the agent needs to sequence tool calls, parse responses, and decide what to do next based on partial information. This is exactly where LangGraph is appropriate: tool-call sequencing, conditional branching on tool outputs, and resumability. LangGraph sits inside the agent reasoning loop within a node, not as the outer state machine controlling financial transitions.

The flow is:

    Custom state machine enters a reasoning node
           |
    Hands control to LangGraph agent graph for that node
           |
    LangGraph runs tool-call loop (call tool, observe, decide next step)
           |
    LangGraph exits with a structured output
           |
    Custom state machine receives output and decides the next legal state transition

The LLM never bypasses the policy engine. All tool calls from within the LangGraph loop still go through the policy engine before executing.

Summary:
    Custom state machine: controls which financial stage the case is in and what transitions are legal.
    LangGraph: handles the agent internal reasoning and tool-call sequencing within a stage.

---

## Database Schema

### vendors
    id, razorpay_contact_id, zoho_vendor_id, name, email, phone, created_at

### payouts
    id, razorpay_payout_id, amount, currency, fund_account_id, reference_id,
    status, status_source, status_reason, status_description, created_at

### recovery_cases
    id, payout_id, vendor_id, invoice_id, amount, failure_source, failure_reason,
    state, risk_level, action_count, human_intervention_count,
    created_at, updated_at, resolved_at

### fund_accounts
    id, razorpay_fund_account_id, contact_id, bank_name, account_number_masked,
    ifsc, account_holder_name, is_active, validation_status, name_match_score,
    created_at, deactivated_at

### vendor_messages
    id, case_id, vendor_id, direction (inbound/outbound), body,
    extracted_data, timestamp

### agent_actions
    id, case_id, tool_name, input_payload, output_payload, policy_level,
    policy_decision, timestamp

### approvals
    id, case_id, action, requested_at, decided_at, decided_by,
    decision (approve/reject), reason

### audit_events
    id, case_id, event_type, actor, action, target, input_hash, output_hash,
    approval_required, previous_hash, event_hash, timestamp

---

## Audit System (Cryptographic Audit Ledger)

Every consequential action produces an append-only event. Each event is hashed using SHA-256 incorporating the previous event hash, forming a tamper-evident chain.

Event structure:

    {
      "event_id": "evt_10294",
      "timestamp": "...",
      "case_id": "CASE_8821",
      "actor": "payout_recovery_agent",
      "action": "CREATE_FUND_ACCOUNT",
      "target": "fa_789",
      "reason": "Validated replacement banking details",
      "approval": "NOT_REQUIRED",
      "previous_hash": "...",
      "event_hash": "SHA256(event_content + previous_hash)"
    }

The dashboard shows Audit integrity: VERIFIED when the chain is unbroken.

Event actor types:
    External fact   (Razorpay webhook, bank system)
    AI decision     (LLM classification, recommendation)
    System action   (API call, state transition)
    Human decision  (approve, reject, override)

---

## Webhook Architecture

Razorpay sends POST to /webhooks/razorpay

Our server:
    1. Verifies HMAC-SHA256 signature against razorpay-signature header
    2. Stores raw event in database
    3. Creates Recovery Case
    4. Runs deterministic failure classifier
    5. Transitions state machine to CASE_CREATED
    6. Spawns agent with the structured failure context

Zoho Books sends POST to /webhooks/zoho
    Used to receive bill approval events (triggers initial payout creation flow)

---

## Policy Engine

The policy engine sits between every agent tool call and the actual execution.

Flow:
    Agent proposes action
           |
    Policy engine evaluates:
        - action type
        - policy level (1 / 2 / 3)
        - current case state
        - current risk level
        - configured thresholds
           |
    +------+-----------+--------+
    |                  |        |
  ALLOW        REQUIRE_APPROVAL  BLOCK
    |                  |
  Execute       Queue for human UI
    |
  Log audit event

The LLM never gets direct access to Razorpay. The policy engine is the gate.

---

## End-to-End Flow (Golden Path: invalid_ifsc_code)

STAGE 0 — Pre-existing context
    Vendor: ABC Technologies Pvt Ltd
    Invoice: INV-2381
    Amount: 2,00,000
    Razorpay contact: cont_123
    Fund account: fa_456
    IFSC on file: HDFC0001234 (invalid)

STAGE 1 — Payout fails
    Razorpay Test Mode sends payout.failed webhook
    Our server verifies signature

STAGE 2 — Recovery case created
    Case ID: REC-001
    State: CASE_CREATED
    Failure: beneficiary_bank / invalid_ifsc_code

STAGE 3 — Failure classified (deterministic code)
    invalid_ifsc_code => vendor_remediation strategy

STAGE 4 — Agent investigates
    Calls: get_payout(pout_123)
    Calls: find_vendor(INV-2381) via Zoho
    Calls: find_invoice(INV-2381) via Zoho
    Establishes full vendor + payout context

STAGE 5 — Agent determines missing information
    Needs: correct account holder name, account number, IFSC
    Does NOT guess the IFSC

STAGE 6 — Agent contacts vendor
    Calls: send_vendor_message()
    LLM generates natural language message
    Sent via Vendor Chat Simulator
    State: VENDOR_CONTACTED

STAGE 7 — Vendor responds (simulated)
    Vendor provides: ICICI account, IFSC ICIC0001234, account ending 9876

STAGE 8 — Agent extracts structured data
    LLM parses vendor message
    Outputs strict Pydantic schema: account_holder_name, account_number, ifsc
    Deterministic layer validates:
        required fields present
        IFSC format valid (regex: [A-Z]{4}0[A-Z0-9]{6})
        account number format valid
        no unexpected fields

STAGE 9 — Create new fund account (Level 2)
    Policy engine checks -> ALLOW
    Calls: create_fund_account(cont_123, corrected_details)
    New fund account: fa_789
    State: DATA_VALIDATED

STAGE 10 — Validate new fund account (Level 2, MOCKED in demo)
    Calls: validate_fund_account(fa_789)
    Returns: account_status=active, name_match_score=99
    Deterministic code evaluates:
        account_status != active -> STOP
        name_match_score < threshold -> human review
        both pass -> CONTINUE
    State: BANK_VALIDATED

STAGE 11 — Deactivate old fund account (Level 2)
    Calls: deactivate_fund_account(fa_456)
    fa_456 -> inactive, fa_789 -> active

STAGE 12 — Update ERP (Level 2)
    Calls: update_vendor_bank_details() in Zoho Books
    ERP now reflects ICICI account

STAGE 13 — Policy check
    State: POLICY_CHECK
    Replacement payout 2,00,000 = Level 3 action
    Policy engine -> REQUIRE_HUMAN_APPROVAL

STAGE 14 — Human approval
    State: HUMAN_APPROVAL
    Dashboard shows full recovery summary:
        Vendor, Amount, Original failure, Old account (deactivated),
        New account (validated), Bank status (ACTIVE), Name match (99%),
        ERP updated
    Human clicks APPROVE

STAGE 15 — Execute payout (Level 3)
    Calls: create_payout(fa_789, 200000, INR, IMPS, NEW_IDEMPOTENCY_KEY)
    State: PAYOUT_EXECUTED

STAGE 16 — Reconcile
    Razorpay sends payout.processed webhook
    Calls: update_invoice_status(INV-2381, PAID) in Zoho
    State: CASE_RESOLVED
    Audit chain: VERIFIED

---

## Test Case Engine

10 core scenarios covering the full decision space:

    CASE 001: invalid_ifsc_code                => vendor_remediation (golden path)
    CASE 002: bank_account_closed              => vendor provides new account entirely
    CASE 003: bank_account_invalid             => re-verification with vendor
    CASE 004: beneficiary_bank_offline         => controlled retry, no vendor contact
    CASE 005: beneficiary_bank_technical_error => retry
    CASE 006: insufficient_funds               => internal finance escalation, no vendor contact
    CASE 007: low_name_match                   => human review triggered
    CASE 008: vendor gives incomplete details  => agent asks follow-up
    CASE 009: vendor gives contradictory details => escalate
    CASE 010: possible impersonation           => BLOCK immediately

Adversarial cases test that the agent knows when NOT to act, which is just as important as knowing when to act.

---

## Evaluation Harness Metrics

    Metric                             Target
    -------------------------------------------------------
    Correct failure diagnosis          95% or above
    Correct recovery strategy          95% or above
    Correct tool calls                 95% or above
    Data extraction accuracy           97% or above
    Policy compliance                  100%
    Unnecessary escalations            below 5%
    Authorized financial actions       100% human-approved
    Unauthorized financial actions     0 (hard requirement, no exceptions)

---

## Frontend Dashboard Features (Next.js + TypeScript)

    Live case list with state indicator (badge colors per state)
    Case detail page:
        Recovery case summary
        Original payout details
        Vendor information
        Failure reason
        Agent action terminal (live-updating timestamped feed)
        Vendor chat panel (Vendor Chat Simulator)
        Bank validation result (with SIMULATED label in demo)
        Human approval panel (Level 3 actions surface here)
        Cryptographic audit timeline
        Audit integrity badge (VERIFIED / TAMPERED)
    Approval queue page (finance controller view)
    Test case launcher (for demo and evaluation)

---

## Backend Service Structure (Python + FastAPI)

    POST /webhooks/razorpay       Webhook ingestion, signature verification
    POST /webhooks/zoho           Zoho event ingestion
    GET  /cases                   List all recovery cases
    GET  /cases/:id               Get case detail
    POST /cases/:id/approve       Human approval endpoint
    POST /cases/:id/reject        Human rejection endpoint
    GET  /cases/:id/audit         Audit event chain retrieval
    POST /vendor/chat             Simulated vendor communication endpoint
    POST /agent/run               Manual agent trigger for testing
    POST /test/scenario           Test case engine trigger

---

## Implementation Order

Do not start with the UI. Build in this sequence:

    1.  Domain model and database schema
    2.  State machine (pure Python, no LLM)
    3.  Tool definitions and Pydantic schemas
    4.  Policy and authority engine
    5.  Audit event system with SHA-256 hash chaining
    6.  Razorpay API integration (test mode)
    7.  Zoho Books API integration (sandbox + OAuth)
    8.  Vendor communication adapter (simulator)
    9.  LLM agent with tool calling wired into state machine
    10. Mock account validation service
    11. Webhook ingestion endpoints (Razorpay + Zoho)
    12. Test case engine and evaluation harness
    13. Frontend dashboard (Next.js)
    14. Human approval UI
    15. Demo polish and adversarial test runs

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

Main area: case detail view.

    Top strip: case metadata. Case ID, payout ID, vendor name, amount, failure reason, current state badge, risk level badge.

    Agent Action Terminal: a live-scrolling feed of every step the agent has taken, timestamped. Each line shows what happened, who did it (AI, system, or human), and whether it was a read or write action. This is the brain-visible element. The audit team can see the agent reasoning in real time.

    Cryptographic Audit Timeline: same events in a more structured table. Columns: timestamp, actor type (External Fact / AI Decision / System Action / Human Decision), action, result. A VERIFIED badge anchors the table header. If the chain is tampered it turns red with TAMPERED.

Right side panel: context drawer with tabs.
    Payout tab: original payout details from Razorpay.
    Vendor tab: vendor record from Zoho Books.
    Bank Validation tab: validation result including account_status, registered_name, name_match_score. Labelled SIMULATED (DEMO ENVIRONMENT) in the demo.

Bottom strip: Vendor Communication entry point. A compact bar at the bottom with a WhatsApp-style logo icon and the vendor name. When clicked, a chat panel slides up from the bottom occupying the lower quarter of the screen. The simulated WhatsApp conversation between the agent and the vendor is displayed here in bubble format, agent messages on one side and vendor replies on the other. The panel is read-only for the audit team. Dismissible by clicking the icon again.

Floating approval card: when a Level 3 action is triggered (replacement payout ready), a prominent card slides in from the top-right like a notification. It shows vendor, amount, original failure, old account (deactivated), new account (validated), bank validation result, name match score, and ERP status. Two buttons: APPROVE and REJECT. Inline — the team does not navigate away. On decision, the card dismisses and the Agent Action Terminal updates immediately.

### Evaluation View

A test case launcher with a grid of the 10 predefined scenarios. Each can be triggered individually or all run as a batch. Results populate a metrics table live. The most prominent metric displayed is Unauthorized Financial Actions which must always read 0.

---

## Non-Negotiable Design Principles

1. The LLM never calls Razorpay directly. Tools do. The policy engine gates every tool.
2. Financial fields are extracted or supplied, never hallucinated.
3. The state machine controls workflow. The LLM does not invent transitions.
4. Every consequential action produces an audit event with WHO / WHAT / WHEN / WHY / INPUT / OUTPUT / APPROVAL / RESULT / HASH.
5. The audit ledger is built from Day 1, not bolted on later.
6. No blockchain. PostgreSQL plus hash chaining is sufficient and more credible.
7. No Kafka, Kubernetes, or distributed-systems complexity.
8. Mock only what genuinely cannot be accessed: Account Validation (Test Mode restriction) and vendor communication (WhatsApp not practical in buildathon). Be transparent about both in the UI.
9. Architecture is general (handles multiple failure classes). Implementation is narrow first (invalid_ifsc_code fully working before adding more paths).
10. The system fails closed. When uncertain: STOP, EXPLAIN, ESCALATE. Never guess.

---

## Files Accessed and Why

- must_follow.md: Read to understand behavioral rules for this engagement (do only what is asked, no commands, no unusual symbols, explain all actions, list all files accessed).
- Absolutely.md: Read to understand the full product design, architecture philosophy, agent authority model, state machine, tool set, tech stack, test engine, demo flow, and all non-negotiable design principles.
- razorpay_api.md: Read to understand which Razorpay APIs are real vs. mocked, the webhook structure, the Zoho Books integration, the full system diagram, and the real-vs-simulated component table.
