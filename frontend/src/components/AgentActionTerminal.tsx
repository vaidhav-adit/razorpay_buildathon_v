"use client";

import React, { useRef, useEffect } from "react";
import { AuditEventItem } from "@/lib/types";
import { Terminal, Bot, Cpu, UserCheck, Radio, Shield } from "lucide-react";

interface AgentActionTerminalProps {
  events: AuditEventItem[];
  isLive?: boolean;
}

export const AgentActionTerminal: React.FC<AgentActionTerminalProps> = ({ events, isLive = true }) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const isUserScrolledUp = useRef<boolean>(false);

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    // If user is more than 50px away from the bottom, do not force scroll down
    isUserScrolledUp.current = scrollHeight - scrollTop - clientHeight > 50;
  };

  useEffect(() => {
    if (scrollRef.current && !isUserScrolledUp.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  function getActorBadge(actorType: string) {
    switch (actorType) {
      case "AI_DECISION":
        return {
          label: "AI AGENT",
          bg: "bg-razor-950 text-razor-400 border-razor-800",
          icon: Bot,
        };
      case "SYSTEM_ACTION":
        return {
          label: "SYSTEM",
          bg: "bg-indigo-950 text-indigo-400 border-indigo-800",
          icon: Cpu,
        };
      case "HUMAN_DECISION":
        return {
          label: "HUMAN CONTROLLER",
          bg: "bg-amber-950 text-amber-400 border-amber-800",
          icon: UserCheck,
        };
      case "EXTERNAL_FACT":
      default:
        return {
          label: "WEBHOOK / FACT",
          bg: "bg-emerald-950 text-emerald-400 border-emerald-800",
          icon: Radio,
        };
    }
  }

  function getActionDescription(action: string, target?: string | null, reason?: string | null) {
    const act = (action || "").toLowerCase();
    if (act.includes("payout.failed") || act.includes("ingest")) {
      return {
        title: "Payout Failure Ingestion",
        what: "Ingested payout failure event from RazorpayX core banking gateway.",
        why: "Initiates deterministic exception investigation.",
      };
    }
    if (act.includes("classify") || act.includes("diagnos")) {
      return {
        title: "Root Cause Classification",
        what: "Analyzed error codes against decision matrix.",
        why: reason || "Determines whether to trigger vendor outreach, retry, or escalate.",
      };
    }
    if (act.includes("send_vendor") || act.includes("contact")) {
      return {
        title: "Autonomous Vendor Outreach",
        what: `Dispatched WhatsApp message with invoice reference${target ? ` to ${target}` : ""}.`,
        why: "Requests corrected beneficiary account details directly from vendor.",
      };
    }
    if (act.includes("receive_vendor")) {
      return {
        title: "Vendor Response Ingestion",
        what: "Received inbound reply from vendor communication channel.",
        why: "Feeds raw vendor text into LLM entity extraction pipeline.",
      };
    }
    if (act.includes("extract") || act.includes("data_validat")) {
      return {
        title: "LLM Entity Extraction & Syntax Check",
        what: "Parsed IFSC code and account number; verified standard regex rules.",
        why: "Prevents invalid or malformed data from reaching payment rails.",
      };
    }
    if (act.includes("create_fund")) {
      return {
        title: "RazorpayX Fund Account Provisioning",
        what: `Created new fund account entity${target ? ` (${target})` : ""}.`,
        why: "Stages updated banking target for penny-drop validation.",
      };
    }
    if (act.includes("validate_fund") || act.includes("penny")) {
      return {
        title: "Penny-Drop Bank Verification",
        what: "Executed instant ₹1 penny-drop validation via banking network.",
        why: "Verifies account is active and matches vendor legal identity.",
      };
    }
    if (act.includes("zoho") || act.includes("erp") || act.includes("update_vendor")) {
      return {
        title: "ERP Ledger Synchronization",
        what: "Updated vendor banking record in Zoho Books.",
        why: "Ensures accounting master data matches verified payment destination.",
      };
    }
    if (act.includes("approve") || act.includes("authoriz")) {
      return {
        title: "Human Controller Authorization",
        what: "Finance controller reviewed audit trail and granted digital approval.",
        why: "Mandatory human governance gate before money movement.",
      };
    }
    if (act.includes("retry") || act.includes("disburs")) {
      return {
        title: "Replacement Payout Disbursement",
        what: "Triggered replacement payout on RazorpayX.",
        why: "Resolves the original failure with 100% verified credentials.",
      };
    }
    return {
      title: action,
      what: reason || "Executed state machine transition step.",
      why: "Progresses workflow along deterministic recovery graph.",
    };
  }

  return (
    <div className="flex flex-col bg-slate-950 border border-slate-800 rounded-xl overflow-hidden shadow-2xl terminal-glow">
      {/* Terminal Title Bar */}
      <div className="bg-slate-900 px-4 py-2.5 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="flex space-x-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-rose-500/80" />
            <div className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
          </div>
          <span className="text-[11px] font-mono text-slate-400 font-semibold pl-2">
            AGENT REASONING & TRANSITION TERMINAL
          </span>
        </div>

        <div className="flex items-center space-x-2">
          {isLive && (
            <span className="flex items-center space-x-1.5 text-[10px] font-mono text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 pulse-dot" />
              <span>LIVE TELEMETRY</span>
            </span>
          )}
          <span className="text-[10px] font-mono text-slate-500">{events.length} actions</span>
        </div>
      </div>

      {/* Terminal Body */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="p-4 overflow-y-auto font-mono text-xs space-y-3 max-h-[360px] bg-slate-950/95"
      >
        {events.length === 0 ? (
          <div className="text-slate-600 italic py-8 text-center">
            Awaiting agent execution telemetry for this case...
          </div>
        ) : (
          events.map((ev, idx) => {
            const actorInfo = getActorBadge(ev.event_type);
            const Icon = actorInfo.icon;
            const desc = getActionDescription(ev.action, ev.target, ev.reason);
            const timeStr = ev.timestamp
              ? new Date(ev.timestamp).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                })
              : "00:00:00";

            return (
              <div
                key={ev.id || idx}
                className="flex items-start space-x-3 p-3 rounded-xl bg-slate-900/50 hover:bg-slate-900/90 border border-slate-800/80 transition shadow-sm"
              >
                {/* Timestamp */}
                <span className="text-slate-500 text-[11px] flex-shrink-0 pt-0.5 font-mono">{timeStr}</span>

                {/* Actor Badge */}
                <span
                  className={`flex items-center space-x-1 text-[10px] uppercase font-semibold px-2 py-0.5 rounded border flex-shrink-0 ${actorInfo.bg}`}
                >
                  <Icon className="w-3 h-3" />
                  <span>{actorInfo.label}</span>
                </span>

                {/* Event Action & Descriptive Callout */}
                <div className="flex-1 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-white font-bold tracking-tight text-xs">{desc.title}</span>
                    <span className="text-[10px] font-mono text-slate-500 px-1.5 py-0.5 rounded bg-slate-950 border border-slate-850">
                      {ev.action}
                    </span>
                  </div>

                  <p className="text-slate-300 text-[11px] leading-relaxed font-sans">
                    <span className="text-emerald-400 font-mono font-semibold text-[10px] mr-1">[WHAT]</span>
                    {desc.what}
                  </p>

                  <p className="text-slate-400 text-[11px] leading-relaxed font-sans">
                    <span className="text-razor-400 font-mono font-semibold text-[10px] mr-1">[WHY]</span>
                    {desc.why}
                  </p>

                  {/* Hash signature badge */}
                  <div className="flex items-center space-x-3 pt-1 text-[10px] text-slate-500 font-mono border-t border-slate-850/60 mt-1">
                    <span className="truncate max-w-[200px]" title={ev.event_hash}>
                      hash: {ev.event_hash.slice(0, 16)}...
                    </span>
                    {ev.approval_required && (
                      <span className="text-amber-400 font-semibold bg-amber-950/60 px-1.5 py-0.2 rounded border border-amber-800/60">
                        POLICY: APPROVAL_REQUIRED
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}

        {/* Blinking Prompt Line */}
        <div className="flex items-center space-x-2 text-slate-600 pt-1">
          <span className="text-razor-500 font-bold">&gt;</span>
          <span className="text-[11px]">razorpayx-agent daemon running</span>
          <span className="w-2 h-4 bg-razor-400 inline-block animate-pulse" />
        </div>
      </div>
    </div>
  );
};
