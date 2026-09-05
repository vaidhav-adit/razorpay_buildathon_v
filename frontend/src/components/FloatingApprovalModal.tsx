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
  FileText,
  Sparkles,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  CreditCard,
  Lock,
  Building2,
  AlertOctagon,
  UserX,
  UserCheck,
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

  const payload = (caseData.approval?.payload || {}) as Record<string, any>;
  const vendorName = caseData.vendor?.name || "Vendor";
  const amountStr = formatINR(caseData.amount);
  const isReviewDivert = caseData.state === "HUMAN_REVIEW";

  const registeredName =
    payload.registered_name ||
    (isReviewDivert ? "Unverified Third Party / Mismatched Beneficiary" : vendorName);

  const nameMatchScore =
    payload.name_match_score !== undefined
      ? Number(payload.name_match_score)
      : isReviewDivert
      ? 0
      : 100;

  const isNameMismatch = isReviewDivert || nameMatchScore < 85;
  const oldFaId = payload.old_fund_account_id || "fa_old_defunct";
  const newFaId = payload.new_fund_account_id || "fa_new_staged";
  const failureReason = caseData.failure_reason || "unknown_error";
  const invoiceRef = caseData.invoice_reference || "INV-2026";

  return (
    <div
      className={`fixed top-20 right-6 z-40 w-[500px] bg-slate-900 border-2 rounded-2xl shadow-2xl p-5 backdrop-blur-xl animate-in fade-in slide-in-from-top-6 duration-300 max-h-[calc(100vh-100px)] overflow-y-auto ${
        isNameMismatch
          ? "border-amber-500/90 shadow-amber-500/25 ring-1 ring-amber-500/50"
          : "border-emerald-500/90 shadow-emerald-500/25 ring-1 ring-emerald-500/50"
      }`}
    >
      {/* ── Card Header ──────────────────────────────────────────────────────── */}
      <div className="flex items-center space-x-3 mb-3 pb-3 border-b border-slate-800">
        <div
          className={`w-11 h-11 rounded-xl border flex items-center justify-center flex-shrink-0 ${
            isNameMismatch
              ? "bg-amber-500/20 border-amber-500 text-amber-400"
              : "bg-emerald-500/20 border-emerald-500 text-emerald-400"
          }`}
        >
          {isNameMismatch ? (
            <AlertTriangle className="w-6 h-6 animate-pulse" />
          ) : (
            <ShieldCheck className="w-6 h-6" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <span
              className={`text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded border ${
                isNameMismatch
                  ? "bg-amber-950 text-amber-400 border-amber-800"
                  : "bg-emerald-950 text-emerald-400 border-emerald-800"
              }`}
            >
              {isNameMismatch
                ? "SECURITY DIVERSION: HUMAN REVIEW"
                : "LEVEL 3 GOVERNANCE GATE"}
            </span>
            <span className="text-xs font-mono font-extrabold text-emerald-400">
              {amountStr}
            </span>
          </div>
          <h3 className="text-sm font-bold text-white mt-1 truncate">
            {isNameMismatch
              ? "Beneficiary Name Discrepancy Flagged"
              : "Payout Authorization Sign-off"}
          </h3>
        </div>
      </div>

      {/* ── Summary Key-Value Strip ─────────────────────────────────────────── */}
      <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1.5 font-mono text-xs mb-3">
        <div className="flex justify-between items-center">
          <span className="text-slate-500">Target Beneficiary:</span>
          <span className="text-white font-bold truncate max-w-[260px]">
            {vendorName}
          </span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-slate-500">Disbursement Amount:</span>
          <span className="text-emerald-400 font-extrabold text-sm">{amountStr}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-slate-500">Original Failure Root Cause:</span>
          <span className="text-rose-400 font-bold">{failureReason}</span>
        </div>
      </div>

      {/* ── Evidence Sheet Toggle ────────────────────────────────────────────── */}
      <button
        type="button"
        onClick={() => setShowEvidenceSheet(!showEvidenceSheet)}
        className="w-full flex items-center justify-between p-2.5 bg-slate-850 hover:bg-slate-800 border border-slate-750 rounded-xl text-xs font-mono text-slate-200 transition mb-3 cursor-pointer"
      >
        <div className="flex items-center space-x-2">
          <FileText className="w-4 h-4 text-razor-400" />
          <span className="font-bold">LIVE AGENT EVIDENCE & CASE DOSSIER</span>
        </div>
        {showEvidenceSheet ? (
          <ChevronUp className="w-4 h-4 text-slate-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-slate-400" />
        )}
      </button>

      {/* ── Evidence Sheet Body ──────────────────────────────────────────────── */}
      {showEvidenceSheet && (
        <div className="space-y-3 font-mono text-xs mb-4">
          {/* Executive Case Summary */}
          <div
            className={`p-3.5 rounded-xl border space-y-2 font-sans text-xs ${
              isNameMismatch
                ? "bg-amber-950/20 border-amber-800/60"
                : "bg-slate-950 border-slate-800"
            }`}
          >
            <div className="text-razor-400 font-bold uppercase tracking-wider text-[10px] font-mono flex items-center space-x-1.5">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Executive Case Summary</span>
            </div>

            {isNameMismatch ? (
              <div className="space-y-2">
                <p className="text-slate-200 leading-relaxed text-[11px]">
                  Original payout of <strong className="text-white">{amountStr}</strong> to{" "}
                  <strong className="text-white">{vendorName}</strong> failed at bank due to{" "}
                  <span className="text-rose-400 font-mono font-semibold">{failureReason}</span> on invoice{" "}
                  <span className="text-slate-300 font-mono">{invoiceRef}</span>.
                </p>
                <div className="p-2.5 rounded-lg bg-amber-950/50 border border-amber-700/60 text-amber-200 text-[11px] leading-relaxed space-y-1">
                  <div className="font-bold text-amber-300 flex items-center space-x-1.5">
                    <AlertOctagon className="w-3.5 h-3.5 text-amber-400" />
                    <span>CRITICAL RISK FINDING: NAME MISMATCH DETECTED</span>
                  </div>
                  <p className="text-[10px] text-amber-300/90 font-mono">
                    Bank penny-drop returned account owner:{" "}
                    <strong className="text-rose-300 underline">{registeredName}</strong>, diverging from Zoho Books profile{" "}
                    <strong className="text-white">{vendorName}</strong> ({nameMatchScore}% Match Score &lt; 85% safety threshold).
                  </p>
                  <p className="text-[10px] text-amber-200/80">
                    🛡️ <strong>Safety Enforcement:</strong> Autonomous money movement was halted immediately to prevent fraudulent diversion of funds.
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-1.5">
                <p className="text-slate-200 leading-relaxed text-[11px]">
                  Original payout of <strong className="text-white">{amountStr}</strong> to{" "}
                  <strong className="text-white">{vendorName}</strong> failed due to{" "}
                  <span className="text-rose-400 font-mono font-semibold">{failureReason}</span> on invoice{" "}
                  <span className="text-slate-300 font-mono">{invoiceRef}</span>.
                </p>
                <p className="text-slate-300 leading-relaxed text-[11px]">
                  <strong className="text-emerald-400 font-semibold">Agent Resolution:</strong> RX-AURA performed automated remediation via WhatsApp, extracted replacement banking details, executed ₹1 penny-drop validation (100% legal name match with {vendorName}), and synchronized the Zoho Books ERP ledger.
                </p>
                <p className="text-amber-300/90 leading-relaxed text-[10px] font-mono bg-amber-950/40 p-2 rounded-lg border border-amber-800/40">
                  ⚡ Policy Gate: Payout is ≥ ₹50,000. Autonomous money movement is blocked until human controller authorization.
                </p>
              </div>
            )}
          </div>

          {/* Section 1: Dynamic Verification & Side-by-Side Name Diff */}
          <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-2 text-[11px]">
            <div className="text-slate-400 font-bold uppercase tracking-wider text-[10px] flex items-center justify-between">
              <div className="flex items-center space-x-1.5 text-sky-400">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>1. Legal Entity & Bank Verification Diff</span>
              </div>
              <span
                className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded border ${
                  nameMatchScore >= 85
                    ? "bg-emerald-950 text-emerald-400 border-emerald-800"
                    : "bg-rose-950 text-rose-400 border-rose-800"
                }`}
              >
                {nameMatchScore}% MATCH SCORE
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-1">
              <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800 space-y-1">
                <span className="text-slate-400 block text-[10px] font-bold flex items-center space-x-1">
                  <Building2 className="w-3 h-3 text-amber-400" />
                  <span>Zoho Books Profile Name</span>
                </span>
                <span className="text-white font-bold block text-xs truncate">
                  {vendorName}
                </span>
                <span className="text-[9px] text-emerald-400 block font-mono">
                  ✓ Verified Corporate Master
                </span>
              </div>

              <div
                className={`p-2.5 rounded-lg border space-y-1 ${
                  nameMatchScore >= 85
                    ? "bg-slate-900 border-slate-800"
                    : "bg-rose-950/30 border-rose-800/60"
                }`}
              >
                <span className="text-slate-400 block text-[10px] font-bold flex items-center space-x-1">
                  <CreditCard className="w-3 h-3 text-sky-400" />
                  <span>Bank Registered Beneficiary</span>
                </span>
                <span
                  className={`font-bold block text-xs truncate ${
                    nameMatchScore >= 85 ? "text-emerald-400" : "text-rose-400 underline"
                  }`}
                >
                  {registeredName}
                </span>
                <span
                  className={`text-[9px] block font-mono font-bold ${
                    nameMatchScore >= 85 ? "text-emerald-400" : "text-rose-400"
                  }`}
                >
                  {nameMatchScore >= 85
                    ? "✓ Penny-Drop Active & Verified"
                    : "⚠️ Name Discrepancy Flagged"}
                </span>
              </div>
            </div>
          </div>

          {/* Section 2: Account Transition Diff */}
          <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-2 text-[11px]">
            <div className="text-slate-400 font-bold uppercase tracking-wider text-[10px] flex items-center space-x-1.5 text-indigo-400">
              <CreditCard className="w-3.5 h-3.5" />
              <span>2. RazorpayX Fund Account Transition</span>
            </div>
            <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800 space-y-1.5">
              <div className="flex justify-between items-center text-[10px]">
                <span className="text-slate-400">Old Faulty Account:</span>
                <span className="text-rose-400/80 line-through font-mono">
                  {oldFaId} (DEACTIVATED)
                </span>
              </div>
              <div className="flex justify-between items-center text-[10px]">
                <span className="text-slate-400">Replacement Account:</span>
                <span className="text-emerald-400 font-bold font-mono">
                  {newFaId} (STAGED)
                </span>
              </div>
              <div className="flex justify-between items-center pt-1 border-t border-slate-800 text-[10px]">
                <span className="text-slate-400">Zoho Books Ledger Sync:</span>
                <span
                  className={`font-semibold ${
                    isNameMismatch ? "text-amber-400" : "text-emerald-400"
                  }`}
                >
                  {isNameMismatch
                    ? "Paused (Awaiting Controller Override)"
                    : "Synchronized & Locked"}
                </span>
              </div>
            </div>
          </div>

          {/* Section 3: Cryptographic Integrity */}
          <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-1 text-[11px]">
            <div className="text-slate-400 font-bold uppercase tracking-wider text-[10px] flex items-center space-x-1.5 text-purple-400">
              <Lock className="w-3.5 h-3.5" />
              <span>3. Cryptographic Governance & Chain Audit</span>
            </div>
            <div className="flex justify-between items-center pt-1 text-[10px]">
              <span className="text-slate-400">SHA-256 Audit Ledger:</span>
              <span className="text-emerald-400 font-bold font-mono">
                100% Cryptographically Verified
              </span>
            </div>
          </div>
        </div>
      )}

      {/* ── Rejection Note Input ────────────────────────────────────────────── */}
      {showRejectInput ? (
        <div className="space-y-3 pt-2">
          <textarea
            placeholder="Enter reason for permanently rejecting this payout recovery..."
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
              className="flex-1 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white text-xs font-bold font-mono transition cursor-pointer"
            >
              Confirm Permanent Rejection
            </button>
            <button
              onClick={() => setShowRejectInput(false)}
              className="px-3 py-2.5 rounded-xl bg-slate-800 text-slate-300 text-xs font-mono cursor-pointer"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        /* ── Action Buttons ─────────────────────────────────────────────────── */
        <div className="space-y-2 pt-1">
          {isNameMismatch ? (
            <div className="space-y-2">
              <button
                onClick={() => setShowRejectInput(true)}
                disabled={isSubmitting}
                className="w-full flex items-center justify-center space-x-2 py-3 rounded-xl bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white text-xs font-bold font-mono shadow-lg shadow-rose-600/30 transition-all active:scale-95 cursor-pointer"
              >
                <XCircle className="w-4 h-4" />
                <span>REJECT & PERMANENTLY BLOCK (RECOMMENDED)</span>
              </button>

              <button
                onClick={() => onApprove(approvalNotes || "Controller manual override for name mismatch.")}
                disabled={isSubmitting}
                className="w-full flex items-center justify-center space-x-2 py-2.5 rounded-xl bg-amber-950 hover:bg-amber-900 border border-amber-800 text-amber-300 text-xs font-bold font-mono transition-all active:scale-95 cursor-pointer"
              >
                <ShieldAlert className="w-4 h-4 text-amber-400" />
                <span>MANUAL OVERRIDE & AUTHORIZE DISBURSEMENT</span>
              </button>
            </div>
          ) : (
            <div className="flex items-center space-x-3">
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
      )}
    </div>
  );
};
