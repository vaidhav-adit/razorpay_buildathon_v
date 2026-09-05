# RX-AURA 3-Minute Live Demo Script

This script provides a structured **3-minute walkthrough** for demonstrating the RazorpayX Autonomous Unified Resolution Agent (RX-AURA) to evaluators, judges, or executive leadership.

---

## Core Thesis & Anchor Pitch
> **"Failed B2B payouts cost finance teams hours of manual triage, vendor email tag, and reconciliation overhead. Our system solves this autonomously with a strict architectural guarantee: AI reasons, deterministic code executes, and humans authorize money movement."**

---

## The 7-Act Live Demo Flow

### Act 1: The Payout Failure (0:00 - 0:30)
1. **Screen**: Open Mission Control Dashboard (`http://localhost:3000`).
2. **Action**: Click the green **"Simulate Exception"** button. Select **"Golden Path: Invalid IFSC Code"** (Vendor: *Apex Logistics India Pvt Ltd*, Amount: *INR 2,50,000*). Click **"Inject Payout Exception"**.
3. **What to highlight**:
   - The case immediately appears in the left **Exception Queue** with a pulse badge on `CASE_CREATED`.
   - The **Cryptographic Audit Ledger** logs Block #1: `PAYOUT_FAILED_WEBHOOK_RECEIVED` (Genesis Block).
   - The **Agent Action Terminal** comes alive with real-time streaming telemetry.

---

### Act 2: Deterministic Classification & Cross-System Investigation (0:30 - 1:00)
1. **Screen**: Case detail workspace.
2. **What to highlight**:
   - **No LLM guessing on error codes**: The failure `(beneficiary_bank, invalid_ifsc_code)` is classified deterministically to `VENDOR_REMEDIATION`.
   - The agent reads vendor context across **Razorpay** (Contact ID) and **Zoho Books ERP** (Bill Reference `INV-2026-8801`).
   - The state machine advances to `VENDOR_CONTACTED`.

---

### Act 3: Natural Language WhatsApp Vendor Outreach (1:00 - 1:30)
1. **Screen**: Click the **WhatsApp Vendor Communication Channel** bar at the bottom to slide up the drawer.
2. **Action**:
   - View the outbound message sent by the agent to the vendor.
   - Click one of the quick preset replies: *"Here are our updated banking details: Account 987654321098, IFSC HDFC0001234, Name: Apex Logistics"*. Click **"Send Reply"**.
3. **What to highlight**:
   - The natural language reply is received in inbound bubble format.
   - The agent uses **LLM Structured Extraction (Google Gemini)** to parse unstructured text into typed banking entities (`ExtractedBankingData`).
   - Downstream deterministic regex verifies the syntax conforms to RBI IFSC standards.

---

### Act 4: Penny-Drop Validation & 3-Tier Policy Gating (1:30 - 2:00)
1. **Screen**: Right **Context Drawer** -> Click **"Validation"** Tab.
2. **What to highlight**:
   - **Simulation Honesty**: The UI clearly displays the `SIMULATED (DEMO ENVIRONMENT)` badge.
   - **Deterministic Name Match**: The system calculates a 99% match between registered name and invoice contact.
   - **ERP Synchronization**: Zoho Books vendor master is updated, and the old faulty fund account on Razorpay is deactivated.
   - **Level 3 Policy Gate**: Because money movement is involved, the Policy Engine strictly returns `REQUIRE_HUMAN_APPROVAL`.

---

### Act 5: The Human Authorization Gate (2:00 - 2:30)
1. **Screen**: The **Floating Level 3 Authorization Card** sliding in from the top right.
2. **Action**: Click the green **"AUTHORIZE & DISPATCH"** button.
3. **What to highlight**:
   - **Money NEVER moves without human authority**: No prompt injection or AI loop can bypass this gate.
   - The approval pins the exact replacement fund account (`fa_...`) and locked amount (*INR 2,50,000*).
   - An immutable `HUMAN_DECISION` block is added to the cryptographic audit chain signed with `actor="finance_controller"`.

---

### Act 6: Execution & ERP Reconciliation (2:30 - 2:45)
1. **Screen**: Case updates to `PAYOUT_EXECUTED` -> `PAYOUT_CONFIRMED` -> `CASE_RESOLVED`.
2. **What to highlight**:
   - Razorpay replacement payout is dispatched.
   - Zoho Books invoice status is automatically updated to `PAID`.
   - The audit table header displays the green **`[CHAIN VERIFIED (100% INTACT)]`** badge, proving every step is tamper-evident.

---

### Act 7: Benchmark Evaluation & Safety Proof (2:45 - 3:00)
1. **Screen**: Click the **"Evaluation Suite (10 Scenarios)"** tab in the top navigation bar.
2. **Action**: Click **"Run Full Benchmark (All 10 Scenarios)"**.
3. **What to highlight**:
   - 10 decision-space scenarios executed in real time:
     - Invalid IFSC, Closed Accounts, Invalid Details.
     - Offline Bank Retries (0 vendor outreach).
     - Insufficient Business Funds (Internal finance escalation).
     - Low Name Match (Diverts to Human Review).
     - Incomplete/Contradictory Details (Halts at Information Received).
     - Frozen/Fraud Account (Immediate Block).
   - **The Hero Metric**: **Unauthorized Financial Actions = 0 (100% Human Governed)**.

---

## Key Talking Points
- **Fails Closed**: When uncertain, the system halts, explains, and escalates. It never hallucinates bank transfers.
- **Auditable**: Every action, tool call, and policy check is linked in an immutable SHA-256 cryptographic chain.
- **Enterprise-Ready**: Bridges the gap between payment gateways (RazorpayX) and ERP accounting (Zoho Books).
