# Phase 13 Documentation: Frontend Dashboard (Next.js + TypeScript)

## Overview

Phase 13 implements the **Mission Control Frontend Dashboard** (`frontend/`) in Next.js 14, React 18, TypeScript, and Tailwind CSS.

Positioned as an **Internal Audit and Finance Operations Mission Control Room**, the dashboard provides real-time visibility into the autonomous exception resolution lifecycle, state machine transitions, cryptographic audit chains, and human-in-the-loop authorization gates.

---

## Key Features & Components

### 1. Global Navigation Bar (`Navbar.tsx`)
- Mission Control branding with status badge (`CORE CONNECTED` / `BACKEND OFFLINE`).
- Tab switcher across three primary views:
  1. **Active Cases**: Live operational workspace.
  2. **Closed Cases**: Historical audit archive.
  3. **Evaluation Suite**: 10-scenario benchmark launcher and metrics scorecard.
- **Simulate Exception** trigger modal and manual refresh controls.

### 2. Active Cases Workspace
- **Case List Sidebar (`CaseListSidebar.tsx`)**:
  - Live filtering by state (`HUMAN_APPROVAL`, `VENDOR_CONTACTED`, etc.) and search by vendor, case number, or failure reason.
  - Color-coded state badges with pulse animation for human intervention states.
  - Formatted currency amounts in INR.
- **Case Header Strip (`CaseHeaderStrip.tsx`)**:
  - Displays Case Number, Razorpay Payout ID, Invoice Reference, Failure Diagnostics, Strategy, and current State.
  - Interactive "Run Agent Turn" button to advance reasoning on-demand.
- **Agent Action Terminal (`AgentActionTerminal.tsx`)**:
  - Monospace scrolling console feed displaying real-time AI thoughts, tool executions, and policy evaluations.
  - Actor badges: `[AI AGENT]`, `[SYSTEM]`, `[HUMAN CONTROLLER]`, `[WEBHOOK / FACT]`.
  - Displays SHA-256 hash signatures and approval-required flags.
- **Cryptographic Audit Timeline (`AuditTimelineTable.tsx`)**:
  - Immutable SHA-256 hash-chained block ledger.
  - Header anchored with real-time `[CHAIN VERIFIED (100% INTACT)]` badge (turns `[TAMPERED DETECTED]` if hash linkage is broken).
  - Expandable row details for previous hash, event hash, actor identity, and audit justification.
- **Context Drawer (`ContextDrawer.tsx`)**:
  - **Payout Tab**: RazorpayX Payout object, status, mode, and diagnostics.
  - **Vendor Tab**: Zoho Books vendor profile and ERP sync status.
  - **Validation Tab**: Penny-drop validation metrics, name match score meter (0-100%), and honest `SIMULATED (DEMO ENVIRONMENT)` badge.
- **Slide-Up Vendor WhatsApp Simulator (`VendorChatDrawer.tsx`)**:
  - WhatsApp bubble conversation feed between Agent and Vendor.
  - Preset reply chips and custom reply input to simulate inbound vendor corrections.
- **Floating Human Approval Card (`FloatingApprovalModal.tsx`)**:
  - Notification card for Level 3 financially consequential money movement.
  - Displays old deactivated account, new validated account, name match score, and Zoho ERP status.
  - Inline `AUTHORIZE & DISPATCH` and `REJECT` actions.

### 3. Closed Cases Archive (`ClosedCasesView.tsx`)
- Searchable and filterable data table of resolved and blocked historical cases.
- Aggregate metrics: Total Closed, Reconciled, Blocked (Fraud/Rejected), and 0 Unauthorized Actions.
- Full cryptographic audit trail inspector modal.

### 4. Benchmark Evaluation Suite (`EvaluationView.tsx`)
- Live scorecards for Diagnosis Accuracy, Strategy Accuracy, Extraction Accuracy, Policy Compliance, and **0 Unauthorized Actions (Hard Invariant)**.
- Master "Run Full Benchmark (All 10 Scenarios)" launcher.
- Grid of all 10 predefined scenario cards with individual execution controls.

---

## Backend Enhancements for Frontend Integration

1. **CORS Middleware (`backend/app/main.py`)**:
   - Enabled `CORSMiddleware` to allow local cross-origin API requests from Next.js (`http://localhost:3000`).
2. **Process Turn Endpoint (`backend/app/api/cases.py`)**:
   - `POST /cases/{case_id}/process`: Advances autonomous agent reasoning on-demand or ingests vendor replies.
3. **Simulate Case Endpoint (`backend/app/api/cases.py`)**:
   - `POST /cases/simulate`: Ingests simulated payout failure events directly into the live database and executes turn 1.

---

## Local Setup & Execution Instructions

### 1. Start the Backend Server (Terminal 1)
```bash
# In project root with active python environment
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Install & Start Frontend (Terminal 2)
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` in your web browser.
