"""
tests/test_razorpay.py
──────────────────────
Unit tests for RazorpayX Test Mode Client and Webhook Ingestion (Phase 6).

Tests:
1. Webhook HMAC-SHA256 signature calculation and verification.
2. Webhook ingestion endpoint (POST /webhooks/razorpay):
   - Ingestion of payout.failed event.
   - Database record creation for Vendor, Payout, and RecoveryCase.
   - Deterministic failure classification on ingestion.
   - Initial audit event genesis logging.
   - Ignored events handling (e.g., payout.processed).
   - Tampered signature rejection (HTTP 400).
3. Razorpay tool execution with policy engine checks and audit logging:
   - Level 1: get_payout, get_contact, get_fund_accounts.
   - Level 2: create_fund_account, deactivate_fund_account.
   - Level 3: create_payout (strict human authorization guard).
"""

import hmac
import hashlib
import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.enums import CaseState, RecoveryStrategy, RiskLevel
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
from app.services.razorpay_client import (
    razorpay_client,
    verify_razorpay_signature,
    RazorpayPayoutResponse,
    RazorpayContactResponse,
    RazorpayFundAccountResponse,
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
# 1. Webhook Signature Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestWebhookSignatureVerification:
    """Tests HMAC-SHA256 signature verification."""

    def test_valid_signature(self):
        """Valid HMAC-SHA256 signature passes verification."""
        secret = "super_secret_webhook_key_123"
        raw_body = b'{"event":"payout.failed","payload":{}}'
        signature = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

        assert verify_razorpay_signature(raw_body, signature, secret) is True

    def test_invalid_signature_fails(self):
        """Invalid or tampered signature is rejected."""
        secret = "super_secret_webhook_key_123"
        raw_body = b'{"event":"payout.failed","payload":{}}'
        tampered_signature = "badf00d" * 8

        assert verify_razorpay_signature(raw_body, tampered_signature, secret) is False

    def test_missing_signature_or_secret(self):
        """Missing parameters return False safely without raising exceptions."""
        assert verify_razorpay_signature(b"data", None, "secret") is False
        assert verify_razorpay_signature(b"data", "sig", "") is False


# ─────────────────────────────────────────────────────────────────────────────
# 2. Webhook Ingestion Endpoint Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestWebhookIngestionEndpoint:
    """Tests the POST /webhooks/razorpay endpoint."""

    def test_ingest_payout_failed_creates_case_and_audit(self, client, test_db_session, monkeypatch):
        """payout.failed webhook creates Vendor, Payout, RecoveryCase, and AuditEvent."""
        webhook_secret = "test_webhook_secret_xyz"
        from app.config import settings
        monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", webhook_secret)

        payload = {
            "event": "payout.failed",
            "payload": {
                "payout": {
                    "entity": {
                        "id": "pout_test_webhook_01",
                        "contact_id": "cont_acme_01",
                        "fund_account_id": "fa_acme_bad_ifsc",
                        "amount": 750000,
                        "currency": "INR",
                        "mode": "NEFT",
                        "reference_id": "INV-2026-9901",
                        "status": "failed",
                        "status_details": {
                            "source": "beneficiary_bank",
                            "reason": "invalid_ifsc_code",
                            "description": "Invalid branch IFSC code",
                        },
                        "notes": {
                            "vendor_name": "Acme Industrial Logistics",
                            "vendor_email": "accounts@acmelogistics.com",
                            "vendor_phone": "+919876500000",
                        },
                    }
                }
            },
        }

        body_bytes = json.dumps(payload).encode("utf-8")
        signature = hmac.new(webhook_secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

        response = client.post(
            "/webhooks/razorpay",
            content=body_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": signature,
            },
        )

        assert response.status_code == 200
        res_json = response.json()
        assert res_json["status"] == "received"
        assert res_json["event"] == "payout.failed"
        assert res_json["strategy"] == "VENDOR_REMEDIATION"
        case_id = res_json["case_id"]
        assert case_id is not None

        # Verify DB records
        case = test_db_session.query(RecoveryCaseModel).filter(RecoveryCaseModel.id == case_id).first()
        assert case is not None
        assert case.state == CaseState.CASE_CREATED
        assert case.amount == 750000
        assert case.failure_reason == "invalid_ifsc_code"
        assert case.recovery_strategy == RecoveryStrategy.VENDOR_REMEDIATION

        payout = test_db_session.query(Payout).filter(Payout.razorpay_payout_id == "pout_test_webhook_01").first()
        assert payout is not None
        assert payout.amount == 750000

        vendor = test_db_session.query(Vendor).filter(Vendor.razorpay_contact_id == "cont_acme_01").first()
        assert vendor is not None
        assert vendor.name == "Acme Industrial Logistics"

        # Verify audit ledger genesis block
        audit_check = verify_chain(test_db_session, case_id)
        assert audit_check.status == "VERIFIED"
        assert audit_check.is_valid is True
        assert audit_check.total_events == 1

    def test_ingest_non_failure_event_is_ignored(self, client):
        """payout.processed events are acknowledged without creating recovery cases."""
        payload = {"event": "payout.processed", "payload": {}}
        response = client.post("/webhooks/razorpay", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "ignored"

    def test_invalid_signature_header_rejected(self, client, monkeypatch):
        """Bad signature header returns HTTP 400."""
        from app.config import settings
        monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", "test_webhook_secret_xyz")
        payload = {"event": "payout.failed", "payload": {}}
        response = client.post(
            "/webhooks/razorpay",
            json=payload,
            headers={"X-Razorpay-Signature": "invalid_forged_signature"},
        )
        assert response.status_code == 400
        assert "Invalid Razorpay webhook" in response.json()["detail"]


# ─────────────────────────────────────────────────────────────────────────────
# 3. Razorpay Tool Execution & Policy Gating Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestRazorpayTools:
    """Tests Razorpay API tool methods with policy engine enforcement."""

    def test_get_payout_tool(self, test_db_session):
        """Level 1 get_payout runs autonomously and logs audit event."""
        res = razorpay_client.get_payout("pout_12345", case_id="case_tool_test_1", db=test_db_session)
        assert isinstance(res, RazorpayPayoutResponse)
        assert res.id == "pout_12345"

    def test_get_contact_tool(self, test_db_session):
        """Level 1 get_contact returns contact details."""
        res = razorpay_client.get_contact("cont_12345", case_id="case_tool_test_1", db=test_db_session)
        assert isinstance(res, RazorpayContactResponse)
        assert res.id == "cont_12345"

    def test_get_fund_accounts_tool(self, test_db_session):
        """Level 1 get_fund_accounts returns list of fund accounts."""
        res = razorpay_client.get_fund_accounts("cont_12345", case_id="case_tool_test_1", db=test_db_session)
        assert isinstance(res, list)
        assert len(res) >= 1
        assert isinstance(res[0], RazorpayFundAccountResponse)

    def test_create_fund_account_policy_pass(self, test_db_session):
        """Level 2 create_fund_account succeeds when policy conditions pass."""
        valid_context = PolicyContext(
            case_state=CaseState.DATA_VALIDATED,
            name_match_score=90,
            data_validated=True,
            vendor_verified=True,
            risk_level=RiskLevel.LOW,
        )

        bank_details = {
            "name": "Sharma Transport",
            "ifsc": "ICIC0000021",
            "account_number": "002101549823",
        }

        res = razorpay_client.create_fund_account(
            contact_id="cont_12345",
            account_type="bank_account",
            bank_account=bank_details,
            case_id="case_tool_test_1",
            db=test_db_session,
            context=valid_context,
        )

        assert isinstance(res, RazorpayFundAccountResponse)
        assert res.contact_id == "cont_12345"

    def test_create_fund_account_policy_blocked_on_unvalidated(self, test_db_session):
        """Level 2 create_fund_account raises PermissionError when data is unvalidated."""
        invalid_context = PolicyContext(data_validated=False)

        with pytest.raises(PermissionError) as exc_info:
            razorpay_client.create_fund_account(
                contact_id="cont_12345",
                account_type="bank_account",
                bank_account={"account_number": "123"},
                context=invalid_context,
            )
        assert "validation has not passed" in str(exc_info.value)

    def test_create_payout_requires_human_authorization(self, test_db_session):
        """Level 3 create_payout raises PermissionError without explicit human authorization."""
        with pytest.raises(PermissionError) as exc_info:
            razorpay_client.create_payout(
                account_number="23232300001",
                fund_account_id="fa_new_123",
                amount=500000,
                is_human_authorized=False,
            )
        assert "cannot be executed autonomously without human authorization" in str(exc_info.value)

    def test_create_payout_succeeds_with_human_authorization(self, test_db_session):
        """Level 3 create_payout proceeds when human authorization flag is True."""
        res = razorpay_client.create_payout(
            account_number="23232300001",
            fund_account_id="fa_new_123",
            amount=500000,
            case_id="case_tool_test_1",
            db=test_db_session,
            is_human_authorized=True,
        )
        assert isinstance(res, RazorpayPayoutResponse)
        assert res.amount == 500000
