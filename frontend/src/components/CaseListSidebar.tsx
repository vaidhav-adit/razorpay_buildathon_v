"use client";

import React, { useState } from "react";
import { CaseListItem } from "@/lib/types";
import { Search, AlertTriangle, ArrowRight, CheckCircle2, Clock, ShieldAlert } from "lucide-react";

interface CaseListSidebarProps {
  cases: CaseListItem[];
  selectedCaseId: string | null;
  onSelectCase: (caseId: string) => void;
  isLoading?: boolean;
}

export function getStateBadgeColor(state: string): { bg: string; text: string; border: string; pulse?: boolean } {
  switch (state) {
    case "HUMAN_APPROVAL":
      return { bg: "bg-amber-950/80", text: "text-amber-400", border: "border-amber-600/80", pulse: true };
    case "HUMAN_REVIEW":
      return { bg: "bg-orange-950/80", text: "text-orange-400", border: "border-orange-600/80", pulse: true };
    case "PAYOUT_EXECUTED":
      return { bg: "bg-blue-950/80", text: "text-blue-400", border: "border-blue-600/80" };
    case "PAYOUT_CONFIRMED":
    case "CASE_RESOLVED":
      return { bg: "bg-emerald-950/80", text: "text-emerald-400", border: "border-emerald-600/80" };
    case "BLOCKED":
    case "ESCALATED":
      return { bg: "bg-rose-950/80", text: "text-rose-400", border: "border-rose-600/80" };
    case "VENDOR_CONTACTED":
      return { bg: "bg-sky-950/80", text: "text-sky-400", border: "border-sky-600/80" };
    case "BANK_VALIDATED":
    case "DATA_VALIDATED":
      return { bg: "bg-indigo-950/80", text: "text-indigo-400", border: "border-indigo-600/80" };
    default:
      return { bg: "bg-slate-800", text: "text-slate-300", border: "border-slate-700" };
  }
}

export function formatINR(paise: number): string {
  const rupees = paise / 100.0;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(rupees);
}

export const CaseListSidebar: React.FC<CaseListSidebarProps> = ({
  cases,
  selectedCaseId,
  onSelectCase,
  isLoading,
}) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [filterState, setFilterState] = useState<string>("ALL");

  const filteredCases = cases.filter((c) => {
    const matchesSearch =
      (c.vendor_name || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.case_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.failure_reason.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesFilter = filterState === "ALL" || c.state === filterState;

    return matchesSearch && matchesFilter;
  });

  return (
    <aside className="w-80 md:w-96 bg-slate-900 border-r border-slate-800 flex flex-col h-[calc(100vh-61px)] flex-shrink-0">
      {/* Header & Search */}
      <div className="p-4 border-b border-slate-800 space-y-3 bg-slate-900/90">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
            Exception Queue ({cases.length})
          </h2>
          <span className="text-[11px] font-mono text-slate-500">Auto-refreshing</span>
        </div>

        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search vendor, case ID, reason..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-razor-500 transition"
          />
        </div>

        {/* Quick Filter Pill Chips */}
        <div className="flex items-center space-x-1.5 overflow-x-auto pb-1 text-[11px] font-mono">
          {["ALL", "HUMAN_APPROVAL", "VENDOR_CONTACTED", "CASE_CREATED"].map((st) => (
            <button
              key={st}
              onClick={() => setFilterState(st)}
              className={`px-2 py-0.5 rounded whitespace-nowrap transition ${
                filterState === st
                  ? "bg-razor-700 text-white font-semibold"
                  : "bg-slate-800/80 text-slate-400 hover:bg-slate-800"
              }`}
            >
              {st === "ALL" ? "All Active" : st.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      {/* Top Half: Case List Content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2 max-h-[50vh] min-h-[220px]">
        {isLoading && cases.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs font-mono">Loading exception queue...</div>
        ) : filteredCases.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-xs space-y-2 font-mono">
            <CheckCircle2 className="w-6 h-6 mx-auto text-slate-600" />
            <p>No active exception cases.</p>
            <p className="text-[10px] text-slate-600">Simulate a failure to begin.</p>
          </div>
        ) : (
          filteredCases.map((c) => {
            const isSelected = c.id === selectedCaseId;
            const badge = getStateBadgeColor(c.state);

            return (
              <div
                key={c.id}
                onClick={() => onSelectCase(c.id)}
                className={`p-3 rounded-xl border transition-all cursor-pointer relative ${
                  isSelected
                    ? "bg-slate-850 border-razor-500 shadow-md shadow-razor-500/10"
                    : "bg-slate-950/60 border-slate-850 hover:bg-slate-850/70 hover:border-slate-750"
                }`}
              >
                {badge.pulse && (
                  <span className="absolute top-2.5 right-2.5 flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
                  </span>
                )}

                {/* Top Row: Vendor & Amount */}
                <div className="flex items-start justify-between mb-1 pr-2">
                  <span className="font-semibold text-xs text-white truncate max-w-[150px]">
                    {c.vendor_name || "Unknown Vendor"}
                  </span>
                  <span className="font-mono text-xs font-bold text-razor-400">
                    {formatINR(c.amount)}
                  </span>
                </div>

                {/* Case Number & Failure Reason */}
                <div className="space-y-1 mb-2">
                  <div className="text-[10px] font-mono text-slate-400 flex items-center justify-between">
                    <span>{c.case_number}</span>
                    <span className="text-slate-500">
                      {new Date(c.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </div>

                  <div className="flex items-center space-x-1.5 text-[10px] text-rose-400 font-mono bg-rose-950/40 px-2 py-0.5 rounded border border-rose-900/40 truncate">
                    <AlertTriangle className="w-3 h-3 flex-shrink-0" />
                    <span className="truncate">{c.failure_reason}</span>
                  </div>
                </div>

                {/* Bottom Row: State Badge */}
                <div className="flex items-center justify-between pt-1 border-t border-slate-850/60">
                  <span
                    className={`text-[9px] font-mono uppercase font-semibold px-2 py-0.5 rounded border ${badge.bg} ${badge.text} ${badge.border}`}
                  >
                    {c.state}
                  </span>

                  <span className="text-[9px] text-slate-500 font-mono">
                    {c.risk_level} RISK
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Bottom Half: Live Gateway & Webhook Traffic Monitor */}
      <div className="h-64 border-t border-slate-800 bg-slate-950/90 flex flex-col font-mono text-[11px]">
        <div className="px-3 py-2 bg-slate-900 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2 text-slate-300">
            <span className="w-2 h-2 rounded-full bg-emerald-400 pulse-dot" />
            <span className="font-bold text-[10px] uppercase tracking-wider text-slate-400">
              Gateway & Webhook Traffic
            </span>
          </div>
          <span className="text-[9px] text-emerald-400 bg-emerald-950/60 px-1.5 py-0.2 rounded border border-emerald-800/80">
            HTTP 200/201
          </span>
        </div>

        <div className="flex-1 overflow-y-auto p-2.5 space-y-2 text-[10px]">
          <div className="p-2 rounded-lg bg-slate-900/60 border border-slate-800 space-y-1 hover:border-slate-700 transition">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-1.5">
                <span className="text-slate-500 text-[9px]">10:42:01</span>
                <span className="text-emerald-400 font-bold">POST /webhooks/razorpay</span>
              </div>
              <span className="text-emerald-400 font-semibold text-[9px] bg-emerald-950/60 px-1 py-0.2 rounded border border-emerald-800/60">200 OK • 42ms</span>
            </div>
            <div className="text-slate-400 text-[10px] truncate">
              event: <span className="text-rose-400 font-semibold">payout.failed</span> • source: beneficiary_bank
            </div>
          </div>

          <div className="p-2 rounded-lg bg-slate-900/60 border border-slate-800 space-y-1 hover:border-slate-700 transition">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-1.5">
                <span className="text-slate-500 text-[9px]">10:42:04</span>
                <span className="text-razor-400 font-bold">POST /vendor/message/send</span>
              </div>
              <span className="text-sky-400 font-semibold text-[9px] bg-sky-950/60 px-1 py-0.2 rounded border border-sky-800/60">201 CREATED • 118ms</span>
            </div>
            <div className="text-slate-400 text-[10px] truncate">
              channel: <span className="text-sky-400 font-semibold">WhatsApp Business</span> • template: remediation
            </div>
          </div>

          <div className="p-2 rounded-lg bg-slate-900/60 border border-slate-800 space-y-1 hover:border-slate-700 transition">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-1.5">
                <span className="text-slate-500 text-[9px]">10:42:09</span>
                <span className="text-purple-400 font-bold">POST /fund_accounts/validate</span>
              </div>
              <span className="text-purple-400 font-semibold text-[9px] bg-purple-950/60 px-1 py-0.2 rounded border border-purple-800/60">200 OK • 310ms</span>
            </div>
            <div className="text-slate-400 text-[10px] truncate">
              service: <span className="text-amber-400 font-semibold">Penny-Drop ₹1.00</span> • match: 100%
            </div>
          </div>

          <div className="p-2 rounded-lg bg-slate-900/60 border border-slate-800 space-y-1 hover:border-slate-700 transition">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-1.5">
                <span className="text-slate-500 text-[9px]">10:42:11</span>
                <span className="text-emerald-400 font-bold">POST /webhooks/zoho</span>
              </div>
              <span className="text-emerald-400 font-semibold text-[9px] bg-emerald-950/60 px-1 py-0.2 rounded border border-emerald-800/60">200 OK • 85ms</span>
            </div>
            <div className="text-slate-400 text-[10px] truncate">
              ledger: <span className="text-emerald-400 font-semibold">Zoho Books ERP</span> • sync: bank_details
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};
