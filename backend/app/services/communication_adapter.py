"""
services/communication_adapter.py
─────────────────────────────────
Vendor Communication Adapter & WhatsApp Simulator (Phase 9).

This module manages all messaging interactions between the AI agent and vendors:
- Sending structured outbound inquiries (remediation requests, missing field notices).
- Receiving and recording inbound vendor responses (from demo simulator or WhatsApp API).
- Parsing and extracting structured banking details (IFSC, Account Number, Name).
- Maintaining conversation history.
- Cryptographically logging every inbound and outbound message as an AuditEvent.

Foundational Architectural Principles:
1. Transparency: Every message is recorded with direction, timestamp, and audit hash.
2. Structured Extraction: Inbound messages are pre-parsed for banking fields.
3. Level 1 Autonomous Action: Inquiries and polling run autonomously without blocking.
"""

import re
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.enums import MessageDirection, AuditActorType, PolicyDecision
from app.models.vendor_message import VendorMessage
from app.policy_engine import evaluate_policy, PolicyContext
from app.audit import log_audit_event


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Schemas
# ─────────────────────────────────────────────────────────────────────────────

class VendorMessagePayload(BaseModel):
    """Schema for sending or receiving vendor messages."""
    model_config = ConfigDict(extra="ignore")
    case_id: str
    vendor_id: str
    message_body: str
    extracted_data: Optional[Dict[str, Any]] = None


class VendorMessageResponse(BaseModel):
    """Schema for serialized vendor message responses."""
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    id: str
    case_id: str
    vendor_id: str
    direction: str
    body: str
    extracted_data: Optional[Dict[str, Any]] = None
    timestamp: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Extraction Utilities
# ─────────────────────────────────────────────────────────────────────────────

# Standard Indian IFSC Code regex: 4 letters, 0, 6 alphanumeric characters
IFSC_REGEX = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b", re.IGNORECASE)

# Standard Indian Bank Account Number: 9 to 18 contiguous digits
ACCOUNT_NUMBER_REGEX = re.compile(r"\b\d{9,18}\b")


def extract_banking_details_from_text(text: str) -> Dict[str, Any]:
    """
    Extracts IFSC and bank account numbers from unstructured vendor reply text.
    """
    if not text:
        return {}

    extracted: Dict[str, Any] = {}

    ifsc_match = IFSC_REGEX.search(text)
    if ifsc_match:
        extracted["ifsc"] = ifsc_match.group(0).upper()

    acc_matches = ACCOUNT_NUMBER_REGEX.findall(text)
    if acc_matches:
        extracted["account_number"] = acc_matches[0]

    if "ifsc" in extracted and "account_number" in extracted:
        extracted["is_syntax_valid"] = True
    elif "ifsc" in extracted or "account_number" in extracted:
        extracted["is_syntax_valid"] = False
    else:
        return {}

    return extracted


# ─────────────────────────────────────────────────────────────────────────────
# Communication Adapter Service
# ─────────────────────────────────────────────────────────────────────────────

class VendorCommunicationAdapter:
    """
    Communication Adapter facilitating multi-channel vendor interactions.
    In demo mode, interfaces with the Vendor Chat Simulator dashboard.
    In production mode, acts as the WhatsApp Business API client.
    """

    def send_message(
        self,
        case_id: str,
        vendor_id: str,
        message_body: str,
        db: Session,
        context: Optional[PolicyContext] = None,
    ) -> VendorMessage:
        """
        Sends an outbound message to a vendor.
        Policy Level: Level 1 (Autonomous).
        """
        # 1. Policy Gate
        ctx = context or PolicyContext()
        policy = evaluate_policy("send_vendor_message", ctx)
        if policy.decision != PolicyDecision.ALLOW:
            raise PermissionError(
                f"Policy Engine BLOCKED send_vendor_message: {policy.reason}"
            )

        # 2. Persist message
        msg = VendorMessage(
            id=str(uuid.uuid4()),
            case_id=case_id,
            vendor_id=vendor_id,
            direction=MessageDirection.OUTBOUND.value if hasattr(MessageDirection.OUTBOUND, "value") else "OUTBOUND",
            body=message_body.strip(),
            extracted_data=None,
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)

        # 3. Cryptographic Audit Log
        log_audit_event(
            db=db,
            case_id=case_id,
            event_type=AuditActorType.SYSTEM_ACTION,
            actor="communication_adapter",
            action="send_vendor_message",
            target=vendor_id,
            input_data={"vendor_id": vendor_id, "message_body": message_body},
            output_data={"message_id": msg.id, "direction": msg.direction},
        )

        return msg

    def receive_message(
        self,
        case_id: str,
        vendor_id: str,
        message_body: str,
        db: Session,
        extracted_data: Optional[Dict[str, Any]] = None,
    ) -> VendorMessage:
        """
        Receives an inbound message from a vendor (or demo chat simulator).
        Extracts banking details and appends an EXTERNAL_FACT audit event.
        """
        # Auto-extract banking fields if not explicitly provided
        parsed_data = extracted_data or extract_banking_details_from_text(message_body)

        msg = VendorMessage(
            id=str(uuid.uuid4()),
            case_id=case_id,
            vendor_id=vendor_id,
            direction=MessageDirection.INBOUND.value if hasattr(MessageDirection.INBOUND, "value") else "INBOUND",
            body=message_body.strip(),
            extracted_data=parsed_data if parsed_data else None,
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)

        # Cryptographic Audit Log
        log_audit_event(
            db=db,
            case_id=case_id,
            event_type=AuditActorType.EXTERNAL_FACT,
            actor="vendor_channel",
            action="receive_vendor_message",
            target=vendor_id,
            input_data={"vendor_id": vendor_id, "message_body": message_body},
            output_data={"message_id": msg.id, "extracted_data": msg.extracted_data},
        )

        return msg

    def get_conversation_history(self, case_id: str, db: Session) -> List[VendorMessage]:
        """
        Retrieves all chronological messages for a recovery case.
        """
        return (
            db.query(VendorMessage)
            .filter(VendorMessage.case_id == case_id)
            .order_by(VendorMessage.timestamp.asc())
            .all()
        )


# Singleton instance
communication_adapter = VendorCommunicationAdapter()
