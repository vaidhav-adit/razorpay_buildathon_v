"""
api/health.py
─────────────
Health check endpoint.

A simple GET /health route that verifies:
  1. The server is running and accepting requests.
  2. The database connection is reachable.

This is the only endpoint in Phase 1. It gives us something concrete to
test before any business logic is written.
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.database import get_db

router = APIRouter()


@router.get("/health", tags=["System"])
def health_check(db: Session = Depends(get_db)):
    """
    Returns the server status and confirms the database is reachable.

    Runs a trivial SQL query (SELECT 1) against the database. If the database
    is down or misconfigured, this route returns a 503 with an error message
    rather than raising an unhandled exception.
    """
    try:
        # Simple query to confirm the DB connection is alive
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as exc:
        # Return 503 so load balancers / health monitors can detect the failure
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "database": "unreachable",
                "detail": str(exc),
            },
        )

    return {
        "status": "ok",
        "phase": 1,
        "description": "RazorpayX Payout Exception Resolution Agent",
        "database": db_status,
    }
