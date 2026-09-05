"use client";

import React, { useState } from "react";
import { simulateCase } from "@/lib/api";
import {
  PlayCircle,
  AlertTriangle,
  Sparkles,
  X,
  CreditCard,
  Building2,
  Eye,
  Zap,
} from "lucide-react";

interface SimulateCaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCaseCreated: (caseId: string) => void;
}

const PRESET_SIMULATIONS = [
  {
    title: "Live Zoho Connected: Acme Industrial Logistics",
    category: "Live Integration",
    vendor_name: "Acme Industrial Logistics",
    contact_id: "cont_TY3jX5qQmhCpa8",
    zoho_vendor_id: "VEND-ACME-8801",
    amount: 25000000, // INR 2,50,000
    failure_source: "beneficiary_bank",
    failure_reason: "invalid_ifsc_code",
    invoice_reference: "INV-2026-8801",
  },
  {
    title: "Live Razorpay Test Contact: Test Vendor Pvt Ltd",
    category: "Live Integration",
    vendor_name: "Test Vendor Pvt Ltd",
    contact_id: "cont_TY3jX5qQmhCpa8",
    zoho_vendor_id: "VEND-TEST-001",
    amount: 15000000, // INR 1,50,000
    failure_source: "beneficiary_bank",
    failure_reason: "invalid_ifsc_code",
    invoice_reference: "INV-2026-9901",
  },
  {
    title: "Golden Path: Invalid IFSC Code",
    category: "Remediation",
    vendor_name: "Apex Logistics India Pvt Ltd",
    contact_id: "",
    zoho_vendor_id: "",
    amount: 20000000, // INR 2,00,000
    failure_source: "beneficiary_bank",
    failure_reason: "invalid_ifsc_code",
    invoice_reference: "INV-2026-8802",
  },
  {
    title: "Closed Bank Account",
    category: "Remediation",
    vendor_name: "Bharat Electro Tech Solutions",
    contact_id: "",
    zoho_vendor_id: "",
    amount: 17500000, // INR 1,75,000
    failure_source: "beneficiary_bank",
    failure_reason: "bank_account_closed",
    invoice_reference: "INV-2026-8803",
  },
  {
    title: "Beneficiary Bank Offline (Retry Strategy)",
    category: "Autonomous Retry",
    vendor_name: "Deccan Steel Corporation",
    contact_id: "",
    zoho_vendor_id: "",
    amount: 42000000, // INR 4,20,000
    failure_source: "beneficiary_bank",
    failure_reason: "beneficiary_bank_offline",
    invoice_reference: "INV-2026-8804",
  },
  {
    title: "Insufficient Balance (Finance Escalation)",
    category: "Escalation",
    vendor_name: "Zenith Cloud Hosting Services",
    contact_id: "",
    zoho_vendor_id: "",
    amount: 85000000, // INR 8,50,000
    failure_source: "business",
    failure_reason: "insufficient_funds",
    invoice_reference: "INV-2026-8805",
  },
  {
    title: "Frozen Account (Deterministic Hard Block)",
    category: "Fraud Block",
    vendor_name: "Shadow Operations Corp",
    contact_id: "",
    zoho_vendor_id: "",
    amount: 99000000, // INR 9,90,000
    failure_source: "beneficiary_bank",
    failure_reason: "bank_account_frozen",
    invoice_reference: "INV-2026-8806",
  },
];

export const SimulateCaseModal: React.FC<SimulateCaseModalProps> = ({
  isOpen,
  onClose,
  onCaseCreated,
}) => {
  const [vendorName, setVendorName] = useState("Acme Industrial Logistics");
  const [contactId, setContactId] = useState("cont_TY3jX5qQmhCpa8");
  const [zohoVendorId, setZohoVendorId] = useState("VEND-ACME-8801");
  const [amountPaise, setAmountPaise] = useState(25000000);
  const [failureSource, setFailureSource] = useState("beneficiary_bank");
  const [failureReason, setFailureReason] = useState("invalid_ifsc_code");
  const [invoiceRef, setInvoiceRef] = useState("INV-2026-8801");
  const [autoRunTurn1, setAutoRunTurn1] = useState(false); // Default to false for Live Watch Mode
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleApplyPreset = (preset: typeof PRESET_SIMULATIONS[0]) => {
    setVendorName(preset.vendor_name);
    setContactId(preset.contact_id);
    setZohoVendorId(preset.zoho_vendor_id);
    setAmountPaise(preset.amount);
    setFailureSource(preset.failure_source);
    setFailureReason(preset.failure_reason);
    setInvoiceRef(preset.invoice_reference);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const newCase = await simulateCase({
        vendor_name: vendorName,
        contact_id: contactId || undefined,
        zoho_vendor_id: zohoVendorId || undefined,
        amount: amountPaise,
        failure_source: failureSource,
        failure_reason: failureReason,
        invoice_reference: invoiceRef,
        auto_run_turn1: autoRunTurn1,
      });
      onCaseCreated(newCase.id);
      onClose();
    } catch (err) {
      console.error("Simulation error", err);
      alert("Failed to simulate case: " + err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
      <div className="bg-slate-900 border border-slate-750 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-5 font-mono text-xs">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-razor-600/20 border border-razor-500/40 flex items-center justify-center text-razor-400">
              <PlayCircle className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                Simulate Payout Exception Case
              </h2>
              <p className="text-[11px] text-slate-400">
                Trigger an autonomous recovery workflow with real connected systems or presets
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="w-7 h-7 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white flex items-center justify-center transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Preset Selection Strip */}
        <div>
          <span className="text-[11px] font-bold uppercase text-slate-400 mb-2 block flex items-center space-x-1.5">
            <Sparkles className="w-3.5 h-3.5 text-razor-400" />
            <span>Select Scenario Preset</span>
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-44 overflow-y-auto pr-1">
            {PRESET_SIMULATIONS.map((preset, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleApplyPreset(preset)}
                className={`p-2 rounded-lg text-left border transition flex flex-col justify-between ${
                  vendorName === preset.vendor_name && failureReason === preset.failure_reason
                    ? "bg-razor-950/70 border-razor-500 text-white ring-1 ring-razor-500"
                    : "bg-slate-950 hover:bg-slate-850 border-slate-800 text-slate-300"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-[11px] text-white truncate">{preset.title}</span>
                  <span className="text-[9px] uppercase px-1.5 py-0.2 rounded bg-slate-800 text-razor-300 font-semibold">
                    {preset.category}
                  </span>
                </div>
                <div className="text-[10px] text-slate-400 mt-1 flex justify-between">
                  <span>INR {(preset.amount / 100).toLocaleString("en-IN")}</span>
                  <span className="text-rose-400 font-mono">{preset.failure_reason}</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Simulation Configuration Form */}
        <form onSubmit={handleSubmit} className="space-y-4 pt-2 border-t border-slate-800">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
                Vendor Name
              </label>
              <input
                type="text"
                value={vendorName}
                onChange={(e) => setVendorName(e.target.value)}
                required
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-xs focus:outline-none focus:border-razor-500"
              />
            </div>

            <div>
              <label className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
                Payout Amount (INR)
              </label>
              <input
                type="number"
                value={amountPaise / 100}
                onChange={(e) => setAmountPaise(Math.round(Number(e.target.value) * 100))}
                required
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-xs focus:outline-none focus:border-razor-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
                Failure Source
              </label>
              <select
                value={failureSource}
                onChange={(e) => setFailureSource(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-xs focus:outline-none focus:border-razor-500"
              >
                <option value="beneficiary_bank">beneficiary_bank</option>
                <option value="business">business</option>
                <option value="internal">internal</option>
                <option value="gateway">gateway</option>
              </select>
            </div>

            <div>
              <label className="text-[10px] uppercase font-bold text-slate-400 block mb-1">
                Failure Reason Code
              </label>
              <input
                type="text"
                value={failureReason}
                onChange={(e) => setFailureReason(e.target.value)}
                required
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-200 text-xs focus:outline-none focus:border-razor-500"
              />
            </div>
          </div>

          {/* Execution Mode Toggle: Live Watch Mode vs Instant */}
          <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <Eye className="w-4 h-4 text-razor-400" />
              <div>
                <span className="font-bold text-white block text-[11px]">
                  Live Watch Mode (Recommended)
                </span>
                <span className="text-[10px] text-slate-400">
                  Starts at CASE_CREATED so you can watch the agent reason and step through live
                </span>
              </div>
            </div>
            <input
              type="checkbox"
              checked={!autoRunTurn1}
              onChange={(e) => setAutoRunTurn1(!e.target.checked)}
              className="w-4 h-4 accent-razor-500 cursor-pointer rounded"
            />
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end space-x-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2 rounded-lg bg-razor-600 hover:bg-razor-500 text-white font-bold transition shadow-lg shadow-razor-600/30 active:scale-95 disabled:opacity-50 flex items-center space-x-1.5"
            >
              {isSubmitting ? (
                <>
                  <Zap className="w-3.5 h-3.5 animate-spin" />
                  <span>Ingesting Exception...</span>
                </>
              ) : (
                <>
                  <PlayCircle className="w-3.5 h-3.5" />
                  <span>Launch Recovery Workflow</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
