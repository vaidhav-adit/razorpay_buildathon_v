"""
tests/test_classifier.py
────────────────────────
Unit tests for the deterministic failure classifier (Phase 3).

Tests:
1. Exact mapping of all known (source, reason) pairs to their defined RecoveryStrategy.
2. Case-insensitivity and whitespace trimming.
3. Fallback behavior on unmapped / unknown failure pairs.
4. Safe handling of None and empty inputs without raising exceptions.
5. Accuracy of flags (is_retryable, requires_vendor_contact, requires_human_attention).
"""

import pytest
from app.enums import RecoveryStrategy
from app.classifier import classify_failure, ClassificationResult, FAILURE_CLASSIFICATION_MAP


class TestFailureClassifierKnownMappings:
    """Tests all standard failure classifications defined in the architecture plan."""

    @pytest.mark.parametrize(
        "source,reason,expected_strategy,expected_retryable,expected_contact,expected_human",
        [
            # Beneficiary bank errors requiring vendor data correction
            ("beneficiary_bank", "invalid_ifsc_code", RecoveryStrategy.VENDOR_REMEDIATION, False, True, False),
            ("beneficiary_bank", "bank_account_closed", RecoveryStrategy.VENDOR_REMEDIATION, False, True, False),
            ("beneficiary_bank", "bank_account_invalid", RecoveryStrategy.VENDOR_REMEDIATION, False, True, False),

            # Beneficiary bank errors requiring human / compliance escalation
            ("beneficiary_bank", "bank_account_frozen", RecoveryStrategy.HUMAN_ESCALATION, False, False, True),

            # Transient beneficiary bank errors that can be retried
            ("beneficiary_bank", "beneficiary_bank_offline", RecoveryStrategy.SCHEDULE_RETRY, True, False, False),
            ("beneficiary_bank", "beneficiary_bank_technical_error", RecoveryStrategy.SCHEDULE_RETRY, True, False, False),
            ("beneficiary_bank", "npci_beneficiary_timeout", RecoveryStrategy.SCHEDULE_RETRY, True, False, False),

            # Mode errors requiring internal routing
            ("beneficiary_bank", "imps_not_allowed", RecoveryStrategy.INTERNAL_WORKFLOW, True, False, False),

            # Business errors requiring treasury / finance action
            ("business", "insufficient_funds", RecoveryStrategy.FINANCE_ESCALATION, False, False, True),

            # Gateway communication timeout
            ("gateway", "timeout", RecoveryStrategy.RETRY_LOGIC, True, False, False),

            # Account validation failures
            ("validation", "low_name_match", RecoveryStrategy.HUMAN_ESCALATION, False, False, True),
            ("validation", "inactive_account", RecoveryStrategy.BLOCK, False, False, True),
        ],
    )
    def test_known_mappings(
        self,
        source: str,
        reason: str,
        expected_strategy: RecoveryStrategy,
        expected_retryable: bool,
        expected_contact: bool,
        expected_human: bool,
    ):
        """Verify each known failure mapping yields correct strategy and operational flags."""
        result = classify_failure(source, reason)

        assert isinstance(result, ClassificationResult)
        assert result.strategy == expected_strategy
        assert result.source == source
        assert result.reason == reason
        assert result.is_retryable == expected_retryable
        assert result.requires_vendor_contact == expected_contact
        assert result.requires_human_attention == expected_human
        assert len(result.description) > 0
        assert len(result.suggested_action) > 0


class TestFailureClassifierNormalization:
    """Tests input sanitation, casing, and whitespace resilience."""

    def test_uppercase_inputs(self):
        """Should normalize UPPERCASE source and reason strings."""
        result = classify_failure("BENEFICIARY_BANK", "INVALID_IFSC_CODE")
        assert result.strategy == RecoveryStrategy.VENDOR_REMEDIATION
        assert result.source == "beneficiary_bank"
        assert result.reason == "invalid_ifsc_code"

    def test_mixed_case_with_whitespace(self):
        """Should strip whitespace and handle mixed case properly."""
        result = classify_failure("  Business  ", "  Insufficient_Funds  ")
        assert result.strategy == RecoveryStrategy.FINANCE_ESCALATION
        assert result.source == "business"
        assert result.reason == "insufficient_funds"


class TestFailureClassifierUnknownAndEdgeCases:
    """Tests resilience against unknown, unmapped, and null inputs."""

    def test_unknown_source_and_reason(self):
        """Unrecognized combinations must return UNKNOWN_FAILURE and escalate."""
        result = classify_failure("unknown_gateway", "alien_rejection_code_99")
        assert result.strategy == RecoveryStrategy.UNKNOWN_FAILURE
        assert result.requires_human_attention is True
        assert result.is_retryable is False
        assert result.requires_vendor_contact is False
        assert "Unrecognized payout failure reason" in result.description

    def test_known_source_but_unknown_reason(self):
        """Known source with new or unexpected reason code falls back cleanly."""
        result = classify_failure("beneficiary_bank", "unexpected_future_rbi_code")
        assert result.strategy == RecoveryStrategy.UNKNOWN_FAILURE
        assert result.requires_human_attention is True

    def test_none_inputs(self):
        """None inputs must not raise exceptions and return UNKNOWN_FAILURE."""
        result = classify_failure(None, None)
        assert result.strategy == RecoveryStrategy.UNKNOWN_FAILURE
        assert result.source == "unknown"
        assert result.reason == "unknown"
        assert result.requires_human_attention is True

    def test_empty_string_inputs(self):
        """Empty strings must safely normalize to 'unknown'."""
        result = classify_failure("", "   ")
        assert result.strategy == RecoveryStrategy.UNKNOWN_FAILURE
        assert result.source == "unknown"
        assert result.reason == "unknown"


class TestFailureClassifierCoverage:
    """Tests completeness and structure of the classification table."""

    def test_all_table_entries_are_valid(self):
        """Ensure all entries in FAILURE_CLASSIFICATION_MAP are well-formed."""
        for (src, rsn), meta in FAILURE_CLASSIFICATION_MAP.items():
            assert isinstance(src, str) and src == src.lower()
            assert isinstance(rsn, str) and rsn == rsn.lower()
            assert isinstance(meta["strategy"], RecoveryStrategy)
            assert isinstance(meta["is_retryable"], bool)
            assert isinstance(meta["requires_vendor_contact"], bool)
            assert isinstance(meta["requires_human_attention"], bool)
            assert isinstance(meta["description"], str)
            assert isinstance(meta["suggested_action"], str)
