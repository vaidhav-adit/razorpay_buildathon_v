"""
api/stream.py
─────────────
Server-Sent Events (SSE) Streaming API (Phase 14 Polish).

Streams real-time agent execution events directly to the frontend:
- state_change (source state, target state, reason)
- audit_block (tamper-evident block mined, actor, action, hash)
- tool_call (tool executed, inputs, outputs, policy level)
- vendor_message (outbound communication sent)
"""

import json
import asyncio
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models.recovery_case import RecoveryCaseModel
from app.models.audit_event import AuditEvent
from app.agent.orchestrator import run_agent_for_case
from app.audit import verify_chain

router = APIRouter(prefix="/cases", tags=["Live Streaming & Telemetry"])


@router.get("/{case_id}/stream")
async def stream_case_events(
    case_id: str,
    action: Optional[str] = Query(None, description="Optional action to trigger during stream, e.g., 'run_step', 'run_all'"),
    vendor_reply: Optional[str] = Query(None, description="Optional vendor reply text"),
):
    """
    Streams Server-Sent Events (SSE) for real-time monitoring of agent reasoning steps.
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        db = SessionLocal()
        try:
            case = db.query(RecoveryCaseModel).filter(RecoveryCaseModel.id == case_id).first()
            if not case:
                yield f"event: error\ndata: {json.dumps({'error': f'Case {case_id} not found'})}\n\n"
                return

            # Initial state packet
            yield f"event: init\ndata: {json.dumps({'case_id': case.id, 'state': case.state if isinstance(case.state, str) else case.state.value, 'amount': case.amount})}\n\n"

            # If action requested, execute turn
            if action in {"run_step", "run_all"}:
                single_step = (action == "run_step")
                run_agent_for_case(case_id=case.id, db=db, vendor_reply_text=vendor_reply, single_step=single_step)
                db.refresh(case)

            # Stream all latest audit events
            events = db.query(AuditEvent).filter(AuditEvent.case_id == case_id).order_by(AuditEvent.id.asc()).all()
            for ev in events:
                payload = {
                    "id": ev.id,
                    "case_id": ev.case_id,
                    "event_type": ev.event_type,
                    "actor": ev.actor,
                    "action": ev.action,
                    "target": ev.target,
                    "reason": ev.reason,
                    "previous_hash": ev.previous_hash,
                    "event_hash": ev.event_hash,
                    "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
                }
                yield f"event: audit_block\ndata: {json.dumps(payload)}\n\n"
                await asyncio.sleep(0.04)

            # Stream final state packet
            verification = verify_chain(db, case_id)
            state_val = case.state if isinstance(case.state, str) else case.state.value
            yield f"event: complete\ndata: {json.dumps({'state': state_val, 'is_valid': verification.is_valid, 'total_events': verification.total_events})}\n\n"

        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
        finally:
            db.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
