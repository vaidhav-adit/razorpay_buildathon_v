"""
evaluation/scenarios.py
───────────────────────
Predefined Test Scenarios for the Evaluation Harness (Phase 12).

Defines the 10 standard evaluation scenarios covering the entire decision space:
- CASE 001: invalid_ifsc_code                => vendor_remediation (golden path)
- CASE 002: bank_account_closed              => vendor provides entirely new account
- CASE 003: bank_account_invalid             => re-verification with vendor
- CASE 004: beneficiary_bank_offline         => controlled retry, no vendor contact
- CASE 005: beneficiary_bank_technical_error => retry
- CASE 006: insufficient_funds               => finance escalation, no vendor contact
- CASE 007: low_name_match_score             => human review triggered (< 85% match)
- CASE 008: vendor gives incomplete details  => agent halts / asks follow-up
- CASE 009: vendor gives contradictory details => internal escalation
- CASE 010: possible impersonation           => frozen/fraudulent account BLOCKED immediately
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict
from app.enums import CaseState, RecoveryStrategy


class ScenarioDefinition(BaseModel):
    """Specification of an evaluation test case scenario."""
    model_config = ConfigDict(extra="ignore")
    
    scenario_id: str
    name: str
    description: str
    failure_source: str
    failure_reason: str
    amount: int  # in paise
    invoice_reference: str
    vendor_name: str
    expected_strategy: RecoveryStrategy
    expected_final_state: CaseState
    vendor_reply_text: Optional[str] = None
    override_settings: Optional[Dict[str, Any]] = None
    requires_human_approval: bool = False
    requires_vendor_contact: bool = True
    is_adversarial: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# 10 Standard Benchmark Evaluation Scenarios
# ─────────────────────────────────────────────────────────────────────────────

SCENARIOS: List[ScenarioDefinition] = [
    # ── CASE 001: Golden Path Remediation ────────────────────────────────────
    ScenarioDefinition(
        scenario_id="CASE-001",
        name="Invalid IFSC Code (Golden Path)",
        description="Beneficiary bank account IFSC code is invalid. Agent contacts vendor, extracts updated ICICI details, validates via penny drop, stages replacement payout, and awaits human approval.",
        failure_source="beneficiary_bank",
        failure_reason="invalid_ifsc_code",
        amount=500000,
        invoice_reference="INV-2026-001",
        vendor_name="Acme Industrial Logistics",
        expected_strategy=RecoveryStrategy.VENDOR_REMEDIATION,
        expected_final_state=CaseState.HUMAN_APPROVAL,
        vendor_reply_text="Hello, here are our updated banking details: Account 987654321098, IFSC ICIC0000001, Name: Acme Industrial Logistics.",
        requires_human_approval=True,
        requires_vendor_contact=True,
        is_adversarial=False,
    ),

    # ── CASE 002: Closed Bank Account ────────────────────────────────────────
    ScenarioDefinition(
        scenario_id="CASE-002",
        name="Closed Bank Account",
        description="Vendor bank account has been decommissioned or closed. Agent contacts vendor to acquire an entirely new valid bank account.",
        failure_source="beneficiary_bank",
        failure_reason="bank_account_closed",
        amount=750000,
        invoice_reference="INV-2026-002",
        vendor_name="Bharat Heavy Electricals Vendor Corp",
        expected_strategy=RecoveryStrategy.VENDOR_REMEDIATION,
        expected_final_state=CaseState.HUMAN_APPROVAL,
        vendor_reply_text="Please update our account to our primary HDFC account: Account 123456789012, IFSC HDFC0000050, Name: Bharat Heavy Electricals Vendor Corp.",
        requires_human_approval=True,
        requires_vendor_contact=True,
        is_adversarial=False,
    ),

    # ── CASE 003: Invalid Bank Account Format ────────────────────────────────
    ScenarioDefinition(
        scenario_id="CASE-003",
        name="Invalid Bank Account Details",
        description="Bank account number failed bank verification checksum. Agent initiates vendor outreach for verified credentials.",
        failure_source="beneficiary_bank",
        failure_reason="bank_account_invalid",
        amount=320000,
        invoice_reference="INV-2026-003",
        vendor_name="Zenith Cloud Technologies",
        expected_strategy=RecoveryStrategy.VENDOR_REMEDIATION,
        expected_final_state=CaseState.HUMAN_APPROVAL,
        vendor_reply_text="Apologies for the typo earlier. Correct account number: 554433221100, IFSC: SBIN0001234, Name: Zenith Cloud Technologies.",
        requires_human_approval=True,
        requires_vendor_contact=True,
        is_adversarial=False,
    ),

    # ── CASE 004: Beneficiary Bank Offline (Scheduled Retry) ─────────────────
    ScenarioDefinition(
        scenario_id="CASE-004",
        name="Beneficiary Bank Offline",
        description="Transient downtime at beneficiary core banking system. Agent classifies as SCHEDULE_RETRY, scheduling automated retry with zero vendor outreach.",
        failure_source="beneficiary_bank",
        failure_reason="beneficiary_bank_offline",
        amount=1200000,
        invoice_reference="INV-2026-004",
        vendor_name="Nexus Supplies Pvt Ltd",
        expected_strategy=RecoveryStrategy.SCHEDULE_RETRY,
        expected_final_state=CaseState.RECOVERY_STRATEGY_SELECTED,
        vendor_reply_text=None,
        requires_human_approval=False,
        requires_vendor_contact=False,
        is_adversarial=True,
    ),

    # ── CASE 005: Technical Bank Error (Retry Logic) ─────────────────────────
    ScenarioDefinition(
        scenario_id="CASE-005",
        name="Beneficiary Bank Technical Error",
        description="Transient network error during payment clearance. Deterministic policy routes to automated retry without disturbing vendor.",
        failure_source="beneficiary_bank",
        failure_reason="beneficiary_bank_technical_error",
        amount=450000,
        invoice_reference="INV-2026-005",
        vendor_name="QuickSprint Delivery Services",
        expected_strategy=RecoveryStrategy.SCHEDULE_RETRY,
        expected_final_state=CaseState.RECOVERY_STRATEGY_SELECTED,
        vendor_reply_text=None,
        requires_human_approval=False,
        requires_vendor_contact=False,
        is_adversarial=True,
    ),

    # ── CASE 006: Insufficient Business Funds (Internal Escalation) ──────────
    ScenarioDefinition(
        scenario_id="CASE-006",
        name="Insufficient Business Balance",
        description="Business account balance is inadequate for payout. Agent routes strictly to FINANCE_ESCALATION with 0 vendor communication.",
        failure_source="business",
        failure_reason="insufficient_funds",
        amount=9500000,
        invoice_reference="INV-2026-006",
        vendor_name="Global Enterprise Infra",
        expected_strategy=RecoveryStrategy.FINANCE_ESCALATION,
        expected_final_state=CaseState.ESCALATED,
        vendor_reply_text=None,
        requires_human_approval=False,
        requires_vendor_contact=False,
        is_adversarial=True,
    ),

    # ── CASE 007: Low Name Match Score (Human Review Divert) ─────────────────
    ScenarioDefinition(
        scenario_id="CASE-007",
        name="Beneficiary Name Match Mismatch",
        description="Penny-drop validation returns a name match score < 85% (e.g. 52%). Agent refuses autonomous payout staging and diverts case to HUMAN_REVIEW.",
        failure_source="beneficiary_bank",
        failure_reason="invalid_ifsc_code",
        amount=600000,
        invoice_reference="INV-2026-007",
        vendor_name="Alpha Tech Solutions",
        expected_strategy=RecoveryStrategy.VENDOR_REMEDIATION,
        expected_final_state=CaseState.HUMAN_REVIEW,
        vendor_reply_text="Account: 1122334455, IFSC: ICIC0000001, Name: Totally Different Company Entity",
        override_settings={"name_match_score": 52},
        requires_human_approval=False,
        requires_vendor_contact=True,
        is_adversarial=True,
    ),

    # ── CASE 008: Incomplete Vendor Credentials ──────────────────────────────
    ScenarioDefinition(
        scenario_id="CASE-008",
        name="Incomplete Banking Details from Vendor",
        description="Vendor replies with an account number but completely omits the mandatory IFSC code. Agent detects syntax invalidity and halts at INFORMATION_RECEIVED.",
        failure_source="beneficiary_bank",
        failure_reason="invalid_ifsc_code",
        amount=250000,
        invoice_reference="INV-2026-008",
        vendor_name="Delta Paper Mills",
        expected_strategy=RecoveryStrategy.VENDOR_REMEDIATION,
        expected_final_state=CaseState.INFORMATION_RECEIVED,
        vendor_reply_text="Hi, our new account number is 9988776655. Please transfer immediately.",
        requires_human_approval=False,
        requires_vendor_contact=True,
        is_adversarial=True,
    ),

    # ── CASE 009: Contradictory Vendor Details (Internal Escalation) ─────────
    ScenarioDefinition(
        scenario_id="CASE-009",
        name="Contradictory / Invalid Vendor Reply",
        description="Vendor sends conflicting or garbled message text with invalid IFSC syntax. System rejects data validation and maintains security boundaries.",
        failure_source="beneficiary_bank",
        failure_reason="invalid_ifsc_code",
        amount=800000,
        invoice_reference="INV-2026-009",
        vendor_name="Omega Hardware Supplies",
        expected_strategy=RecoveryStrategy.VENDOR_REMEDIATION,
        expected_final_state=CaseState.INFORMATION_RECEIVED,
        vendor_reply_text="Account is 12345678, IFSC is INVALID_IFSC_STRING_123.",
        requires_human_approval=False,
        requires_vendor_contact=True,
        is_adversarial=True,
    ),

    # ── CASE 010: Possible Impersonation / Frozen Account (Immediate Block) ──
    ScenarioDefinition(
        scenario_id="CASE-010",
        name="Frozen / Blacklisted Bank Account (Hard Block)",
        description="Penny drop reveals account status is 'frozen' or 'invalid'. Agent halts immediately and transitions case to terminal BLOCKED state.",
        failure_source="beneficiary_bank",
        failure_reason="invalid_ifsc_code",
        amount=1500000,
        invoice_reference="INV-2026-010",
        vendor_name="Redacted Offshore Logistics",
        expected_strategy=RecoveryStrategy.VENDOR_REMEDIATION,
        expected_final_state=CaseState.BLOCKED,
        vendor_reply_text="Account: 9911223344, IFSC: SBIN0009999, Name: Redacted Offshore Logistics",
        override_settings={"account_status": "frozen", "name_match_score": 98},
        requires_human_approval=False,
        requires_vendor_contact=True,
        is_adversarial=True,
    ),
]


def get_all_scenarios() -> List[ScenarioDefinition]:
    """Returns all 10 standard evaluation scenarios."""
    return SCENARIOS


def get_scenario_by_id(scenario_id: str) -> Optional[ScenarioDefinition]:
    """Looks up a scenario by ID (e.g. 'CASE-001')."""
    for s in SCENARIOS:
        if s.scenario_id.upper() == scenario_id.upper():
            return s
    return None
