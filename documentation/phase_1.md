# Phase 1 Documentation: Project Scaffold, Database Models, and Environment Setup

## Overview

Phase 1 established the foundation for the RazorpayX Payout Exception Resolution Agent. The objective was to create a clean, extensible backend skeleton with all 8 database models, configure PostgreSQL with Alembic migrations, and verify connectivity via a health check endpoint.

---

## What Was Built

### 1. Project Structure and Configuration
- Virtual Environment: Created a dedicated Python 3.13 virtual environment named `razor`.
- Environment Management: Implemented `pydantic-settings` in `backend/app/config.py` loading from `backend/.env`.
- Database Connectivity: Created SQLAlchemy engine and session factory in `backend/app/database.py` with standard `get_db` dependency.

### 2. Application Enums (`backend/app/enums.py`)
Defined all core domain enums used across the system:
- `CaseState`: 11 lifecycle states (failed, investigating, vendor_contacted, details_provided, validation_passed, validation_failed, retry_scheduled, awaiting_approval, resolving, resolved, dead_letter).
- `RecoveryStrategy`: Retry, vendor update, or manual review.
- `RiskLevel`: Low, medium, high, critical.
- `PolicyDecision`: Auto approve, human approval required, or reject.
- `PolicyLevel`: Level 0 to Level 4 boundaries.
- `MessageDirection`: Inbound and outbound communication.
- `AuditActorType`: System, agent, human, or vendor.
- `ApprovalDecision`: Approved, rejected, or reassigned.
- `PayoutStatus`: Queued, pending, processing, processed, reversed, or failed.
- `ValidationStatus`: Pending, passed, failed, or skipped.

### 3. Database Models (`backend/app/models/`)
Implemented 8 relational database models using SQLAlchemy 2.0 declarative base:
1. `Vendor` (`vendors`): Vendor details, contact info, Razorpay contact ID, and Zoho vendor ID.
2. `Payout` (`payouts`): Payout records with amounts stored as integers in paise, status, failure reasons, and tracking IDs.
3. `RecoveryCase` (`recovery_cases`): The central stateful entity with a unique case number, current state, strategy, and risk score.
4. `FundAccount` (`fund_accounts`): Bank account / VPA details with masking, IFSC, bank name, and validation flags.
5. `VendorMessage` (`vendor_messages`): Inbound and outbound vendor communications with extracted structured JSON.
6. `AgentAction` (`agent_actions`): Granular tool execution history with policy level and policy decision tags.
7. `Approval` (`approvals`): Human approval requests with structured payload JSON for review cards.
8. `AuditEvent` (`audit_events`): Tamper-evident ledger using SHA-256 hash chaining (`previous_hash` + `event_hash`).

### 4. Migration System & API
- Alembic Setup: Configured `alembic.ini` and `backend/alembic/env.py` to dynamically discover all models and autogenerate migrations.
- Health Endpoint: Implemented `GET /health` in `backend/app/api/health.py` that executes a database ping (`SELECT 1`) to confirm live connectivity.

---

## Challenges Faced and Solutions

### Challenge 1: Python 3.13 Dependency Compatibility
- **Issue**: Installing exact pins such as `psycopg2-binary==2.9.9` and older `pydantic-core` packages failed because pre-compiled binary wheels were not available for Python 3.13 on Apple Silicon (macOS ARM64), triggering local C compiler errors.
- **Root Cause**: Python 3.13 requires newer library builds that support updated CPython APIs and PyO3 bindings.
- **Resolution**: Updated package dependencies in `requirements.txt` to use compatible `>=` minimum versions (`psycopg2-binary>=2.9.10`, `pydantic>=2.10.0`, `fastapi>=0.111.0`). Captured the locked set via `pip freeze > backend/requirements.lock`.

### Challenge 2: Background PostgreSQL Instance Conflict
- **Issue**: Running `psql postgres` prompted for a password for user `vaidhav` and failed with `password authentication failed`, despite `pg_hba.conf` being set to `trust`. Homebrew's `postgresql@16` service repeatedly crashed on startup (`error 1`).
- **Root Cause**: An existing PostgreSQL process (PID 537) installed via a previous system installer was running under the system user `postgres` and bound to port 5432 and `/tmp/.s.PGSQL.5432`. This blocked Homebrew's PostgreSQL service from starting and intercepted all connection attempts.
- **Resolution**: Used `sudo lsof -i :5432` to identify the rogue PID, terminated the process with `sudo kill -9 537`, and freed port 5432.

### Challenge 3: Stale Socket Lock File Permission Denial
- **Issue**: After freeing port 5432, Homebrew's `postgresql@16` failed to start with the error: `FATAL: could not open lock file "/tmp/.s.PGSQL.5432.lock": Permission denied`.
- **Root Cause**: The killed system instance left behind socket and lock files in `/tmp` owned by `root`/`postgres`. The Homebrew service running under macOS user `vaidhav` lacked permission to overwrite them.
- **Resolution**: Removed stale lock files using `sudo rm -rf /tmp/.s.PGSQL*` and restarted the service with `brew services restart postgresql@16`.

### Challenge 4: Database Role Mismatch in Environment Config
- **Issue**: Running `alembic revision --autogenerate` resulted in `sqlalchemy.exc.OperationalError: FATAL: role "postgres" does not exist`.
- **Root Cause**: `backend/.env` contained `DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/razorpay_agent`. Homebrew PostgreSQL on macOS uses the local operating system username (`vaidhav`) as the default superuser, not `postgres`.
- **Resolution**: Updated `backend/.env` to `DATABASE_URL=postgresql://vaidhav@localhost:5432/razorpay_agent`.

---

## Verification and Final Status

1. **Database Creation**: Created `razorpay_agent` database.
2. **Schema Migration**: Generated and applied migration `ee2dbb7a0c2f_phase_1_initial_schema.py`, creating all 8 tables and indexes.
3. **Health Check**: Verified `curl http://localhost:8000/health`:
```json
{
  "status": "ok",
  "phase": 1,
  "description": "RazorpayX Payout Exception Resolution Agent",
  "database": "connected"
}
```
Phase 1 is complete and ready for Phase 2 implementation.
