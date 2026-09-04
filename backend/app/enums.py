"""
enums.py
────────
All application-level enums in one place.

Keeping enums separate from models means they can be imported by:
  - SQLAlchemy models (for column types)
  - The state machine (Phase 2)
  - The policy engine (Phase 4)
  - API schemas
  - Test code
...without creating circular imports.
"""

import enum


# ── Recovery Case States ──────────────────────────────────────────────────────
class CaseState(str, enum.Enum):
    """
    Every state the recovery case state machine can be in.
    Inheriting from str makes these directly serialisable to JSON,
    which means they can be stored as plain strings in PostgreSQL
    and returned directly in API responses.
    """
    PAYOUT_FAILED             = "PAYOUT_FAILED"
    CASE_CREATED              = "CASE_CREATED"
    FAILURE_CLASSIFIED        = "FAILURE_CLASSIFIED"
    RECOVERY_STRATEGY_SELECTED = "RECOVERY_STRATEGY_SELECTED"
    VENDOR_CONTACTED          = "VENDOR_CONTACTED"
    INFORMATION_RECEIVED      = "INFORMATION_RECEIVED"
    DATA_VALIDATED            = "DATA_VALIDATED"
    BANK_VALIDATED            = "BANK_VALIDATED"
    POLICY_CHECK              = "POLICY_CHECK"
    PAYOUT_READY              = "PAYOUT_READY"
    HUMAN_REVIEW              = "HUMAN_REVIEW"
    HUMAN_APPROVAL            = "HUMAN_APPROVAL"
    PAYOUT_EXECUTED           = "PAYOUT_EXECUTED"
    PAYOUT_CONFIRMED          = "PAYOUT_CONFIRMED"
    CASE_RESOLVED             = "CASE_RESOLVED"
    ESCALATED                 = "ESCALATED"
    BLOCKED                   = "BLOCKED"


# ── Recovery Strategies ───────────────────────────────────────────────────────
class RecoveryStrategy(str, enum.Enum):
    """
    The recovery path selected by the deterministic failure classifier.
    The agent uses this to know which workflow to run.
    """
    VENDOR_REMEDIATION        = "VENDOR_REMEDIATION"   # Contact vendor for new details
    SCHEDULE_RETRY            = "SCHEDULE_RETRY"        # Transient error, retry later
    HUMAN_ESCALATION          = "HUMAN_ESCALATION"      # Needs human attention
    FINANCE_ESCALATION        = "FINANCE_ESCALATION"    # Internal finance team issue
    INTERNAL_WORKFLOW         = "INTERNAL_WORKFLOW"     # Routing/mode decision needed
    RETRY_LOGIC               = "RETRY_LOGIC"           # Gateway timeout, retry
    BLOCK                     = "BLOCK"                 # Do not proceed
    UNKNOWN_FAILURE           = "UNKNOWN_FAILURE"       # Unrecognised failure code


# ── Risk Levels ───────────────────────────────────────────────────────────────
class RiskLevel(str, enum.Enum):
    """
    Risk assessment for a recovery case.
    Set by the policy engine based on amount, validation scores, and vendor signals.
    """
    LOW    = "LOW"
    MEDIUM = "MEDIUM"
    HIGH   = "HIGH"


# ── Policy Decisions ──────────────────────────────────────────────────────────
class PolicyDecision(str, enum.Enum):
    """
    The output of the policy engine for any proposed agent action.
    """
    ALLOW            = "ALLOW"             # Agent can proceed autonomously
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"  # Pause and wait for human approval
    BLOCK            = "BLOCK"             # Action is not permitted


# ── Policy Levels ─────────────────────────────────────────────────────────────
class PolicyLevel(int, enum.Enum):
    """
    The authority level of each tool/action.
    Stored as an integer so it is easy to compare and filter.
    """
    AUTONOMOUS             = 1  # Read ops, messaging, case creation
    CONTROLLED_MUTATION    = 2  # Fund account creation, ERP updates
    FINANCIALLY_CONSEQUENTIAL = 3  # Payout execution, overrides


# ── Message Direction ─────────────────────────────────────────────────────────
class MessageDirection(str, enum.Enum):
    """Direction of a vendor communication message."""
    INBOUND  = "INBOUND"   # Vendor -> Agent
    OUTBOUND = "OUTBOUND"  # Agent -> Vendor


# ── Audit Event Actor Types ───────────────────────────────────────────────────
class AuditActorType(str, enum.Enum):
    """
    Classifies who or what produced an audit event.
    This distinction is critical for the audit dashboard —
    judges and auditors can see exactly what was a machine fact
    vs. an AI interpretation vs. a human decision.
    """
    EXTERNAL_FACT  = "EXTERNAL_FACT"   # Razorpay webhook, banking system response
    AI_DECISION    = "AI_DECISION"     # LLM classification or recommendation
    SYSTEM_ACTION  = "SYSTEM_ACTION"   # Deterministic API call or state transition
    HUMAN_DECISION = "HUMAN_DECISION"  # Approve, reject, or override by a person


# ── Approval Decisions ────────────────────────────────────────────────────────
class ApprovalDecision(str, enum.Enum):
    """Human decision on an approval request."""
    APPROVE = "APPROVE"
    REJECT  = "REJECT"


# ── Payout Status ─────────────────────────────────────────────────────────────
class PayoutStatus(str, enum.Enum):
    """
    Mirrors the Razorpay payout status values we care about.
    Reference: Razorpay Payout API docs.
    """
    PROCESSING = "processing"
    PROCESSED  = "processed"
    FAILED     = "failed"
    REVERSED   = "reversed"
    CANCELLED  = "cancelled"
    QUEUED     = "queued"


# ── Fund Account Validation Status ───────────────────────────────────────────
class ValidationStatus(str, enum.Enum):
    """
    Status of a fund account after bank validation is run.
    Note: in demo mode, this is set by the mock validation service.
    """
    PENDING  = "PENDING"
    ACTIVE   = "ACTIVE"
    INACTIVE = "INACTIVE"
    UNKNOWN  = "UNKNOWN"
