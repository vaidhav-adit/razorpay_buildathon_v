"""
api/vendor_communication.py
───────────────────────────
Vendor Communication Adapter Endpoints (Phase 9).

Exposes:
  POST /vendor/message/send     — Sends an outbound message to a vendor.
  POST /vendor/message/receive  — Ingests an inbound response from the vendor simulator.
  GET  /vendor/message/receive  — Polls for inbound messages for a given case_id.
  GET  /vendor/messages/{case_id} — Retrieves chronological conversation history.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.communication_adapter import (
    communication_adapter,
    VendorMessagePayload,
    VendorMessageResponse,
)

router = APIRouter(prefix="/vendor", tags=["Vendor Communication"])


@router.post(
    "/message/send",
    response_model=VendorMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send message to vendor",
)
def send_vendor_message(
    payload: VendorMessagePayload,
    db: Session = Depends(get_db),
):
    """
    Sends an outbound message to the vendor and appends an audit event.
    """
    try:
        msg = communication_adapter.send_message(
            case_id=payload.case_id,
            vendor_id=payload.vendor_id,
            message_body=payload.message_body,
            db=db,
        )
        return msg
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/message/receive",
    response_model=VendorMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest inbound vendor message",
)
def receive_vendor_message(
    payload: VendorMessagePayload,
    db: Session = Depends(get_db),
):
    """
    Simulates receiving an inbound message from a vendor.
    Parses banking details and appends an audit event.
    """
    try:
        msg = communication_adapter.receive_message(
            case_id=payload.case_id,
            vendor_id=payload.vendor_id,
            message_body=payload.message_body,
            db=db,
            extracted_data=payload.extracted_data,
        )
        return msg
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/message/receive",
    response_model=List[VendorMessageResponse],
    status_code=status.HTTP_200_OK,
    summary="Poll messages for a recovery case",
)
def poll_vendor_messages(
    case_id: str = Query(..., description="The recovery case ID to poll messages for"),
    db: Session = Depends(get_db),
):
    """
    Polls messages for a recovery case.
    """
    messages = communication_adapter.get_conversation_history(case_id=case_id, db=db)
    return messages


@router.get(
    "/messages/{case_id}",
    response_model=List[VendorMessageResponse],
    status_code=status.HTTP_200_OK,
    summary="Get full conversation history for a case",
)
def get_case_messages(
    case_id: str,
    db: Session = Depends(get_db),
):
    """
    Returns the chronological conversation history between agent and vendor.
    """
    messages = communication_adapter.get_conversation_history(case_id=case_id, db=db)
    return messages
