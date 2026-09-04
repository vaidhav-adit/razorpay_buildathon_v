"""
policy_engine.py
────────────────
Deterministic Authority and Policy Engine for the RazorpayX Resolution Agent.

This module evaluates proposed agent actions against business rules, risk levels,
financial limits, and state guards.

Foundational Architectural Principle:
- AI reasons and proposes actions.
- Deterministic policy engine checks permissions.
- Level 1 (Autonomous) -> ALLOW always.
- Level 2 (Controlled Mutation) -> ALLOW if within risk/data thresholds, else REQUIRE_APPROVAL.
- Level 3 (Financially Consequential) -> REQUIRE_APPROVAL ALWAYS (Zero LLM autonomy over money).
- BLOCKED or CASE_RESOLVED states -> BLOCK all mutation actions.
"""

from typing import Optional, Dict
from pydantic import BaseModel, Field

from app.config import settings
from app.enums import CaseState, RiskLevel, PolicyDecision, PolicyLevel


class PolicyContext(BaseModel):
    """
    Contextual information regarding the current recovery case used to evaluate policy.
    
    Attributes:
        case_state: Current lifecycle state of the recovery case.
        risk_level: Risk assessment (LOW, MEDIUM, HIGH).
        amount_in_paise: Payout amount in paise (e.g., 500000 paise = INR 5,000.00).
        name_match_score: Score from bank account validation (0-100), if available.
        is_account_active: Verification status of the target account.
        vendor_verified: Whether vendor contact/identity was confirmed.
        data_validated: Whether account format/IFSC syntax passed deterministic validation.
    """
    case_state: CaseState = CaseState.PAYOUT_FAILED
    risk_level: RiskLevel = RiskLevel.LOW
    amount_in_paise: int = 0
    name_match_score: Optional[int] = None
    is_account_active: Optional[bool] = None
    vendor_verified: bool = True
    data_validated: bool = True


class PolicyEvaluationResult(BaseModel):
    """
    Structured outcome returned by the policy engine for any proposed action.
    
    Attributes:
        decision: ALLOW, REQUIRE_APPROVAL, or BLOCK.
        level: Authority level (Level 1, Level 2, Level 3).
        action_name: The name of the evaluated action.
        reason: Human-readable rationale for the decision.
        requires_human: Boolean convenience property (True when decision is REQUIRE_APPROVAL).
    """
    decision: PolicyDecision
    level: PolicyLevel
    action_name: str
    reason: str
    requires_human: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# Action Registry
# Maps every tool/operation name to its strict PolicyLevel.
# ─────────────────────────────────────────────────────────────────────────────
ACTION_REGISTRY: Dict[str, PolicyLevel] = {
    # ── Level 1: Autonomous (Read Operations, Ingestion, Messaging) ───────────
    "get_payout": PolicyLevel.AUTONOMOUS,
    "read_payout": PolicyLevel.AUTONOMOUS,
    "get_contact": PolicyLevel.AUTONOMOUS,
    "read_vendor": PolicyLevel.AUTONOMOUS,
    "get_fund_accounts": PolicyLevel.AUTONOMOUS,
    "find_vendor": PolicyLevel.AUTONOMOUS,
    "find_invoice": PolicyLevel.AUTONOMOUS,
    "get_vendor_bank_details": PolicyLevel.AUTONOMOUS,
    "classify_failure": PolicyLevel.AUTONOMOUS,
    "send_vendor_message": PolicyLevel.AUTONOMOUS,
    "create_recovery_case": PolicyLevel.AUTONOMOUS,
    "parse_vendor_response": PolicyLevel.AUTONOMOUS,
    "query_status": PolicyLevel.AUTONOMOUS,
    "log_audit_event": PolicyLevel.AUTONOMOUS,

    # ── Level 2: Controlled Mutation (State & Entity Modifications) ───────────
    "create_fund_account": PolicyLevel.CONTROLLED_MUTATION,
    "deactivate_fund_account": PolicyLevel.CONTROLLED_MUTATION,
    "update_erp_vendor": PolicyLevel.CONTROLLED_MUTATION,
    "update_vendor_bank_details": PolicyLevel.CONTROLLED_MUTATION,
    "update_invoice_status": PolicyLevel.CONTROLLED_MUTATION,
    "initiate_account_validation": PolicyLevel.CONTROLLED_MUTATION,
    "validate_fund_account": PolicyLevel.CONTROLLED_MUTATION,
    "update_case_state": PolicyLevel.CONTROLLED_MUTATION,
    "schedule_retry": PolicyLevel.CONTROLLED_MUTATION,

    # ── Level 3: Financially Consequential (Money Movement & Overrides) ────────
    "execute_payout": PolicyLevel.FINANCIALLY_CONSEQUENTIAL,
    "execute_replacement_payout": PolicyLevel.FINANCIALLY_CONSEQUENTIAL,
    "override_validation": PolicyLevel.FINANCIALLY_CONSEQUENTIAL,
    "override_risk_policy": PolicyLevel.FINANCIALLY_CONSEQUENTIAL,
    "approve_large_transaction": PolicyLevel.FINANCIALLY_CONSEQUENTIAL,
}


def get_action_policy_level(action_name: str) -> PolicyLevel:
    """
    Retrieve the authority level for a given action name.
    Unregistered actions default safely to Level 3 (Financially Consequential).
    """
    normalized_action = action_name.strip().lower()
    return ACTION_REGISTRY.get(normalized_action, PolicyLevel.FINANCIALLY_CONSEQUENTIAL)


def evaluate_policy(action_name: str, context: Optional[PolicyContext] = None) -> PolicyEvaluationResult:
    """
    Evaluates whether a proposed agent action is allowed, requires human approval, or is blocked.
    
    Evaluation Rules:
    1. Terminal/Blocked States:
       - If case is in BLOCKED or CASE_RESOLVED, all state mutations and financial actions are BLOCKED.
       - Read operations are allowed for audit/history inspection.
    2. Escalated State:
       - If case is ESCALATED, mutations require approval or are blocked until triaged.
    3. Level 1 (Autonomous):
       - Always ALLOWED.
    4. Level 2 (Controlled Mutation):
       - ALLOWED if: data is validated, vendor verified, risk is not HIGH, and validation meets threshold.
       - REQUIRE_APPROVAL if: high risk, name match score below threshold, or vendor unverified.
       - BLOCKED if: target account is explicitly inactive.
    5. Level 3 (Financially Consequential):
       - ALWAYS REQUIRE_APPROVAL. No autonomous money movement is ever allowed.
       
    Args:
        action_name: The identifier of the action/tool to be executed.
        context: PolicyContext containing state, risk, validation results, and amounts.
        
    Returns:
        PolicyEvaluationResult: Decision (ALLOW, REQUIRE_APPROVAL, BLOCK) with justification.
    """
    ctx = context or PolicyContext()
    normalized_action = action_name.strip().lower()
    level = get_action_policy_level(normalized_action)

    # ─────────────────────────────────────────────────────────────────────────
    # Rule 0: State-based Immobility & Guards
    # ─────────────────────────────────────────────────────────────────────────
    if ctx.case_state == CaseState.BLOCKED:
        if level == PolicyLevel.AUTONOMOUS:
            return PolicyEvaluationResult(
                decision=PolicyDecision.ALLOW,
                level=level,
                action_name=normalized_action,
                reason="Read operation allowed on blocked case for audit inspection.",
                requires_human=False,
            )
        return PolicyEvaluationResult(
            decision=PolicyDecision.BLOCK,
            level=level,
            action_name=normalized_action,
            reason=f"Action '{normalized_action}' is blocked because the case is in BLOCKED state.",
            requires_human=False,
        )

    if ctx.case_state == CaseState.CASE_RESOLVED:
        if level == PolicyLevel.AUTONOMOUS:
            return PolicyEvaluationResult(
                decision=PolicyDecision.ALLOW,
                level=level,
                action_name=normalized_action,
                reason="Read operation allowed on resolved case for audit inspection.",
                requires_human=False,
            )
        return PolicyEvaluationResult(
            decision=PolicyDecision.BLOCK,
            level=level,
            action_name=normalized_action,
            reason=f"Action '{normalized_action}' is blocked because the case is already CASE_RESOLVED.",
            requires_human=False,
        )

    if ctx.case_state == CaseState.ESCALATED:
        if level == PolicyLevel.AUTONOMOUS:
            return PolicyEvaluationResult(
                decision=PolicyDecision.ALLOW,
                level=level,
                action_name=normalized_action,
                reason="Read operation allowed on escalated case.",
                requires_human=False,
            )
        return PolicyEvaluationResult(
            decision=PolicyDecision.REQUIRE_APPROVAL,
            level=level,
            action_name=normalized_action,
            reason=f"Action '{normalized_action}' on an ESCALATED case requires human triage and approval.",
            requires_human=True,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Rule 1: Level 1 — Autonomous Actions (Always Allowed)
    # ─────────────────────────────────────────────────────────────────────────
    if level == PolicyLevel.AUTONOMOUS:
        return PolicyEvaluationResult(
            decision=PolicyDecision.ALLOW,
            level=level,
            action_name=normalized_action,
            reason=f"Level 1 action '{normalized_action}' is permitted autonomously.",
            requires_human=False,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Rule 2: Level 2 — Controlled Mutations (Conditional Permission)
    # ─────────────────────────────────────────────────────────────────────────
    if level == PolicyLevel.CONTROLLED_MUTATION:
        # Check 2a: Target account reported inactive/dormant -> BLOCK
        if ctx.is_account_active is False:
            return PolicyEvaluationResult(
                decision=PolicyDecision.BLOCK,
                level=level,
                action_name=normalized_action,
                reason="Target fund account is inactive or dormant. Mutation blocked.",
                requires_human=False,
            )

        # Check 2b: Data format/syntax validation failed -> REQUIRE_APPROVAL
        if not ctx.data_validated:
            return PolicyEvaluationResult(
                decision=PolicyDecision.REQUIRE_APPROVAL,
                level=level,
                action_name=normalized_action,
                reason="Underlying data validation has not passed. Human approval required.",
                requires_human=True,
            )

        # Check 2c: Vendor identity unverified -> REQUIRE_APPROVAL
        if not ctx.vendor_verified:
            return PolicyEvaluationResult(
                decision=PolicyDecision.REQUIRE_APPROVAL,
                level=level,
                action_name=normalized_action,
                reason="Vendor identity is not confirmed. Human approval required.",
                requires_human=True,
            )

        # Check 2d: Name match score threshold evaluation
        min_name_score = getattr(settings, "MIN_NAME_MATCH_SCORE", 85)
        if ctx.name_match_score is not None and ctx.name_match_score < min_name_score:
            return PolicyEvaluationResult(
                decision=PolicyDecision.REQUIRE_APPROVAL,
                level=level,
                action_name=normalized_action,
                reason=(
                    f"Name match score ({ctx.name_match_score}%) is below the auto-approval threshold "
                    f"({min_name_score}%). Human approval required."
                ),
                requires_human=True,
            )

        # Check 2e: High risk cases require approval for mutations
        if ctx.risk_level == RiskLevel.HIGH:
            return PolicyEvaluationResult(
                decision=PolicyDecision.REQUIRE_APPROVAL,
                level=level,
                action_name=normalized_action,
                reason="High-risk case requires human approval for state or entity mutations.",
                requires_human=True,
            )

        # All Level 2 checks passed -> ALLOW
        return PolicyEvaluationResult(
            decision=PolicyDecision.ALLOW,
            level=level,
            action_name=normalized_action,
            reason=f"Level 2 action '{normalized_action}' satisfies all risk and validation policies.",
            requires_human=False,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Rule 3: Level 3 — Financially Consequential Actions (Strict Human Gate)
    # ─────────────────────────────────────────────────────────────────────────
    if level == PolicyLevel.FINANCIALLY_CONSEQUENTIAL:
        return PolicyEvaluationResult(
            decision=PolicyDecision.REQUIRE_APPROVAL,
            level=level,
            action_name=normalized_action,
            reason=(
                f"Level 3 action '{normalized_action}' is financially consequential. "
                "Money movement and security overrides strictly require human authorization."
            ),
            requires_human=True,
        )

    # Fallback safety guard
    return PolicyEvaluationResult(
        decision=PolicyDecision.REQUIRE_APPROVAL,
        level=PolicyLevel.FINANCIALLY_CONSEQUENTIAL,
        action_name=normalized_action,
        reason=f"Unclassified action '{normalized_action}' defaulted to strict human approval.",
        requires_human=True,
    )
