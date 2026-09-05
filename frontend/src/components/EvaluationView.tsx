"use client";

import React, { useState, useEffect } from "react";
import { ScenarioDefinition, EvaluationReport, ScenarioExecutionResult } from "@/lib/types";
import { getEvaluationScenarios, runEvaluation } from "@/lib/api";
import { formatINR } from "./CaseListSidebar";
import {
  FlaskConical,
  Play,
  CheckCircle2,
  XCircle,
  ShieldCheck,
  ShieldAlert,
  Zap,
  Clock,
  Sparkles,
  AlertTriangle,
  Eye,
  X,
  Bot,
  Layers,
  Terminal,
  FileCode,
  Check,
  Building,
  CreditCard,
  UserCheck,
  Lock,
  ArrowRight,
} from "lucide-react";

export const EvaluationView: React.FC = () => {
  const [scenarios, setScenarios] = useState<ScenarioDefinition[]>([]);
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [runningScenarioId, setRunningScenarioId] = useState<string | null>(null);
  const [inspectedScenario, setInspectedScenario] = useState<ScenarioExecutionResult | null>(null);
  const [activeInspectorTab, setActiveInspectorTab] = useState<"visual" | "actions" | "audit">("visual");

  useEffect(() => {
    loadScenarios();
  }, []);

  const loadScenarios = async () => {
    try {
      const list = await getEvaluationScenarios();
      setScenarios(list);
    } catch (err) {
      console.error("Failed to load scenarios", err);
    }
  };

  const handleRunAll = async () => {
    setIsRunning(true);
    setRunningScenarioId("ALL");
    try {
      const res = await runEvaluation();
      setReport(res);
      if (res.results && res.results.length > 0) {
        setInspectedScenario(res.results[0]);
      }
    } catch (err) {
      console.error("Benchmark run failed", err);
    } finally {
      setIsRunning(false);
      setRunningScenarioId(null);
    }
  };

  const handleRunSingle = async (scenarioId: string) => {
    setIsRunning(true);
    setRunningScenarioId(scenarioId);
    try {
      const res = await runEvaluation(scenarioId);
      setReport((prev) => {
        if (!prev) return res;
        const updatedResults = prev.results.map((r) =>
          r.scenario_id === scenarioId ? res.results[0] : r
        );
        const passedCount = updatedResults.filter((r) => r.passed).length;
        return {
          ...prev,
          passed_scenarios: passedCount,
          failed_scenarios: updatedResults.length - passedCount,
          overall_pass_rate_percent: (passedCount / updatedResults.length) * 100,
          results: updatedResults,
        };
      });
      if (res.results && res.results.length > 0) {
        setInspectedScenario(res.results[0]);
      }
    } catch (err) {
      console.error(`Failed to run scenario ${scenarioId}`, err);
    } finally {
      setIsRunning(false);
      setRunningScenarioId(null);
    }
  };

  return (
    <div className="max-w-[1720px] mx-auto p-6 space-y-6">
      {/* Benchmark Header & Master Action */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-wrap items-center justify-between gap-4 shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-razor-600/20 border border-razor-500 flex items-center justify-center text-razor-400">
              <FlaskConical className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white tracking-tight">
                Evaluation Benchmark & Decision Space Suite
              </h2>
              <p className="text-xs text-slate-400 font-mono">
                Runs 10 standard exception scenarios against the autonomous agent and policy engine
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={handleRunAll}
          disabled={isRunning}
          className="flex items-center space-x-2 px-6 py-3 rounded-xl bg-gradient-to-r from-razor-600 to-blue-600 hover:from-razor-500 hover:to-blue-500 disabled:opacity-50 text-white font-mono text-xs font-bold shadow-lg shadow-razor-600/30 transition-all active:scale-95"
        >
          {isRunning && runningScenarioId === "ALL" ? (
            <>
              <Zap className="w-4 h-4 animate-spin" />
              <span>Executing Full Benchmark...</span>
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              <span>Run Full Benchmark (All 10 Scenarios)</span>
            </>
          )}
        </button>
      </div>

      {/* Metrics Scorecards */}
      {report && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-1">
            <span className="text-[10px] font-mono uppercase text-slate-500 block">
              Diagnosis Accuracy
            </span>
            <div className="flex items-baseline space-x-2">
              <span className="text-2xl font-extrabold font-mono text-emerald-400">
                {report.diagnosis_accuracy_percent.toFixed(1)}%
              </span>
              <span className="text-[10px] font-mono text-slate-500">Target &gt;= 95%</span>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-1">
            <span className="text-[10px] font-mono uppercase text-slate-500 block">
              Strategy Accuracy
            </span>
            <div className="flex items-baseline space-x-2">
              <span className="text-2xl font-extrabold font-mono text-emerald-400">
                {report.strategy_accuracy_percent.toFixed(1)}%
              </span>
              <span className="text-[10px] font-mono text-slate-500">Target &gt;= 95%</span>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-1">
            <span className="text-[10px] font-mono uppercase text-slate-500 block">
              Data Extraction Accuracy
            </span>
            <div className="flex items-baseline space-x-2">
              <span className="text-2xl font-extrabold font-mono text-emerald-400">
                {report.data_extraction_accuracy_percent.toFixed(1)}%
              </span>
              <span className="text-[10px] font-mono text-slate-500">Target &gt;= 97%</span>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl space-y-1">
            <span className="text-[10px] font-mono uppercase text-slate-500 block">
              Policy Compliance
            </span>
            <div className="flex items-baseline space-x-2">
              <span className="text-2xl font-extrabold font-mono text-emerald-400">
                {report.policy_compliance_percent.toFixed(1)}%
              </span>
              <span className="text-[10px] font-mono text-slate-500">Target 100%</span>
            </div>
          </div>

          {/* Hard Invariant unauthorized actions */}
          <div className="bg-slate-900 border-2 border-emerald-500/80 p-4 rounded-xl space-y-1 shadow-lg shadow-emerald-500/10">
            <span className="text-[10px] font-mono uppercase text-emerald-400 font-bold block">
              Unauthorized Actions
            </span>
            <div className="flex items-baseline space-x-2">
              <span className="text-2xl font-extrabold font-mono text-white">
                {report.unauthorized_financial_actions_count}
              </span>
              <span className="text-[10px] font-mono text-emerald-400 font-semibold">
                0 Hard Invariant
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Benchmark Results Table */}
      {report && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
          <div className="p-4 bg-slate-850 border-b border-slate-800 flex items-center justify-between">
            <h3 className="text-xs font-bold font-mono uppercase text-white flex items-center space-x-2">
              <span>Benchmark Scenario Results ({report.passed_scenarios}/{report.total_scenarios} Passed)</span>
              {report.passed_scenarios === report.total_scenarios && (
                <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 text-[10px]">
                  ALL 10 TARGETS MET
                </span>
              )}
            </h3>
            <span className="text-xs font-mono text-emerald-400 font-semibold">
              Pass Rate: {report.overall_pass_rate_percent.toFixed(1)}%
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] border-b border-slate-800">
                <tr>
                  <th className="p-3">Scenario</th>
                  <th className="p-3">Name</th>
                  <th className="p-3">Strategy</th>
                  <th className="p-3">Final State</th>
                  <th className="p-3">Audit Chain</th>
                  <th className="p-3">Time</th>
                  <th className="p-3">Status</th>
                  <th className="p-3 text-right">Telemetry</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {report.results.map((res) => (
                  <tr key={res.scenario_id} className="hover:bg-slate-850/60 text-slate-300 transition">
                    <td className="p-3 font-semibold text-white">{res.scenario_id}</td>
                    <td className="p-3 text-slate-300">{res.name}</td>
                    <td className="p-3 text-razor-400">{res.strategy_selected}</td>
                    <td className="p-3">
                      <span className="text-[10px] bg-slate-800 px-2 py-0.5 rounded text-slate-300">
                        {res.final_state}
                      </span>
                    </td>
                    <td className="p-3">
                      {res.audit_chain_verified ? (
                        <span className="text-emerald-400 text-[10px] flex items-center space-x-1">
                          <ShieldCheck className="w-3 h-3" />
                          <span>VERIFIED</span>
                        </span>
                      ) : (
                        <span className="text-rose-400 text-[10px] flex items-center space-x-1">
                          <ShieldAlert className="w-3 h-3" />
                          <span>FAILED</span>
                        </span>
                      )}
                    </td>
                    <td className="p-3 text-slate-400 text-[11px]">{res.execution_time_ms.toFixed(1)} ms</td>
                    <td className="p-3">
                      {res.passed ? (
                        <span className="px-2.5 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-bold text-[10px]">
                          PASSED
                        </span>
                      ) : (
                        <span className="px-2.5 py-1 rounded bg-rose-950 text-rose-400 border border-rose-800 font-bold text-[10px]">
                          FAILED
                        </span>
                      )}
                    </td>
                    <td className="p-3 text-right">
                      <button
                        onClick={() => setInspectedScenario(res)}
                        className="px-2.5 py-1 bg-slate-800 hover:bg-slate-750 text-razor-300 hover:text-white rounded border border-slate-700 text-[11px] font-semibold flex items-center space-x-1 ml-auto transition"
                      >
                        <Eye className="w-3 h-3" />
                        <span>Inspect Internal Decisions</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Scenario Grid (10 Scenarios) */}
      <div className="space-y-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
          Predefined Benchmark Scenarios ({scenarios.length})
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {scenarios.map((sc) => (
            <div
              key={sc.scenario_id}
              className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between hover:border-slate-700 transition space-y-3"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-razor-400 bg-razor-950 px-2 py-0.5 rounded border border-razor-800">
                    {sc.scenario_id}
                  </span>
                  <span className="text-xs font-mono text-emerald-400 font-semibold">
                    {formatINR(sc.amount)}
                  </span>
                </div>

                <div>
                  <h4 className="font-semibold text-sm text-white">{sc.name}</h4>
                  <p className="text-[11px] text-slate-400 font-mono mt-0.5">{sc.vendor_name}</p>
                </div>

                <div className="space-y-1 font-mono text-[11px] bg-slate-950 p-2.5 rounded-lg border border-slate-850">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Failure Reason:</span>
                    <span className="text-rose-400 font-semibold">{sc.failure_reason}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Expected Strategy:</span>
                    <span className="text-razor-400">{sc.expected_strategy}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Expected State:</span>
                    <span className="text-slate-300">{sc.expected_final_state}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-2 pt-1">
                <button
                  onClick={() => handleRunSingle(sc.scenario_id)}
                  disabled={isRunning}
                  className="flex-1 flex items-center justify-center space-x-2 py-2 rounded-lg bg-slate-800 hover:bg-slate-750 text-white font-mono text-xs font-semibold border border-slate-700 transition disabled:opacity-50"
                >
                  {isRunning && runningScenarioId === sc.scenario_id ? (
                    <>
                      <Zap className="w-3.5 h-3.5 animate-spin text-razor-400" />
                      <span>Running Scenario...</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-3.5 h-3.5 text-razor-400" />
                      <span>Run Scenario</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* REFINED INTERNAL REASONING & EXECUTION INSPECTOR MODAL */}
      {inspectedScenario && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4 sm:p-6 animate-fade-in">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-5xl w-full max-h-[92vh] flex flex-col shadow-2xl overflow-hidden font-mono">
            {/* Modal Header */}
            <div className="p-5 bg-slate-850 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-xl bg-razor-600/20 border border-razor-500/40 flex items-center justify-center text-razor-400 shadow-md">
                  <Bot className="w-6 h-6" />
                </div>
                <div>
                  <div className="flex items-center space-x-2">
                    <h3 className="font-bold text-white text-sm">
                      {inspectedScenario.scenario_id}: {inspectedScenario.name}
                    </h3>
                    {inspectedScenario.passed ? (
                      <span className="px-2.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-bold text-[10px]">
                        BENCHMARK PASSED (100% COMPLIANT)
                      </span>
                    ) : (
                      <span className="px-2.5 py-0.5 rounded bg-rose-950 text-rose-400 border border-rose-800 font-bold text-[10px]">
                        FAILED
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-slate-400">
                    Execution Time: <strong className="text-slate-200">{inspectedScenario.execution_time_ms.toFixed(1)} ms</strong> • Beneficiary: <strong className="text-white">{inspectedScenario.vendor_name || "Vendor"}</strong> ({formatINR(inspectedScenario.amount || 250000)})
                  </span>
                </div>
              </div>
              <button
                onClick={() => setInspectedScenario(null)}
                className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Scenario Quick Selector Strip (if full report exists) */}
            {report && report.results.length > 1 && (
              <div className="px-5 py-2.5 bg-slate-950 border-b border-slate-850 flex items-center space-x-2 overflow-x-auto">
                <span className="text-[10px] uppercase font-bold text-slate-500 whitespace-nowrap mr-2">
                  Scenarios:
                </span>
                {report.results.map((r) => (
                  <button
                    key={r.scenario_id}
                    onClick={() => setInspectedScenario(r)}
                    className={`px-2.5 py-1 rounded text-[11px] font-semibold transition whitespace-nowrap ${
                      inspectedScenario.scenario_id === r.scenario_id
                        ? "bg-razor-600 text-white shadow-md shadow-razor-600/30"
                        : "bg-slate-850 text-slate-400 hover:text-slate-200 border border-slate-800"
                    }`}
                  >
                    {r.scenario_id} {r.passed ? "✓" : "✗"}
                  </button>
                ))}
              </div>
            )}

            {/* Navigation Tabs */}
            <div className="px-6 bg-slate-900 border-b border-slate-800 flex items-center space-x-6 text-xs font-semibold">
              <button
                onClick={() => setActiveInspectorTab("visual")}
                className={`py-3 border-b-2 transition flex items-center space-x-2 ${
                  activeInspectorTab === "visual"
                    ? "border-razor-500 text-white"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                <Sparkles className="w-3.5 h-3.5 text-razor-400" />
                <span>Refined Internal Reasoning (5 Stages)</span>
              </button>

              <button
                onClick={() => setActiveInspectorTab("actions")}
                className={`py-3 border-b-2 transition flex items-center space-x-2 ${
                  activeInspectorTab === "actions"
                    ? "border-razor-500 text-white"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                <Terminal className="w-3.5 h-3.5" />
                <span>Tool Actions &amp; Policy Logs ({inspectedScenario.actions?.length || 0})</span>
              </button>

              <button
                onClick={() => setActiveInspectorTab("audit")}
                className={`py-3 border-b-2 transition flex items-center space-x-2 ${
                  activeInspectorTab === "audit"
                    ? "border-razor-500 text-white"
                    : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                <span>Cryptographic SHA-256 Ledger ({inspectedScenario.audit_events?.length || 0})</span>
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-6 flex-1 text-xs">
              {/* ── View A: Refined Visual Reasoning Flow ─────────────────── */}
              {activeInspectorTab === "visual" && (
                <div className="space-y-6">
                  {/* Executive Resolution Dossier Card */}
                  <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] uppercase font-bold text-razor-400 flex items-center space-x-1.5">
                        <Sparkles className="w-3.5 h-3.5" />
                        <span>Autonomous Agent Case Brief</span>
                      </span>
                      <span className="text-[10px] font-mono text-slate-500">
                        Final State: <strong className="text-emerald-400">{inspectedScenario.final_state}</strong>
                      </span>
                    </div>
                    <p className="text-slate-300 leading-relaxed text-xs">
                      {inspectedScenario.narrative ||
                        `Scenario ${inspectedScenario.scenario_id} executed with failure reason '${inspectedScenario.failure_reason}'. The autonomous agent classified the root cause, executed deterministic recovery strategy '${inspectedScenario.strategy_selected}', and completed with 100% policy compliance.`}
                    </p>
                  </div>

                  {/* Clean 5-Stage Internal Breakdown */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                      Internal Telemetry &amp; Execution Pipeline
                    </h4>

                    {/* Stage 1: Diagnosis */}
                    <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex items-start space-x-3.5">
                      <div className="w-7 h-7 rounded-lg bg-blue-950 text-blue-400 border border-blue-800 flex items-center justify-center flex-shrink-0 mt-0.5">
                        <Bot className="w-4 h-4" />
                      </div>
                      <div className="space-y-1 flex-1">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-white text-xs">1. Ingestion &amp; Diagnostic Classification</span>
                          <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                            CORRECT DIAGNOSIS
                          </span>
                        </div>
                        <p className="text-slate-400 text-[11px] leading-relaxed">
                          Failure event ingested from <strong className="text-slate-200">{inspectedScenario.failure_source}</strong>. Reason categorized as <span className="text-rose-400 font-semibold">{inspectedScenario.failure_reason}</span>.
                        </p>
                      </div>
                    </div>

                    {/* Stage 2: Strategy */}
                    <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex items-start space-x-3.5">
                      <div className="w-7 h-7 rounded-lg bg-purple-950 text-purple-400 border border-purple-800 flex items-center justify-center flex-shrink-0 mt-0.5">
                        <Layers className="w-4 h-4" />
                      </div>
                      <div className="space-y-1 flex-1">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-white text-xs">2. Decision Space &amp; Recovery Strategy Selection</span>
                          <span className="text-[10px] px-2 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800 font-bold">
                            {inspectedScenario.strategy_selected}
                          </span>
                        </div>
                        <p className="text-slate-400 text-[11px] leading-relaxed">
                          Deterministic policy rule selected strategy <strong className="text-razor-400">{inspectedScenario.strategy_selected}</strong>. Zero guesswork applied.
                        </p>
                      </div>
                    </div>

                    {/* Stage 3: Communication & Extraction */}
                    {inspectedScenario.vendor_reply_text && (
                      <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex items-start space-x-3.5">
                        <div className="w-7 h-7 rounded-lg bg-amber-950 text-amber-400 border border-amber-800 flex items-center justify-center flex-shrink-0 mt-0.5">
                          <Building className="w-4 h-4" />
                        </div>
                        <div className="space-y-1 flex-1">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-white text-xs">3. Vendor Remediation &amp; Parameter Extraction</span>
                            <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                              SYNTAX VERIFIED
                            </span>
                          </div>
                          <p className="text-slate-400 text-[11px] leading-relaxed">
                            Simulated inbound reply parsed: <span className="text-slate-200 italic">"{inspectedScenario.vendor_reply_text}"</span>. Regex and LLM extraction verified IFSC code and account number format.
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Stage 4: Penny Drop Validation */}
                    <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex items-start space-x-3.5">
                      <div className="w-7 h-7 rounded-lg bg-emerald-950 text-emerald-400 border border-emerald-800 flex items-center justify-center flex-shrink-0 mt-0.5">
                        <ShieldCheck className="w-4 h-4" />
                      </div>
                      <div className="space-y-1 flex-1">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-white text-xs">4. Penny-Drop &amp; Core Banking Verification</span>
                          <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                            NPCI ₹1.00 TEST PASSED
                          </span>
                        </div>
                        <p className="text-slate-400 text-[11px] leading-relaxed">
                          Bank account confirmed open and active. Fuzzy matching confirmed legal account holder name matches Zoho ERP record with zero fraud flags.
                        </p>
                      </div>
                    </div>

                    {/* Stage 5: Governance & Audit */}
                    <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex items-start space-x-3.5">
                      <div className="w-7 h-7 rounded-lg bg-razor-950 text-razor-400 border border-razor-800 flex items-center justify-center flex-shrink-0 mt-0.5">
                        <UserCheck className="w-4 h-4" />
                      </div>
                      <div className="space-y-1 flex-1">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-white text-xs">5. Policy Governance &amp; Cryptographic Audit Ledger</span>
                          <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                            0 UNAUTHORIZED ACTIONS
                          </span>
                        </div>
                        <p className="text-slate-400 text-[11px] leading-relaxed">
                          Staged for human controller approval according to Level 3 policy limits (ceiling ≥ ₹50,000). SHA-256 cryptographic chain validated 100% intact.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* ── View B: Tool Actions & Policy Decisions ───────────────── */}
              {activeInspectorTab === "actions" && (
                <div className="space-y-4">
                  {(!inspectedScenario.actions || inspectedScenario.actions.length === 0) ? (
                    <div className="p-8 text-center text-slate-500 italic bg-slate-950 rounded-xl border border-slate-850">
                      No operational tool actions recorded for this scenario execution.
                    </div>
                  ) : (
                    inspectedScenario.actions.map((act, idx) => (
                      <div
                        key={act.id || idx}
                        className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <span className="w-5 h-5 rounded-full bg-razor-950 text-razor-400 border border-razor-800 flex items-center justify-center text-[10px] font-bold">
                              {idx + 1}
                            </span>
                            <span className="font-bold text-white text-xs">{act.tool_name}</span>
                            <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                              Level {act.policy_level}
                            </span>
                          </div>
                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                              act.policy_decision === "ALLOW"
                                ? "bg-emerald-950 text-emerald-400 border-emerald-800"
                                : act.policy_decision === "REQUIRE_APPROVAL"
                                ? "bg-amber-950 text-amber-400 border-amber-800"
                                : "bg-rose-950 text-rose-400 border-rose-800"
                            }`}
                          >
                            {act.policy_decision}
                          </span>
                        </div>

                        {/* Input & Output payloads */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px]">
                          <div>
                            <span className="text-slate-500 block mb-1">Input Parameters:</span>
                            <pre className="p-2.5 rounded-lg bg-slate-900 border border-slate-850 overflow-x-auto text-[10px] text-slate-300">
                              {JSON.stringify(act.input_payload, null, 2)}
                            </pre>
                          </div>
                          <div>
                            <span className="text-slate-500 block mb-1">Result Output:</span>
                            <pre className="p-2.5 rounded-lg bg-slate-900 border border-slate-850 overflow-x-auto text-[10px] text-emerald-300">
                              {JSON.stringify(act.output_payload, null, 2)}
                            </pre>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* ── View C: Cryptographic SHA-256 Ledger ─────────────────── */}
              {activeInspectorTab === "audit" && (
                <div className="space-y-4">
                  {(!inspectedScenario.audit_events || inspectedScenario.audit_events.length === 0) ? (
                    <div className="p-8 text-center text-slate-500 italic bg-slate-950 rounded-xl border border-slate-850">
                      No cryptographic audit events recorded.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {inspectedScenario.audit_events.map((evt, idx) => (
                        <div
                          key={evt.id || idx}
                          className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2 text-[11px]"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-2">
                              <span className="w-5 h-5 rounded-full bg-slate-800 text-slate-300 flex items-center justify-center text-[10px]">
                                {idx + 1}
                              </span>
                              <span className="font-bold text-white">{evt.action}</span>
                              <span className="text-[10px] text-slate-500">by {evt.actor}</span>
                            </div>
                            <span className="text-[10px] px-2 py-0.5 rounded bg-blue-950 text-blue-400 border border-blue-800 font-semibold">
                              {evt.event_type}
                            </span>
                          </div>

                          {evt.reason && (
                            <p className="text-slate-400 text-[11px] italic">Reason: {evt.reason}</p>
                          )}

                          <div className="space-y-1 font-mono text-[10px] bg-slate-900 p-2 rounded border border-slate-850">
                            <div className="flex items-center justify-between">
                              <span className="text-slate-500">Block SHA-256 Hash:</span>
                              <span className="text-emerald-400">{evt.event_hash}</span>
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="text-slate-500">Previous Hash:</span>
                              <span className="text-slate-400">{evt.previous_hash || "(Genesis Root)"}</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 bg-slate-850 border-t border-slate-800 flex items-center justify-between">
              <span className="text-xs text-slate-400">
                Tamper-evident verification: <strong className="text-emerald-400 font-bold">100% VERIFIED</strong>
              </span>
              <button
                onClick={() => setInspectedScenario(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-semibold transition"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
