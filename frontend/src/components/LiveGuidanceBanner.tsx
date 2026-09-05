"use client";

import React from "react";
import { CaseDetail } from "@/lib/types";
import { formatINR } from "./CaseListSidebar";
import {
  HelpCircle,
  ArrowRight,
  Bot,
  UserCheck,
  ShieldCheck,
  AlertTriangle,
  Sparkles,
  MessageSquare,
  Play,
  CheckCircle2,
  Lock,
  Zap,
} from "lucide-react";

interface LiveGuidanceBannerProps {
  caseData: CaseDetail;
  onRunStep: () => void;
  onRunAutoPlay: () => void;
  onSimulateVendorReply: (replyText: string) => void;
  onApprove: () => void;
  isProcessing: boolean;
  isAutoPlaying: boolean;
}

export const LiveGuidanceBanner: React.FC<LiveGuidanceBannerProps> = ({
  caseData,
  onRunStep,
  onRunAutoPlay,
  onSimulateVendorReply,
  onApprove,
  isProcessing,
  isAutoPlaying,
}) => {
  const state = caseData.state;
  const vendorName = caseData.vendor?.name || "the vendor";
  const invoiceRef = caseData.invoice_reference || "INV-2026-8801";
  const amountStr = formatINR(caseData.amount);

  // Generate clear, intuitive guidance for each state
  const getGuidance = () => {
    switch (state) {
      case "CASE_CREATED":
        return {
          stepBadge: "STEP 1 OF 5: INGESTION & DIAGNOSIS",
          badgeColor: "bg-blue-950 text-blue-400 border-blue-800",
          headline: "Payout failed at bank. Ready for autonomous AI investigation.",
          explanation: `Razorpay reported that a payout of ${amountStr} failed due to "${caseData.failure_reason}". The AI agent is ready to look up invoice ${invoiceRef} in Zoho Books and classify the root cause.`,
          actionPrompt: "Click 'Auto-Play Agent' to let the agent investigate and generate vendor outreach.",
          primaryAction: {
            label: "Auto-Play Agent",
            onClick: onRunAutoPlay,
            icon: Play,
            color: "bg-razor-600 hover:bg-razor-500 text-white",
          },
        };

      case "FAILURE_CLASSIFIED":
      case "RECOVERY_STRATEGY_SELECTED":
        if (caseData.recovery_strategy === "SCHEDULE_RETRY") {
          return {
            stepBadge: "STEP 2 OF 5: AUTOMATED RETRY QUEUED",
            badgeColor: "bg-blue-950 text-blue-400 border-blue-800",
            headline: "Beneficiary bank offline. Controlled retry scheduled with zero vendor contact.",
            actionPrompt: "Transient bank downtime detected. Gateway retry scheduled automatically.",
            primaryAction: null,
          };
        }
        if (caseData.recovery_strategy === "FINANCE_ESCALATION") {
          return {
            stepBadge: "STEP 2 OF 5: FINANCE ESCALATION ACTIVE",
            badgeColor: "bg-amber-950 text-amber-400 border-amber-800",
            headline: "Insufficient business balance. Escalation ticket dispatched to internal treasury.",
            actionPrompt: "Zoho Books finance ticket logged. Awaiting treasury balance replenishment.",
            primaryAction: null,
          };
        }
        if (caseData.recovery_strategy === "BLOCK" || caseData.failure_reason === "bank_account_frozen") {
          return {
            stepBadge: "SECURITY HARD BLOCK: TERMINAL",
            badgeColor: "bg-rose-950 text-rose-400 border-rose-800",
            headline: "Bank account flagged as frozen. Workflow aborted immediately.",
            actionPrompt: "Account permanently blocked to protect company funds. Zero payout disbursed.",
            primaryAction: null,
          };
        }
        return {
          stepBadge: "STEP 2 OF 5: ROOT CAUSE CLASSIFIED",
          badgeColor: "bg-indigo-950 text-indigo-400 border-indigo-800",
          headline: "Failure diagnosed as Vendor Remediation. Reaching out via WhatsApp.",
          explanation: `The agent confirmed the failure requires updated bank credentials from ${vendorName}. It is looking up Zoho Books contacts and composing a personalized WhatsApp message.`,
          actionPrompt: "Click 'Auto-Play Agent' to send WhatsApp outreach...",
          primaryAction: {
            label: "Step Next",
            onClick: onRunStep,
            icon: ArrowRight,
            color: "bg-slate-800 hover:bg-slate-700 text-white",
          },
        };

      case "VENDOR_CONTACTED":
        return {
          stepBadge: "STEP 3 OF 5: VENDOR OUTREACH DISPATCHED",
          badgeColor: "bg-amber-950 text-amber-400 border-amber-800",
          headline: "Agent reached out via WhatsApp. Awaiting vendor's reply.",
          explanation: `The AI agent drafted and sent a WhatsApp message asking ${vendorName} for corrected bank account details for invoice ${invoiceRef}. The agent is now paused awaiting their response.`,
          actionPrompt: "Simulate the vendor's WhatsApp reply by clicking below:",
          primaryAction: {
            label: "Send Valid Bank Details",
            onClick: () =>
              onSimulateVendorReply(
                `Hello, here are our updated banking details for ${invoiceRef}: Account 987654321098, IFSC HDFC0001234, Name: ${vendorName}.`
              ),
            icon: MessageSquare,
            color: "bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/30",
          },
        };

      case "INFORMATION_RECEIVED":
      case "DATA_VALIDATED":
        return {
          stepBadge: "STEP 4 OF 5: EXTRACTING & VALIDATING",
          badgeColor: "bg-purple-950 text-purple-400 border-purple-800",
          headline: "Vendor reply received. LLM extracting banking parameters.",
          explanation: `The AI agent parsed the message using LLM extraction, verified IFSC and Account Number regex formats, and is now running penny-drop account validation.`,
          actionPrompt: "Verifying account status and name match score...",
          primaryAction: {
            label: "Continue Flow",
            onClick: onRunStep,
            icon: ArrowRight,
            color: "bg-razor-600 hover:bg-razor-500 text-white",
          },
        };

      case "BANK_VALIDATED":
      case "POLICY_CHECK":
      case "PAYOUT_READY":
        return {
          stepBadge: "STEP 4 OF 5: CHECKS PASSED — STAGING PAYOUT",
          badgeColor: "bg-emerald-950 text-emerald-400 border-emerald-800",
          headline: "Penny-drop validation & policy checks passed successfully.",
          explanation: `Bank account verified as 'active' with a 100% name match score. Amount is within policy limits. Replacement payout is now staged for human controller authorization.`,
          actionPrompt: "Preparing final human approval card...",
          primaryAction: {
            label: "Stage Approval",
            onClick: onRunStep,
            icon: ArrowRight,
            color: "bg-razor-600 hover:bg-razor-500 text-white",
          },
        };

      case "HUMAN_APPROVAL":
        return {
          stepBadge: "STEP 5 OF 5: HUMAN AUTHORIZATION GATE",
          badgeColor: "bg-razor-950 text-razor-400 border-razor-800",
          headline: "All automated checks complete. Awaiting Finance Controller sign-off.",
          explanation: `By strict policy governance, AI never moves money autonomously. All diagnostics, validation scores, and replacement parameters are locked. A human must click Authorize.`,
          actionPrompt: "Review the approval card below and authorize the disbursement:",
          primaryAction: {
            label: `Authorize Payout (${amountStr})`,
            onClick: onApprove,
            icon: UserCheck,
            color: "bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/30",
          },
        };

      case "HUMAN_REVIEW":
        return {
          stepBadge: "SECURITY DIVERSION: HUMAN REVIEW",
          badgeColor: "bg-amber-950 text-amber-400 border-amber-800",
          headline: "Beneficiary name mismatch detected. Diverted to manual review.",
          explanation: `The name registered at the bank differed from the vendor profile (name match score < 85%). The agent safely halted to prevent potential fraud or impersonation.`,
          actionPrompt: "A finance controller must inspect the mismatch and manually approve or reject.",
          primaryAction: {
            label: "Authorize Despite Warning",
            onClick: onApprove,
            icon: ShieldCheck,
            color: "bg-amber-600 hover:bg-amber-500 text-white",
          },
        };

      case "PAYOUT_EXECUTED":
      case "CASE_RESOLVED":
        return {
          stepBadge: "WORKFLOW COMPLETE: CASE RESOLVED",
          badgeColor: "bg-emerald-950 text-emerald-400 border-emerald-800",
          headline: `Success! Replacement payout of ${amountStr} disbursed and confirmed.`,
          explanation: `Replacement payout successfully initiated on RazorpayX. Zoho Books accounting records updated. Complete SHA-256 cryptographic audit ledger verified 100% intact.`,
          actionPrompt: "Workflow complete. You can simulate another case from the top bar.",
          primaryAction: null,
        };

      case "BLOCKED":
        return {
          stepBadge: "SECURITY HARD BLOCK: TERMINAL",
          badgeColor: "bg-rose-950 text-rose-400 border-rose-800",
          headline: "Workflow permanently BLOCKED due to fatal account status.",
          explanation: `The bank account supplied by the vendor was identified as frozen or inactive. The deterministic state machine aborted the workflow to prevent loss of funds.`,
          actionPrompt: "Case is in terminal state. Zero funds were disbursed.",
          primaryAction: null,
        };

      default:
        return {
          stepBadge: "RECOVERY IN PROGRESS",
          badgeColor: "bg-slate-800 text-slate-300 border-slate-700",
          headline: `Current State: ${state}`,
          explanation: `The autonomous resolution agent is managing this case according to deterministic policy rules.`,
          actionPrompt: "Click step next to continue.",
          primaryAction: {
            label: "Step Next",
            onClick: onRunStep,
            icon: ArrowRight,
            color: "bg-razor-600 text-white",
          },
        };
    }
  };

  const guidance = getGuidance();
  const PrimaryIcon = guidance.primaryAction?.icon || ArrowRight;

  return (
    <div className="bg-slate-900/90 border-b border-slate-800 px-6 py-4 transition-all">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 p-4 rounded-xl bg-slate-950 border border-slate-800 shadow-inner">
        {/* Left Side: What is happening right now */}
        <div className="space-y-1.5 max-w-3xl font-mono">
          <div className="flex items-center space-x-2.5">
            <span
              className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border ${guidance.badgeColor}`}
            >
              {guidance.stepBadge}
            </span>
            <span className="text-xs font-bold text-white tracking-tight">
              {guidance.headline}
            </span>
          </div>

          <p className="text-[11px] text-razor-400 font-semibold">
            👉 {guidance.actionPrompt}
          </p>
        </div>

        {/* Right Side: Big Clear Action Button */}
        {guidance.primaryAction && (
          <div className="flex-shrink-0">
            <button
              onClick={guidance.primaryAction.onClick}
              disabled={isProcessing}
              className={`px-4 py-2.5 rounded-xl text-xs font-mono font-bold flex items-center space-x-2 transition shadow-lg active:scale-95 disabled:opacity-50 ${guidance.primaryAction.color}`}
            >
              {isProcessing || isAutoPlaying ? (
                <>
                  <Zap className="w-4 h-4 animate-spin" />
                  <span>Agent Working...</span>
                </>
              ) : (
                <>
                  <PrimaryIcon className="w-4 h-4" />
                  <span>{guidance.primaryAction.label}</span>
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
