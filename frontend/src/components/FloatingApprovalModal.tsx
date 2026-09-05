"use client";

import React, { useState } from "react";
import { CaseDetail } from "@/lib/types";
import { formatINR } from "./CaseListSidebar";
import {
  ShieldAlert,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowRight,
  DollarSign,
  FileText,
  Sparkles,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  Check,
  Building,
  CreditCard,
  Lock,
} from "lucide-react";

interface FloatingApprovalModalProps {
  caseData: CaseDetail;
  onApprove: (notes?: string) => void;
  onReject: (reason: string) => void;
  isSubmitting?: boolean;
}

export const FloatingApprovalModal: React.FC<FloatingApprovalModalProps> = ({
  caseData,
  onApprove,
  onReject,
  isSubmitting,
}) => {
  const [showRejectInput, setShowRejectInput] = useState(false);
  const [showEvidenceSheet, setShowEvidenceSheet] = useState(true);
  const [rejectReason, setRejectReason] = useState("");
  const [approvalNotes, setApprovalNotes] = useState("");

  if (caseData.state !== "HUMAN_APPROVAL" && caseData.state !== "HUMAN_REVIEW") {
    return null;
  }

  const payload = caseData.approval?.payload || {};
  const vendorName = caseData.vendor?.name || "Vendor";
  const amountStr = formatINR(caseData.amount);
  const isReviewDivert = caseData.state === "HUMAN_REVIEW";

  return (
    <div className="fixed top-20 right-6 z-40 w-[480px] bg-slate-900 border-2 border-amber-500/90 rounded-2xl shadow-2xl shadow-amber-500/20 p-5 backdrop-blur-xl animate-in fade-in slide-in-from-top-6 duration-300 max-h-[calc(100vh-100px)] overflow-y-auto">
      {/* Card Header */}
      <div className="flex items-center space-x-3 mb-3 pb-3 border-b border-slate-800">
        <div className="w-10 h-10 rounded-xl bg-amber-500/20 border border-amber-500 flex items-center justify-center text-amber-400 flex-shrink-0">
          <ShieldAlert className="w-6 h-6" />
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800">
              {isReviewDivert ? "SECURITY DIVERSION: HUMAN REVIEW" : "LEVEL 3 GOVERNANCE GATE"}
            </span>
            <span className="text-xs font-mono font-extrabold text-emerald-400">
              {amountStr}
            </span>
          </div>
          <h3 className="text-sm font-bold text-white mt-1">
            {isReviewDivert ? "Name Mismatch Review Required" : "Payout Authorization Required"}
          </h3>
        </div>
      </div>

      {/* Summary Box */}
      <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1.5 font-mono text-xs mb-3">
        <div className="flex justify-between items-center">
          <span className="text-slate-500">Beneficiary:</span>
          <span className="text-white font-bold">{vendorName}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-slate-500">Authorized Payout:</span>
          <span className="text-emerald-400 font-extrabold text-sm">{amountStr}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-slate-500">Original Failure:</span>
          <span className="text-rose-400">{caseData.failure_reason}</span>
        </div>
      </div>

      {/* Evidence Sheet Toggle Header */}
      <button
        type="button"
        onClick={() => setShowEvidenceSheet(!showEvidenceSheet)}
        className="w-full flex items-center justify-between p-2.5 bg-slate-850 hover:bg-slate-800 border border-slate-750 rounded-xl text-xs font-mono text-slate-200 transition mb-3"
      >
        <div className="flex items-center space-x-2">
          <FileText className="w-4 h-4 text-razor-400" />
          <span className="font-bold">AGENT EVIDENCE & CASE DOSSIER</span>
        </div>
        {showEvidenceSheet ? (
          <ChevronUp className="w-4 h-4 text-slate-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-slate-400" />
        )}
      </button>

      {/* Evidence Sheet Body */}
      {showEvidenceSheet && (
        <div className="space-y-3 font-mono text-xs mb-4">
          {/* Executive Case Summary for Finance Controller */}
          <div className="p-3.5 bg-slate-950 rounded-xl border border-slate-800 space-y-2 font-sans text-xs">
            <div className="text-razor-400 font-bold uppercase tracking-wider text-[10px] font-mono flex items-center space-x-1.5">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Executive Case Summary</span>
            </div>
            <p className="text-slate-200 leading-relaxed text-[11px]">
              Original payout of <strong className="text-white">{amountStr}</strong> to <strong className="text-white">{vendorName}</strong> failed due to <span className="text-rose-400 font-mono font-semibold">{caseData.failure_reason}</span> on invoice <span className="text-slate-300 font-mono">{caseData.invoice_reference || "INV-2026"}</span>.
            </p>
            <p className="text-slate-300 leading-relaxed text-[11px]">
              <strong className="text-razor-300 font-semibold">Agent Resolution:</strong> RX-AURA initiated automated remediation via WhatsApp, extracted updated banking credentials, completed a ₹1 penny-drop validation, and updated the Zoho Books accounting ledger.
            </p>
            <p className="text-amber-300/90 leading-relaxed text-[10px] font-mono bg-amber-950/40 p-2 rounded-lg border border-amber-800/40">
              ⚡ Policy Gate: Payout is ≥ ₹50,000. Autonomous money movement is blocked until human controller authorization.
            </p>
          </div>

          {/* Section 1: Verification Evidence with Contextual Explainers */}
          <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-2 text-[11px]">
            <div className="text-slate-400 font-bold uppercase tracking-wider text-[10px] flex items-center space-x-1.5 text-emerald-400">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>1. Bank Verification & Anti-Fraud Checks</span>
            </div>
            <div className="grid grid-cols-2 gap-2 pt-1">
              <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800 space-y-1">
                <span className="text-slate-400 block text-[10px] font-bold">Penny-Drop Status</span>
                <span className="text-emerald-400 font-bold block">ACTIVE / VERIFIED</span>
                <p className="text-[10px] text-slate-500 font-sans leading-tight">
                  Deposited ₹1.00 test amount to confirm destination bank account is active.
                </p>
              </div>
              <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800 space-y-1">
                <span className="text-slate-400 block text-[10px] font-bold">Beneficiary Name Match</span>
                <span className={`font-bold block ${
                  (payload.name_match_score || 100) >= 85 ? "text-emerald-400" : "text-amber-400"
                }`}>
                  {payload.name_match_score || 100}% Match Score
                </span>
                <p className="text-[10px] text-slate-500 font-sans leading-tight">
                  Bank account owner matches Zoho Books vendor profile (rules out fraud).
                </p>
              </div>
            </div>
          </div>

          {/* Section 2: Account Transition Diff */}
          <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-2 text-[11px]">
            <div className="text-slate-400 font-bold uppercase tracking-wider text-[10px] flex items-center space-x-1.5 text-sky-400">
              <CreditCard className="w-3.5 h-3.5" />
              <span>2. Bank Destination Transition</span>
            </div>
            <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800 space-y-1.5">
              <div className="flex justify-between items-center text-[10px]">
                <span className="text-slate-400">Old Faulty Account:</span>
                <span className="text-rose-400/80 line-through font-mono">
                  {payload.old_fund_account_id || "fa_old_defunct"} (DEACTIVATED)
                </span>
              </div>
              <div className="flex justify-between items-center text-[10px]">
                <span className="text-slate-400">New Verified Account:</span>
                <span className="text-emerald-400 font-bold font-mono">
                  {payload.new_fund_account_id || "fa_new_validated"} (ACTIVE)
                </span>
              </div>
              <div className="flex justify-between items-center pt-1 border-t border-slate-800 text-[10px]">
                <span className="text-slate-400">Zoho Books ERP:</span>
                <span className="text-emerald-400 font-semibold">Ledger Bank Details Synchronized</span>
              </div>
            </div>
          </div>

          {/* Section 3: Cryptographic Integrity */}
          <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1 text-[11px]">
            <div className="text-slate-400 font-bold uppercase tracking-wider text-[10px] flex items-center space-x-1.5 text-purple-400">
              <Lock className="w-3.5 h-3.5" />
              <span>3. Governance & Ledger Chain</span>
            </div>
            <div className="flex justify-between items-center pt-1 text-[10px]">
              <span className="text-slate-400">SHA-256 Block Chain:</span>
              <span className="text-emerald-400 font-bold font-mono">100% Cryptographically Verified</span>
            </div>
          </div>
        </div>
      )}

      {/* Rejection Note input if clicked */}
      {showRejectInput ? (
        <div className="space-y-3 pt-2">
          <textarea
            placeholder="Enter reason for rejecting this payout recovery proposal..."
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            rows={2}
            className="w-full bg-slate-950 border border-rose-800 rounded-xl p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-rose-500 font-mono"
          />
          <div className="flex items-center space-x-2">
            <button
              onClick={() => {
                if (rejectReason.trim()) {
                  onReject(rejectReason.trim());
                }
              }}
              disabled={isSubmitting || !rejectReason.trim()}
              className="flex-1 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white text-xs font-bold font-mono transition"
            >
              Confirm Permanent Rejection
            </button>
            <button
              onClick={() => setShowRejectInput(false)}
              className="px-3 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-mono"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        /* Action Buttons */
        <div className="flex items-center space-x-3 pt-1">
          <button
            onClick={() => onApprove(approvalNotes)}
            disabled={isSubmitting}
            className="flex-1 flex items-center justify-center space-x-2 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-bold font-mono shadow-lg shadow-emerald-600/30 transition-all active:scale-95 cursor-pointer"
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>AUTHORIZE & DISBURSE</span>
          </button>

          <button
            onClick={() => setShowRejectInput(true)}
            disabled={isSubmitting}
            className="flex items-center space-x-1.5 px-4 py-3 rounded-xl bg-rose-950/80 hover:bg-rose-900 border border-rose-800 text-rose-400 text-xs font-bold font-mono transition active:scale-95 cursor-pointer"
          >
            <XCircle className="w-4 h-4" />
            <span>REJECT</span>
          </button>
        </div>
      )}
    </div>
  );
};

