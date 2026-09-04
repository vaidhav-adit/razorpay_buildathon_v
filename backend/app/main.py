"""
main.py
───────
FastAPI application entry point.

This module:
  - Creates the FastAPI app instance with metadata (title, version, docs URL).
  - Registers all API routers with their URL prefixes.
  - Adds startup/shutdown lifecycle hooks (database connection pool management).

Run the server with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Interactive API docs are available at:
    http://localhost:8000/docs   (Swagger UI)
    http://localhost:8000/redoc  (ReDoc)
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.audit import router as audit_router


# ── Lifecycle manager ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown lifecycle.
    Database connections are managed per-request via the get_db() dependency.
    """
    print("RazorpayX Exception Resolution Agent starting up...")
    yield
    print("RazorpayX Exception Resolution Agent shutting down.")


# ── App instance ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="RazorpayX Payout Exception Resolution Agent",
    description=(
        "AI-powered, human-governed system for resolving failed B2B vendor payouts. "
        "The agent investigates failures, communicates with vendors, validates corrected "
        "banking details, and prepares replacement payouts for human authorization."
    ),
    version="0.5.0",  # Updated for Phase 5
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health_router)
app.include_router(audit_router)

# Future routers (added as phases complete):
# app.include_router(webhook_router, prefix="/webhooks")
# app.include_router(cases_router, prefix="/cases")
# app.include_router(vendor_router, prefix="/vendor")
# app.include_router(agent_router, prefix="/agent")
# app.include_router(test_router, prefix="/test")
