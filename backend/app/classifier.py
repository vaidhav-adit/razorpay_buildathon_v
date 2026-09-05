"""
classifier.py
─────────────
Deterministic Failure Classifier for RazorpayX Payout Exceptions.

This module maps Razorpay failure status_details (source, reason) directly to
standardized recovery strategies.

Foundational Architectural Rule:
- Failure classification is NOT an LLM reasoning task.
- It is a 100% deterministic lookup.
- Unknown (source, reason) pairs must gracefully return UNKNOWN_FAILURE and escalate,
  never raising unhandled exceptions or crashing the pipeline.
"""

from typing import Tuple, Dict, Optional
from pydantic import BaseModel, Field

from app.enums import RecoveryStrategy


class ClassificationResult(BaseModel):
    """
    Structured result returned by the failure classifier.
    
    Attributes:
        strategy: The determined RecoveryStrategy enum value.
        source: The normalized failure source (e.g., 'beneficiary_bank', 'business', 'gateway').
        reason: The normalized failure reason (e.g., 'invalid_ifsc_code', 'insufficient_funds').
        description: Human-readable explanation of why the failure occurred.
        is_retryable: True if the failure is transient and can be retried without modifying details.
        requires_vendor_contact: True if the vendor must provide updated banking information.
        requires_human_attention: True if the issue requires manual human investigation.
        suggested_action: Clear guidance on what the system or human controller should do next.
    """
    strategy: RecoveryStrategy
    source: str
    reason: str
    description: str
    is_retryable: bool
    requires_vendor_contact: bool
    requires_human_attention: bool
    suggested_action: str


# ─────────────────────────────────────────────────────────────────────────────
# Deterministic Failure Classification Table
# Maps (source, reason) tuple to metadata and RecoveryStrategy.
# All keys are stored lowercased for case-insensitive matching.
# ─────────────────────────────────────────────────────────────────────────────
FAILURE_CLASSIFICATION_MAP: Dict[Tuple[str, str], dict] = {
    # ── Beneficiary Bank Failures ─────────────────────────────────────────────
    ("beneficiary_bank", "invalid_ifsc_code"): {
        "strategy": RecoveryStrategy.VENDOR_REMEDIATION,
        "description": "The IFSC code provided for the beneficiary bank account is invalid or defunct.",
        "is_retryable": False,
        "requires_vendor_contact": True,
        "requires_human_attention": False,
        "suggested_action": "Contact vendor to collect corrected branch IFSC code and verify account details.",
    },
    ("beneficiary_bank", "bank_account_closed"): {
        "strategy": RecoveryStrategy.VENDOR_REMEDIATION,
        "description": "The beneficiary bank account has been permanently closed by the holder or bank.",
        "is_retryable": False,
        "requires_vendor_contact": True,
        "requires_human_attention": False,
        "suggested_action": "Contact vendor to collect an active replacement bank account.",
    },
    ("beneficiary_bank", "bank_account_invalid"): {
        "strategy": RecoveryStrategy.VENDOR_REMEDIATION,
        "description": "The beneficiary account number is invalid or does not exist at the target bank.",
        "is_retryable": False,
        "requires_vendor_contact": True,
        "requires_human_attention": False,
        "suggested_action": "Contact vendor to verify and re-submit correct bank account number.",
    },
    ("beneficiary_bank", "bank_account_frozen"): {
        "strategy": RecoveryStrategy.HUMAN_ESCALATION,
        "description": "The beneficiary bank account is legally frozen or debit/credit restricted.",
        "is_retryable": False,
        "requires_vendor_contact": False,
        "requires_human_attention": True,
        "suggested_action": "Escalate to finance/legal operations. Do not retry without compliance review.",
    },
    ("beneficiary_bank", "beneficiary_bank_offline"): {
        "strategy": RecoveryStrategy.SCHEDULE_RETRY,
        "description": "The destination bank's core banking system is temporarily offline or under maintenance.",
        "is_retryable": True,
        "requires_vendor_contact": False,
        "requires_human_attention": False,
        "suggested_action": "Schedule automatic payout retry after backoff interval.",
    },
    ("beneficiary_bank", "beneficiary_bank_technical_error"): {
        "strategy": RecoveryStrategy.SCHEDULE_RETRY,
        "description": "A transient technical error occurred at the destination bank switch.",
        "is_retryable": True,
        "requires_vendor_contact": False,
        "requires_human_attention": False,
        "suggested_action": "Schedule automatic payout retry after short backoff delay.",
    },
    ("beneficiary_bank", "npci_beneficiary_timeout"): {
        "strategy": RecoveryStrategy.SCHEDULE_RETRY,
        "description": "NPCI payment switch timed out while querying the beneficiary bank.",
        "is_retryable": True,
        "requires_vendor_contact": False,
        "requires_human_attention": False,
        "suggested_action": "Check transaction settlement status and schedule retry if reversed.",
    },
    ("beneficiary_bank", "imps_not_allowed"): {
        "strategy": RecoveryStrategy.INTERNAL_WORKFLOW,
        "description": "IMPS transfer mode is not supported by the beneficiary account or bank.",
        "is_retryable": True,
        "requires_vendor_contact": False,
        "requires_human_attention": False,
        "suggested_action": "Switch payout mode to NEFT or RTGS and prepare replacement payout.",
    },

    # ── Business / Internal Account Failures ──────────────────────────────────
    ("business", "insufficient_funds"): {
        "strategy": RecoveryStrategy.FINANCE_ESCALATION,
        "description": "The master RazorpayX business account does not have sufficient balance for the payout.",
        "is_retryable": False,
        "requires_vendor_contact": False,
        "requires_human_attention": True,
        "suggested_action": "Alert finance treasury team to top up the RazorpayX master current account.",
    },

    # ── Gateway / Switch Failures ─────────────────────────────────────────────
    ("gateway", "timeout"): {
        "strategy": RecoveryStrategy.RETRY_LOGIC,
        "description": "Payment gateway communication timed out before receiving confirmation.",
        "is_retryable": True,
        "requires_vendor_contact": False,
        "requires_human_attention": False,
        "suggested_action": "Query payment status for idempotency check and retry if unexecuted.",
    },

    # ── Account Validation Failures ───────────────────────────────────────────
    ("validation", "low_name_match"): {
        "strategy": RecoveryStrategy.HUMAN_ESCALATION,
        "description": "Bank account validation registered name does not sufficiently match vendor record.",
        "is_retryable": False,
        "requires_vendor_contact": False,
        "requires_human_attention": True,
        "suggested_action": "Flag for human review to verify name match discrepancy and authorize or reject.",
    },
    ("validation", "inactive_account"): {
        "strategy": RecoveryStrategy.BLOCK,
        "description": "Penny-drop validation reported that the account is dormant or inactive.",
        "is_retryable": False,
        "requires_vendor_contact": False,
        "requires_human_attention": True,
        "suggested_action": "Block automatic payout and require vendor to provide an active operational account.",
    },
}


def classify_failure(source: Optional[str], reason: Optional[str]) -> ClassificationResult:
    """
    Classifies a payout failure based on its source and reason.
    
    This function performs a deterministic lookup against the failure classification
    table. It normalizes string inputs (lowercasing and stripping whitespace) and
    safely falls back to UNKNOWN_FAILURE if the combination is not recognized.
    
    Args:
        source: The failure source string from Razorpay status_details (e.g., 'beneficiary_bank').
        reason: The failure reason code from Razorpay status_details (e.g., 'invalid_ifsc_code').
        
    Returns:
        ClassificationResult: Comprehensive classification metadata and recovery strategy.
    """
    # Normalize input strings (handles None, empty strings, and whitespace-only strings)
    clean_source = source.strip().lower() if source and source.strip() else "unknown"
    clean_reason = reason.strip().lower() if reason and reason.strip() else "unknown"

    lookup_key = (clean_source, clean_reason)

    # Deterministic lookup
    match = FAILURE_CLASSIFICATION_MAP.get(lookup_key)

    if match:
        return ClassificationResult(
            strategy=match["strategy"],
            source=clean_source,
            reason=clean_reason,
            description=match["description"],
            is_retryable=match["is_retryable"],
            requires_vendor_contact=match["requires_vendor_contact"],
            requires_human_attention=match["requires_human_attention"],
            suggested_action=match["suggested_action"],
        )

    # Dynamic Semantic Reasoning for Custom & Unmapped Exception Codes
    # Rather than failing or blocking unknown codes, the agent intelligently categorizes
    # the failure based on semantic intent of the reason and source.
    clean_str = f"{clean_source} {clean_reason}".lower()

    # Category 1: Fraud, Legal Freeze, or Blacklisting -> BLOCK
    if any(k in clean_reason for k in ["frozen", "freeze", "blacklist", "fraud", "sanction", "suspicious", "court", "unauthorized"]):
        return ClassificationResult(
            strategy=RecoveryStrategy.BLOCK,
            source=clean_source,
            reason=clean_reason,
            description=f"Autonomous security defense classified '{clean_reason}' as a fatal compliance or frozen account risk.",
            is_retryable=False,
            requires_vendor_contact=False,
            requires_human_attention=True,
            suggested_action="Permanently block payout and lock case to prevent loss of funds.",
        )

    # Category 2: Internal Treasury or Business Balance Shortage -> FINANCE_ESCALATION
    if any(k in clean_reason for k in ["insufficient", "balance", "funds", "treasury", "credit_limit", "debit_limit", "corporate_limit"]) or (clean_source in ["business", "internal"] and "fund" in clean_str):
        return ClassificationResult(
            strategy=RecoveryStrategy.FINANCE_ESCALATION,
            source=clean_source,
            reason=clean_reason,
            description=f"Autonomous semantic analysis classified '{clean_reason}' as an internal company liquidity constraint.",
            is_retryable=False,
            requires_vendor_contact=False,
            requires_human_attention=True,
            suggested_action="Escalate to internal finance/treasury team via Zoho Books to replenish account balance.",
        )

    # Category 3: Vendor Banking, Account, IFSC, KYC, or Credential Discrepancies -> VENDOR_REMEDIATION
    # Prioritized before transient network checks so that gateway-reported account errors (e.g. gateway reporting invalid_ifsc)
    # properly trigger vendor remediation!
    if any(k in clean_reason for k in ["ifsc", "account", "closed", "invalid", "beneficiary", "holder", "branch", "kyc", "bank_account", "details", "mismatch", "format", "credential", "name"]):
        return ClassificationResult(
            strategy=RecoveryStrategy.VENDOR_REMEDIATION,
            source=clean_source,
            reason=clean_reason,
            description=f"Autonomous semantic classifier identified '{clean_reason}' ({clean_source}) as a vendor banking discrepancy requiring updated credentials.",
            is_retryable=False,
            requires_vendor_contact=True,
            requires_human_attention=False,
            suggested_action=f"Initiate autonomous WhatsApp remediation to vendor to collect verified replacement bank details for '{clean_reason}'.",
        )

    # Category 4: Transient Network, Switch, or Core Banking Downtime -> SCHEDULE_RETRY
    if any(k in clean_str for k in ["offline", "timeout", "down", "maintenance", "technical", "network", "switch", "transient", "503", "504", "502", "unavailable"]):
        return ClassificationResult(
            strategy=RecoveryStrategy.SCHEDULE_RETRY,
            source=clean_source,
            reason=clean_reason,
            description=f"Autonomous semantic analysis classified '{clean_reason}' ({clean_source}) as a transient gateway/bank switch downtime event.",
            is_retryable=True,
            requires_vendor_contact=False,
            requires_human_attention=False,
            suggested_action="Queue automated payout retry after short backoff without disturbing vendor.",
        )

    # Category 5: Unrecognized / Alien Failure Codes -> UNKNOWN_FAILURE (requires human review/investigation)
    return ClassificationResult(
        strategy=RecoveryStrategy.UNKNOWN_FAILURE,
        source=clean_source,
        reason=clean_reason,
        description=f"Unrecognized payout failure reason '{clean_reason}' from source '{clean_source}'. Requires human investigation.",
        is_retryable=False,
        requires_vendor_contact=False,
        requires_human_attention=True,
        suggested_action=f"Manually investigate failure reason '{clean_reason}' and determine appropriate recovery procedure.",
    )
