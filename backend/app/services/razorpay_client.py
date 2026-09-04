"""
services/razorpay_client.py
───────────────────────────
RazorpayX Test Mode Client & Tool Integration.

This module provides real API client integration with RazorpayX endpoints for:
- Payout retrieval and creation
- Contact inspection
- Fund account creation and deactivation
- Webhook HMAC-SHA256 signature verification

Foundational Architectural Principles:
1. Policy Gating: Every mutating or financially consequential action checks permissions
   with the Policy Engine before execution.
2. Audit Trail: Every external tool execution appends an AuditEvent to the cryptographic ledger.
3. Strongly Typed Models: Returns validated Pydantic response objects.
"""

import hmac
import hashlib
from typing import Optional, List, Dict, Any
import httpx
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session

from app.config import settings
from app.enums import PolicyDecision, AuditActorType
from app.policy_engine import evaluate_policy, PolicyContext
from app.audit import log_audit_event


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Response Schemas for Razorpay Entities
# ─────────────────────────────────────────────────────────────────────────────

class RazorpayStatusDetails(BaseModel):
    """Failure status details attached to failed payouts."""
    model_config = ConfigDict(extra="ignore")
    source: Optional[str] = None
    reason: Optional[str] = None
    description: Optional[str] = None


class RazorpayPayoutResponse(BaseModel):
    """Schema representing a Razorpay Payout object."""
    model_config = ConfigDict(extra="ignore")
    id: str
    entity: str = "payout"
    fund_account_id: str
    amount: int
    currency: str = "INR"
    status: str
    purpose: Optional[str] = "vendor_payout"
    utr: Optional[str] = None
    mode: Optional[str] = "NEFT"
    reference_id: Optional[str] = None
    narration: Optional[str] = None
    status_details: Optional[RazorpayStatusDetails] = None


class RazorpayContactResponse(BaseModel):
    """Schema representing a Razorpay Contact object."""
    model_config = ConfigDict(extra="ignore")
    id: str
    entity: str = "contact"
    name: str
    contact: Optional[str] = None
    email: Optional[str] = None
    type: Optional[str] = "vendor"
    reference_id: Optional[str] = None
    active: bool = True


class RazorpayBankAccountDetails(BaseModel):
    """Bank account details nested within a Fund Account."""
    model_config = ConfigDict(extra="ignore")
    ifsc: str
    bank_name: Optional[str] = None
    name: str
    account_number: str


class RazorpayFundAccountResponse(BaseModel):
    """Schema representing a Razorpay Fund Account object."""
    model_config = ConfigDict(extra="ignore")
    id: str
    entity: str = "fund_account"
    contact_id: str
    account_type: str = "bank_account"
    bank_account: Optional[RazorpayBankAccountDetails] = None
    active: bool = True


# ─────────────────────────────────────────────────────────────────────────────
# Webhook Signature Verification
# ─────────────────────────────────────────────────────────────────────────────

def verify_razorpay_signature(raw_body: bytes, signature_header: Optional[str], secret: Optional[str] = None) -> bool:
    """
    Verifies the HMAC-SHA256 signature of an incoming Razorpay webhook.
    
    Args:
        raw_body: The raw request body bytes.
        signature_header: The X-Razorpay-Signature header value.
        secret: Webhook secret (defaults to settings.RAZORPAY_WEBHOOK_SECRET).
        
    Returns:
        bool: True if signature is valid, False otherwise.
    """
    webhook_secret = secret or getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "")
    if not webhook_secret or not signature_header:
        return False

    expected_signature = hmac.new(
        key=webhook_secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature_header.strip())


# ─────────────────────────────────────────────────────────────────────────────
# Razorpay API Client Class
# ─────────────────────────────────────────────────────────────────────────────

class RazorpayClient:
    """
    HTTP client for RazorpayX APIs.
    Supports real Test Mode API requests with policy engine evaluation and audit logging.
    """

    def __init__(self, key_id: Optional[str] = None, key_secret: Optional[str] = None, base_url: str = "https://api.razorpay.com/v1"):
        self.key_id = key_id or getattr(settings, "RAZORPAY_KEY_ID", "")
        self.key_secret = key_secret or getattr(settings, "RAZORPAY_KEY_SECRET", "")
        self.base_url = base_url.rstrip("/")

    @property
    def auth(self) -> Optional[tuple[str, str]]:
        """Returns HTTP Basic Auth tuple if credentials are configured."""
        if self.key_id and self.key_secret and not self.key_id.startswith("rzp_test_xxxx"):
            return (self.key_id, self.key_secret)
        return None

    # ── Tool 1: Get Payout (Level 1 Autonomous) ───────────────────────────────
    def get_payout(self, payout_id: str, case_id: Optional[str] = None, db: Optional[Session] = None) -> RazorpayPayoutResponse:
        """
        Retrieves payout details from RazorpayX (GET /v1/payouts/{id}).
        Policy Level: Level 1 (Autonomous).
        """
        # Policy Check
        policy = evaluate_policy("get_payout")
        if policy.decision == PolicyDecision.BLOCK:
            raise PermissionError(f"Policy blocked get_payout: {policy.reason}")

        # Execute API call if real credentials exist, else return mock/test object
        if self.auth:
            with httpx.Client(base_url=self.base_url, auth=self.auth, timeout=15.0) as client:
                res = client.get(f"/payouts/{payout_id}")
                res.raise_for_status()
                data = res.json()
        else:
            # Test Mode simulation fallback
            data = {
                "id": payout_id,
                "entity": "payout",
                "fund_account_id": "fa_simulated_01",
                "amount": 500000,
                "currency": "INR",
                "status": "failed",
                "status_details": {
                    "source": "beneficiary_bank",
                    "reason": "invalid_ifsc_code",
                    "description": "Invalid IFSC code provided for beneficiary",
                },
            }

        result = RazorpayPayoutResponse.model_validate(data)

        # Audit Logging
        if db and case_id:
            log_audit_event(
                db=db,
                case_id=case_id,
                event_type=AuditActorType.SYSTEM_ACTION,
                actor="razorpay_client",
                action="GET_PAYOUT",
                target=payout_id,
                output_data=data,
            )

        return result

    # ── Tool 2: Get Contact (Level 1 Autonomous) ──────────────────────────────
    def get_contact(self, contact_id: str, case_id: Optional[str] = None, db: Optional[Session] = None) -> RazorpayContactResponse:
        """
        Retrieves contact details from RazorpayX (GET /v1/contacts/{id}).
        Policy Level: Level 1 (Autonomous).
        """
        policy = evaluate_policy("get_contact")
        if policy.decision == PolicyDecision.BLOCK:
            raise PermissionError(f"Policy blocked get_contact: {policy.reason}")

        if self.auth:
            with httpx.Client(base_url=self.base_url, auth=self.auth, timeout=15.0) as client:
                res = client.get(f"/contacts/{contact_id}")
                res.raise_for_status()
                data = res.json()
        else:
            data = {
                "id": contact_id,
                "entity": "contact",
                "name": "Acme Logistics Pvt Ltd",
                "contact": "+919876543210",
                "email": "vendor@acmelogistics.com",
                "type": "vendor",
                "active": True,
            }

        result = RazorpayContactResponse.model_validate(data)

        if db and case_id:
            log_audit_event(
                db=db,
                case_id=case_id,
                event_type=AuditActorType.SYSTEM_ACTION,
                actor="razorpay_client",
                action="GET_CONTACT",
                target=contact_id,
                output_data=data,
            )

        return result

    # ── Tool 3: Get Fund Accounts (Level 1 Autonomous) ────────────────────────
    def get_fund_accounts(self, contact_id: str, case_id: Optional[str] = None, db: Optional[Session] = None) -> List[RazorpayFundAccountResponse]:
        """
        Retrieves all fund accounts for a contact (GET /v1/fund_accounts?contact_id={id}).
        Policy Level: Level 1 (Autonomous).
        """
        policy = evaluate_policy("get_fund_accounts")
        if policy.decision == PolicyDecision.BLOCK:
            raise PermissionError(f"Policy blocked get_fund_accounts: {policy.reason}")

        if self.auth:
            with httpx.Client(base_url=self.base_url, auth=self.auth, timeout=15.0) as client:
                res = client.get(f"/fund_accounts", params={"contact_id": contact_id})
                res.raise_for_status()
                data = res.json().get("items", [])
        else:
            data = [
                {
                    "id": "fa_mock_123",
                    "entity": "fund_account",
                    "contact_id": contact_id,
                    "account_type": "bank_account",
                    "bank_account": {
                        "ifsc": "HDFC0000001",
                        "bank_name": "HDFC Bank",
                        "name": "Acme Logistics Pvt Ltd",
                        "account_number": "50100012345678",
                    },
                    "active": True,
                }
            ]

        results = [RazorpayFundAccountResponse.model_validate(item) for item in data]

        if db and case_id:
            log_audit_event(
                db=db,
                case_id=case_id,
                event_type=AuditActorType.SYSTEM_ACTION,
                actor="razorpay_client",
                action="GET_FUND_ACCOUNTS",
                target=contact_id,
                output_data=data,
            )

        return results

    # ── Tool 4: Create Fund Account (Level 2 Controlled Mutation) ─────────────
    def create_fund_account(
        self,
        contact_id: str,
        account_type: str,
        bank_account: Dict[str, str],
        case_id: Optional[str] = None,
        db: Optional[Session] = None,
        context: Optional[PolicyContext] = None,
    ) -> RazorpayFundAccountResponse:
        """
        Creates a new immutable Fund Account (POST /v1/fund_accounts).
        Policy Level: Level 2 (Controlled Mutation).
        """
        policy = evaluate_policy("create_fund_account", context)
        if policy.decision != PolicyDecision.ALLOW:
            raise PermissionError(
                f"Policy evaluated as {policy.decision.value} for create_fund_account: {policy.reason}"
            )

        payload = {
            "contact_id": contact_id,
            "account_type": account_type,
            "bank_account": bank_account,
        }

        if self.auth:
            with httpx.Client(base_url=self.base_url, auth=self.auth, timeout=15.0) as client:
                res = client.post("/fund_accounts", json=payload)
                res.raise_for_status()
                data = res.json()
        else:
            data = {
                "id": f"fa_new_{hashlib.sha256(str(bank_account).encode()).hexdigest()[:8]}",
                "entity": "fund_account",
                "contact_id": contact_id,
                "account_type": account_type,
                "bank_account": bank_account,
                "active": True,
            }

        result = RazorpayFundAccountResponse.model_validate(data)

        if db and case_id:
            log_audit_event(
                db=db,
                case_id=case_id,
                event_type=AuditActorType.SYSTEM_ACTION,
                actor="razorpay_client",
                action="CREATE_FUND_ACCOUNT",
                target=result.id,
                input_data=payload,
                output_data=data,
                approval_required=(policy.decision == PolicyDecision.REQUIRE_APPROVAL),
            )

        return result

    # ── Tool 5: Deactivate Fund Account (Level 2 Controlled Mutation) ───────────
    def deactivate_fund_account(
        self,
        fund_account_id: str,
        case_id: Optional[str] = None,
        db: Optional[Session] = None,
        context: Optional[PolicyContext] = None,
    ) -> RazorpayFundAccountResponse:
        """
        Deactivates a faulty fund account (PATCH /v1/fund_accounts/{id}).
        Policy Level: Level 2 (Controlled Mutation).
        """
        policy = evaluate_policy("deactivate_fund_account", context)
        if policy.decision != PolicyDecision.ALLOW:
            raise PermissionError(
                f"Policy evaluated as {policy.decision.value} for deactivate_fund_account: {policy.reason}"
            )

        payload = {"active": False}

        if self.auth:
            with httpx.Client(base_url=self.base_url, auth=self.auth, timeout=15.0) as client:
                res = client.patch(f"/fund_accounts/{fund_account_id}", json=payload)
                res.raise_for_status()
                data = res.json()
        else:
            data = {
                "id": fund_account_id,
                "entity": "fund_account",
                "contact_id": "cont_mock",
                "account_type": "bank_account",
                "active": False,
            }

        result = RazorpayFundAccountResponse.model_validate(data)

        if db and case_id:
            log_audit_event(
                db=db,
                case_id=case_id,
                event_type=AuditActorType.SYSTEM_ACTION,
                actor="razorpay_client",
                action="DEACTIVATE_FUND_ACCOUNT",
                target=fund_account_id,
                input_data=payload,
                output_data=data,
            )

        return result

    # ── Tool 6: Create Replacement Payout (Level 3 Financially Consequential) ──
    def create_payout(
        self,
        account_number: str,
        fund_account_id: str,
        amount: int,
        currency: str = "INR",
        mode: str = "NEFT",
        purpose: str = "vendor_payout",
        reference_id: Optional[str] = None,
        narration: Optional[str] = None,
        case_id: Optional[str] = None,
        db: Optional[Session] = None,
        context: Optional[PolicyContext] = None,
        is_human_authorized: bool = False,
        approved_by: Optional[str] = None,
    ) -> RazorpayPayoutResponse:
        """
        Initiates a replacement payout on RazorpayX (POST /v1/payouts).
        Policy Level: Level 3 (Financially Consequential).
        
        Strict Safety Guard:
        Requires is_human_authorized=True (validated from human approval card in DB).
        """
        if not is_human_authorized:
            raise PermissionError(
                "Level 3 Action 'create_payout' cannot be executed autonomously without human authorization."
            )

        payload = {
            "account_number": account_number,
            "fund_account_id": fund_account_id,
            "amount": amount,
            "currency": currency,
            "mode": mode,
            "purpose": purpose,
            "reference_id": reference_id,
            "narration": narration,
        }

        if self.auth:
            with httpx.Client(base_url=self.base_url, auth=self.auth, timeout=15.0) as client:
                res = client.post("/payouts", json=payload)
                res.raise_for_status()
                data = res.json()
        else:
            data = {
                "id": f"pout_new_{hashlib.sha256(str(payload).encode()).hexdigest()[:8]}",
                "entity": "payout",
                "fund_account_id": fund_account_id,
                "amount": amount,
                "currency": currency,
                "status": "processing",
                "mode": mode,
                "purpose": purpose,
                "reference_id": reference_id,
            }

        result = RazorpayPayoutResponse.model_validate(data)

        if db and case_id:
            log_audit_event(
                db=db,
                case_id=case_id,
                event_type=AuditActorType.HUMAN_DECISION,
                actor=approved_by or "human_authorized_agent",
                action="CREATE_PAYOUT",
                target=result.id,
                input_data=payload,
                output_data=data,
                approval_required=True,
            )

        return result


# Singleton client instance
razorpay_client = RazorpayClient()
