"""
tests/test_communication.py
───────────────────────────
Unit tests for Vendor Communication Adapter and API Endpoints (Phase 9).

Tests:
1. Regex extraction of Indian IFSC and Bank Account numbers from raw unstructured text.
2. Vendor Communication Adapter service methods:
   - Outbound message sending, persistence, and audit trail emission.
   - Inbound message ingestion, automatic banking data extraction, and audit logging.
   - Conversation history ordering.
3. FastAPI Endpoints:
   - POST /vendor/message/send
   - POST /vendor/message/receive
   - GET  /vendor/message/receive?case_id=...
   - GET  /vendor/messages/{case_id}
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.enums import MessageDirection, CaseState
from app.models.vendor import Vendor
from app.models.payout import Payout
from app.models.recovery_case import RecoveryCaseModel
from app.models.fund_account import FundAccount
from app.models.vendor_message import VendorMessage
from app.models.agent_action import AgentAction
from app.models.approval import Approval
from app.models.audit_event import AuditEvent
from app.audit import verify_chain
from app.services.communication_adapter import (
    communication_adapter,
    extract_banking_details_from_text,
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

    # Pre-populate test vendor, payout, and case for foreign keys
    test_vendor = Vendor(
        id="vend_comm_test_01",
        name="Acme Logistics",
        email="accounts@acme.com",
        phone="+919876543210",
    )
    session.add(test_vendor)
    session.commit()

    test_payout = Payout(
        id="pout_comm_test_01",
        razorpay_payout_id="pout_rzp_comm_01",
        razorpay_fund_account_id="fa_test_comm_01",
        razorpay_contact_id="cont_test_comm_01",
        amount=500000,
        currency="INR",
        status="failed",
    )
    session.add(test_payout)
    session.commit()

    test_case = RecoveryCaseModel(
        id="case_comm_test_01",
        case_number="CASE-COMM-001",
        payout_id=test_payout.id,
        vendor_id=test_vendor.id,
        amount=500000,
        failure_source="beneficiary_bank",
        failure_reason="invalid_ifsc_code",
        state=CaseState.VENDOR_CONTACTED,
    )
    session.add(test_case)
    session.commit()

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
# 1. Regex Banking Details Extraction Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestRegexExtraction:
    """Tests heuristic extraction of IFSC and account numbers from raw text."""

    def test_extract_ifsc_and_account_number(self):
        """Extracts valid IFSC and bank account number from conversational response."""
        text = "Hello, please use my new bank details: IFSC is HDFC0001234 and Account Number is 98765432109876. Thanks!"
        extracted = extract_banking_details_from_text(text)

        assert extracted.get("ifsc") == "HDFC0001234"
        assert extracted.get("account_number") == "98765432109876"

    def test_extract_mixed_case_ifsc(self):
        """Extracts and standardizes lower/mixed case IFSC code to uppercase."""
        text = "Account: 123456789012, ifsc code: icic0000021"
        extracted = extract_banking_details_from_text(text)

        assert extracted.get("ifsc") == "ICIC0000021"
        assert extracted.get("account_number") == "123456789012"

    def test_extract_empty_or_no_details(self):
        """Returns empty dict when text does not contain banking credentials."""
        assert extract_banking_details_from_text("Let me check and get back to you later.") == {}
        assert extract_banking_details_from_text("") == {}


# ─────────────────────────────────────────────────────────────────────────────
# 2. Adapter Service Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestVendorCommunicationAdapter:
    """Tests sending, receiving, and history retrieval through the adapter."""

    def test_send_message_creates_outbound_record_and_audit(self, test_db_session):
        """send_message creates an OUTBOUND VendorMessage and appends an AuditEvent."""
        case_id = "case_comm_test_01"
        vendor_id = "vend_comm_test_01"

        msg = communication_adapter.send_message(
            case_id=case_id,
            vendor_id=vendor_id,
            message_body="Your payout failed due to invalid IFSC. Please provide your updated bank account.",
            db=test_db_session,
        )

        assert msg.id is not None
        assert msg.direction == "OUTBOUND"
        assert "invalid IFSC" in msg.body

        # Verify DB persistence
        db_msg = test_db_session.query(VendorMessage).filter(VendorMessage.id == msg.id).first()
        assert db_msg is not None
        assert db_msg.case_id == case_id

        # Verify audit ledger
        audit_check = verify_chain(test_db_session, case_id)
        assert audit_check.status == "VERIFIED"
        assert audit_check.total_events == 1

    def test_receive_message_creates_inbound_record_with_extracted_data(self, test_db_session):
        """receive_message parses banking details and logs an EXTERNAL_FACT audit event."""
        case_id = "case_comm_test_01"
        vendor_id = "vend_comm_test_01"

        reply_text = "Here are my details: A/C 998877665544 and IFSC SBIN0000123"
        msg = communication_adapter.receive_message(
            case_id=case_id,
            vendor_id=vendor_id,
            message_body=reply_text,
            db=test_db_session,
        )

        assert msg.id is not None
        assert msg.direction == "INBOUND"
        assert msg.extracted_data is not None
        assert msg.extracted_data.get("ifsc") == "SBIN0000123"
        assert msg.extracted_data.get("account_number") == "998877665544"

        # Verify audit ledger
        audit_check = verify_chain(test_db_session, case_id)
        assert audit_check.status == "VERIFIED"
        assert audit_check.total_events == 1

    def test_get_conversation_history_ordering(self, test_db_session):
        """get_conversation_history returns all messages in ascending chronological order."""
        case_id = "case_comm_test_01"
        vendor_id = "vend_comm_test_01"

        communication_adapter.send_message(
            case_id=case_id,
            vendor_id=vendor_id,
            message_body="Message 1: Outbound inquiry",
            db=test_db_session,
        )
        communication_adapter.receive_message(
            case_id=case_id,
            vendor_id=vendor_id,
            message_body="Message 2: Inbound response",
            db=test_db_session,
        )

        history = communication_adapter.get_conversation_history(case_id=case_id, db=test_db_session)
        assert len(history) == 2
        assert history[0].direction == "OUTBOUND"
        assert history[1].direction == "INBOUND"


# ─────────────────────────────────────────────────────────────────────────────
# 3. API Endpoint Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestVendorCommunicationAPI:
    """Tests the REST API routes for sending, receiving, and polling messages."""

    def test_api_send_message(self, client):
        """POST /vendor/message/send returns HTTP 201 and creates outbound message."""
        payload = {
            "case_id": "case_comm_test_01",
            "vendor_id": "vend_comm_test_01",
            "message_body": "Hello from agent: please verify your IFSC code.",
        }
        res = client.post("/vendor/message/send", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["direction"] == "OUTBOUND"
        assert data["case_id"] == "case_comm_test_01"
        assert "IFSC" in data["body"]

    def test_api_receive_message(self, client):
        """POST /vendor/message/receive simulates vendor replying with updated bank details."""
        payload = {
            "case_id": "case_comm_test_01",
            "vendor_id": "vend_comm_test_01",
            "message_body": "Updated account is 112233445566 with IFSC UTIB0000004.",
        }
        res = client.post("/vendor/message/receive", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["direction"] == "INBOUND"
        assert data["extracted_data"]["ifsc"] == "UTIB0000004"
        assert data["extracted_data"]["account_number"] == "112233445566"

    def test_api_poll_and_get_history(self, client):
        """GET /vendor/message/receive?case_id=... and GET /vendor/messages/{case_id} return conversation history."""
        case_id = "case_comm_test_01"

        # Poll endpoint
        poll_res = client.get(f"/vendor/message/receive?case_id={case_id}")
        assert poll_res.status_code == 200
        assert isinstance(poll_res.json(), list)

        # History endpoint
        history_res = client.get(f"/vendor/messages/{case_id}")
        assert history_res.status_code == 200
        assert isinstance(history_res.json(), list)
