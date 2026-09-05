"use client";

import React, { useState, useEffect } from "react";
import { AlertTriangle, Trash2, X, RefreshCw, ShieldAlert } from "lucide-react";

interface ResetConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isResetting?: boolean;
}

export const ResetConfirmModal: React.FC<ResetConfirmModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  isResetting,
}) => {
  const [confirmInput, setConfirmInput] = useState("");

  useEffect(() => {
    if (isOpen) {
      setConfirmInput("");
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const isConfirmed = confirmInput.trim().toUpperCase() === "RESET";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-md animate-fadeIn">
      <div className="bg-slate-900 border border-rose-850/60 rounded-2xl max-w-lg w-full p-6 shadow-2xl shadow-rose-950/40 space-y-5 font-mono text-xs">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center space-x-2.5 text-rose-400 font-bold">
            <div className="w-9 h-9 rounded-xl bg-rose-950/80 border border-rose-800 flex items-center justify-center text-rose-400 shadow-inner">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm text-white font-sans font-bold">
                Reset Demo Environment?
              </div>
              <div className="text-[11px] text-rose-400 font-normal">
                Destructive Action • Requires Confirmation
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isResetting}
            className="w-7 h-7 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-400 hover:text-white flex items-center justify-center transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body Text */}
        <div className="space-y-3 text-slate-300 font-sans text-xs">
          <div className="p-3 bg-rose-950/30 border border-rose-850/50 rounded-xl text-rose-200 leading-relaxed font-sans">
            <strong className="font-semibold text-rose-100">Are you sure you want to reset everything?</strong>
            <p className="mt-1 text-[11px] text-rose-300/90 font-mono">
              This will permanently wipe all current session data and return the system to an empty initial state.
            </p>
          </div>

          <ul className="list-disc list-inside space-y-1.5 text-slate-400 text-[11px] font-mono bg-slate-950 p-3.5 rounded-xl border border-slate-800">
            <li>Clears all <span className="text-slate-200 font-semibold">Active & Closed</span> recovery cases</li>
            <li>Wipes simulated <span className="text-slate-200 font-semibold">WhatsApp vendor chats</span> & inbound logs</li>
            <li>Resets the cryptographic <span className="text-slate-200 font-semibold">SHA-256 audit ledger</span> chain to genesis</li>
            <li>Clears pending human authorizations and penny-drop mock records</li>
          </ul>

          {/* Verification Challenge */}
          <div className="pt-2 space-y-1.5 font-mono">
            <label className="text-[11px] text-slate-300 flex items-center justify-between">
              <span>To verify, type <span className="text-rose-400 font-bold bg-rose-950/60 px-1.5 py-0.5 rounded border border-rose-800/60">RESET</span> below:</span>
              <button 
                type="button" 
                onClick={() => setConfirmInput("RESET")}
                className="text-[10px] text-slate-400 hover:text-razor-400 underline underline-offset-2"
              >
                Auto-fill
              </button>
            </label>
            <input
              type="text"
              value={confirmInput}
              onChange={(e) => setConfirmInput(e.target.value)}
              placeholder='Type "RESET" to confirm'
              disabled={isResetting}
              autoFocus
              className="w-full bg-slate-950 border border-slate-750 focus:border-rose-500 rounded-lg px-3 py-2 text-white font-mono text-xs focus:outline-none transition uppercase tracking-wider placeholder:text-slate-600"
            />
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-800 font-mono">
          <button
            type="button"
            onClick={onClose}
            disabled={isResetting}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-750 text-slate-300 transition text-xs font-medium"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={!isConfirmed || isResetting}
            className={`px-4 py-2 rounded-lg font-bold transition shadow-lg flex items-center space-x-1.5 text-xs active:scale-95 ${
              isConfirmed && !isResetting
                ? "bg-rose-600 hover:bg-rose-500 text-white shadow-rose-600/30 cursor-pointer"
                : "bg-slate-800 text-slate-400 border border-slate-750 opacity-60 cursor-not-allowed"
            }`}
          >
            {isResetting ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Resetting State...</span>
              </>
            ) : (
              <>
                <Trash2 className="w-3.5 h-3.5" />
                <span>Yes, Reset All Cases</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

