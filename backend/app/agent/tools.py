"""
agent/tools.py
──────────────
Agent Tool Definitions & Execution Wrappers (Phase 10).

Exposes typed tool functions that the reasoning agent invokes during each workflow stage.
Every tool execution:
1. Evaluates permissions against the Policy Engine.
2. Appends an AgentAction record to PostgreSQL for operational tracking.
3. Produces an immutable AuditEvent in the cryptographic ledger.
4. Returns strongly-typed output schemas.
"""

import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.enums import PolicyLevel, PolicyDecision, CaseState, RiskLevel, ApprovalDecision
from app.models.agent_action import AgentAction
from app.models.approval import Approval
from app.models.fund_account import FundAccount
from app.policy_engine import evaluate_policy, PolicyContext, get_action_policy_level
from app.services.razorpay_client import razorpay_client
from app.services.zoho_client import zoho_client
from app.services.validation_service import validation_service, evaluate_validation_result
from app.services.communication_adapter import communication_adapter


def _record_agent_action(
    db: Session,
    case_id: str,
    tool_name: str,
    input_payload: Dict[str, Any],
    output_payload: Optional[Dict[str, Any]],
    policy_level: PolicyLevel,
    policy_decision: PolicyDecision,
) -> AgentAction:
    """Records an operational agent action execution in PostgreSQL."""
    action = AgentAction(
        id=str(uuid.uuid4()),
        case_id=case_id,
        tool_name=tool_name,
        actor="payout_recovery_agent",
        input_payload=input_payload,
        output_payload=output_payload,
        policy_level=policy_level.value,
        policy_decision=policy_decision.value,
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


# ─────────────────────────────────────────────────────────────────────────────
# 1. Razorpay Read & Write Tools
# ─────────────────────────────────────────────────────────────────────────────

def tool_get_payout(case_id: str, payout_id: str, db: Session) -> Dict[str, Any]:
    """Retrieves payout details from Razorpay."""
    policy = evaluate_policy("get_payout")
    res = razorpay_client.get_payout(payout_id=payout_id, case_id=case_id, db=db)
    out = res.model_dump()
    _record_agent_action(db, case_id, "get_payout", {"payout_id": payout_id}, out, PolicyLevel.AUTONOMOUS, policy.decision)
    return out


def tool_get_contact(case_id: str, contact_id: str, db: Session) -> Dict[str, Any]:
    """Retrieves contact profile from Razorpay."""
    policy = evaluate_policy("get_contact")
    res = razorpay_client.get_contact(contact_id=contact_id, case_id=case_id, db=db)
    out = res.model_dump()
    _record_agent_action(db, case_id, "get_contact", {"contact_id": contact_id}, out, PolicyLevel.AUTONOMOUS, policy.decision)
    return out


def tool_get_fund_accounts(case_id: str, contact_id: str, db: Session) -> List[Dict[str, Any]]:
    """Lists fund accounts for a contact in Razorpay."""
    policy = evaluate_policy("get_fund_accounts")
    res = razorpay_client.get_fund_accounts(contact_id=contact_id, case_id=case_id, db=db)
    out = [item.model_dump() for item in res]
    _record_agent_action(db, case_id, "get_fund_accounts", {"contact_id": contact_id}, {"accounts": out}, PolicyLevel.AUTONOMOUS, policy.decision)
    return out


def tool_create_fund_account(
    case_id: str,
    contact_id: str,
    account_number: str,
    ifsc: str,
    name: str,
    db: Session,
    context: Optional[PolicyContext] = None,
) -> Dict[str, Any]:
    """
    Creates a new immutable Fund Account in Razorpay (Level 2 Controlled Mutation).
    """
    bank_account_payload = {
        "name": name,
        "ifsc": ifsc.upper(),
        "account_number": account_number,
    }
    res = razorpay_client.create_fund_account(
        contact_id=contact_id,
        account_type="bank_account",
        bank_account=bank_account_payload,
        case_id=case_id,
        db=db,
        context=context,
    )
    out = res.model_dump()

    # Also persist to fund_accounts database table
    from app.models.recovery_case import RecoveryCaseModel
    from app.models.vendor import Vendor
    
    case_obj = db.query(RecoveryCaseModel).filter(RecoveryCaseModel.id == case_id).first()
    vendor_obj = db.query(Vendor).filter(Vendor.razorpay_contact_id == contact_id).first()
    v_id = vendor_obj.id if vendor_obj else (case_obj.vendor_id if case_obj else "vend_unknown")

    masked = f"XXXXXX{account_number[-4:]}" if len(account_number) >= 4 else account_number
    db_fa = FundAccount(
        id=str(uuid.uuid4()),
        razorpay_fund_account_id=res.id,
        razorpay_contact_id=contact_id,
        vendor_id=v_id,
        recovery_case_id=case_id,
        bank_name=res.bank_account.bank_name if res.bank_account else "Unknown Bank",
        account_number_masked=masked,
        ifsc=ifsc.upper(),
        account_holder_name=name,
        is_active=True,
    )
    db.add(db_fa)
    db.commit()

    _record_agent_action(
        db, case_id, "create_fund_account",
        {"contact_id": contact_id, "bank_account": bank_account_payload},
        out, PolicyLevel.CONTROLLED_MUTATION, PolicyDecision.ALLOW,
    )
    return out


def tool_deactivate_fund_account(
    case_id: str,
    fund_account_id: str,
    db: Session,
    context: Optional[PolicyContext] = None,
) -> Dict[str, Any]:
    """Deactivates a faulty fund account in Razorpay (Level 2 Controlled Mutation)."""
    res = razorpay_client.deactivate_fund_account(
        fund_account_id=fund_account_id,
        case_id=case_id,
        db=db,
        context=context,
    )
    out = res.model_dump()

    # Update DB fund_account record if exists
    fa = db.query(FundAccount).filter(FundAccount.razorpay_fund_account_id == fund_account_id).first()
    if fa:
        fa.is_active = False
        db.commit()

    _record_agent_action(
        db, case_id, "deactivate_fund_account",
        {"fund_account_id": fund_account_id},
        out, PolicyLevel.CONTROLLED_MUTATION, PolicyDecision.ALLOW,
    )
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 2. Zoho Books ERP Tools
# ─────────────────────────────────────────────────────────────────────────────

def tool_find_vendor(case_id: str, reference_id: str, db: Session) -> Optional[Dict[str, Any]]:
    """Looks up vendor profile and banking details in Zoho Books."""
    policy = evaluate_policy("find_vendor")
    res = zoho_client.find_vendor(reference_id=reference_id, case_id=case_id, db=db)
    out = res.model_dump() if res else None
    _record_agent_action(db, case_id, "find_vendor", {"reference_id": reference_id}, out, PolicyLevel.AUTONOMOUS, policy.decision)
    return out


def tool_find_invoice(case_id: str, invoice_id: str, db: Session) -> Optional[Dict[str, Any]]:
    """Looks up invoice/bill in Zoho Books."""
    policy = evaluate_policy("find_invoice")
    res = zoho_client.find_invoice(invoice_id=invoice_id, case_id=case_id, db=db)
    out = res.model_dump() if res else None
    _record_agent_action(db, case_id, "find_invoice", {"invoice_id": invoice_id}, out, PolicyLevel.AUTONOMOUS, policy.decision)
    return out


def tool_update_vendor_bank_details(
    case_id: str,
    vendor_id: str,
    bank_details: Dict[str, Any],
    db: Session,
    context: Optional[PolicyContext] = None,
) -> Dict[str, Any]:
    """Updates vendor bank details in Zoho Books (Level 2 Controlled Mutation)."""
    res = zoho_client.update_vendor_bank_details(
        vendor_id=vendor_id,
        bank_details=bank_details,
        case_id=case_id,
        db=db,
        context=context,
    )
    out = res.model_dump()
    _record_agent_action(
        db, case_id, "update_vendor_bank_details",
        {"vendor_id": vendor_id, "bank_details": bank_details},
        out, PolicyLevel.CONTROLLED_MUTATION, PolicyDecision.ALLOW,
    )
    return out


def tool_update_invoice_status(
    case_id: str,
    invoice_id: str,
    status: str,
    db: Session,
    context: Optional[PolicyContext] = None,
) -> Dict[str, Any]:
    """Updates invoice status in Zoho Books (Level 2 Controlled Mutation)."""
    res = zoho_client.update_invoice_status(
        invoice_id=invoice_id,
        status=status,
        case_id=case_id,
        db=db,
        context=context,
    )
    out = res.model_dump()
    _record_agent_action(
        db, case_id, "update_invoice_status",
        {"invoice_id": invoice_id, "status": status},
        out, PolicyLevel.CONTROLLED_MUTATION, PolicyDecision.ALLOW,
    )
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 3. Vendor Messaging & Validation Tools
# ─────────────────────────────────────────────────────────────────────────────

def tool_send_vendor_message(
    case_id: str,
    vendor_id: str,
    message_body: str,
    db: Session,
) -> Dict[str, Any]:
    """Dispatches outbound message to vendor."""
    msg = communication_adapter.send_message(
        case_id=case_id,
        vendor_id=vendor_id,
        message_body=message_body,
        db=db,
    )
    out = {"message_id": msg.id, "direction": msg.direction, "body": msg.body}
    _record_agent_action(
        db, case_id, "send_vendor_message",
        {"vendor_id": vendor_id, "message_body": message_body},
        out, PolicyLevel.AUTONOMOUS, PolicyDecision.ALLOW,
    )
    return out


def tool_validate_fund_account(
    case_id: str,
    fund_account_id: str,
    vendor_name: str,
    registered_name: Optional[str],
    db: Session,
    context: Optional[PolicyContext] = None,
) -> Dict[str, Any]:
    """
    Performs penny-drop validation on the replacement fund account (Level 2 Controlled Mutation).
    """
    res = validation_service.validate_fund_account(
        fund_account_id=fund_account_id,
        vendor_name=vendor_name,
        registered_name=registered_name,
        case_id=case_id,
        db=db,
        context=context,
    )
    evaluation = evaluate_validation_result(res)
    out = {
        "fund_account_id": res.fund_account_id,
        "account_status": res.account_status,
        "name_match_score": res.name_match_score,
        "is_valid": evaluation.is_valid,
        "next_state": evaluation.next_state.value if hasattr(evaluation.next_state, "value") else str(evaluation.next_state),
        "reason": evaluation.reason,
    }
    _record_agent_action(
        db, case_id, "validate_fund_account",
        {"fund_account_id": fund_account_id, "vendor_name": vendor_name},
        out, PolicyLevel.CONTROLLED_MUTATION, PolicyDecision.ALLOW,
    )
    return out


def tool_prepare_replacement_payout(
    case_id: str,
    old_fund_account_id: str,
    new_fund_account_id: str,
    amount: int,
    vendor_name: str,
    invoice_reference: str,
    validation_score: int,
    db: Session,
    context: Optional[PolicyContext] = None,
) -> Dict[str, Any]:
    """
    Prepares the replacement payout card and creates the Approval record for human controller (Level 2).
    """
    approval_payload = {
        "case_id": case_id,
        "vendor_name": vendor_name,
        "invoice_reference": invoice_reference,
        "amount_paise": amount,
        "amount_inr": amount / 100.0,
        "old_fund_account_id": old_fund_account_id,
        "new_fund_account_id": new_fund_account_id,
        "validation_score": validation_score,
        "recommended_action": "CREATE_PAYOUT",
        "action": "execute_replacement_payout",
    }

    approval = Approval(
        id=str(uuid.uuid4()),
        case_id=case_id,
        action_description="execute_replacement_payout",
        payload=approval_payload,
        decision=None,
    )
    db.add(approval)
    db.commit()

    _record_agent_action(
        db, case_id, "prepare_replacement_payout",
        approval_payload,
        {"approval_id": approval.id, "status": "PENDING"},
        PolicyLevel.CONTROLLED_MUTATION, PolicyDecision.ALLOW,
    )

    return {"approval_id": approval.id, "status": "PENDING", "payload": approval_payload}
