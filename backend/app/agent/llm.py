"""
agent/llm.py
────────────
LLM Provider Abstraction supporting Google Gemini (Free Tier), OpenAI, and Mock Simulator.

This module provides structured inference capabilities for:
1. Extracting structured banking credentials from conversational replies.
2. Generating personalized vendor remediation outreach messages.
3. Generating human-readable case summaries for the finance approval card.
"""

import os
import json
import re
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
import httpx

from app.config import settings
from app.agent.prompts import (
    AGENT_SYSTEM_PROMPT,
    VENDOR_OUTREACH_PROMPT,
    BANKING_EXTRACTION_SYSTEM_PROMPT,
)
from app.services.communication_adapter import extract_banking_details_from_text


# ─────────────────────────────────────────────────────────────────────────────
# Structured Extraction Schema
# ─────────────────────────────────────────────────────────────────────────────

class ExtractedBankingData(BaseModel):
    """Structured extraction of bank account information from vendor communication."""
    model_config = ConfigDict(extra="ignore")
    account_holder_name: Optional[str] = None
    account_number: Optional[str] = None
    ifsc: Optional[str] = None
    confidence: float = 1.0

    @property
    def is_valid(self) -> bool:
        """Returns True if account_number and ifsc are both present and valid."""
        if not self.account_number or not self.ifsc:
            return False
        # IFSC format: 4 alpha, '0', 6 alphanumeric
        ifsc_valid = bool(re.match(r"^[A-Z]{4}0[A-Z0-9]{6}$", self.ifsc.upper()))
        # Account number format: 9 to 18 digits
        acc_valid = bool(re.match(r"^\d{9,18}$", str(self.account_number).strip()))
        return ifsc_valid and acc_valid


# ─────────────────────────────────────────────────────────────────────────────
# LLM Client Provider
# ─────────────────────────────────────────────────────────────────────────────

class LLMClient:
    """
    LLM Client supporting Google Gemini, OpenAI, and deterministic Mock fallback.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
    ):
        self.provider = (provider or getattr(settings, "LLM_PROVIDER", "gemini")).lower()
        self.gemini_key = gemini_api_key or getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
        self.openai_key = openai_api_key or getattr(settings, "OPENAI_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")

    def generate_vendor_message(
        self,
        vendor_name: str,
        failure_reason: str,
        invoice_reference: Optional[str] = None,
        amount_paise: int = 0,
    ) -> str:
        """
        Generates a clear and polite payout failure remediation request to the vendor.
        """
        amount_inr = amount_paise / 100.0 if amount_paise else 0.0
        ref = invoice_reference or "Recent Invoice"
        friendly_reason = failure_reason.replace("_", " ").title()

        # If Gemini key configured, attempt generation
        if self.provider == "gemini" and self.gemini_key:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
                prompt_content = VENDOR_OUTREACH_PROMPT.format(
                    failure_reason=friendly_reason,
                    invoice_reference=ref,
                    vendor_name=vendor_name,
                    amount_inr=amount_inr,
                )
                payload = {
                    "contents": [{"parts": [{"text": prompt_content}]}],
                    "systemInstruction": {"parts": [{"text": AGENT_SYSTEM_PROMPT}]},
                }
                res = httpx.post(url, json=payload, timeout=10.0)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if text:
                            return text.strip()
            except Exception:
                pass

        # Deterministic template fallback
        return (
            f"Dear {vendor_name},\n\n"
            f"We attempted to process your payout for {ref} (INR {amount_inr:,.2f}), but the transaction failed "
            f"due to: {friendly_reason}.\n\n"
            f"To reprocess your payment without delay, please reply directly with your updated banking details:\n"
            f"- Registered Account Holder Name\n"
            f"- Bank Account Number\n"
            f"- 11-digit IFSC Code\n\n"
            f"Thank you,\nFinance Operations Team"
        )

    def extract_banking_data(self, message_text: str, default_name: Optional[str] = None) -> ExtractedBankingData:
        """
        Extracts structured banking details (name, account number, IFSC) from vendor text.
        """
        if not message_text:
            return ExtractedBankingData()

        # 1. Live Gemini / OpenAI extraction if configured
        if self.provider == "gemini" and self.gemini_key:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
                payload = {
                    "contents": [{"parts": [{"text": f"Extract banking data from this message:\n\n{message_text}"}]}],
                    "systemInstruction": {"parts": [{"text": BANKING_EXTRACTION_SYSTEM_PROMPT}]},
                    "generationConfig": {"response_mime_type": "application/json"},
                }
                res = httpx.post(url, json=payload, timeout=10.0)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        raw_json_str = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        parsed = json.loads(raw_json_str)
                        return ExtractedBankingData(
                            account_holder_name=parsed.get("account_holder_name") or default_name,
                            account_number=parsed.get("account_number"),
                            ifsc=parsed.get("ifsc"),
                            confidence=0.95,
                        )
            except Exception:
                pass

        # 2. Deterministic Regex / Heuristic Fallback
        heuristic = extract_banking_details_from_text(message_text)
        
        # Name heuristic extraction (if name is mentioned after 'name:' or 'holder:')
        extracted_name = default_name
        name_match = re.search(r"(?:name|holder|beneficiary)\s*[:=-]\s*([A-Za-z\s]+)", message_text, re.IGNORECASE)
        if name_match:
            candidate_name = name_match.group(1).split("\n")[0].strip()
            if len(candidate_name) > 3:
                extracted_name = candidate_name

        return ExtractedBankingData(
            account_holder_name=extracted_name,
            account_number=heuristic.get("account_number"),
            ifsc=heuristic.get("ifsc"),
            confidence=0.90 if (heuristic.get("ifsc") and heuristic.get("account_number")) else 0.50,
        )


# Singleton instance
llm_client = LLMClient()
