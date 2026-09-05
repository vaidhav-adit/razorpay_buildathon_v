"""
api/evaluation.py
─────────────────
Evaluation Benchmark & Test Launcher API (Phase 12).

Exposes:
  POST /evaluation/run        — Executes the benchmark evaluation suite and returns metrics.
  GET  /evaluation/scenarios  — Returns the 10 predefined evaluation test scenario definitions.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel

from app.evaluation.scenarios import get_all_scenarios, get_scenario_by_id, ScenarioDefinition
from app.evaluation.harness import evaluation_harness, EvaluationReport, ScenarioExecutionResult

router = APIRouter(prefix="/evaluation", tags=["Evaluation Benchmark"])


class RunEvaluationRequest(BaseModel):
    scenario_id: Optional[str] = None


@router.post("/run", response_model=EvaluationReport, status_code=status.HTTP_200_OK)
def run_evaluation_benchmark(
    payload: Optional[RunEvaluationRequest] = None,
    scenario_id: Optional[str] = Query(None, description="Optional ID of a specific scenario to run (e.g. 'CASE-001')"),
):
    """
    Executes the benchmark evaluation harness.
    
    If scenario_id is provided, runs only that specific scenario.
    Otherwise, runs all 10 standard evaluation scenarios and compiles the benchmark report.
    """
    target_id = scenario_id or (payload.scenario_id if payload else None)

    if target_id:
        scenario = get_scenario_by_id(target_id)
        if not scenario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scenario with ID '{target_id}' not found.",
            )
        single_result = evaluation_harness.run_scenario(scenario)
        report = EvaluationReport(
            timestamp=datetime.now(),
            total_scenarios=1,
            passed_scenarios=1 if single_result.passed else 0,
            failed_scenarios=0 if single_result.passed else 1,
            overall_pass_rate_percent=100.0 if single_result.passed else 0.0,
            diagnosis_accuracy_percent=100.0 if single_result.diagnosis_correct else 0.0,
            strategy_accuracy_percent=100.0 if single_result.strategy_correct else 0.0,
            policy_compliance_percent=100.0 if single_result.policy_compliant else 0.0,
            data_extraction_accuracy_percent=100.0 if single_result.data_extraction_correct else 0.0,
            unauthorized_financial_actions_count=single_result.unauthorized_financial_actions,
            all_targets_met=single_result.passed,
            results=[single_result],
            summary_table=evaluation_harness._format_ascii_table(
                [single_result],
                100.0 if single_result.diagnosis_correct else 0.0,
                100.0 if single_result.strategy_correct else 0.0,
                100.0 if single_result.policy_compliant else 0.0,
                100.0 if single_result.data_extraction_correct else 0.0,
                single_result.unauthorized_financial_actions,
            ),
        )
        return report

    return evaluation_harness.run_all_scenarios()


@router.get("/scenarios", response_model=List[ScenarioDefinition], status_code=status.HTTP_200_OK)
def list_evaluation_scenarios():
    """
    Returns the metadata and parameters for all 10 predefined benchmark evaluation scenarios.
    """
    return get_all_scenarios()
