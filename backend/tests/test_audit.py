"""
tests/test_audit.py
───────────────────
Unit tests for the Cryptographic Audit Ledger (Phase 5).

Tests:
1. Payload hashing consistency and JSON key-sorting determinism.
2. Event hash chaining across sequential blocks.
3. Genesis block previous_hash validation.
4. Cryptographic integrity verification for untampered chains (VERIFIED).
5. Immediate detection of tampering:
   - Modifying actor, action, or reason.
   - Modifying input/output data.
   - Modifying previous_hash links.
   - Forging event hashes.
6. Database audit logging integration.
7. Audit trail API endpoint (GET /cases/{case_id}/audit).
"""

import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base
from app.enums import AuditActorType, CaseState
from app.models.recovery_case import RecoveryCaseModel
from app.models.payout import Payout
from app.models.audit_event import AuditEvent
from app.audit import (
    compute_payload_hash,
    compute_event_hash,
    log_audit_event,
    verify_events_chain,
    verify_chain,
    ChainVerificationResult,
)
from app.main import app


class TestPayloadHashing:
    """Tests payload hashing determinism and serialization."""

    def test_json_key_order_independence(self):
        """Dicts with different key order must generate identical hashes."""
        payload_1 = {"name": "Sharma Logistics", "ifsc": "HDFC0001234", "account": "1234567890"}
        payload_2 = {"account": "1234567890", "name": "Sharma Logistics", "ifsc": "HDFC0001234"}

        hash_1 = compute_payload_hash(payload_1)
        assert hash_1 is not None
        hash_2 = compute_payload_hash(payload_2)
        assert hash_1 == hash_2

    def test_string_payload_hashing(self):
        """String payloads generate standard SHA-256 digests."""
        h1 = compute_payload_hash("raw text message")
        h2 = compute_payload_hash("raw text message")
        h3 = compute_payload_hash("different text")

        assert h1 == h2
        assert h1 != h3

    def test_none_and_empty_payloads(self):
        """None and empty strings return None without raising exceptions."""
        assert compute_payload_hash(None) is None
        assert compute_payload_hash("") is None
        assert compute_payload_hash("   ") is None


class TestChainVerificationInMemory:
    """Tests cryptographic chain verification algorithms with in-memory AuditEvent objects."""

    def test_empty_chain_is_valid(self):
        """An empty event list returns status EMPTY and is_valid True."""
        result = verify_events_chain([])
        assert result.status == "EMPTY"
        assert result.is_valid is True
        assert result.total_events == 0

    def test_single_genesis_event_verifies(self):
        """A single genesis event with previous_hash='' passes verification."""
        case_id = f"case_{uuid.uuid4().hex[:8]}"
        ev_hash = compute_event_hash(
            case_id=case_id,
            event_type="EXTERNAL_FACT",
            actor="razorpay",
            action="PAYOUT_FAILED",
            target="pout_123",
            reason="Invalid IFSC",
            input_hash=None,
            output_hash=None,
            approval_required=False,
            previous_hash="",
        )

        event = AuditEvent(
            id="ev_001",
            case_id=case_id,
            event_type="EXTERNAL_FACT",
            actor="razorpay",
            action="PAYOUT_FAILED",
            target="pout_123",
            reason="Invalid IFSC",
            input_hash=None,
            output_hash=None,
            approval_required=False,
            previous_hash="",
            event_hash=ev_hash,
        )

        result = verify_events_chain([event])
        assert result.status == "VERIFIED"
        assert result.is_valid is True
        assert result.total_events == 1

    def test_multi_event_chain_verifies(self):
        """A multi-event properly linked chain passes verification."""
        case_id = f"case_{uuid.uuid4().hex[:8]}"

        # Event 1: Genesis
        h1 = compute_event_hash(case_id, "EXTERNAL_FACT", "razorpay", "PAYOUT_FAILED", "pout_1", None, None, None, False, "")
        ev1 = AuditEvent(id="ev_1", case_id=case_id, event_type="EXTERNAL_FACT", actor="razorpay", action="PAYOUT_FAILED", target="pout_1", approval_required=False, previous_hash="", event_hash=h1)

        # Event 2: Classifier
        h2 = compute_event_hash(case_id, "AI_DECISION", "classifier", "CLASSIFY_FAILURE", "pout_1", "Vendor data remediation needed", None, None, False, h1)
        ev2 = AuditEvent(id="ev_2", case_id=case_id, event_type="AI_DECISION", actor="classifier", action="CLASSIFY_FAILURE", target="pout_1", reason="Vendor data remediation needed", approval_required=False, previous_hash=h1, event_hash=h2)

        # Event 3: Human Approval
        h3 = compute_event_hash(case_id, "HUMAN_DECISION", "finance_controller", "APPROVE_PAYOUT", "pout_2", "Authorized by controller", None, None, True, h2)
        ev3 = AuditEvent(id="ev_3", case_id=case_id, event_type="HUMAN_DECISION", actor="finance_controller", action="APPROVE_PAYOUT", target="pout_2", reason="Authorized by controller", approval_required=True, previous_hash=h2, event_hash=h3)

        result = verify_events_chain([ev1, ev2, ev3])
        assert result.status == "VERIFIED"
        assert result.is_valid is True
        assert result.total_events == 3

    def test_tampered_event_content_detected(self):
        """Modifying an event's action or actor breaks the chain verification."""
        case_id = "case_tamper_test"
        h1 = compute_event_hash(case_id, "EXTERNAL_FACT", "razorpay", "PAYOUT_FAILED", None, None, None, None, False, "")
        ev1 = AuditEvent(id="ev_1", case_id=case_id, event_type="EXTERNAL_FACT", actor="razorpay", action="PAYOUT_FAILED", approval_required=False, previous_hash="", event_hash=h1)

        h2 = compute_event_hash(case_id, "SYSTEM_ACTION", "agent", "CREATE_CASE", None, None, None, None, False, h1)
        # Malicious actor changes 'agent' to 'rogue_admin' without updating hash
        ev2 = AuditEvent(id="ev_2", case_id=case_id, event_type="SYSTEM_ACTION", actor="rogue_admin", action="CREATE_CASE", approval_required=False, previous_hash=h1, event_hash=h2)

        result = verify_events_chain([ev1, ev2])
        assert result.status == "TAMPERED"
        assert result.is_valid is False
        assert result.broken_at_index == 1
        assert result.broken_event_id == "ev_2"
        assert "Stored hash" in result.details

    def test_broken_previous_hash_link_detected(self):
        """Modifying previous_hash is immediately identified as a broken link."""
        case_id = "case_link_test"
        h1 = compute_event_hash(case_id, "EXTERNAL_FACT", "razorpay", "PAYOUT_FAILED", None, None, None, None, False, "")
        ev1 = AuditEvent(id="ev_1", case_id=case_id, event_type="EXTERNAL_FACT", actor="razorpay", action="PAYOUT_FAILED", approval_required=False, previous_hash="", event_hash=h1)

        # Event 2 has an invalid previous_hash
        fake_prev = "deadbeef" * 8
        h2 = compute_event_hash(case_id, "SYSTEM_ACTION", "agent", "CREATE_CASE", None, None, None, None, False, fake_prev)
        ev2 = AuditEvent(id="ev_2", case_id=case_id, event_type="SYSTEM_ACTION", actor="agent", action="CREATE_CASE", approval_required=False, previous_hash=fake_prev, event_hash=h2)

        result = verify_events_chain([ev1, ev2])
        assert result.status == "TAMPERED"
        assert result.is_valid is False
        assert result.broken_at_index == 1
        assert "Broken chain link" in result.details


class TestAuditDatabaseIntegration:
    """Tests database logging and end-to-end verification using an in-memory SQLite database."""

    @pytest.fixture
    def test_db(self):
        """Create a fresh isolated in-memory SQLite database for testing."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        try:
            # Seed prerequisite recovery case
            case = RecoveryCaseModel(
                id="case_db_test_1",
                case_number="CASE-2026-0001",
                payout_id="pout_test_1",
                vendor_id="vend_test_1",
                amount=500000,
                failure_source="beneficiary_bank",
                failure_reason="invalid_ifsc_code",
                state=CaseState.CASE_CREATED,
            )
            session.add(case)
            session.commit()
            yield session
        finally:
            session.close()

    def test_log_audit_event_chains_sequentially(self, test_db):
        """Sequential log_audit_event calls create an unbroken cryptographic chain."""
        case_id = "case_db_test_1"

        # Event 1
        ev1 = log_audit_event(
            db=test_db,
            case_id=case_id,
            event_type=AuditActorType.EXTERNAL_FACT,
            actor="razorpay_webhook",
            action="PAYOUT_FAILED",
            target="pout_123",
            input_data={"error": "invalid_ifsc"},
        )
        assert ev1.previous_hash == ""
        assert len(ev1.event_hash) == 64

        # Event 2
        ev2 = log_audit_event(
            db=test_db,
            case_id=case_id,
            event_type=AuditActorType.SYSTEM_ACTION,
            actor="failure_classifier",
            action="CLASSIFY_FAILURE",
            target=ev1.id,
            output_data={"strategy": "VENDOR_REMEDIATION"},
        )
        assert ev2.previous_hash == ev1.event_hash
        assert len(ev2.event_hash) == 64

        # Event 3
        ev3 = log_audit_event(
            db=test_db,
            case_id=case_id,
            event_type=AuditActorType.HUMAN_DECISION,
            actor="finance_manager",
            action="AUTHORIZE_PAYMENT",
            target="pout_replacement",
            approval_required=True,
        )
        assert ev3.previous_hash == ev2.event_hash

        # Verify full chain via database query
        result = verify_chain(test_db, case_id)
        assert result.status == "VERIFIED"
        assert result.is_valid is True
        assert result.total_events == 3


class TestAuditAPIEndpoint:
    """Tests the GET /cases/{case_id}/audit HTTP endpoint."""

    def test_get_case_audit_endpoint(self):
        """FastAPI endpoint returns verification status and event chain."""
        client = TestClient(app)
        response = client.get("/cases/non_existent_case/audit")
        assert response.status_code == 200

        data = response.json()
        assert "case_id" in data
        assert "verification" in data
        assert "events" in data
        assert data["verification"]["status"] == "EMPTY"
        assert data["verification"]["is_valid"] is True
