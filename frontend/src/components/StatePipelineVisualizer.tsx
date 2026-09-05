"use client";

import React from "react";
import { CaseDetail } from "@/lib/types";
import { formatINR } from "./CaseListSidebar";
import {
  Play,
  FastForward,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Sparkles,
  Bot,
  UserCheck,
  ShieldCheck,
  CreditCard,
  Building,
  Check,
  Pause,
} from "lucide-react";

interface StatePipelineVisualizerProps {
  caseData: CaseDetail;
  onRunStep: () => void;
  onRunAutoPlay: () => void;
  isAutoPlaying: boolean;
  isProcessing: boolean;
}

interface PipelineStep {
  key: string;
  label: string;
  sublabel: string;
  icon: React.ComponentType<{ className?: string }>;
  states: string[];
  toolHint?: string;
}

const PIPELINE_STEPS: PipelineStep[] = [
  {
    key: "genesis",
    label: "Failure Ingestion",
    sublabel: "Webhook Event",
    icon: CreditCard,
    states: ["CASE_CREATED"],
    toolHint: "webhook_ingest",
  },
  {
    key: "classify",
    label: "Root Diagnosis",
    sublabel: "Classification",
    icon: Bot,
    states: ["FAILURE_CLASSIFIED", "RECOVERY_STRATEGY_SELECTED"],
    toolHint: "classify_failure",
  },
  {
    key: "outreach",
    label: "Vendor Outreach",
    sublabel: "WhatsApp / Email",
    icon: Building,
    states: ["VENDOR_CONTACTED"],
    toolHint: "send_vendor_message",
  },
  {
    key: "extraction",
    label: "LLM Extraction",
    sublabel: "Syntax Check",
    icon: Sparkles,
    states: ["INFORMATION_RECEIVED", "DATA_VALIDATED"],
    toolHint: "extract_banking_data",
  },
  {
    key: "validation",
    label: "Penny-Drop",
    sublabel: "Account Validation",
    icon: ShieldCheck,
    states: ["BANK_VALIDATED"],
    toolHint: "validate_fund_account",
  },
  {
    key: "policy",
    label: "Policy Check",
    sublabel: "Limits & ERP",
    icon: ShieldCheck,
    states: ["POLICY_CHECK", "PAYOUT_READY"],
    toolHint: "evaluate_policy",
  },
  {
    key: "approval",
    label: "Human Gate",
    sublabel: "Controller Approval",
    icon: UserCheck,
    states: ["HUMAN_APPROVAL", "HUMAN_REVIEW"],
    toolHint: "human_approval_gate",
  },
  {
    key: "execution",
    label: "Replacement Payout",
    sublabel: "Money Disbursed",
    icon: CreditCard,
    states: ["PAYOUT_EXECUTED"],
    toolHint: "create_payout",
  },
  {
    key: "resolved",
    label: "Case Resolved",
    sublabel: "Audit Verified",
    icon: CheckCircle2,
    states: ["CASE_RESOLVED", "BLOCKED", "ESCALATED"],
    toolHint: "chain_verified",
  },
];

function getDynamicNarrative(state: string, caseData: CaseDetail) {
  const vendorName = caseData.vendor?.name || "Vendor";
  const amountStr = formatINR(caseData.amount);
  const failureReason = caseData.failure_reason;

  switch (state) {
    case "CASE_CREATED":
      return {
        status: "INVESTIGATION_INITIALIZED",
        text: `Payout failure of ${amountStr} to ${vendorName} ingested from Razorpay. RX-AURA is initializing root-cause diagnosis.`,
      };
    case "FAILURE_CLASSIFIED":
    case "RECOVERY_STRATEGY_SELECTED":
      return {
        status: "DIAGNOSIS_COMPLETE",
        text: `Root cause classified as '${failureReason}'. Autonomous recovery strategy '${caseData.recovery_strategy || "VENDOR_REMEDIATION"}' selected based on policy engine decision matrix.`,
      };
    case "VENDOR_CONTACTED":
      return {
        status: "OUTREACH_DISPATCHED",
        text: `Personalized remediation message composed and dispatched to ${vendorName} via WhatsApp. System is paused awaiting inbound vendor response.`,
      };
    case "INFORMATION_RECEIVED":
      return {
        status: "INBOUND_PARSED",
        text: `Inbound WhatsApp response received from ${vendorName}. LLM entity extraction successfully identified replacement banking parameters.`,
      };
    case "DATA_VALIDATED":
      return {
        status: "SYNTAX_VERIFIED",
        text: `Replacement account number and IFSC code passed deterministic regex syntax checksum. Provisioning replacement fund account on RazorpayX.`,
      };
    case "BANK_VALIDATED":
      return {
        status: "PENNY_DROP_CONFIRMED",
        text: `₹1.00 Penny-Drop test completed successfully. Account confirmed active with 100% legal beneficiary name match. Zero fraud indicators detected.`,
      };
    case "POLICY_CHECK":
    case "PAYOUT_READY":
      return {
        status: "POLICY_STAGED",
        text: `Old defunct fund account deactivated. Zoho Books ERP master records synchronized with verified bank destination. Replacement payout prepared.`,
      };
    case "HUMAN_APPROVAL":
    case "HUMAN_REVIEW":
      return {
        status: "GOVERNANCE_GATE_ACTIVE",
        text: `Automated recovery pipeline complete. By strict policy governance, payout of ${amountStr} (>= ₹50,000 ceiling) requires human finance controller authorization before money movement.`,
      };
    case "CASE_RESOLVED":
    case "PAYOUT_EXECUTED":
      return {
        status: "WORKFLOW_RESOLVED",
        text: `Finance controller authorized disbursement. Replacement payout of ${amountStr} successfully executed on RazorpayX. SHA-256 cryptographic audit ledger sealed and verified 100% intact.`,
      };
    case "ESCALATED":
      return {
        status: "FINANCE_ESCALATED",
        text: `Internal financial failure diagnosed. Escalation ticket dispatched to finance controller and treasury in Zoho Books. Case archived in ESCALATED queue with 0 vendor disturbance.`,
      };
    case "BLOCKED":
      return {
        status: "SECURITY_HARD_BLOCKED",
        text: `Workflow aborted and case permanently BLOCKED due to fatal bank account status or policy violation. Zero funds were disbursed.`,
      };
    default:
      return {
        status: "ACTIVE",
        text: `RX-AURA is managing exception recovery for ${vendorName} (${amountStr}).`,
      };
  }
}

export const StatePipelineVisualizer: React.FC<StatePipelineVisualizerProps> = ({
  caseData,
  onRunStep,
  onRunAutoPlay,
  isAutoPlaying,
  isProcessing,
}) => {
  const currentState = caseData.state;

  // Determine current active step index in the pipeline
  const currentStepIndex = PIPELINE_STEPS.findIndex((step) =>
    step.states.includes(currentState)
  );

  const isTerminal =
    currentState === "CASE_RESOLVED" ||
    currentState === "BLOCKED" ||
    currentState === "ESCALATED";

  const isAwaitingVendor = currentState === "VENDOR_CONTACTED";
  const isAwaitingApproval =
    currentState === "HUMAN_APPROVAL" || currentState === "HUMAN_REVIEW";

  const narrative = getDynamicNarrative(currentState, caseData);

  return (
    <div className="bg-slate-900 border-b border-slate-800 px-6 py-4">
      {/* Top Bar: Title & Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-razor-600/20 border border-razor-500/40 flex items-center justify-center text-razor-400 shadow-md shadow-razor-600/10">
            <Bot className="w-4 h-4 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-xs font-bold uppercase tracking-wider text-white font-mono">
                Autonomous State Machine Pipeline
              </h2>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                9 Deterministic Stages
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">
              Deterministic state progression with policy gates and SHA-256 audit hashing
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-2">
          {!isTerminal && (
            <>
              {/* Step Next Node Button */}
              <button
                onClick={onRunStep}
                disabled={isProcessing || isAutoPlaying || isAwaitingVendor || isAwaitingApproval}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 disabled:opacity-40 text-slate-200 border border-slate-700 text-xs font-mono font-medium transition active:scale-95"
                title="Execute single node transition"
              >
                <FastForward className="w-3.5 h-3.5 text-razor-400" />
                <span>Step Next (1-Step)</span>
              </button>

              {/* Auto-Play Paced Flow */}
              <button
                onClick={onRunAutoPlay}
                disabled={isProcessing || isAwaitingVendor || isAwaitingApproval}
                className={`flex items-center space-x-1.5 px-4 py-1.5 rounded-lg text-xs font-mono font-bold transition shadow-md ${
                  isAutoPlaying
                    ? "bg-amber-600 text-white shadow-amber-600/20"
                    : "bg-razor-600 hover:bg-razor-500 text-white shadow-razor-600/30"
                } disabled:opacity-40`}
              >
                {isAutoPlaying ? (
                  <>
                    <Pause className="w-3.5 h-3.5" />
                    <span>Pause Flow</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5" />
                    <span>Auto-Play Agent</span>
                  </>
                )}
              </button>
            </>
          )}

          {isAwaitingVendor && (
            <span className="flex items-center space-x-1.5 text-xs font-mono font-semibold px-3 py-1.5 rounded-lg bg-amber-950/80 border border-amber-500/60 text-amber-300">
              <Clock className="w-3.5 h-3.5 animate-spin" />
              <span>Awaiting Vendor Reply</span>
            </span>
          )}

          {isAwaitingApproval && (
            <span className="flex items-center space-x-1.5 text-xs font-mono font-semibold px-3 py-1.5 rounded-lg bg-razor-950 border border-razor-500 text-razor-300 animate-pulse">
              <UserCheck className="w-3.5 h-3.5" />
              <span>Human Approval Required</span>
            </span>
          )}
        </div>
      </div>

      {/* Visual Stepper Pipeline */}
      <div className="relative">
        <div className="grid grid-cols-3 md:grid-cols-9 gap-2">
          {PIPELINE_STEPS.map((step, idx) => {
            const Icon = step.icon;
            const isCompleted = currentStepIndex > idx || (currentStepIndex === idx && isTerminal);
            const isCurrent = currentStepIndex === idx && !isTerminal;

            return (
              <div
                key={step.key}
                className={`relative flex flex-col p-2.5 rounded-xl border transition-all duration-300 font-mono ${
                  isCurrent
                    ? "bg-razor-950/70 border-razor-500 shadow-lg shadow-razor-600/20 ring-1 ring-razor-500"
                    : isCompleted
                    ? "bg-slate-950/60 border-emerald-500/40 text-slate-300"
                    : "bg-slate-950/30 border-slate-850 text-slate-500 opacity-60"
                }`}
              >
                {/* Step Number & Icon */}
                <div className="flex items-center justify-between mb-1.5">
                  <span
                    className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                      isCurrent
                        ? "bg-razor-500 text-white animate-pulse"
                        : isCompleted
                        ? "bg-emerald-500 text-white"
                        : "bg-slate-800 text-slate-400"
                    }`}
                  >
                    {isCompleted ? <Check className="w-3 h-3" /> : idx + 1}
                  </span>

                  <Icon
                    className={`w-3.5 h-3.5 ${
                      isCurrent
                        ? "text-razor-400 animate-bounce"
                        : isCompleted
                        ? "text-emerald-400"
                        : "text-slate-600"
                    }`}
                  />
                </div>

                {/* Step Labels */}
                <div className="text-[11px] font-bold text-white leading-tight break-words">
                  {step.label}
                </div>
                <div className="text-[10px] text-slate-400 leading-tight break-words mt-0.5">
                  {step.sublabel}
                </div>

                {/* Tool Hint Badge */}
                {isCurrent && (
                  <div className="mt-1.5 text-[9px] uppercase tracking-tighter font-semibold px-1 py-0.5 rounded bg-razor-900/80 text-razor-300 border border-razor-700/60 leading-tight">
                    {step.toolHint}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Dynamic Narrative Case Summary & Resolution Dossier */}
      <div className="mt-4 p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 text-xs font-sans space-y-1.5">
        <div className="flex items-center justify-between font-mono text-[10px] font-bold uppercase tracking-wider text-slate-400">
          <div className="flex items-center space-x-1.5 text-razor-400">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Live Agent Reasoning & Case Brief</span>
          </div>
          <span className="text-slate-500 font-mono">
            {caseData.case_number} • {caseData.invoice_reference || "INV-2026"}
          </span>
        </div>
        <p className="text-slate-300 leading-relaxed text-[11px]">
          <strong className="text-white font-semibold">Incident:</strong> Payout of <strong className="text-white">{formatINR(caseData.amount)}</strong> to <strong className="text-white">{caseData.vendor?.name || "Vendor"}</strong> failed at bank (<span className="text-rose-400 font-mono font-semibold">{caseData.failure_reason}</span>).
        </p>
        <p className="text-slate-300 leading-relaxed text-[11px]">
          <strong className="text-razor-300 font-semibold font-mono text-[10px] uppercase mr-1">[{narrative.status}]</strong>
          {narrative.text}
        </p>
      </div>
    </div>
  );
};
