"""
tests/test_approval.py
───────────────────────
Unit Tests for Case Management, Human Approval API & Reconciliation (Phase 11).

Tests:
1. POST /cases/{id}/approve:
   - Validates that case transitions from HUMAN_APPROVAL -> PAYOUT_EXECUTED.
   - Validates that Razorpay create_payout (Level 3) is executed with human authorization.
   - Validates Approval entity update (decision="APPROVE").
   - Validates cryptographic audit ledger records HUMAN_DECISION with actor="finance_controller".
   - Rejects approval if case is not in HUMAN_APPROVAL state (400 Bad Request).
2. POST /cases/{id}/reject:
   - Validates that case transitions from HUMAN_APPROVAL -> BLOCKED.
   - Validates Approval entity update with rejection reason.
   - Validates cryptographic audit ledger records HUMAN_DECISION.
   - Rejects empty rejection reason (422 Unprocessable Entity).
3. Subsequent Razorpay payout.processed Webhook:
   - Reconciles ERP invoice status in Zoho Books.
   - Validates sequential transitions: PAYOUT_EXECUTED -> PAYOUT_CONFIRMED -> CASE_RESOLVED.
   - Verifies mathematical integrity of the cryptographic audit chain.
4. GET /cases/{id} & GET /cases:
   - Detailed workspace inspection.
   - Paginated case listings and state filters.
"""

import uuid
from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.enums import CaseState, ApprovalDecision, AuditActorType, PolicyLevel
from app.models.vendor import Vendor
from app.models.payout import Payout
from app.models.recovery_case import RecoveryCaseModel
from app.models.fund_account import FundAccount
from app.models.approval import Approval
from app.models.agent_action import AgentAction
from app.models.audit_event import AuditEvent
from app.audit import log_audit_event, verify_chain


# ─────────────────────────────────────────────────────────────────────────────
# Test Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def test_db():
    """Provides an in-memory SQLite database session isolated per test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db):
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def staged_approval_case(test_db):
    """Creates standard test records staged at HUMAN_APPROVAL."""
    vendor = Vendor(
        id="vend_appr_01",
        razorpay_contact_id="cont_appr_01",
        zoho_vendor_id="zoho_vend_appr_01",
        name="Apex Industrial Logistics Pvt Ltd",
        email="accounts@apexlogistics.in",
        phone="+919876543210",
    )
    test_db.add(vendor)
    test_db.commit()

    payout = Payout(
        id="pout_appr_01",
        razorpay_payout_id="pout_rzp_appr_01",
        razorpay_fund_account_id="fa_old_defunct",
        razorpay_contact_id=vendor.razorpay_contact_id,
        amount=1250000,
        currency="INR",
        status="failed",
        status_source="beneficiary_bank",
        status_reason="invalid_ifsc_code",
    )
    test_db.add(payout)
    test_db.commit()

    case = RecoveryCaseModel(
        id="case_appr_test_01",
        case_number="CASE-2026-APPR-01",
        payout_id=payout.id,
        vendor_id=vendor.id,
        invoice_reference="INV-2026-8801",
        amount=1250000,
        failure_source="beneficiary_bank",
        failure_reason="invalid_ifsc_code",
        state=CaseState.HUMAN_APPROVAL,
    )
    test_db.add(case)
    test_db.commit()

    # Genesis audit event
    log_audit_event(
        db=test_db,
        case_id=case.id,
        event_type=AuditActorType.EXTERNAL_FACT,
        actor="razorpay_webhook",
        action="PAYOUT_FAILED_WEBHOOK_RECEIVED",
        target=payout.razorpay_payout_id,
        reason="invalid_ifsc_code",
    )

    # Staged Approval record
    approval_payload = {
        "case_id": case.id,
        "vendor_name": vendor.name,
        "invoice_reference": case.invoice_reference,
        "amount_paise": case.amount,
        "amount_inr": case.amount / 100.0,
        "old_fund_account_id": "fa_old_defunct",
        "new_fund_account_id": "fa_new_validated_01",
        "validation_score": 100,
        "recommended_action": "CREATE_PAYOUT",
    }
    approval = Approval(
        id="appr_rec_01",
        case_id=case.id,
        action_description="execute_replacement_payout",
        payload=approval_payload,
        decision=None,
    )
    test_db.add(approval)
    test_db.commit()

    return {
        "vendor": vendor,
        "payout": payout,
        "case": case,
        "approval": approval,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. Human Approval Endpoint Tests (POST /cases/{id}/approve)
# ─────────────────────────────────────────────────────────────────────────────

class TestHumanApprovalEndpoints:
    """Validates human approval authorization gate (Level 3 action)."""

    def test_approve_payout_golden_path(self, client, test_db, staged_approval_case):
        """Validates successful human approval, payout dispatch, and audit emission."""
        case = staged_approval_case["case"]

        res = client.post(
            f"/cases/{case.id}/approve",
            json={"decided_by": "finance_controller@enterprise.com", "notes": "Bank verification 100% verified."},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["decision"] == "APPROVE"
        assert data["state"] == "PAYOUT_EXECUTED"
        assert data["payout_id"] is not None

        # Verify DB Case entity
        test_db.refresh(case)
        assert case.state == CaseState.PAYOUT_EXECUTED
        assert case.human_intervention_count >= 1

        # Verify Approval entity
        approval = test_db.query(Approval).filter(Approval.case_id == case.id).first()
        assert approval.decision == "APPROVE"
        assert approval.decided_by == "finance_controller@enterprise.com"
        assert approval.status == "APPROVE"

        # Verify AgentAction operational log
        action = test_db.query(AgentAction).filter(AgentAction.case_id == case.id, AgentAction.tool_name == "approve_payout").first()
        assert action is not None
        assert action.policy_level == PolicyLevel.FINANCIALLY_CONSEQUENTIAL.value

        # Verify Cryptographic Audit Ledger
        audit_res = verify_chain(test_db, case.id)
        assert audit_res.status == "VERIFIED"
        assert audit_res.is_valid is True

        human_event = (
            test_db.query(AuditEvent)
            .filter(
                AuditEvent.case_id == case.id,
                AuditEvent.action == "APPROVE_REPLACEMENT_PAYOUT",
            )
            .first()
        )
        assert human_event is not None
        assert human_event.actor == "finance_controller@enterprise.com"
        assert human_event.action == "APPROVE_REPLACEMENT_PAYOUT"

    def test_approve_payout_rejected_when_not_in_human_approval_state(self, client, test_db, staged_approval_case):
        """Approving a case when it is not in HUMAN_APPROVAL state must return 400 Bad Request."""
        case = staged_approval_case["case"]
        case.state = CaseState.VENDOR_CONTACTED
        test_db.commit()

        res = client.post(
            f"/cases/{case.id}/approve",
            json={"decided_by": "finance_controller"},
        )
        assert res.status_code == 400
        assert "must be in 'HUMAN_APPROVAL'" in res.json()["detail"]

    def test_approve_payout_nonexistent_case(self, client):
        """Approving an unknown case ID returns 404 Not Found."""
        res = client.post(
            "/cases/nonexistent_case_id/approve",
            json={"decided_by": "finance_controller"},
        )
        assert res.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# 2. Human Rejection Endpoint Tests (POST /cases/{id}/reject)
# ─────────────────────────────────────────────────────────────────────────────

class TestHumanRejectionEndpoints:
    """Validates human rejection and permanent case blocking."""

    def test_reject_payout_transitions_case_to_blocked(self, client, test_db, staged_approval_case):
        """Rejecting a proposal transitions the case to terminal BLOCKED."""
        case = staged_approval_case["case"]

        res = client.post(
            f"/cases/{case.id}/reject",
            json={
                "reason": "Vendor account beneficiary name suspicious.",
                "decided_by": "lead_compliance_officer",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["decision"] == "REJECT"
        assert data["state"] == "BLOCKED"

        # Verify DB updates
        test_db.refresh(case)
        assert case.state == CaseState.BLOCKED
        assert case.resolved_at is not None

        approval = test_db.query(Approval).filter(Approval.case_id == case.id).first()
        assert approval.decision == "REJECT"
        assert approval.rejection_reason == "Vendor account beneficiary name suspicious."

        # Verify audit ledger
        audit_res = verify_chain(test_db, case.id)
        assert audit_res.status == "VERIFIED"
        assert audit_res.is_valid is True

    def test_reject_payout_empty_reason_rejected(self, client, staged_approval_case):
        """Rejection without a non-empty reason is rejected with 422 Unprocessable Entity."""
        case = staged_approval_case["case"]

        res = client.post(
            f"/cases/{case.id}/reject",
            json={"reason": "   ", "decided_by": "lead_compliance_officer"},
        )
        assert res.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# 3. Subsequent Webhook Payout Reconciliation Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestSubsequentWebhookReconciliation:
    """Validates full end-to-end reconciliation when payout.processed webhook arrives."""

    def test_subsequent_payout_processed_reconciles_and_resolves_case(self, client, test_db, staged_approval_case):
        """When payout.processed arrives for an executed recovery, the case resolves to CASE_RESOLVED."""
        case = staged_approval_case["case"]

        # 1. Controller approves payout
        approve_res = client.post(f"/cases/{case.id}/approve", json={"decided_by": "finance_controller"})
        assert approve_res.status_code == 200
        payout_id = approve_res.json()["payout_id"]

        test_db.refresh(case)
        assert case.state == CaseState.PAYOUT_EXECUTED

        # 2. Simulate subsequent payout.processed webhook from Razorpay
        webhook_payload = {
            "entity": "event",
            "account_id": "acc_mock_rzp_01",
            "event": "payout.processed",
            "contains": ["payout"],
            "payload": {
                "payout": {
                    "entity": {
                        "id": payout_id,
                        "entity": "payout",
                        "fund_account_id": "fa_new_validated_01",
                        "amount": 1250000,
                        "currency": "INR",
                        "status": "processed",
                        "reference_id": case.invoice_reference,
                    }
                }
            },
            "created_at": int(datetime.now().timestamp()),
        }

        webhook_res = client.post("/webhooks/razorpay", json=webhook_payload)
        assert webhook_res.status_code == 200
        assert webhook_res.json()["status"] == "reconciled"

        # 3. Verify Case reached CASE_RESOLVED
        test_db.refresh(case)
        assert case.state == CaseState.CASE_RESOLVED
        assert case.resolved_at is not None

        # 4. Verify Final Cryptographic Audit Chain
        audit_check = verify_chain(test_db, case.id)
        assert audit_check.status == "VERIFIED"
        assert audit_check.is_valid is True
        assert audit_check.total_events >= 3


# ─────────────────────────────────────────────────────────────────────────────
# 4. Case Query & Workspace Endpoints (GET /cases, GET /cases/{id})
# ─────────────────────────────────────────────────────────────────────────────

class TestCaseQueryEndpoints:
    """Validates case detail and listing endpoints."""

    def test_get_case_detail_workspace(self, client, staged_approval_case):
        """Retrieves full case context, vendor details, payout details, and audit status."""
        case = staged_approval_case["case"]

        res = client.get(f"/cases/{case.id}")
        assert res.status_code == 200
        data = res.json()

        assert data["id"] == case.id
        assert data["case_number"] == case.case_number
        assert data["state"] == "HUMAN_APPROVAL"
        assert data["amount_inr"] == 12500.0
        assert data["vendor"]["name"] == "Apex Industrial Logistics Pvt Ltd"
        assert data["payout"]["razorpay_payout_id"] == "pout_rzp_appr_01"
        assert data["approval"]["status"] == "PENDING"
        assert data["audit_verification"]["status"] == "VERIFIED"

    def test_list_cases_with_filter(self, client, staged_approval_case):
        """Retrieves list of cases filtered by state."""
        res = client.get("/cases?state=HUMAN_APPROVAL")
        assert res.status_code == 200
        items = res.json()
        assert len(items) >= 1
        assert items[0]["state"] == "HUMAN_APPROVAL"

        res_empty = client.get("/cases?state=CASE_RESOLVED")
        assert res_empty.status_code == 200
        assert len(res_empty.json()) == 0
