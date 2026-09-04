Yes — and this is an important distinction because **the plan was never to simulate the whole thing**.

From the research you shared, we actually have enough public/developer-accessible Razorpay infrastructure to make the **core workflow real**, while mocking only the pieces that genuinely aren't available in Test Mode.

## **What we actually found**

### **1\. Razorpay Payout APIs — REAL**

We can interact with Razorpay's payout infrastructure through APIs.

Our research identified:

POST /v1/payouts

GET  /v1/payouts/:id

and, crucially, Razorpay exposes payout lifecycle webhooks including:

payout.failed

payout.reversed

The failure webhook contains `status_details`, including:

description

source

reason

next\_steps

with failure reasons such as:

invalid\_ifsc\_code

bank\_account\_closed

bank\_account\_frozen

bank\_account\_invalid

imps\_not\_allowed

beneficiary\_bank\_technical\_error

beneficiary\_bank\_offline

npci\_beneficiary\_timeout

insufficient\_funds

...

So **we do NOT need to simulate the initial failure event**. We can build a real webhook endpoint and have Razorpay tell our system that the payout failed.

That's huge because it means our demo can genuinely start with:

> Razorpay → `payout.failed` → our agent

rather than:

> Fake JSON → our agent.

---

# **2\. Razorpay Test Mode**

This is what makes the buildathon implementation feasible.

Your research found that Razorpay has **Test Mode** for payout APIs, contacts and fund accounts, and that the payout lifecycle can be simulated through the test environment.

So the intended architecture is:

                RAZORPAY TEST MODE

                       │

                       │ payout

                       ▼

                 payout.failed

                       │

                    webhook

                       │

                       ▼

              OUR BACKEND

                       │

                       ▼

                  AI AGENT

We don't need to fake the Razorpay side.

---

# **3\. Fund Accounts — REAL**

We also found:

POST /v1/fund\_accounts

for creating a fund account.

And fund accounts are **immutable**.

You cannot simply edit the bank account attached to an existing fund account.

The documented approach is:

Old Fund Account

       ↓

deactivate

       ↓

Create NEW Fund Account

       ↓

use new account

That is actually perfect for our use case because a bad IFSC shouldn't result in the agent "editing" the old financial destination.

It creates a new one.

---

# **4\. Account Validation — REAL API, but there's a catch**

We found:

POST /v1/fund\_accounts/validations

This gives us things like:

account\_status

registered\_name

name\_match\_score

validated\_account\_type

This is exactly what we wanted for the agent's safety gate.

### **BUT:**

Our research specifically found:

> **Account Validation is unavailable in Razorpay Test Mode.**

It uses actual banking rails.

So **this is one of the things we will have to mock in the buildathon demo**, unless we obtain appropriate live access.

This is an important correction to one of the earlier research snippets that claimed test-mode mock validation. The later technical report explicitly flagged validation as **live-only**, and I would trust the later technical validation.

So:

Razorpay Test Mode

      │

      ├── payout API       REAL

      ├── payout webhook   REAL

      ├── fund account     REAL

      │

      └── account validation

                 │

                 └── MOCKED

And we should be completely transparent about that in the demo.

---

# **5\. Contacts / Vendors — REAL**

We also have the Contacts API.

The research found endpoints for:

POST /v1/contacts

GET  /v1/contacts

GET  /v1/contacts/:id

and contacts can represent vendors.

Fund accounts are associated with those contacts.

So our agent can actually work with the Razorpay-side vendor identity rather than maintaining an entirely fake vendor database.

---

# **6\. Zoho Books — REAL sandbox integration**

This is another important piece.

We chose Zoho Books because we found:

* Contacts APIs  
* Bills APIs  
* vendor bank account APIs  
* outgoing webhooks  
* OAuth 2.0  
* sandbox/developer testing environments

So we can actually create a realistic:

Zoho Books

    ↕

Our Agent

    ↕

Razorpay

architecture.

For example:

Zoho bill approved

       ↓

Zoho webhook

       ↓

Our system

       ↓

Razorpay payout

       ↓

payout.failed

       ↓

Agent recovery

       ↓

Zoho update

That's **much more impressive than a standalone chatbot**.

---

# **7\. Vendor communication — this is where I'd simulate**

We discussed WhatsApp Business API.

Technically we could integrate it, but **I don't think we should spend our three weeks building production-grade WhatsApp infrastructure.**

Instead:

             COMMUNICATION ADAPTER

                       │

             ┌─────────┴─────────┐

             │                   │

       Demo Simulator       Production

             │                WhatsApp

For the demo, make a convincing vendor chat interface.

The agent sends:

> "We couldn't process your ₹2,00,000 payout because the IFSC associated with your account appears invalid. Please provide your updated bank details."

Vendor responds:

> "Yes, sorry. The correct IFSC is HDFC0001234."

Then the agent extracts the information.

This component is simulated, **but the downstream Razorpay actions can be real.**

---

# **8\. The LLM itself**

This part is ours.

I'd use:

### **Python \+ FastAPI \+ Pydantic**

and an LLM with structured tool calling.

Given what you've told me previously about using Antigravity, I'd let **Antigravity handle the implementation environment**, but I would not let it dictate the financial architecture.

The agent gets tools like:

get\_payout()

get\_contact()

get\_fund\_accounts()

get\_invoice()

request\_vendor\_details()

parse\_vendor\_response()

create\_fund\_account()

validate\_fund\_account()

deactivate\_fund\_account()

prepare\_replacement\_payout()

request\_human\_approval()

execute\_payout()

The crucial thing:

**Those aren't arbitrary functions the LLM can freely abuse.**

They're controlled tools behind our policy engine.

---

# **9\. Our tech stack**

I'd lock this:

| Layer | Technology |
| ----- | ----- |
| Frontend | Next.js \+ React \+ TypeScript |
| Backend | Python \+ FastAPI |
| Data validation | Pydantic |
| Database | PostgreSQL |
| Agent | LLM \+ structured tool calling |
| Orchestration | Our own deterministic state machine |
| Policy | Python policy/authority engine |
| Audit | PostgreSQL \+ SHA-256 hash chain |
| ERP | Zoho Books Sandbox |
| Payments | Razorpay Test Mode |
| Webhooks | Razorpay \+ Zoho |
| Vendor communication | Simulated WhatsApp-style interface |
| Account validation | Mocked for demo |
| Dev environment | Antigravity |
| Testing | pytest \+ scenario/evaluation harness |

And I would **not** add:

* Kafka  
* Kubernetes  
* blockchain  
* microservices everywhere  
* complicated vector databases  
* a giant ML model

None of those help us win this particular project.

---

# **10\. How the actual Razorpay webhook works**

This is probably what you were really asking.

Our backend exposes something like:

POST /webhooks/razorpay

Razorpay sends:

{

  "event": "payout.failed",

  "payload": {

    ...

  }

}

Our server:

Razorpay webhook

       ↓

Verify webhook signature

       ↓

Store event

       ↓

Create Recovery Case

       ↓

Classify failure

       ↓

Start agent

So the agent isn't sitting there polling Razorpay every five seconds asking:

> "Did something fail?"

It's **event-driven**.

That's much cleaner.

---

# **11\. The whole system therefore becomes**

                   ZOHO BOOKS

                        │

                  bill approved

                        │

                     webhook

                        ▼

                ┌──────────────┐

                │ OUR BACKEND  │

                └──────┬───────┘

                       │

                       ▼

                 RAZORPAY API

                       │

                  create payout

                       │

                       ▼

                ┌──────────────┐

                │ RAZORPAY     │

                │ TEST MODE    │

                └──────┬───────┘

                       │

                  payout.failed

                       │

                    webhook

                       ▼

              ┌─────────────────┐

              │ RECOVERY CASE   │

              └────────┬────────┘

                       │

                       ▼

                 ┌───────────┐

                 │ AI AGENT  │

                 └─────┬─────┘

                       │

             ┌─────────┼──────────┐

             ▼         ▼          ▼

           Razorpay   Zoho     Vendor

            Tools     Tools   Communication

             │         │          │

             └─────────┼──────────┘

                       ▼

                POLICY ENGINE

                       │

             ┌─────────┼─────────┐

             ▼         ▼         ▼

           ALLOW    APPROVAL    BLOCK

             │         │

             │         ▼

             │      HUMAN

             │

             ▼

          EXECUTE

             │

             ▼

       RAZORPAY PAYOUT

             │

             ▼

          WEBHOOK

             │

             ▼

          RESOLVED

And **every meaningful transition produces an audit event**.

---

# **12\. What gets simulated vs real**

This is the table I would literally give Antigravity:

| Component | Demo |
| ----- | ----- |
| Razorpay payout creation | **REAL / Test Mode** |
| Razorpay payout failure | **REAL / Test Mode** |
| Razorpay `payout.failed` webhook | **REAL** |
| Failure reason | **REAL** |
| Payout retrieval | **REAL** |
| Contact/vendor | **REAL / Test Mode** |
| Fund account creation | **REAL / Test Mode** |
| Fund account deactivation | **REAL / Test Mode** |
| Account validation | **MOCKED** |
| Zoho vendor/invoice | **REAL / Sandbox** |
| Zoho webhook | **REAL / Sandbox** |
| Vendor conversation | **SIMULATED** |
| AI reasoning | **REAL** |
| Policy engine | **REAL** |
| Human approval | **REAL UI** |
| Audit ledger | **REAL** |
| Test-case generation | **OURS** |

So no, **the plan is absolutely not "simulate everything."**

It's almost the opposite:

> **Use real developer infrastructure wherever Razorpay exposes it; simulate only the external dependencies that aren't realistically accessible in the buildathon environment.**

That is a much stronger engineering story.

One other thing I would add: before Antigravity starts implementation, we should **verify the current Razorpay developer documentation ourselves** for the exact webhook setup, authentication, Test Mode behavior, endpoint payloads and signature verification. Your research is excellent for architecture, but those are implementation-level details where we shouldn't rely blindly on a compiled research report.

