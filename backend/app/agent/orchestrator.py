"""
agent/orchestrator.py
─────────────────────
Outer Custom State Machine & Agent Orchestrator (Phase 10).

This module coordinates the end-to-end exception resolution lifecycle:
- Manages legal state machine transitions using `app.state_machine.transition_state`.
- Hands control to inner reasoning nodes in `app.agent.graph`.
- Enforces strict execution boundaries: safely pauses at `HUMAN_APPROVAL`, `HUMAN_REVIEW`,
  `BLOCKED`, or while awaiting vendor responses in `VENDOR_CONTACTED`.
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.enums import CaseState, AuditActorType
from app.models.recovery_case import RecoveryCaseModel
from app.models.payout import Payout
from app.state_machine import transition_state, is_terminal_state
from app.audit import log_audit_event
from app.agent.graph import (
    run_case_classification_node,
    run_vendor_contact_node,
    run_information_extraction_node,
    run_bank_validation_node,
    run_policy_and_payout_prep_node,
)


class AgentOrchestrator:
    """
    Orchestrates the resolution workflow by combining the deterministic outer state machine
    with the inner reasoning tool-calling nodes.
    """

    def process_case(
        self,
        case_id: str,
        db: Session,
        vendor_reply_text: Optional[str] = None,
    ) -> RecoveryCaseModel:
        """
        Executes autonomous reasoning steps for a recovery case until a pause or human-in-the-loop state.
        """
        case = db.query(RecoveryCaseModel).filter(RecoveryCaseModel.id == case_id).first()
        if not case:
            raise ValueError(f"RecoveryCase {case_id} not found.")

        # Local cache of state variables during execution
        extracted_banking_data: Dict[str, Any] = {}
        new_fund_account_id: Optional[str] = None
        validation_score: int = 100

        # Payout context for old fund account ID
        payout = db.query(Payout).filter(Payout.id == case.payout_id).first()
        old_fa_id = payout.razorpay_fund_account_id if payout else "fa_old_faulty"

        # Continuous execution loop through autonomous nodes
        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # ── Check Terminal States ────────────────────────────────────────
            if is_terminal_state(case.state):
                break

            current_state = case.state

            # ── Node 1: CASE_CREATED ─────────────────────────────────────────
            if current_state == CaseState.CASE_CREATED:
                node_out = run_case_classification_node(case, db)
                self._apply_transition(case, CaseState.FAILURE_CLASSIFIED, "Root-cause failure classified deterministically.", db)
                self._apply_transition(case, node_out.next_state, node_out.transition_reason, db)
                continue

            # ── Node 2: FAILURE_CLASSIFIED / RECOVERY_STRATEGY_SELECTED ──────
            elif current_state == CaseState.FAILURE_CLASSIFIED:
                self._apply_transition(case, CaseState.RECOVERY_STRATEGY_SELECTED, "Recovery strategy determined.", db)
                continue

            elif current_state == CaseState.RECOVERY_STRATEGY_SELECTED:
                node_out = run_vendor_contact_node(case, db)
                self._apply_transition(case, node_out.next_state, node_out.transition_reason, db)
                continue

            # ── Node 3: VENDOR_CONTACTED ─────────────────────────────────────
            elif current_state == CaseState.VENDOR_CONTACTED:
                # If a vendor response has arrived, process extraction; otherwise pause and await reply
                if not vendor_reply_text:
                    break  # Pauses in VENDOR_CONTACTED awaiting vendor reply

                node_out = run_information_extraction_node(case, vendor_reply_text, db)
                if node_out.extracted_data:
                    extracted_banking_data = node_out.extracted_data

                self._apply_transition(case, node_out.next_state, node_out.transition_reason, db)
                # Clear vendor reply so subsequent turns do not re-process
                vendor_reply_text = None
                continue

            # ── Node 4: INFORMATION_RECEIVED ─────────────────────────────────
            elif current_state == CaseState.INFORMATION_RECEIVED:
                # If syntax was valid, progress to DATA_VALIDATED, else halt for clarification
                if extracted_banking_data.get("is_syntax_valid"):
                    self._apply_transition(case, CaseState.DATA_VALIDATED, "Banking data syntax verified.", db)
                    continue
                else:
                    break

            # ── Node 5: DATA_VALIDATED ───────────────────────────────────────
            elif current_state == CaseState.DATA_VALIDATED:
                if not extracted_banking_data and vendor_reply_text:
                    from app.agent.llm import llm_client
                    extracted = llm_client.extract_banking_data(vendor_reply_text)
                    extracted_banking_data = {
                        "account_holder_name": extracted.account_holder_name,
                        "account_number": extracted.account_number,
                        "ifsc": extracted.ifsc,
                        "is_syntax_valid": extracted.is_valid,
                    }
                node_out = run_bank_validation_node(case, extracted_banking_data, db)
                if node_out.extracted_data:
                    new_fund_account_id = node_out.extracted_data.get("new_fund_account_id")
                    validation_info = node_out.extracted_data.get("validation", {})
                    validation_score = validation_info.get("name_match_score", 100)

                self._apply_transition(case, node_out.next_state, node_out.transition_reason, db)
                if node_out.requires_human:
                    break
                continue

            # ── Node 6: BANK_VALIDATED ───────────────────────────────────────
            elif current_state == CaseState.BANK_VALIDATED:
                self._apply_transition(case, CaseState.POLICY_CHECK, "Penny-drop validation passed. Entering pre-payout policy checks.", db)
                continue

            # ── Node 7: POLICY_CHECK / PAYOUT_READY ──────────────────────────
            elif current_state in {CaseState.POLICY_CHECK, CaseState.PAYOUT_READY}:
                node_out = run_policy_and_payout_prep_node(
                    case=case,
                    new_fund_account_id=new_fund_account_id or "fa_new_validated",
                    old_fund_account_id=old_fa_id,
                    validation_score=validation_score,
                    db=db,
                )
                self._apply_transition(case, node_out.next_state, node_out.transition_reason, db)
                break  # Halts in HUMAN_APPROVAL awaiting finance controller authorization

            # ── Node 8: Human-in-the-Loop & Terminal States ───────────────────
            elif current_state in {CaseState.HUMAN_APPROVAL, CaseState.HUMAN_REVIEW, CaseState.BLOCKED, CaseState.ESCALATED}:
                break

            else:
                break

        return case

    def _apply_transition(
        self,
        case: RecoveryCaseModel,
        next_state: CaseState,
        reason: str,
        db: Session,
    ) -> None:
        """
        Validates transition with the state machine, updates the database, increments action count,
        and logs the transition in the cryptographic audit ledger.
        """
        old_state = case.state
        # Validate transition using custom state machine
        validated_state = transition_state(old_state, next_state)

        # Update database entity
        case.state = validated_state
        case.action_count = (case.action_count or 0) + 1
        db.commit()
        db.refresh(case)

        # Log cryptographic audit event
        old_val = old_state.value if hasattr(old_state, "value") else str(old_state)
        new_val = validated_state.value if hasattr(validated_state, "value") else str(validated_state)
        log_audit_event(
            db=db,
            case_id=case.id,
            event_type=AuditActorType.SYSTEM_ACTION,
            actor="payout_recovery_agent",
            action="STATE_TRANSITION",
            target=case.id,
            input_data={"from_state": old_val},
            output_data={"to_state": new_val, "reason": reason},
        )


# Singleton instance
orchestrator = AgentOrchestrator()


def run_agent_for_case(
    case_id: str,
    db: Session,
    vendor_reply_text: Optional[str] = None,
) -> RecoveryCaseModel:
    """Helper entry point for running the agent reasoning loop on a recovery case."""
    return orchestrator.process_case(case_id=case_id, db=db, vendor_reply_text=vendor_reply_text)
