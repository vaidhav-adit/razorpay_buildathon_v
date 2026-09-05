"use client";

import React, { useState, useEffect, useRef } from "react";
import { VendorMessage } from "@/lib/types";
import { MessageSquare, ChevronUp, ChevronDown, Send, Bot, User, CheckCheck, Sparkles } from "lucide-react";

interface VendorChatDrawerProps {
  caseId: string;
  vendorName: string;
  messages: VendorMessage[];
  onSimulateVendorReply: (replyText: string) => void;
  isOpen: boolean;
  onToggle: () => void;
  isSending?: boolean;
}

export const VendorChatDrawer: React.FC<VendorChatDrawerProps> = ({
  caseId,
  vendorName,
  messages,
  onSimulateVendorReply,
  isOpen,
  onToggle,
  isSending,
}) => {
  const [customReply, setCustomReply] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isOpen]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customReply.trim()) return;
    onSimulateVendorReply(customReply.trim());
    setCustomReply("");
  };

  const quickTemplates = [
    "Here are our updated banking details: Account 987654321098, IFSC HDFC0001234, Name: Acme Industrial Supplies.",
    "Our bank account has changed to ICICI Bank. Account number is 001122334455, IFSC ICIC0000001.",
    "Sorry, please use our current account: Account 112233445566, IFSC SBIN0001234.",
  ];

  return (
    <div className="fixed bottom-0 left-0 right-0 z-30 flex flex-col pointer-events-none">
      <div className="max-w-[1720px] w-full mx-auto px-6 pointer-events-auto">
        {/* Slide-up Container */}
        <div
          className={`bg-slate-900 border-x border-t border-slate-750 rounded-t-2xl shadow-2xl transition-all duration-300 ${
            isOpen ? "h-96" : "h-12"
          }`}
        >
          {/* Header Bar / Compact Pill */}
          <div
            onClick={onToggle}
            className="h-12 px-5 flex items-center justify-between cursor-pointer hover:bg-slate-850/80 transition rounded-t-2xl select-none"
          >
            <div className="flex items-center space-x-3">
              <div className="w-7 h-7 rounded-full bg-emerald-600 flex items-center justify-center text-white shadow-md shadow-emerald-600/30">
                <MessageSquare className="w-4 h-4" />
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-xs font-bold text-white font-mono">
                  WhatsApp Vendor Communication Channel
                </span>
                <span className="text-xs text-slate-400 font-mono">({vendorName})</span>
              </div>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                SIMULATOR
              </span>
            </div>

            <div className="flex items-center space-x-3 text-xs text-slate-400 font-mono">
              <span>{messages.length} messages</span>
              {isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
            </div>
          </div>

          {/* Chat Body when open */}
          {isOpen && (
            <div className="flex flex-col h-[calc(100%-48px)] bg-slate-950/90 border-t border-slate-800">
              {/* Message Feed */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3 font-mono text-xs">
                {messages.length === 0 ? (
                  <div className="text-slate-600 text-center py-8 italic">
                    No vendor messages exchanged yet.
                  </div>
                ) : (
                  messages.map((msg) => {
                    const isOutbound = msg.direction === "outbound";
                    return (
                      <div
                        key={msg.id}
                        className={`flex items-start space-x-2 ${
                          isOutbound ? "justify-end" : "justify-start"
                        }`}
                      >
                        {!isOutbound && (
                          <div className="w-6 h-6 rounded-full bg-slate-800 flex items-center justify-center text-slate-300 flex-shrink-0 mt-0.5">
                            <User className="w-3.5 h-3.5" />
                          </div>
                        )}

                        <div
                          className={`max-w-[75%] p-3 rounded-2xl ${
                            isOutbound
                              ? "bg-razor-700 text-white rounded-tr-none shadow-md shadow-razor-700/20"
                              : "bg-slate-850 text-slate-200 rounded-tl-none border border-slate-750"
                          }`}
                        >
                          <div className="flex items-center justify-between space-x-3 mb-1 text-[10px] opacity-80">
                            <span className="font-semibold">
                              {isOutbound ? "AI Exception Agent" : vendorName}
                            </span>
                            <span>
                              {new Date(msg.created_at || Date.now()).toLocaleTimeString([], {
                                hour: "2-digit",
                                minute: "2-digit",
                              })}
                            </span>
                          </div>

                          <p className="leading-relaxed whitespace-pre-wrap">{msg.message_body}</p>

                          {isOutbound && (
                            <div className="flex justify-end pt-1">
                              <CheckCheck className="w-3.5 h-3.5 text-razor-200" />
                            </div>
                          )}
                        </div>

                        {isOutbound && (
                          <div className="w-6 h-6 rounded-full bg-razor-600 flex items-center justify-center text-white flex-shrink-0 mt-0.5">
                            <Bot className="w-3.5 h-3.5" />
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Quick Preset Replies & Input Bar */}
              <div className="p-3 bg-slate-900 border-t border-slate-800 space-y-2">
                {/* Preset Chips */}
                <div className="flex items-center space-x-2 overflow-x-auto pb-1 text-[11px] font-mono">
                  <span className="text-slate-500 flex items-center space-x-1 flex-shrink-0">
                    <Sparkles className="w-3 h-3 text-amber-400" />
                    <span>Preset Replies:</span>
                  </span>
                  {quickTemplates.map((tmpl, idx) => (
                    <button
                      key={idx}
                      onClick={() => onSimulateVendorReply(tmpl)}
                      disabled={isSending}
                      className="px-2.5 py-1 rounded-md bg-slate-800 hover:bg-slate-750 border border-slate-700 text-slate-300 text-[10px] whitespace-nowrap transition disabled:opacity-50"
                    >
                      {tmpl.slice(0, 36)}...
                    </button>
                  ))}
                </div>

                {/* Custom Message Input Form */}
                <form onSubmit={handleSend} className="flex items-center space-x-2">
                  <input
                    type="text"
                    value={customReply}
                    onChange={(e) => setCustomReply(e.target.value)}
                    placeholder="Simulate custom vendor reply (e.g. IFSC code, bank account number)..."
                    disabled={isSending}
                    className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-razor-500 transition font-mono"
                  />
                  <button
                    type="submit"
                    disabled={isSending || !customReply.trim()}
                    className="flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white text-xs font-semibold shadow-md shadow-emerald-600/30 transition font-mono"
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span>Send Reply</span>
                  </button>
                </form>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
