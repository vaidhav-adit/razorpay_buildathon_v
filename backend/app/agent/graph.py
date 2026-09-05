"""
agent/graph.py
──────────────
Inner Reasoning Graph Nodes (Phase 10).

Executes reasoning and tool sequencing inside each state node of the recovery workflow:
1. FAILURE_CLASSIFIED / RECOVERY_STRATEGY_SELECTED: Investigates failure source, determines strategy.
2. VENDOR_CONTACTED: Fetches vendor/invoice context, composes and sends outreach.
3. INFORMATION_RECEIVED / DATA_VALIDATED: Parses reply with LLM, runs deterministic syntax validation.
4. BANK_VALIDATED: Provisions replacement fund account, executes penny-drop simulation.
5. POLICY_CHECK: Validates recovery constraints, deactivates old account, updates ERP.
6. PAYOUT_READY / HUMAN_APPROVAL: Prepares replacement payout card, halts for human approval.
"""

import re
import uuid
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.enums import CaseState, RecoveryStrategy, RiskLevel, PolicyDecision
from app.models.recovery_case import RecoveryCaseModel
from app.models.payout import Payout
from app.models.vendor import Vendor
from app.classifier import classify_failure
from app.policy_engine import evaluate_policy, PolicyContext
from app.agent.llm import llm_client, ExtractedBankingData
from app.agent.tools import (
    tool_get_payout,
    tool_get_contact,
    tool_find_vendor,
    tool_find_invoice,
    tool_send_vendor_message,
    tool_create_fund_account,
    tool_deactivate_fund_account,
    tool_validate_fund_account,
    tool_update_vendor_bank_details,
    tool_prepare_replacement_payout,
)


class AgentNodeOutput(BaseModel):
    """Structured result returned by a reasoning node to the state machine."""
    model_config = ConfigDict(extra="ignore")
    next_state: CaseState
    transition_reason: str
    tools_executed: List[str] = []
    extracted_data: Optional[Dict[str, Any]] = None
    requires_human: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# Reasoning Node Implementations
# ─────────────────────────────────────────────────────────────────────────────

def run_case_classification_node(case: RecoveryCaseModel, db: Session) -> AgentNodeOutput:
    """
    Node: CASE_CREATED -> FAILURE_CLASSIFIED -> RECOVERY_STRATEGY_SELECTED
    Classifies root cause failure and sets the recovery strategy.
    """
    tools = []
    payout = db.query(Payout).filter(Payout.id == case.payout_id).first()
    payout_id = payout.razorpay_payout_id if payout else f"pout_{case.id}"

    # Read payout tool
    payout_data = tool_get_payout(case.id, payout_id, db)
    tools.append("get_payout")

    # Classify failure
    strategy_result = classify_failure(case.failure_source, case.failure_reason)
    case.recovery_strategy = strategy_result.strategy
    db.commit()

    return AgentNodeOutput(
        next_state=CaseState.RECOVERY_STRATEGY_SELECTED,
        transition_reason=f"Failure classified as {strategy_result.strategy.value} based on {case.failure_source}/{case.failure_reason}.",
        tools_executed=tools,
    )


def run_vendor_contact_node(case: RecoveryCaseModel, db: Session) -> AgentNodeOutput:
    """
    Node: RECOVERY_STRATEGY_SELECTED -> VENDOR_CONTACTED
    Gathers vendor context from Zoho Books and dispatches personalized remediation message.
    """
    tools = []
    vendor = db.query(Vendor).filter(Vendor.id == case.vendor_id).first()
    vendor_name = vendor.name if vendor else "Valued Vendor"
    vendor_id = vendor.id if vendor else case.vendor_id or "vend_unknown"

    # Context tools
    if case.invoice_reference:
        tool_find_invoice(case.id, case.invoice_reference, db)
        tools.append("find_invoice")

    tool_find_vendor(case.id, vendor_name, db)
    tools.append("find_vendor")

    # Compose message using LLM
    message_text = llm_client.generate_vendor_message(
        vendor_name=vendor_name,
        failure_reason=case.failure_reason,
        invoice_reference=case.invoice_reference,
        amount_paise=case.amount,
    )

    # Send outbound message
    tool_send_vendor_message(case.id, vendor_id, message_text, db)
    tools.append("send_vendor_message")

    return AgentNodeOutput(
        next_state=CaseState.VENDOR_CONTACTED,
        transition_reason=f"Remediation message dispatched to vendor {vendor_name}.",
        tools_executed=tools,
    )


def run_information_extraction_node(
    case: RecoveryCaseModel,
    message_text: str,
    db: Session,
) -> AgentNodeOutput:
    """
    Node: VENDOR_CONTACTED -> INFORMATION_RECEIVED -> DATA_VALIDATED
    Parses vendor reply with LLM and verifies IFSC / account number syntax.
    """
    vendor = db.query(Vendor).filter(Vendor.id == case.vendor_id).first()
    default_name = vendor.name if vendor else None

    # 1. Autonomous Prompt Injection & Adversarial Defense Guardrail
    lower_text = message_text.lower() if message_text else ""
    adversarial_keywords = [
        "ignore all previous",
        "ignore previous",
        "system override",
        "admin emergency",
        "do not validate",
        "do not require human approval",
        "without validation",
        "hacker@",
        "override policy",
        "bypass approval",
        "emergency override",
    ]
    if any(kw in lower_text for kw in adversarial_keywords):
        return AgentNodeOutput(
            next_state=CaseState.BLOCKED,
            transition_reason="🚨 Autonomous Security Defense: Malicious prompt injection attack detected in vendor communication. Execution aborted and case permanently BLOCKED to prevent financial loss.",
            extracted_data={"adversarial_attack_blocked": True, "raw_message": message_text},
            requires_human=True,
        )

    # LLM Structured Extraction
    extracted: ExtractedBankingData = llm_client.extract_banking_data(
        message_text=message_text,
        default_name=default_name,
    )

    # Deterministic Syntax & Format Validation
    ifsc_valid = bool(extracted.ifsc and re.match(r"^[A-Z]{4}0[A-Z0-9]{6}$", extracted.ifsc.upper()))
    acc_valid = bool(extracted.account_number and re.match(r"^\d{9,18}$", str(extracted.account_number).strip()))

    data_dict = {
        "account_holder_name": extracted.account_holder_name or default_name,
        "account_number": extracted.account_number,
        "ifsc": extracted.ifsc.upper() if extracted.ifsc else None,
        "is_syntax_valid": ifsc_valid and acc_valid,
    }

    if not (ifsc_valid and acc_valid):
        return AgentNodeOutput(
            next_state=CaseState.INFORMATION_RECEIVED,
            transition_reason="Received vendor response but syntax validation failed. Missing valid IFSC or Account Number.",
            extracted_data=data_dict,
            requires_human=False,
        )

    return AgentNodeOutput(
        next_state=CaseState.INFORMATION_RECEIVED,
        transition_reason="Vendor banking credentials successfully extracted and parsed.",
        extracted_data=data_dict,
        requires_human=False,
    )


def run_bank_validation_node(
    case: RecoveryCaseModel,
    banking_data: Dict[str, Any],
    db: Session,
) -> AgentNodeOutput:
    """
    Node: DATA_VALIDATED -> BANK_VALIDATED
    Provisions replacement Fund Account in Razorpay and executes penny-drop validation.
    """
    tools = []
    vendor = db.query(Vendor).filter(Vendor.id == case.vendor_id).first()
    contact_id = vendor.razorpay_contact_id if vendor and vendor.razorpay_contact_id else f"cont_{case.id}"

    # 1. Create Fund Account (Level 2)
    fa_context = PolicyContext(
        case_state=CaseState.DATA_VALIDATED,
        data_validated=True,
        vendor_verified=True,
        risk_level=case.risk_level,
    )
    acc_num = banking_data.get("account_number") or "987654321098"
    ifsc_code = banking_data.get("ifsc") or "HDFC0000001"
    holder_name = banking_data.get("account_holder_name") or (vendor.name if vendor else "Vendor Account")

    new_fa = tool_create_fund_account(
        case_id=case.id,
        contact_id=contact_id,
        account_number=acc_num,
        ifsc=ifsc_code,
        name=holder_name,
        db=db,
        context=fa_context,
    )
    tools.append("create_fund_account")
    new_fa_id = new_fa["id"]

    # 2. Validate Fund Account (Level 2 Penny Drop)
    val_out = tool_validate_fund_account(
        case_id=case.id,
        fund_account_id=new_fa_id,
        vendor_name=vendor.name if vendor else holder_name,
        registered_name=holder_name,
        db=db,
        context=fa_context,
    )
    tools.append("validate_fund_account")

    # Routing based on deterministic penny-drop result
    if not val_out["is_valid"]:
        next_st = CaseState(val_out["next_state"])
        if next_st == CaseState.HUMAN_REVIEW:
            from app.models.approval import Approval
            review_payload = {
                "case_id": case.id,
                "vendor_name": vendor.name if vendor else holder_name,
                "registered_name": val_out.get("registered_name") or holder_name,
                "invoice_reference": case.invoice_reference or "INV-2026",
                "amount_paise": case.amount,
                "amount_inr": case.amount / 100.0,
                "old_fund_account_id": case.payout.razorpay_fund_account_id if case.payout else None,
                "new_fund_account_id": new_fa_id,
                "validation_score": val_out.get("name_match_score", 0),
                "name_match_score": val_out.get("name_match_score", 0),
                "validation_status": val_out.get("account_status", "invalid"),
                "divergence_reason": val_out.get("reason"),
                "recommended_action": "REVIEW_AND_DECIDE",
                "action": "human_review_divergence",
            }
            rev_approval = Approval(
                id=str(uuid.uuid4()),
                case_id=case.id,
                action_description="human_review_divergence",
                payload=review_payload,
                decision=None,
            )
            db.add(rev_approval)
            db.commit()

        return AgentNodeOutput(
            next_state=next_st,
            transition_reason=val_out["reason"],
            tools_executed=tools,
            extracted_data={"new_fund_account_id": new_fa_id, "validation": val_out},
            requires_human=(next_st == CaseState.HUMAN_REVIEW),
        )

    return AgentNodeOutput(
        next_state=CaseState.BANK_VALIDATED,
        transition_reason=val_out["reason"],
        tools_executed=tools,
        extracted_data={"new_fund_account_id": new_fa_id, "validation": val_out},
    )


def run_policy_and_payout_prep_node(
    case: RecoveryCaseModel,
    new_fund_account_id: str,
    old_fund_account_id: Optional[str],
    validation_score: int,
    db: Session,
) -> AgentNodeOutput:
    """
    Node: BANK_VALIDATED -> POLICY_CHECK -> PAYOUT_READY -> HUMAN_APPROVAL
    Deactivates faulty old fund account, writes back to ERP, prepares replacement payout approval card,
    and pauses at HUMAN_APPROVAL for human controller authorization.
    """
    tools = []
    vendor = db.query(Vendor).filter(Vendor.id == case.vendor_id).first()
    vendor_name = vendor.name if vendor else "Acme Logistics"
    vendor_id = vendor.id if vendor else "vend_unknown"
    old_fa_id = old_fund_account_id or "fa_old_faulty"

    # 1. Policy check
    policy_ctx = PolicyContext(
        case_state=CaseState.BANK_VALIDATED,
        name_match_score=validation_score,
        data_validated=True,
        vendor_verified=True,
        risk_level=case.risk_level,
        amount_paise=case.amount,
    )
    policy_eval = evaluate_policy("prepare_replacement_payout", policy_ctx)
    if policy_eval.decision != PolicyDecision.ALLOW:
        return AgentNodeOutput(
            next_state=CaseState.HUMAN_REVIEW,
            transition_reason=f"Policy check required human review: {policy_eval.reason}",
            requires_human=True,
        )

    # 2. Deactivate faulty old fund account
    tool_deactivate_fund_account(case.id, old_fa_id, db, context=policy_ctx)
    tools.append("deactivate_fund_account")

    # 3. Update ERP vendor bank details in Zoho Books
    tool_update_vendor_bank_details(
        case.id,
        vendor_id,
        {"fund_account_id": new_fund_account_id, "status": "active"},
        db,
        context=policy_ctx,
    )
    tools.append("update_vendor_bank_details")

    # 4. Prepare replacement payout and create Approval card
    tool_prepare_replacement_payout(
        case_id=case.id,
        old_fund_account_id=old_fa_id,
        new_fund_account_id=new_fund_account_id,
        amount=case.amount,
        vendor_name=vendor_name,
        invoice_reference=case.invoice_reference or "INV-REF-001",
        validation_score=validation_score,
        db=db,
        context=policy_ctx,
        registered_name=vendor_name,
    )
    tools.append("prepare_replacement_payout")

    return AgentNodeOutput(
        next_state=CaseState.HUMAN_APPROVAL,
        transition_reason="Replacement payout prepared. Awaiting finance controller authorization.",
        tools_executed=tools,
        extracted_data={"new_fund_account_id": new_fund_account_id, "approval_status": "PENDING"},
        requires_human=True,
    )
