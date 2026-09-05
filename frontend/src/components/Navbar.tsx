"use client";

import React from "react";
import { Activity, ShieldCheck, PlayCircle, Archive, FlaskConical, AlertCircle, RefreshCw } from "lucide-react";

interface NavbarProps {
  activeTab: "active" | "closed" | "evaluation";
  onTabChange: (tab: "active" | "closed" | "evaluation") => void;
  backendOnline: boolean;
  activeCount: number;
  onOpenSimulate: () => void;
  onRefresh: () => void;
  onResetAll?: () => void;
  isRefreshing?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  onTabChange,
  backendOnline,
  activeCount,
  onOpenSimulate,
  onRefresh,
  onResetAll,
  isRefreshing,
}) => {
  return (
    <header className="bg-slate-900 border-b border-slate-800 sticky top-0 z-40 px-6 py-3.5 backdrop-blur-md bg-opacity-95">
      <div className="max-w-[1720px] mx-auto flex items-center justify-between">
        {/* Left: Brand & Tagline */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-razor-500 to-blue-700 flex items-center justify-center shadow-lg shadow-razor-500/20">
              <ShieldCheck className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-lg text-white tracking-tight bg-gradient-to-r from-white via-slate-100 to-razor-300 bg-clip-text text-transparent">
                  RX-AURA
                </span>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-razor-950 text-razor-400 border border-razor-800/80 font-bold tracking-wider">
                  AUTONOMOUS UNIFIED RESOLUTION AGENT
                </span>
              </div>
              <p className="text-xs text-slate-400 font-medium">
                RazorpayX Payout Exception Resolution & Cryptographic Ledger
              </p>
            </div>
          </div>

          <div className="h-6 w-[1px] bg-slate-800 mx-2" />

          {/* System Status Pill */}
          <div className="flex items-center space-x-2 px-3 py-1 rounded-full bg-slate-850 border border-slate-750 text-xs">
            <div
              className={`w-2 h-2 rounded-full ${
                backendOnline ? "bg-emerald-400 pulse-dot" : "bg-rose-500"
              }`}
            />
            <span className={`font-mono text-[11px] ${backendOnline ? "text-emerald-400" : "text-rose-400"}`}>
              {backendOnline ? "CORE CONNECTED" : "BACKEND OFFLINE"}
            </span>
          </div>
        </div>

        {/* Center: Navigation Tabs */}
        <nav className="flex items-center space-x-1 bg-slate-950/80 p-1 rounded-xl border border-slate-800/80">
          <button
            onClick={() => onTabChange("active")}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-medium transition-all ${
              activeTab === "active"
                ? "bg-razor-600 text-white shadow-md shadow-razor-600/30"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-850"
            }`}
          >
            <Activity className="w-4 h-4" />
            <span>Active Cases</span>
            {activeCount > 0 && (
              <span
                className={`ml-1 text-[11px] font-mono px-1.5 py-0.2 rounded-full ${
                  activeTab === "active" ? "bg-white/20 text-white" : "bg-razor-950 text-razor-400 border border-razor-800"
                }`}
              >
                {activeCount}
              </span>
            )}
          </button>

          <button
            onClick={() => onTabChange("closed")}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-medium transition-all ${
              activeTab === "closed"
                ? "bg-razor-600 text-white shadow-md shadow-razor-600/30"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-850"
            }`}
          >
            <Archive className="w-4 h-4" />
            <span>Closed Cases</span>
          </button>

          <button
            onClick={() => onTabChange("evaluation")}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-medium transition-all ${
              activeTab === "evaluation"
                ? "bg-razor-600 text-white shadow-md shadow-razor-600/30"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-850"
            }`}
          >
            <FlaskConical className="w-4 h-4" />
            <span>Evaluation Suite (10 Scenarios)</span>
          </button>
        </nav>

        {/* Right: Actions */}
        <div className="flex items-center space-x-3">
          {onResetAll && (
            <button
              onClick={onResetAll}
              title="Reset all demo cases and start fresh"
              className="px-3 py-2 rounded-lg bg-slate-850 hover:bg-rose-950/60 hover:border-rose-800 border border-slate-750 text-slate-400 hover:text-rose-300 text-xs font-mono transition flex items-center space-x-1.5"
            >
              <span>Reset State</span>
            </button>
          )}

          <button
            onClick={onRefresh}
            title="Refresh active state"
            className="p-2 rounded-lg bg-slate-850 hover:bg-slate-800 border border-slate-750 text-slate-300 transition"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin text-razor-400" : ""}`} />
          </button>

          <button
            onClick={onOpenSimulate}
            className="flex items-center space-x-2 px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md shadow-emerald-600/20 transition-all active:scale-95"
          >
            <PlayCircle className="w-4 h-4" />
            <span>Simulate Exception</span>
          </button>
        </div>
      </div>
    </header>
  );
};
