"""
models/__init__.py
──────────────────
Imports all models so that:
  1. SQLAlchemy's relationship resolution works (all classes are in scope).
  2. Alembic's env.py can import this single module and get Base.metadata
     with all tables registered, which is required for autogenerate migrations.

Import order matters — models with no foreign keys come before those that
reference them, but SQLAlchemy handles forward references through string names
in relationship() so the order here is mostly for readability.
"""

from app.models.vendor import Vendor
from app.models.payout import Payout
from app.models.recovery_case import RecoveryCaseModel
from app.models.fund_account import FundAccount
from app.models.vendor_message import VendorMessage
from app.models.agent_action import AgentAction
from app.models.approval import Approval
from app.models.audit_event import AuditEvent

# Expose all models at package level for convenient importing elsewhere
__all__ = [
    "Vendor",
    "Payout",
    "RecoveryCaseModel",
    "FundAccount",
    "VendorMessage",
    "AgentAction",
    "Approval",
    "AuditEvent",
]
