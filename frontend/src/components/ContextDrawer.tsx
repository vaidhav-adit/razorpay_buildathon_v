"use client";

import React, { useState } from "react";
import { CaseDetail } from "@/lib/types";
import { formatINR } from "./CaseListSidebar";
import {
  CreditCard,
  Building2,
  CheckCircle,
  ShieldCheck,
  AlertCircle,
  Info,
  Radio,
  ExternalLink,
  Cpu,
  Lock,
  Layers,
  Zap,
} from "lucide-react";

interface ContextDrawerProps {
  caseData: CaseDetail;
}

export const ContextDrawer: React.FC<ContextDrawerProps> = ({ caseData }) => {
  const [activeTab, setActiveTab] = useState<"connections" | "payout" | "vendor" | "validation">("connections");

  const approvalPayload = caseData.approval?.payload || {};

  return (
    <div className="w-80 md:w-96 bg-slate-900 border-l border-slate-800 flex flex-col h-[calc(100vh-61px)] flex-shrink-0">
      {/* Header & Tabs */}
      <div className="p-4 border-b border-slate-800 bg-slate-900/90">
        <h3 className="text-xs font-bold uppercase tracking-wider text-white font-mono mb-3 flex items-center space-x-2">
          <Layers className="w-3.5 h-3.5 text-razor-400" />
          <span>System Context & Integrations</span>
        </h3>

        <div className="grid grid-cols-4 gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 text-[10px] font-mono">
          <button
            onClick={() => setActiveTab("connections")}
            className={`py-1.5 rounded text-center transition ${
              activeTab === "connections"
                ? "bg-razor-700 text-white font-semibold"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Integrations
          </button>
          <button
            onClick={() => setActiveTab("payout")}
            className={`py-1.5 rounded text-center transition ${
              activeTab === "payout"
                ? "bg-razor-700 text-white font-semibold"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Payout
          </button>
          <button
            onClick={() => setActiveTab("vendor")}
            className={`py-1.5 rounded text-center transition ${
              activeTab === "vendor"
                ? "bg-razor-700 text-white font-semibold"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Vendor
          </button>
          <button
            onClick={() => setActiveTab("validation")}
            className={`py-1.5 rounded text-center transition ${
              activeTab === "validation"
                ? "bg-razor-700 text-white font-semibold"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Validation
          </button>
        </div>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 font-mono text-xs">
        {/* ── 1. Live Connections & Integrations Tab ─────────────────────────── */}
        {activeTab === "connections" && (
          <div className="space-y-3">
            {/* Razorpay Integration Card */}
            <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-razor-400 font-bold text-xs">
                  <CreditCard className="w-4 h-4" />
                  <span>RazorpayX API</span>
                </div>
                <span className="text-[10px] uppercase px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-bold">
                  CONNECTED
                </span>
              </div>
              <p className="text-[11px] text-slate-400 leading-snug">
                Test Mode API active. Governed by 3-Tier Policy Engine (Autonomous / Controlled / Human Gate).
              </p>
              <div className="text-[10px] text-slate-500 pt-1 border-t border-slate-850 flex justify-between">
                <span>Account Number:</span>
                <span className="text-slate-300">2323230099887766</span>
              </div>
            </div>

            {/* Zoho Books ERP Card */}
            <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-amber-400 font-bold text-xs">
                  <Building2 className="w-4 h-4" />
                  <span>Zoho Books ERP</span>
                </div>
                <span className="text-[10px] uppercase px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-bold">
                  OAUTH ACTIVE
                </span>
              </div>
              <p className="text-[11px] text-slate-400 leading-snug">
                Connected to vendor accounting database. Bi-directional vendor invoice verification & audit writeback.
              </p>
              <div className="text-[10px] text-slate-500 pt-1 border-t border-slate-850 flex justify-between">
                <span>Vendor Reference:</span>
                <span className="text-slate-300">{caseData.vendor?.zoho_vendor_id || "VEND-ACME-8801"}</span>
              </div>
            </div>

            {/* Penny-Drop Validation Card */}
            <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-indigo-400 font-bold text-xs">
                  <ShieldCheck className="w-4 h-4" />
                  <span>Penny-Drop Engine</span>
                </div>
                <span className="text-[10px] uppercase px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800 font-bold">
                  SIMULATED
                </span>
              </div>
              <p className="text-[11px] text-slate-400 leading-snug">
                Deterministic account verification with fuzzy name matching (0-100 score) and fraud diversion.
              </p>
            </div>

            {/* Deterministic FSM Card */}
            <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-emerald-400 font-bold text-xs">
                  <Lock className="w-4 h-4" />
                  <span>State Machine & Audit</span>
                </div>
                <span className="text-[10px] uppercase px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-bold">
                  SHA-256
                </span>
              </div>
              <p className="text-[11px] text-slate-400 leading-snug">
                10 non-bypassable lifecycle states. Every state transition cryptographically logged.
              </p>
            </div>
          </div>
        )}

        {/* ── 2. Payout Tab ─────────────────────────────────────────── */}
        {activeTab === "payout" && (
          <div className="space-y-4">
            <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2.5">
              <div className="flex items-center space-x-2 text-razor-400 font-semibold text-xs border-b border-slate-850 pb-2">
                <CreditCard className="w-4 h-4" />
                <span>Original Failed Payout</span>
              </div>

              <div className="space-y-1.5 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-slate-500">Payout ID:</span>
                  <span className="text-slate-200 font-semibold">{caseData.payout?.razorpay_payout_id || "N/A"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Amount:</span>
                  <span className="text-emerald-400 font-bold">{formatINR(caseData.amount)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Currency / Mode:</span>
                  <span className="text-slate-200">{caseData.payout?.currency || "INR"} / {caseData.payout?.mode || "NEFT"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Status:</span>
                  <span className="text-rose-400 font-semibold uppercase">{caseData.payout?.status || "failed"}</span>
                </div>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
              <span className="text-slate-400 text-[11px] font-semibold block">Failure Diagnostics</span>
              <div className="space-y-1 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-slate-500">Source:</span>
                  <span className="text-slate-300">{caseData.failure_source}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Reason Code:</span>
                  <span className="text-rose-400 font-semibold">{caseData.failure_reason}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Recovery Strategy:</span>
                  <span className="text-razor-400 font-semibold">{caseData.recovery_strategy || "VENDOR_REMEDIATION"}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── 3. Vendor Tab ─────────────────────────────────────────── */}
        {activeTab === "vendor" && (
          <div className="space-y-4">
            <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2.5">
              <div className="flex items-center space-x-2 text-razor-400 font-semibold text-xs border-b border-slate-850 pb-2">
                <Building2 className="w-4 h-4" />
                <span>Vendor Master Record</span>
              </div>

              <div className="space-y-1.5 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-slate-500">Name:</span>
                  <span className="text-slate-200 font-semibold">{caseData.vendor?.name || "N/A"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Email:</span>
                  <span className="text-slate-200 truncate max-w-[170px]">{caseData.vendor?.email || "N/A"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Phone:</span>
                  <span className="text-slate-200">{caseData.vendor?.phone || "+919876543210"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Zoho ID:</span>
                  <span className="text-amber-400 font-semibold">{caseData.vendor?.zoho_vendor_id || "VEND-ACME-8801"}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── 4. Validation Tab ─────────────────────────────────────── */}
        {activeTab === "validation" && (
          <div className="space-y-4">
            <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-2.5">
              <div className="flex items-center space-x-2 text-razor-400 font-semibold text-xs border-b border-slate-850 pb-2">
                <ShieldCheck className="w-4 h-4" />
                <span>Penny-Drop Validation Result</span>
              </div>

              {approvalPayload.new_fund_account_id ? (
                <div className="space-y-2 text-[11px]">
                  <div className="flex justify-between">
                    <span className="text-slate-500">New Fund Account:</span>
                    <span className="text-emerald-400 font-mono text-[10px]">{approvalPayload.new_fund_account_id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Name Match Score:</span>
                    <span className="text-emerald-400 font-bold">{approvalPayload.name_match_score || 95}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Account Status:</span>
                    <span className="text-emerald-400 font-bold uppercase">{approvalPayload.validation_status || "ACTIVE"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Simulation Flag:</span>
                    <span className="text-indigo-400 font-semibold">is_simulated = True</span>
                  </div>
                </div>
              ) : (
                <div className="text-slate-500 text-[11px] py-4 text-center italic">
                  Validation occurs once vendor supplies updated banking details.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
