"use client";

import React from "react";
import { CaseDetail } from "@/lib/types";
import { getStateBadgeColor, formatINR } from "./CaseListSidebar";
import { AlertCircle, ArrowRight, Play, Zap, ShieldAlert, CheckCircle2 } from "lucide-react";

interface CaseHeaderStripProps {
  caseData: CaseDetail;
  onProcessTurn: () => void;
  isProcessing?: boolean;
}

export const CaseHeaderStrip: React.FC<CaseHeaderStripProps> = ({
  caseData,
  onProcessTurn,
  isProcessing,
}) => {
  const badge = getStateBadgeColor(caseData.state);

  return (
    <div className="bg-slate-900 border-b border-slate-800 p-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* Left: Metadata Group */}
        <div className="space-y-1.5">
          <div className="flex items-center space-x-3">
            <h1 className="text-base font-bold text-white tracking-tight">
              {caseData.vendor?.name || "Vendor Payout Exception"}
            </h1>
            <span className="text-xs font-mono text-slate-400 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
              {caseData.case_number}
            </span>
            <span
              className={`text-xs font-mono font-semibold uppercase px-2.5 py-0.5 rounded-md border ${badge.bg} ${badge.text} ${badge.border}`}
            >
              {caseData.state}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-400 font-mono">
            <div>
              <span className="text-slate-500">Payout ID: </span>
              <span className="text-slate-300 font-semibold">{caseData.payout?.razorpay_payout_id || "N/A"}</span>
            </div>
            <div>
              <span className="text-slate-500">Invoice: </span>
              <span className="text-slate-300 font-semibold">{caseData.invoice_reference || "N/A"}</span>
            </div>
            <div>
              <span className="text-slate-500">Failure: </span>
              <span className="text-rose-400 font-semibold">
                {caseData.failure_source} / {caseData.failure_reason}
              </span>
            </div>
            <div>
              <span className="text-slate-500">Strategy: </span>
              <span className="text-razor-400 font-semibold">{caseData.recovery_strategy || "N/A"}</span>
            </div>
          </div>
        </div>

        {/* Right: Amount & Status */}
        <div className="flex items-center space-x-4">
          <div className="text-right">
            <span className="block text-[11px] font-mono text-slate-400 uppercase tracking-wider">
              Payout Amount
            </span>
            <span className="font-mono text-xl font-extrabold text-white">
              {formatINR(caseData.amount)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
