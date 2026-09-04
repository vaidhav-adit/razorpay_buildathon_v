# RazorpayX Payout Exception Resolution Agent

Self-healing payouts, with humans in control.

An AI-powered, human-governed system for resolving failed B2B vendor payouts on RazorpayX. When a payout fails, the agent investigates the root cause, communicates with the vendor to obtain corrected banking details, validates the new account, and prepares a replacement payout for human authorization. Money never moves without a human approval.

---

## Architecture in One Line

    AI reasons. Deterministic code executes. Humans authorize money movement.

For the full architecture and implementation plan, see:
- [antigrav_plan.md](./antigrav_plan.md) — full system design
- [implementation_plan.md](./implementation_plan.md) — phase-by-phase build plan
- [documentation/phase_1.md](./documentation/phase_1.md) — Phase 1 architecture, challenges, and resolutions
- [documentation/phase_2.md](./documentation/phase_2.md) — Phase 2 state machine specification and test suite
- [documentation/phase_3.md](./documentation/phase_3.md) — Phase 3 deterministic failure classifier and test suite
- [documentation/phase_4.md](./documentation/phase_4.md) — Phase 4 policy and authority engine specification and tests
- [documentation/phase_5.md](./documentation/phase_5.md) — Phase 5 cryptographic audit ledger and chain verification
- [documentation/phase_6.md](./documentation/phase_6.md) — Phase 6 RazorpayX client tools and webhook ingestion
- [documentation/phase_7.md](./documentation/phase_7.md) — Phase 7 Zoho Books ERP client tools and webhook ingestion
- [documentation/phase_8.md](./documentation/phase_8.md) — Phase 8 Mock Account Validation Service

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
| 9     | Vendor communication adapter            | Not started |
| 10    | LLM agent with LangGraph                | Not started |
| 11    | Human approval API                      | Not started |
| 12    | Test case engine and evaluation harness | Not started |
| 13    | Frontend dashboard (Next.js)            | Not started |
| 14    | Demo polish and adversarial testing     | Not started |

---

## Tech Stack

| Layer               | Technology                          |
|---------------------|-------------------------------------|
| Frontend            | Next.js + React + TypeScript        |
| Backend             | Python + FastAPI                    |
| Data validation     | Pydantic                            |
| Database            | PostgreSQL                          |
| Agent LLM           | OpenAI (structured tool calling)    |
| Agent orchestration | Custom state machine + LangGraph    |
| Policy engine       | Python (deterministic rule engine)  |
| Audit system        | PostgreSQL + SHA-256 hash chaining  |
| ERP                 | Zoho Books Sandbox                  |
| Payments            | Razorpay Test Mode                  |

---

## Local Setup

### Prerequisites

- Python 3.11 or above
- PostgreSQL running locally (or a remote instance)
- Git

### 1. Clone the repository

    git clone https://github.com/YOUR_USERNAME/razorpay-exception-agent.git
    cd razorpay-exception-agent

### 2. Create and activate the virtual environment

    python3 -m venv razor
    source razor/bin/activate       # macOS / Linux
    razor\Scripts\activate           # Windows

### 3. Install dependencies

    pip install -r backend/requirements.txt

### 4. Configure environment variables

    cp backend/.env.example backend/.env

Open backend/.env and fill in:
- DATABASE_URL — your PostgreSQL connection string
- All other values can stay as placeholders until their phase is reached

### 5. Create the database

In PostgreSQL (via psql or your preferred client):

    CREATE DATABASE razorpay_agent;

### 6. Run migrations

    cd backend
    alembic upgrade head

This creates all 8 database tables.

### 7. Start the server

    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

### 8. Verify the setup

    curl http://localhost:8000/health

Expected response:

    {
      "status": "ok",
      "phase": 1,
      "description": "RazorpayX Payout Exception Resolution Agent",
      "database": "connected"
    }

Interactive API docs: http://localhost:8000/docs

---

## Project Structure

    razorpayyyy/
    ├── backend/
    │   ├── app/
    │   │   ├── main.py              FastAPI app entry point
    │   │   ├── config.py            Settings (loaded from .env)
    │   │   ├── database.py          SQLAlchemy engine and session
    │   │   ├── enums.py             All application enums
    │   │   ├── state_machine.py     Pure Python state machine and transition table
    │   │   ├── classifier.py        Deterministic failure classification engine
    │   │   ├── policy_engine.py     Deterministic policy and authority engine
    │   │   ├── audit.py             Cryptographic SHA-256 audit ledger service
    │   │   ├── services/            External service client integrations
    │   │   │   ├── __init__.py
    │   │   │   └── razorpay_client.py
    │   │   ├── models/              SQLAlchemy table definitions
    │   │   │   ├── vendor.py
    │   │   │   ├── payout.py
    │   │   │   ├── recovery_case.py
    │   │   │   ├── fund_account.py
    │   │   │   ├── vendor_message.py
    │   │   │   ├── agent_action.py
    │   │   │   ├── approval.py
    │   │   │   └── audit_event.py
    │   │   └── api/
    │   │       ├── health.py        GET /health endpoint
    │   │       ├── audit.py         GET /cases/{id}/audit endpoint
    │   │       └── webhooks.py      POST /webhooks/razorpay endpoint
    │   ├── tests/                   Unit and integration test suite
    │   │   ├── __init__.py
    │   │   ├── test_state_machine.py
    │   │   ├── test_classifier.py
    │   │   ├── test_policy_engine.py
    │   │   ├── test_audit.py
    │   │   └── test_razorpay.py
    │   ├── alembic/                 Database migration system
    │   │   ├── env.py
    │   │   ├── script.py.mako
    │   │   └── versions/
    │   ├── alembic.ini
    │   ├── requirements.txt
    │   └── .env.example
    ├── documentation/
    │   ├── phase_1.md               Phase 1 overview, challenges, and solutions
    │   ├── phase_2.md               Phase 2 state machine specification and tests
    │   ├── phase_3.md               Phase 3 failure classification engine and tests
    │   ├── phase_4.md               Phase 4 policy and authority engine and tests
    │   ├── phase_5.md               Phase 5 cryptographic audit ledger and tests
    │   └── phase_6.md               Phase 6 RazorpayX client tools and webhooks
    ├── antigrav_plan.md             Full system architecture
    ├── implementation_plan.md       Phase-by-phase build plan
    ├── must_follow.md               Engineering rules for this project
    ├── .gitignore
    └── README.md

---

## Next Phase

Phase 7: Zoho Books Integration (Sandbox) — OAuth 2.0 token manager, vendor synchronization, and invoice matching.
