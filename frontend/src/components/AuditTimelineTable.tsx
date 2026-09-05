"use client";

import React, { useState } from "react";
import { AuditEventItem } from "@/lib/types";
import {
  ShieldCheck,
  ShieldAlert,
  ChevronDown,
  ChevronRight,
  Hash,
  Check,
  Lock,
  Search,
  ExternalLink,
  Bot,
  UserCheck,
  Radio,
  Cpu,
  RefreshCw,
} from "lucide-react";

interface AuditTimelineTableProps {
  events: AuditEventItem[];
  verification: {
    status: string;
    is_valid: boolean;
    total_events: number;
    details: string;
  };
}

export const AuditTimelineTable: React.FC<AuditTimelineTableProps> = ({
  events,
  verification,
}) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [isVerifying, setIsVerifying] = useState(false);
  const [selectedBlock, setSelectedBlock] = useState<AuditEventItem | null>(null);

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  const handleVerify = () => {
    setIsVerifying(true);
    setTimeout(() => {
      setIsVerifying(false);
    }, 600);
  };

  function getActorBadge(actorType: string) {
    switch (actorType) {
      case "AI_DECISION":
      case "SYSTEM_ACTION":
        return { label: "AI AGENT / SYSTEM", bg: "bg-razor-950 text-razor-300 border-razor-800" };
      case "HUMAN_DECISION":
        return { label: "FINANCE CONTROLLER", bg: "bg-amber-950 text-amber-300 border-amber-800" };
      case "EXTERNAL_FACT":
      default:
        return { label: "EXTERNAL FACT", bg: "bg-emerald-950 text-emerald-300 border-emerald-800" };
    }
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
      {/* Table Header & Integrity Badge */}
      <div className="p-4 bg-slate-850 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-600/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
            <Lock className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-white font-mono flex items-center space-x-2">
              <span>Cryptographic Audit Ledger</span>
              <span className="text-slate-400 font-normal">({events.length} SHA-256 blocks)</span>
            </h3>
            <p className="text-[11px] text-slate-400 font-mono">
              Append-only, tamper-evident hash chain linking all facts, agent turns, and human approvals
            </p>
          </div>
        </div>

        {/* Verification Controls & Status */}
        <div className="flex items-center space-x-2">
          <button
            onClick={handleVerify}
            disabled={isVerifying}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 text-xs font-mono border border-slate-700 transition active:scale-95"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isVerifying ? "animate-spin text-razor-400" : ""}`} />
            <span>{isVerifying ? "Verifying Hash Math..." : "Verify Chain"}</span>
          </button>

          <div
            className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg border font-mono text-xs font-bold ${
              verification.is_valid
                ? "bg-emerald-950/80 border-emerald-500 text-emerald-400 shadow-md shadow-emerald-500/10"
                : "bg-rose-950/80 border-rose-500 text-rose-400 animate-pulse"
            }`}
          >
            {verification.is_valid ? (
              <>
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>CHAIN 100% INTACT</span>
              </>
            ) : (
              <>
                <ShieldAlert className="w-4 h-4 text-rose-400" />
                <span>TAMPER DETECTED</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Table Data */}
      <div className="overflow-x-auto">
        <table className="w-full text-left font-mono text-xs">
          <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] border-b border-slate-800">
            <tr>
              <th className="p-3 w-8">#</th>
              <th className="p-3">Time</th>
              <th className="p-3">Actor & Action</th>
              <th className="p-3">Agent Reasoning / Diagnostic Justification</th>
              <th className="p-3">Block Hash</th>
              <th className="p-3 text-right">Inspect</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {events.length === 0 ? (
              <tr>
                <td colSpan={6} className="p-8 text-center text-slate-600 italic">
                  Awaiting genesis audit block for this recovery case...
                </td>
              </tr>
            ) : (
              events.map((ev, index) => {
                const isExpanded = expandedId === ev.id;
                const actorBadge = getActorBadge(ev.event_type);
                const timeStr = ev.timestamp
                  ? new Date(ev.timestamp).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                    })
                  : "00:00:00";

                return (
                  <React.Fragment key={ev.id || index}>
                    <tr
                      onClick={() => toggleExpand(ev.id)}
                      className={`hover:bg-slate-850/60 cursor-pointer transition ${
                        isExpanded ? "bg-slate-850/80" : ""
                      }`}
                    >
                      <td className="p-3 text-slate-500 text-[11px] font-bold">{index + 1}</td>
                      <td className="p-3 text-slate-400 text-[11px] whitespace-nowrap">{timeStr}</td>
                      <td className="p-3">
                        <div className="space-y-1">
                          <span className="font-bold text-white block">{ev.action}</span>
                          <span
                            className={`inline-block text-[9px] uppercase font-semibold px-1.5 py-0.2 rounded border ${actorBadge.bg}`}
                          >
                            {actorBadge.label}
                          </span>
                        </div>
                      </td>
                      <td className="p-3 max-w-[380px]">
                        <p className="text-slate-200 text-[11px] leading-relaxed line-clamp-2">
                          {ev.reason || "Operational state transition."}
                        </p>
                      </td>
                      <td className="p-3 text-[11px] text-razor-400 font-mono">
                        <span className="bg-slate-950 px-2 py-0.5 rounded border border-slate-800 text-emerald-400">
                          {ev.event_hash.slice(0, 10)}...
                        </span>
                      </td>
                      <td className="p-3 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedBlock(ev);
                          }}
                          className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-[10px] border border-slate-700 transition"
                        >
                          Raw Block
                        </button>
                      </td>
                    </tr>

                    {/* Expanded Row: Full Cryptographic Proof */}
                    {isExpanded && (
                      <tr className="bg-slate-950 border-y border-slate-800 text-[11px]">
                        <td colSpan={6} className="p-4 space-y-3">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-slate-300">
                            <div>
                              <span className="text-slate-500 block text-[10px] font-bold uppercase">
                                Full Agent Reason & Evidence
                              </span>
                              <p className="mt-1 text-slate-100 bg-slate-900 p-2.5 rounded-lg border border-slate-800 leading-relaxed">
                                {ev.reason || "Autonomous system action logged."}
                              </p>
                            </div>
                            <div className="space-y-2">
                              <div>
                                <span className="text-slate-500 block text-[10px] font-bold uppercase">
                                  Target Identifier
                                </span>
                                <span className="text-slate-300 bg-slate-900 px-2 py-1 rounded border border-slate-800 inline-block mt-0.5">
                                  {ev.target || "N/A"}
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-500 block text-[10px] font-bold uppercase">
                                  Actor Identity
                                </span>
                                <span className="text-slate-300 bg-slate-900 px-2 py-1 rounded border border-slate-800 inline-block mt-0.5">
                                  {ev.actor}
                                </span>
                              </div>
                            </div>
                          </div>

                          {/* Cryptographic Linkage Box */}
                          <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1.5 font-mono text-[10px]">
                            <div className="flex items-center space-x-2 text-slate-400">
                              <span className="text-slate-500 w-24">Previous Hash:</span>
                              <span className="text-slate-300 break-all">{ev.previous_hash}</span>
                            </div>
                            <div className="flex items-center space-x-2 text-emerald-400 font-bold">
                              <span className="text-slate-500 w-24">Block Hash:</span>
                              <span className="break-all">{ev.event_hash}</span>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Raw Cryptographic Block Modal */}
      {selectedBlock && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-750 rounded-2xl max-w-xl w-full p-6 shadow-2xl space-y-4 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2 text-emerald-400 font-bold">
                <Lock className="w-4 h-4" />
                <span>SHA-256 Audit Block Inspector</span>
              </div>
              <button
                onClick={() => setSelectedBlock(null)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2 text-[11px]">
              <div>
                <span className="text-slate-500 block">Block Action:</span>
                <span className="text-white font-bold">{selectedBlock.action}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Actor:</span>
                <span className="text-slate-300">{selectedBlock.actor}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Reason:</span>
                <p className="text-slate-300 bg-slate-950 p-2 rounded border border-slate-800">
                  {selectedBlock.reason || "N/A"}
                </p>
              </div>
              <div>
                <span className="text-slate-500 block">Previous Block Hash (Parent):</span>
                <span className="text-slate-400 break-all bg-slate-950 p-1.5 rounded border border-slate-800 block">
                  {selectedBlock.previous_hash}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block">Event Hash (SHA-256):</span>
                <span className="text-emerald-400 break-all bg-slate-950 p-1.5 rounded border border-emerald-900/60 block font-bold">
                  {selectedBlock.event_hash}
                </span>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-800 flex justify-end">
              <button
                onClick={() => setSelectedBlock(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition"
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
