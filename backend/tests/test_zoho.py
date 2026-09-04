"""
tests/test_zoho.py
──────────────────
Unit tests for Zoho Books Sandbox Client and Webhook Ingestion (Phase 7).

Tests:
1. OAuth 2.0 Token Manager lifecycle (caching, automatic refresh, authorization code exchange).
2. Level 1 Read Tools (find_vendor, find_invoice, get_vendor_bank_details):
   - Autonomous execution without approval.
   - Cryptographic audit event logging.
   - Pydantic schema validation.
3. Level 2 Controlled Mutation Tools (update_vendor_bank_details, update_invoice_status):
   - Policy Engine permission gating.
   - Mutation allowed when validation passes.
   - Mutation blocked when validation is missing or case is blocked.
   - Cryptographic audit logging of updates.
4. Zoho Webhook Ingestion Endpoint (POST /webhooks/zoho):
   - Ingestion of bill approval / invoice events.
   - Malformed JSON handling.
"""

import time
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.enums import CaseState, RiskLevel, PolicyDecision
from app.models.vendor import Vendor
from app.models.payout import Payout
from app.models.recovery_case import RecoveryCaseModel
from app.models.fund_account import FundAccount
from app.models.vendor_message import VendorMessage
from app.models.agent_action import AgentAction
from app.models.approval import Approval
from app.models.audit_event import AuditEvent
from app.policy_engine import PolicyContext
from app.audit import verify_chain
from app.services.zoho_client import (
    zoho_client,
    ZohoTokenManager,
    ZohoBooksClient,
    ZohoContactResponse,
    ZohoInvoiceResponse,
    ZohoBankAccountResponse,
    ZohoUpdateResponse,
)
from app.main import app


# ─────────────────────────────────────────────────────────────────────────────
# Test Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def test_db_session():
    """Provides an isolated in-memory SQLite database session for unit tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db_session):
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# 1. OAuth 2.0 Token Manager Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestZohoOAuth:
    """Tests OAuth 2.0 token lifecycle management."""

    def test_token_manager_returns_cached_token(self):
        """Valid cached token is returned directly without making network requests."""
        tm = ZohoTokenManager()
        tm.access_token = "valid_cached_token_123"
        tm.expires_at = time.time() + 1800  # valid for 30 more minutes

        token = tm.get_access_token()
        assert token == "valid_cached_token_123"

    def test_token_manager_refreshes_when_expired(self):
        """Expired or missing token is refreshed automatically."""
        tm = ZohoTokenManager()
        tm.access_token = "expired_token_000"
        tm.expires_at = time.time() - 100  # expired

        token = tm.get_access_token()
        assert token is not None
        assert tm.expires_at > time.time()

    def test_token_exchange_authorization_code(self):
        """Exchange authorization code returns valid token payload."""
        tm = ZohoTokenManager()
        result = tm.exchange_authorization_code("sample_auth_code_xyz")
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["expires_in"] > 0


# ─────────────────────────────────────────────────────────────────────────────
# 2. Zoho Books Tool Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestZohoTools:
    """Tests Zoho Books tool methods, policy engine enforcement, and audit logs."""

    def test_find_vendor_autonomous_and_audited(self, test_db_session):
        """Level 1 find_vendor runs autonomously and logs an audit event."""
        case_id = "case_zoho_test_01"
        res = zoho_client.find_vendor("INV-2026-9901", case_id=case_id, db=test_db_session)

        assert isinstance(res, ZohoContactResponse)
        assert "INV-2026-9901" in res.contact_id
        assert res.contact_name == "Acme Industrial Logistics"
        assert len(res.bank_accounts) >= 1

        # Verify audit event was logged
        audit_check = verify_chain(test_db_session, case_id)
        assert audit_check.status == "VERIFIED"
        assert audit_check.total_events == 1

    def test_find_invoice_autonomous_and_audited(self, test_db_session):
        """Level 1 find_invoice returns bill details and logs an audit event."""
        case_id = "case_zoho_test_02"
        res = zoho_client.find_invoice("inv_8899", case_id=case_id, db=test_db_session)

        assert isinstance(res, ZohoInvoiceResponse)
        assert res.invoice_id == "inv_8899"
        assert res.total == 750000
        assert res.status == "open"

        audit_check = verify_chain(test_db_session, case_id)
        assert audit_check.status == "VERIFIED"
        assert audit_check.total_events == 1

    def test_get_vendor_bank_details_autonomous_and_audited(self, test_db_session):
        """Level 1 get_vendor_bank_details returns list of bank accounts."""
        case_id = "case_zoho_test_03"
        res = zoho_client.get_vendor_bank_details("zoho_cont_01", case_id=case_id, db=test_db_session)

        assert isinstance(res, list)
        assert len(res) >= 1
        assert isinstance(res[0], ZohoBankAccountResponse)
        assert res[0].ifsc == "HDFC0000001"

        audit_check = verify_chain(test_db_session, case_id)
        assert audit_check.status == "VERIFIED"
        assert audit_check.total_events == 1

    def test_update_vendor_bank_details_policy_pass(self, test_db_session):
        """Level 2 update_vendor_bank_details succeeds when policy context is valid."""
        case_id = "case_zoho_test_04"
        valid_context = PolicyContext(
            case_state=CaseState.DATA_VALIDATED,
            name_match_score=90,
            data_validated=True,
            vendor_verified=True,
            risk_level=RiskLevel.LOW,
        )

        new_bank_details = {
            "account_name": "Acme Industrial Logistics",
            "account_number": "987654321098",
            "ifsc": "HDFC0000001",
            "bank_name": "HDFC Bank",
        }

        res = zoho_client.update_vendor_bank_details(
            vendor_id="zoho_cont_01",
            bank_details=new_bank_details,
            case_id=case_id,
            db=test_db_session,
            context=valid_context,
        )

        assert isinstance(res, ZohoUpdateResponse)
        assert res.code == 0
        assert "Successfully updated" in res.message

        audit_check = verify_chain(test_db_session, case_id)
        assert audit_check.status == "VERIFIED"
        assert audit_check.total_events == 1

    def test_update_vendor_bank_details_policy_blocked(self, test_db_session):
        """Level 2 update_vendor_bank_details is BLOCKED if data is unvalidated."""
        case_id = "case_zoho_test_05"
        invalid_context = PolicyContext(data_validated=False)

        with pytest.raises(PermissionError) as exc_info:
            zoho_client.update_vendor_bank_details(
                vendor_id="zoho_cont_01",
                bank_details={"account_number": "123"},
                case_id=case_id,
                db=test_db_session,
                context=invalid_context,
            )
        assert "Policy Engine BLOCKED" in str(exc_info.value)
        assert "validation has not passed" in str(exc_info.value)

    def test_update_invoice_status_policy_pass(self, test_db_session):
        """Level 2 update_invoice_status succeeds under valid policy context."""
        case_id = "case_zoho_test_06"
        valid_context = PolicyContext(
            case_state=CaseState.PAYOUT_CONFIRMED,
            risk_level=RiskLevel.LOW,
        )

        res = zoho_client.update_invoice_status(
            invoice_id="inv_9901",
            status="paid",
            case_id=case_id,
            db=test_db_session,
            context=valid_context,
        )

        assert isinstance(res, ZohoUpdateResponse)
        assert res.code == 0
        assert "paid" in res.message

        audit_check = verify_chain(test_db_session, case_id)
        assert audit_check.status == "VERIFIED"
        assert audit_check.total_events == 1

    def test_update_invoice_status_policy_blocked_on_terminal_state(self, test_db_session):
        """Level 2 update_invoice_status is BLOCKED when case is in BLOCKED terminal state."""
        case_id = "case_zoho_test_07"
        blocked_context = PolicyContext(case_state=CaseState.BLOCKED)

        with pytest.raises(PermissionError) as exc_info:
            zoho_client.update_invoice_status(
                invoice_id="inv_9901",
                status="paid",
                case_id=case_id,
                db=test_db_session,
                context=blocked_context,
            )
        assert "Policy Engine BLOCKED" in str(exc_info.value)
        assert "is in BLOCKED state" in str(exc_info.value)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Zoho Webhook Ingestion Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestZohoWebhook:
    """Tests the POST /webhooks/zoho endpoint."""

    def test_zoho_webhook_ingestion(self, client):
        """Valid Zoho bill approval webhook returns HTTP 200."""
        payload = {
            "event": "bill_approved",
            "bill": {
                "bill_id": "bill_998877",
                "bill_number": "BILL-2026-0042",
                "total": 500000,
            },
        }
        response = client.post("/webhooks/zoho", json=payload)
        assert response.status_code == 200
        res = response.json()
        assert res["status"] == "received"
        assert res["event"] == "bill_approved"
        assert res["invoice_id"] == "bill_998877"
        assert res["bill_number"] == "BILL-2026-0042"

    def test_zoho_webhook_invalid_json(self, client):
        """Malformed JSON payload returns HTTP 400."""
        response = client.post(
            "/webhooks/zoho",
            content=b"not a valid json {",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400
        assert "Malformed JSON" in response.json()["detail"]
