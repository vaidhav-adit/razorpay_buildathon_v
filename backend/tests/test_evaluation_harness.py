"""
tests/test_evaluation_harness.py
─────────────────────────────────
Unit Tests & Benchmark Execution for the 10 Predefined Scenarios (Phase 12).

Tests:
1. All 10 benchmark scenarios individually covering the entire decision space.
2. The aggregate evaluation harness runner ensuring:
   - Diagnosis accuracy >= 95%
   - Strategy accuracy >= 95%
   - Policy compliance = 100%
   - Data extraction accuracy >= 95%
   - Unauthorized financial actions = 0 (Hard Invariant)
3. REST API endpoints:
   - GET /evaluation/scenarios
   - POST /evaluation/run
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.evaluation.scenarios import get_all_scenarios, get_scenario_by_id
from app.evaluation.harness import evaluation_harness


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client


# ─────────────────────────────────────────────────────────────────────────────
# 1. Scenario Definition Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestScenarioDefinitions:
    """Validates structure and completeness of the 10 benchmark scenarios."""

    def test_all_10_scenarios_exist(self):
        """Ensures all 10 required scenarios are defined."""
        scenarios = get_all_scenarios()
        assert len(scenarios) == 10
        scenario_ids = [s.scenario_id for s in scenarios]
        for i in range(1, 11):
            assert f"CASE-{i:03d}" in scenario_ids

    def test_lookup_scenario_by_id(self):
        """Ensures scenarios can be looked up by case ID."""
        s1 = get_scenario_by_id("CASE-001")
        assert s1 is not None
        assert s1.failure_reason == "invalid_ifsc_code"

        s_none = get_scenario_by_id("CASE-999")
        assert s_none is None


# ─────────────────────────────────────────────────────────────────────────────
# 2. Individual Scenario Benchmark Tests (All 10 Decision Paths)
# ─────────────────────────────────────────────────────────────────────────────

class TestBenchmarkScenarios:
    """Executes each of the 10 benchmark scenarios through the evaluation harness."""

    def test_case_001_golden_path_invalid_ifsc(self):
        """CASE 001: invalid_ifsc_code => vendor_remediation (golden path)."""
        s = get_scenario_by_id("CASE-001")
        res = evaluation_harness.run_scenario(s)
        assert res.passed is True
        assert res.diagnosis_correct is True
        assert res.strategy_correct is True
        assert res.final_state == "HUMAN_APPROVAL"
        assert res.unauthorized_financial_actions == 0
        assert res.audit_chain_verified is True

    def test_case_002_bank_account_closed(self):
        """CASE 002: bank_account_closed => vendor provides new account."""
        s = get_scenario_by_id("CASE-002")
        res = evaluation_harness.run_scenario(s)
        assert res.passed is True
        assert res.strategy_correct is True
        assert res.final_state == "HUMAN_APPROVAL"
        assert res.unauthorized_financial_actions == 0

    def test_case_003_bank_account_invalid(self):
        """CASE 003: bank_account_invalid => re-verification with vendor."""
        s = get_scenario_by_id("CASE-003")
        res = evaluation_harness.run_scenario(s)
        assert res.passed is True
        assert res.strategy_correct is True
        assert res.final_state == "HUMAN_APPROVAL"
        assert res.unauthorized_financial_actions == 0

    def test_case_004_beneficiary_bank_offline_retry(self):
        """CASE 004: beneficiary_bank_offline => controlled retry, 0 vendor contact."""
        s = get_scenario_by_id("CASE-004")
        res = evaluation_harness.run_scenario(s)
        assert res.passed is True
        assert res.strategy_selected == "SCHEDULE_RETRY"
        assert res.final_state == "RECOVERY_STRATEGY_SELECTED"
        assert res.unauthorized_financial_actions == 0

    def test_case_005_bank_technical_error_retry(self):
        """CASE 005: beneficiary_bank_technical_error => retry without vendor disturbance."""
        s = get_scenario_by_id("CASE-005")
        res = evaluation_harness.run_scenario(s)
        assert res.passed is True
        assert res.strategy_selected == "SCHEDULE_RETRY"
        assert res.final_state == "RECOVERY_STRATEGY_SELECTED"
        assert res.unauthorized_financial_actions == 0

    def test_case_006_insufficient_funds_internal_escalation(self):
        """CASE 006: insufficient_funds => internal finance escalation, 0 vendor contact."""
        s = get_scenario_by_id("CASE-006")
        res = evaluation_harness.run_scenario(s)
        assert res.passed is True
        assert res.strategy_selected == "FINANCE_ESCALATION"
        assert res.final_state == "ESCALATED"
        assert res.unauthorized_financial_actions == 0

    def test_case_007_low_name_match_human_review(self):
        """CASE 007: low name match score (< 85%) => human review triggered."""
        s = get_scenario_by_id("CASE-007")
        res = evaluation_harness.run_scenario(s)
        assert res.passed is True
        assert res.final_state == "HUMAN_REVIEW"
        assert res.unauthorized_financial_actions == 0

    def test_case_008_incomplete_vendor_details(self):
        """CASE 008: vendor omits IFSC code => syntax invalid, halts at INFORMATION_RECEIVED."""
        s = get_scenario_by_id("CASE-008")
        res = evaluation_harness.run_scenario(s)
        assert res.passed is True
        assert res.final_state == "INFORMATION_RECEIVED"
        assert res.unauthorized_financial_actions == 0

    def test_case_009_contradictory_vendor_details(self):
        """CASE 009: vendor sends contradictory/invalid details => halts safely."""
        s = get_scenario_by_id("CASE-009")
        res = evaluation_harness.run_scenario(s)
        assert res.passed is True
        assert res.final_state == "INFORMATION_RECEIVED"
        assert res.unauthorized_financial_actions == 0

    def test_case_010_frozen_account_immediate_block(self):
        """CASE 010: frozen/fraud account => immediately transitions to BLOCKED."""
        s = get_scenario_by_id("CASE-010")
        res = evaluation_harness.run_scenario(s)
        assert res.passed is True
        assert res.final_state == "BLOCKED"
        assert res.unauthorized_financial_actions == 0


# ─────────────────────────────────────────────────────────────────────────────
# 3. Full Benchmark Suite Execution & Metric Compliance
# ─────────────────────────────────────────────────────────────────────────────

class TestEvaluationHarnessAggregate:
    """Executes the full 10-scenario suite and asserts strict metric requirements."""

    def test_full_benchmark_run_and_all_targets_met(self):
        """
        Runs all 10 scenarios and verifies:
        - Diagnosis accuracy >= 95%
        - Strategy accuracy >= 95%
        - Policy compliance = 100%
        - Data extraction accuracy >= 95%
        - Unauthorized financial actions = 0 (HARD REQUIREMENT)
        - All 10 scenarios pass
        """
        report = evaluation_harness.run_all_scenarios()
        print("\n" + report.summary_table)

        assert report.total_scenarios == 10
        assert report.passed_scenarios == 10
        assert report.failed_scenarios == 0
        assert report.overall_pass_rate_percent == 100.0
        assert report.diagnosis_accuracy_percent >= 95.0
        assert report.strategy_accuracy_percent >= 95.0
        assert report.policy_compliance_percent == 100.0
        assert report.data_extraction_accuracy_percent >= 95.0
        assert report.unauthorized_financial_actions_count == 0
        assert report.all_targets_met is True


# ─────────────────────────────────────────────────────────────────────────────
# 4. Evaluation REST API Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestEvaluationAPI:
    """Validates the REST API endpoints for the evaluation harness."""

    def test_get_scenarios_endpoint(self, client):
        """GET /evaluation/scenarios returns all 10 scenarios."""
        res = client.get("/evaluation/scenarios")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 10
        assert data[0]["scenario_id"] == "CASE-001"

    def test_post_run_evaluation_single_scenario(self, client):
        """POST /evaluation/run?scenario_id=CASE-001 runs single scenario."""
        res = client.post("/evaluation/run?scenario_id=CASE-001")
        assert res.status_code == 200
        data = res.json()
        assert data["total_scenarios"] == 1
        assert data["passed_scenarios"] == 1
        assert data["unauthorized_financial_actions_count"] == 0
        assert data["results"][0]["scenario_id"] == "CASE-001"

    def test_post_run_evaluation_all_scenarios(self, client):
        """POST /evaluation/run runs all 10 benchmark scenarios."""
        res = client.post("/evaluation/run")
        assert res.status_code == 200
        data = res.json()
        assert data["total_scenarios"] == 10
        assert data["passed_scenarios"] == 10
        assert data["all_targets_met"] is True
        assert data["unauthorized_financial_actions_count"] == 0
