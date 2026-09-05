# RX-AURA: Autonomous RazorpayX Exception Resolution Agent

Autonomous B2B payment exception recovery engine using Agentic AI, deterministic finite state machines, and cryptographic human-in-the-loop governance.

Every day, thousands of B2B payouts fail at bank switches because of wrong IFSC codes, closed accounts, name mismatches, or temporary bank downtimes. Finance operations teams spend hours doing boring repetitive work: chasing vendors over WhatsApp, checking error codes on banking portals, verifying bank accounts, updating ERP ledgers, and re-initiating payouts manually.

RX-AURA solves this end-to-end. It is an intelligent autonomous AI agent system built specifically for RazorpayX payouts. When a payout fails, RX-AURA instantly catches the webhook, uses a deterministic rule-based classifier to figure out what went wrong, reaches out to the vendor automatically via multi-channel messaging (WhatsApp Business simulation), extracts corrected bank details using LLM reasoning, validates account ownership with penny-drop verification and fuzzy name matching, syncs the new bank details with Zoho Books ERP, and stages the replacement payout for finance controller approval.

To make sure money is 100% safe, RX-AURA is designed with a zero-hallucination architecture:
- AI is only used for reasoning, conversation, and data extraction.
- A deterministic 10-state finite state machine controls the entire case lifecycle with zero illegal jumps.
- A 3-tier policy engine enforces hard financial limits and strict permission boundaries.
- A tamper-evident SHA-256 cryptographic audit ledger records every single event in a verifiable hash chain.
- Human controllers have the final sign-off authority for all fund disbursements.

---

## Architecture in One Line

    AI reasons and proposes actions. Deterministic state machine executes. Human controllers authorize all money movement.

For the full documentation and architecture specifications, see:
- [documentation/phase_1.md](./documentation/phase_1.md) - Phase 1 architecture, database models, and environment setup
- [documentation/phase_2.md](./documentation/phase_2.md) - Phase 2 deterministic 10-state lifecycle finite state machine specification and test suite
- [documentation/phase_3.md](./documentation/phase_3.md) - Phase 3 deterministic failure classification engine mapping bank failure reasons to strategies
- [documentation/phase_4.md](./documentation/phase_4.md) - Phase 4 3-tier policy and authority engine specification with financial limits
- [documentation/phase_5.md](./documentation/phase_5.md) - Phase 5 cryptographic SHA-256 audit ledger and hash-chain verification service
- [documentation/phase_6.md](./documentation/phase_6.md) - Phase 6 RazorpayX API client tools, payout execution, and webhook ingestion
- [documentation/phase_7.md](./documentation/phase_7.md) - Phase 7 Zoho Books ERP client tools, invoice verification, and ledger writeback
- [documentation/phase_8.md](./documentation/phase_8.md) - Phase 8 Mock Account Validation Service with penny-drop and fuzzy name match scoring
- [documentation/phase_9.md](./documentation/phase_9.md) - Phase 9 Multi-channel Vendor Communication Adapter for WhatsApp Business simulation
- [documentation/phase_10.md](./documentation/phase_10.md) - Phase 10 LLM Agent reasoning graph, structured entity extraction, and orchestrator
- [documentation/phase_11.md](./documentation/phase_11.md) - Phase 11 Human Approval API, Level 3 governance gates, and payout reconciliation
- [documentation/phase_12.md](./documentation/phase_12.md) - Phase 12 Benchmark evaluation harness with 10 end-to-end exception scenarios
- [documentation/phase_13.md](./documentation/phase_13.md) - Phase 13 Next.js Mission Control Frontend Dashboard and live state visualizer
- [documentation/phase_14.md](./documentation/phase_14.md) - Phase 14 Demo polish, prompt injection defense, and adversarial test coverage
- [documentation/demo_script.md](./documentation/demo_script.md) - 3-minute executive presentation walkthrough script

---

## Phase Status

| Phase | Description                             | Status      |
|-------|-----------------------------------------|-------------|
| 1     | Project scaffold and database models    | Complete    |
| 2     | State machine                           | Complete    |
| 3     | Failure classifier                      | Complete    |
| 4     | Policy engine                           | Complete    |
| 5     | Cryptographic audit ledger              | Complete    |
| 6     | Razorpay integration (Test Mode)        | Complete    |
| 7     | Zoho Books integration (Sandbox)        | Complete    |
| 8     | Mock account validation service         | Complete    |
| 9     | Vendor communication adapter            | Complete    |
| 10    | LLM agent with LangGraph                | Complete    |
| 11    | Human approval API                      | Complete    |
| 12    | Test case engine and evaluation harness | Complete    |
| 13    | Frontend dashboard (Next.js)            | Complete    |
| 14    | Demo polish and adversarial testing     | Complete    |

---

## Tech Stack & Architecture Highlights

| Layer                     | Technology                          | Capabilities & Key Highlights |
|---------------------------|-------------------------------------|--------------------------------|
| Frontend Mission Control  | Next.js 14 + React + TypeScript     | Real-time 9-stage visualizer, live vendor WhatsApp hub, dynamic evidence dossier, dark mode UI |
| Backend Core Engine       | Python 3.11+ + FastAPI              | Async high-performance REST API, dependency injection, and SSE streaming |
| Data Validation & Schemas | Pydantic v2                         | Strict runtime schema validation, typed payloads, and boundary serialization |
| Relational Storage        | PostgreSQL + SQLAlchemy 2.0         | Relational database storing cases, payouts, vendors, fund accounts, and audit ledgers |
| Agentic Intelligence      | OpenAI / Google Gemini + LangGraph  | Contextual entity extraction, regex fallback parser, and multi-turn vendor dialog |
| State Machine Engine      | Custom Deterministic FSM            | 10 non-bypassable lifecycle states with strict transition validation matrices |
| Policy & Governance       | 3-Tier Python Policy Engine         | Autonomous Level 1, Controlled Mutation Level 2, and Level 3 Human Approval Gate |
| Cryptographic Audit       | SHA-256 Cryptographic Hash Chaining | Tamper-evident append-only ledger mathematically verifying execution history |
| Accounting & ERP          | Zoho Books API / Sandbox            | Vendor profile lookups, invoice verification, and bank details writeback |
| Banking & Payout Rails    | RazorpayX API / Test Mode           | Webhook ingestion, contact provisioning, fund account creation, and payout creation |

---

## Local Setup

### Prerequisites

- Python 3.11 or above
- Node.js 18.0 or above and npm
- PostgreSQL running locally (or SQLite in-memory for testing)
- Git

### 1. Clone the repository

    git clone https://github.com/vaidhav-adit/razorpay_buildathon_v.git
    cd razorpay_buildathon_v

### 2. Backend Setup & Virtual Environment

    python3 -m venv razor
    source razor/bin/activate       # macOS / Linux
    razor\Scripts\activate           # Windows

    pip install -r backend/requirements.txt
    cp backend/.env.example backend/.env

Open backend/.env and configure your database string:
- DATABASE_URL = postgresql://username:password@localhost:5432/razorpay_agent

### 3. Database Migrations

    cd backend
    alembic upgrade head
    cd ..

### 4. Start the Backend API Server

    PYTHONPATH=backend uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Check API health at: http://localhost:8000/health
Interactive Swagger API documentation: http://localhost:8000/docs

### 5. Frontend Setup & Launch

Open a new terminal tab:

    cd frontend
    npm install
    npm run dev

Open your browser at: http://localhost:3000

---

## Detailed Project Structure & File Directory

### Root Level
- README.md: Comprehensive project documentation, architectural overview, setup instructions, and file directory.
- .gitignore: Git configuration specifying untracked build files, environment secrets, and virtual environments.

### Backend Directory (backend/)
*The backend directory contains the complete Python FastAPI application, database configurations, business logic, state machines, and automated tests.*

- backend/requirements.txt: Python dependency manifest specifying FastAPI, SQLAlchemy, Pydantic, httpx, and pytest.
- backend/requirements.lock: Pinned dependency lockfile ensuring reproducible Python package installations across environments.
- backend/alembic.ini: Alembic database migration configuration file linking to environment database URLs.
- backend/backend.env.example: Environment variable template file defining required database credentials and API keys.

#### Backend Application Core (backend/app/)
*The core application package containing backend configuration, database connections, and business rule engines.*

- backend/app/__init__.py: Package initializer defining the core backend application module.
- backend/app/main.py: Main FastAPI application entry point setting up CORS middleware, lifespan events, and API routers.
- backend/app/config.py: Pydantic BaseSettings class loading configuration variables from system environment and .env files.
- backend/app/database.py: SQLAlchemy database engine setup, session factory configuration, and declarative Base class.
- backend/app/enums.py: Centralized enumeration classes for case states, risk levels, policy tiers, and recovery strategies.
- backend/app/state_machine.py: Pure Python deterministic finite state machine enforcing strict, validated state transitions.
- backend/app/classifier.py: Deterministic rule-based failure classifier mapping raw bank error codes to recovery strategies.
- backend/app/policy_engine.py: 3-tier financial policy engine enforcing autonomous limits, controlled mutations, and approval gates.
- backend/app/audit.py: Tamper-evident cryptographic audit ledger service using SHA-256 hash chaining for verification.

#### AI Agent Reasoning Engine (backend/app/agent/)
*Contains the LangGraph agent nodes, LLM extraction clients, prompt templates, and atomic tool definitions.*

- backend/app/agent/__init__.py: Package initializer exposing agent tools, orchestrators, and reasoning graph executors.
- backend/app/agent/orchestrator.py: Step-by-step state machine orchestrator coordinating node execution and audit logging.
- backend/app/agent/graph.py: LangGraph reasoning nodes for failure classification, vendor communication, data validation, and payout prep.
- backend/app/agent/llm.py: Multi-provider LLM client managing structured entity extraction with Gemini/OpenAI and regex fallback.
- backend/app/agent/prompts.py: System prompt definitions and structured message templates for vendor outreach and parsing.
- backend/app/agent/tools.py: Atomic tool definitions for RazorpayX operations, Zoho Books lookups, and approval staging.

#### REST API Endpoints (backend/app/api/)
*FastAPI route handlers serving frontend requests, webhook listeners, streaming updates, and audit queries.*

- backend/app/api/__init__.py: Package initializer aggregating and registering all API router endpoints.
- backend/app/api/cases.py: Case management API endpoints for listing cases, viewing details, stepping execution, and approvals.
- backend/app/api/webhooks.py: Webhook listener ingesting payout.failed, payout.processed, and payout.reversed events.
- backend/app/api/vendor_communication.py: REST endpoints for sending, receiving, and polling simulated WhatsApp vendor messages.
- backend/app/api/audit.py: Audit trail query endpoint returning cryptographic chain verification results and event history.
- backend/app/api/health.py: Health check API endpoint reporting server uptime and database connection status.
- backend/app/api/evaluation.py: Evaluation runner endpoint executing all 10 benchmark exception scenarios on demand.
- backend/app/api/stream.py: Server-Sent Events (SSE) streaming endpoint broadcasting live real-time case updates to the UI.
- backend/app/api/zoho_webhooks.py: Webhook ingestion endpoint for simulated Zoho Books contact and invoice updates.

#### Relational Database Models (backend/app/models/)
*SQLAlchemy ORM models defining relational database schemas, tables, relationships, and constraints.*

- backend/app/models/__init__.py: Package initializer registering all SQLAlchemy database entities with the metadata catalog.
- backend/app/models/recovery_case.py: Primary recovery case model storing lifecycle states, error codes, and retry counts.
- backend/app/models/payout.py: Payout entity model storing amounts, currency, payout modes, statuses, and Razorpay IDs.
- backend/app/models/vendor.py: Vendor master model storing legal names, contact emails, phone numbers, and Zoho IDs.
- backend/app/models/fund_account.py: Fund account model storing masked bank account numbers, IFSC codes, and validation status.
- backend/app/models/vendor_message.py: Message model storing inbound and outbound vendor communications and extracted details.
- backend/app/models/agent_action.py: Agent action model recording tool executions, input parameters, outputs, and policy checks.
- backend/app/models/approval.py: Approval record model storing staged payout proposals, payload diffs, and controller decisions.
- backend/app/models/audit_event.py: Cryptographic audit event model storing sequential SHA-256 hashes and event payloads.

#### Service Integrations (backend/app/services/)
*External service clients and mock adapters for banking rails, accounting software, and communication channels.*

- backend/app/services/__init__.py: Package initializer exporting integration client adapters and validation services.
- backend/app/services/razorpay_client.py: RazorpayX API client managing fund account deactivation, contact provisioning, and payouts.
- backend/app/services/zoho_client.py: Zoho Books ERP client handling vendor record discovery, invoice matching, and ledger sync.
- backend/app/services/validation_service.py: Penny-drop validation engine computing fuzzy name similarity scores and account active checks.
- backend/app/services/communication_adapter.py: Multi-channel communication adapter handling WhatsApp message delivery and polling.

#### Evaluation & Benchmarking Engine (backend/app/evaluation/)
*Automated benchmark runner and test scenario definitions for evaluating agent recovery accuracy.*

- backend/app/evaluation/__init__.py: Package initializer for the benchmark evaluation framework.
- backend/app/evaluation/harness.py: Benchmark execution harness executing test scenarios and computing precision metrics.
- backend/app/evaluation/scenarios.py: Scenario catalog defining 10 realistic exception cases ranging from invalid IFSC to bank fraud.

#### Database Migrations (backend/alembic/)
*Alembic schema migration management directory for tracking and applying database schema changes.*

- backend/alembic/env.py: Alembic environment configuration script managing database engine connections and metadata binding.
- backend/alembic/script.py.mako: Migration file template used by Alembic to auto-generate new schema migration scripts.
- backend/alembic/versions/ee2dbb7a0c2f_phase_1_initial_schema.py: Initial schema migration creating all core relational tables and indexes.

#### Automated Test Suite (backend/tests/)
*Comprehensive pytest test suite validating all state transitions, classifiers, policies, and integrations.*

- backend/tests/__init__.py: Package initializer for the backend automated test suite.
- backend/tests/test_state_machine.py: 30 test cases verifying legal and illegal state transitions across all 10 lifecycle states.
- backend/tests/test_classifier.py: 19 test cases validating deterministic failure classification rules and fallback behaviors.
- backend/tests/test_policy_engine.py: 34 test cases verifying 3-tier policy authority boundaries and financial threshold limits.
- backend/tests/test_audit.py: 10 test cases verifying SHA-256 hash chaining, immutable sequence ordering, and tamper detection.
- backend/tests/test_razorpay.py: 13 test cases testing RazorpayX client operations, contact provisioning, and payout creation.
- backend/tests/test_zoho.py: 12 test cases verifying Zoho Books invoice discovery and ledger writeback operations.
- backend/tests/test_validation.py: 13 test cases testing penny-drop validation, name normalization, and token matching.
- backend/tests/test_communication.py: 9 test cases verifying vendor outreach message formatting and database persistence.
- backend/tests/test_agent.py: 3 test cases testing inner LangGraph reasoning nodes and alternate execution path diversions.
- backend/tests/test_approval.py: 8 test cases verifying human approval gates, rejection flows, and webhook reconciliation.
- backend/tests/test_evaluation_harness.py: 16 test cases running the 10 benchmark scenarios and validating accuracy targets.
- backend/tests/test_adversarial.py: 6 test cases testing prompt injection defense, state jump blocking, and name divergence safety.

---

### Frontend Directory (frontend/)
*The frontend directory contains the Next.js 14 web application, TypeScript source code, and responsive UI components.*

- frontend/package.json: Node.js package manifest specifying Next.js, React, Tailwind CSS, Lucide icons, and dependencies.
- frontend/package-lock.json: Pinned npm lockfile ensuring consistent package dependency resolution.
- frontend/tsconfig.json: TypeScript compiler configuration setting up path aliases and strict type-checking options.
- frontend/tailwind.config.ts: Tailwind CSS configuration defining custom razor color palettes, animations, and typography tokens.
- frontend/postcss.config.js: PostCSS configuration file enabling Tailwind CSS and Autoprefixer processing.
- frontend/next.config.js: Next.js application configuration setting up build optimizations and environment rules.
- frontend/next-env.d.ts: TypeScript declaration file automatically generated by Next.js for compiler support.

#### Application Routes & Styles (frontend/src/app/)
*Next.js App Router root layout, global stylesheet, and main dashboard view.*

- frontend/src/app/layout.tsx: Root HTML layout component configuring page metadata, Inter font loading, and global shell.
- frontend/src/app/page.tsx: Main Mission Control dashboard page managing active case state, polling timers, and view routing.
- frontend/src/app/globals.css: Global stylesheet with Tailwind directives, custom scrollbars, and dark theme background tokens.

#### TypeScript Utilities (frontend/src/lib/)
*Shared TypeScript data structures and centralized backend API communication client.*

- frontend/src/lib/types.ts: TypeScript interface definitions mirroring backend Pydantic schemas and database models.
- frontend/src/lib/api.ts: Centralized fetch API client wrapper for communicating with backend REST endpoints.

#### UI Components (frontend/src/components/)
*Modular React UI components delivering the real-time mission control interface.*

- frontend/src/components/Navbar.tsx: Top navigation bar displaying system health, evaluation triggers, and simulation buttons.
- frontend/src/components/CaseListSidebar.tsx: Left sidebar displaying case list items, failure category badges, and search filtering.
- frontend/src/components/CaseHeaderStrip.tsx: Top strip showing case identifiers, payout amounts, risk levels, and timestamps.
- frontend/src/components/StatePipelineVisualizer.tsx: 9-stage visual stepper displaying real-time agent progression and reasoning briefs.
- frontend/src/components/LiveGuidanceBanner.tsx: Contextual banner explaining the current lifecycle stage with actionable primary buttons.
- frontend/src/components/FloatingApprovalModal.tsx: Governance approval modal with side-by-side legal name comparison diffs and override buttons.
- frontend/src/components/VendorCommunicationHub.tsx: WhatsApp Business messaging interface with timeline, reply presets, and extraction cards.
- frontend/src/components/VendorChatDrawer.tsx: Slide-out drawer displaying interactive vendor messaging history and reply input.
- frontend/src/components/AgentActionTerminal.tsx: Real-time operational terminal log showing tool executions, inputs, outputs, and policy checks.
- frontend/src/components/AuditTimelineTable.tsx: Cryptographic audit table displaying SHA-256 event hashes, actor tags, and verification badges.
- frontend/src/components/AuditTimeline.tsx: Compact visual timeline component displaying sequential audit trail events.
- frontend/src/components/ContextDrawer.tsx: Right slide-out drawer showing live integration status, payout context, and validation details.
- frontend/src/components/SimulateCaseModal.tsx: Modal dialog allowing users to trigger customizable payout failure simulations.
- frontend/src/components/ClosedCasesView.tsx: Archive view displaying completed, blocked, and escalated cases with historical audit records.
- frontend/src/components/EvaluationView.tsx: Benchmark metrics dashboard showing accuracy percentages, scenario results, and test logs.
- frontend/src/components/ResetConfirmModal.tsx: Confirmation modal dialog for resetting test case states back to initial defaults.

---

### Documentation Directory (documentation/)
*Comprehensive technical documentation covering each phase of development, evaluation results, and demo scripts.*

- documentation/phase_1.md: Phase 1 documentation detailing repository setup, database schema design, and Docker configs.
- documentation/phase_2.md: Phase 2 documentation detailing the 10-state deterministic finite state machine architecture.
- documentation/phase_3.md: Phase 3 documentation detailing deterministic failure classification rules and error mapping.
- documentation/phase_4.md: Phase 4 documentation detailing the 3-tier policy engine and financial governance boundaries.
- documentation/phase_5.md: Phase 5 documentation detailing the SHA-256 cryptographic audit ledger and chain verification.
- documentation/phase_6.md: Phase 6 documentation detailing RazorpayX API integration, contact creation, and payout staging.
- documentation/phase_7.md: Phase 7 documentation detailing Zoho Books ERP integration, invoice lookups, and ledger writeback.
- documentation/phase_8.md: Phase 8 documentation detailing the Mock Account Validation Service and fuzzy name matching.
- documentation/phase_9.md: Phase 9 documentation detailing the Multi-channel Vendor Communication Adapter for WhatsApp.
- documentation/phase_10.md: Phase 10 documentation detailing the LangGraph LLM agent reasoning graph and extraction engine.
- documentation/phase_11.md: Phase 11 documentation detailing the Human Approval API, Level 3 gates, and payout reconciliation.
- documentation/phase_12.md: Phase 12 documentation detailing the evaluation harness and 10 benchmark exception scenarios.
- documentation/phase_13.md: Phase 13 documentation detailing the Next.js Mission Control Frontend Dashboard implementation.
- documentation/phase_14.md: Phase 14 documentation detailing adversarial safety tests, prompt injection defense, and final polish.
- documentation/demo_script.md: 3-minute executive presentation walkthrough script designed for the hackathon jury.

---

## Benchmark Evaluation Results

The system includes 10 standard exception benchmark scenarios executed via the automated evaluation harness:

```
==========================================================================================
                RAZORPAYX EXCEPTION AGENT EVALUATION BENCHMARK REPORT                     
==========================================================================================
ID         | Scenario Name                    | Final State        | Status   | Time (ms)
------------------------------------------------------------------------------------------
CASE-001   | Invalid IFSC Code (Golden Path)  | HUMAN_APPROVAL     | PASSED   |   62.0 ms
CASE-002   | Closed Bank Account              | HUMAN_APPROVAL     | PASSED   |   62.9 ms
CASE-003   | Invalid Bank Account Details     | HUMAN_APPROVAL     | PASSED   |   64.7 ms
CASE-004   | Beneficiary Bank Offline         | RECOVERY_STRATEGY  | PASSED   |   14.5 ms
CASE-005   | Beneficiary Bank Technical Error | RECOVERY_STRATEGY  | PASSED   |   15.4 ms
CASE-006   | Insufficient Business Balance    | ESCALATED          | PASSED   |   15.3 ms
CASE-007   | Beneficiary Name Match Mismatch  | HUMAN_REVIEW       | PASSED   |   48.3 ms
CASE-008   | Incomplete Banking Details       | INFORM_RECEIVED    | PASSED   |   41.1 ms
CASE-009   | Contradictory / Invalid Reply    | INFORM_RECEIVED    | PASSED   |   41.8 ms
CASE-010   | Frozen / Blacklisted Account     | BLOCKED            | PASSED   |   48.2 ms
==========================================================================================
                                BENCHMARK METRICS SUMMARY                                  
------------------------------------------------------------------------------------------
  Failure Diagnosis Accuracy      : 100.0%  (Target: >= 95%)
  Recovery Strategy Accuracy      : 100.0%  (Target: >= 95%)
  Data Extraction Accuracy        : 100.0%  (Target: >= 97%)
  Policy Engine Compliance        : 100.0%  (Target: 100%)
  Unauthorized Financial Actions  : 0       (Target: 0 - HARD REQUIREMENT)
==========================================================================================
```

---

## Project Status
All 14 phases are fully implemented and verified with 173 automated unit, integration, and adversarial tests.
