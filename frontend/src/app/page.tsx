"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { CaseListItem, CaseDetail, AuditChainResponse, VendorMessage } from "@/lib/types";
import {
  getCases,
  getCaseDetail,
  getCaseAudit,
  getCaseMessages,
  processCase,
  stepCase,
  receiveVendorMessage,
  approveCase,
  rejectCase,
  getHealth,
  resetCases,
} from "@/lib/api";

import { Navbar } from "@/components/Navbar";
import { CaseListSidebar } from "@/components/CaseListSidebar";
import { CaseHeaderStrip } from "@/components/CaseHeaderStrip";
import { StatePipelineVisualizer } from "@/components/StatePipelineVisualizer";
import { LiveGuidanceBanner } from "@/components/LiveGuidanceBanner";
import { AgentActionTerminal } from "@/components/AgentActionTerminal";
import { VendorCommunicationHub } from "@/components/VendorCommunicationHub";
import { AuditTimelineTable } from "@/components/AuditTimelineTable";
import { ContextDrawer } from "@/components/ContextDrawer";
import { FloatingApprovalModal } from "@/components/FloatingApprovalModal";
import { ClosedCasesView } from "@/components/ClosedCasesView";
import { EvaluationView } from "@/components/EvaluationView";
import { SimulateCaseModal } from "@/components/SimulateCaseModal";
import { ResetConfirmModal } from "@/components/ResetConfirmModal";

export default function MissionControlDashboard() {
  const [activeTab, setActiveTab] = useState<"active" | "closed" | "evaluation">("active");
  const [backendOnline, setBackendOnline] = useState(true);
  const [allCases, setAllCases] = useState<CaseListItem[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null);
  const [auditData, setAuditData] = useState<AuditChainResponse | null>(null);
  const [vendorMessages, setVendorMessages] = useState<VendorMessage[]>([]);

  const [isProcessing, setIsProcessing] = useState(false);
  const [isAutoPlaying, setIsAutoPlaying] = useState(false);
  const [isSendingReply, setIsSendingReply] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [isSimulateOpen, setIsSimulateOpen] = useState(false);
  const [isResetModalOpen, setIsResetModalOpen] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const autoPlayRef = useRef(false);

  // ── 1. Fetch Cases and Health ──────────────────────────────────────────────
  const loadCases = useCallback(async () => {
    try {
      const [health, cases] = await Promise.all([
        getHealth().catch(() => ({ status: "offline" })),
        getCases(),
      ]);
      setBackendOnline(health.status === "healthy" || health.status === "ok");
      setAllCases(cases);

      // Auto-select first active case if none selected
      if (!selectedCaseId && cases.length > 0) {
        const firstActive =
          cases.find((c) => c.state !== "CASE_RESOLVED" && c.state !== "BLOCKED") || cases[0];
        setSelectedCaseId(firstActive.id);
      }
    } catch (err) {
      console.error("Failed to fetch cases", err);
      setBackendOnline(false);
    }
  }, [selectedCaseId]);

  // ── 2. Fetch Selected Case Detail, Audit, and Messages ─────────────────────
  const loadSelectedCaseData = useCallback(async (caseId: string) => {
    try {
      const [detail, audit, msgs] = await Promise.all([
        getCaseDetail(caseId),
        getCaseAudit(caseId),
        getCaseMessages(caseId),
      ]);
      setCaseDetail(detail);
      setAuditData(audit);
      setVendorMessages(msgs);
    } catch (err) {
      console.error(`Failed to load case data for ${caseId}`, err);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadCases();
  }, [loadCases]);

  // Selected case sync
  useEffect(() => {
    if (selectedCaseId) {
      loadSelectedCaseData(selectedCaseId);
    }
  }, [selectedCaseId, loadSelectedCaseData]);

  // Background telemetry refresh
  useEffect(() => {
    const timer = setInterval(() => {
      if (!isProcessing && !isAutoPlaying) {
        loadCases();
        if (selectedCaseId) {
          loadSelectedCaseData(selectedCaseId);
        }
      }
    }, 4000);
    return () => clearInterval(timer);
  }, [loadCases, loadSelectedCaseData, selectedCaseId, isProcessing, isAutoPlaying]);

  const handleManualRefresh = async () => {
    setIsRefreshing(true);
    await loadCases();
    if (selectedCaseId) {
      await loadSelectedCaseData(selectedCaseId);
    }
    setIsRefreshing(false);
  };

  // ── 3. Step-by-Step Execution ──────────────────────────────────────────────
  const handleRunStep = async () => {
    if (!selectedCaseId) return;
    if (caseDetail?.state === "HUMAN_APPROVAL" || caseDetail?.state === "HUMAN_REVIEW") {
      await handleApprove("Approved via Mission Control Single Step");
      return;
    }
    setIsProcessing(true);
    try {
      const updated = await stepCase(selectedCaseId);
      setCaseDetail(updated);
      await Promise.all([loadSelectedCaseData(selectedCaseId), loadCases()]);
    } catch (err) {
      console.error("Step execution failed", err);
      alert("Step Execution Failed: " + err);
    } finally {
      setIsProcessing(false);
    }
  };

  // ── 4. Live Visual Auto-Play Flow ──────────────────────────────────────────
  const handleRunAutoPlay = async () => {
    if (!selectedCaseId) return;
    if (caseDetail?.state === "HUMAN_APPROVAL" || caseDetail?.state === "HUMAN_REVIEW") {
      await handleApprove("Approved via Mission Control Auto-Play");
      return;
    }
    if (isAutoPlaying) {
      autoPlayRef.current = false;
      setIsAutoPlaying(false);
      return;
    }

    autoPlayRef.current = true;
    setIsAutoPlaying(true);

    let maxSteps = 10;
    let currentStep = 0;

    while (autoPlayRef.current && currentStep < maxSteps) {
      currentStep++;
      try {
        const updated = await stepCase(selectedCaseId);
        setCaseDetail(updated);
        await Promise.all([loadSelectedCaseData(selectedCaseId), loadCases()]);

        // Break if reached terminal or pause state
        if (
          updated.state === "VENDOR_CONTACTED" ||
          updated.state === "HUMAN_APPROVAL" ||
          updated.state === "HUMAN_REVIEW" ||
          updated.state === "BLOCKED" ||
          updated.state === "CASE_RESOLVED"
        ) {
          break;
        }

        // Pacing delay between steps so user sees agent work live
        await new Promise((r) => setTimeout(r, 700));
      } catch (err) {
        console.error("Auto-play step failed", err);
        break;
      }
    }

    autoPlayRef.current = false;
    setIsAutoPlaying(false);
  };

  // ── 5. Run Full Turn ───────────────────────────────────────────────────────
  const handleProcessTurn = async () => {
    if (!selectedCaseId) return;
    setIsProcessing(true);
    try {
      const updated = await processCase(selectedCaseId);
      setCaseDetail(updated);
      await Promise.all([loadSelectedCaseData(selectedCaseId), loadCases()]);
    } catch (err) {
      console.error("Process turn failed", err);
      alert("Agent Turn Failed: " + err);
    } finally {
      setIsProcessing(false);
    }
  };

  // ── 6. Simulate Vendor Reply ───────────────────────────────────────────────
  const handleSimulateVendorReply = async (replyText: string) => {
    if (!selectedCaseId || !caseDetail) return;
    setIsSendingReply(true);
    try {
      // 1. Send inbound vendor message to DB
      await receiveVendorMessage(
        selectedCaseId,
        caseDetail.vendor?.id || "vend_unknown",
        replyText
      );

      // 2. Fetch messages immediately to render the vendor bubble
      const updatedMsgs = await getCaseMessages(selectedCaseId);
      setVendorMessages(updatedMsgs);

      // 3. Trigger live agent step processing
      await handleRunAutoPlay();
    } catch (err) {
      console.error("Simulate vendor reply failed", err);
      alert("Failed to process vendor reply: " + err);
    } finally {
      setIsSendingReply(false);
    }
  };

  // ── 7. Human Authorization & Rejection ─────────────────────────────────────
  const handleApprove = async (notes?: string) => {
    if (!selectedCaseId) return;
    setIsApproving(true);
    try {
      await approveCase(selectedCaseId, notes);
      await Promise.all([loadSelectedCaseData(selectedCaseId), loadCases()]);

      // Complete settlement reconciliation to CASE_RESOLVED
      try {
        await stepCase(selectedCaseId);
        await Promise.all([loadSelectedCaseData(selectedCaseId), loadCases()]);
      } catch {
        // already terminal
      }
    } catch (err) {
      console.error("Approve failed", err);
      alert("Human Approval Failed: " + err);
    } finally {
      setIsApproving(false);
    }
  };

  const handleReject = async (reason: string) => {
    if (!selectedCaseId) return;
    setIsApproving(true);
    try {
      await rejectCase(selectedCaseId, reason);
      await Promise.all([loadSelectedCaseData(selectedCaseId), loadCases()]);
    } catch (err) {
      console.error("Reject failed", err);
      alert("Rejection Failed: " + err);
    } finally {
      setIsApproving(false);
    }
  };

  const handleCaseCreated = (newCaseId: string) => {
    setSelectedCaseId(newCaseId);
    loadCases();
    loadSelectedCaseData(newCaseId);
  };

  const handleOpenResetModal = () => {
    setIsResetModalOpen(true);
  };

  const handleConfirmReset = async () => {
    setIsResetting(true);
    try {
      await resetCases();
      setSelectedCaseId(null);
      setCaseDetail(null);
      setAuditData(null);
      setVendorMessages([]);
      await loadCases();
      setIsResetModalOpen(false);
    } catch (err) {
      console.error("Reset failed", err);
      alert("Failed to reset cases: " + err);
    } finally {
      setIsResetting(false);
    }
  };

  const activeCases = allCases.filter(
    (c) => c.state !== "CASE_RESOLVED" && c.state !== "BLOCKED"
  );

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100 selection:bg-razor-600">
      {/* Global Top Navbar */}
      <Navbar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        backendOnline={backendOnline}
        activeCount={activeCases.length}
        onOpenSimulate={() => setIsSimulateOpen(true)}
        onRefresh={handleManualRefresh}
        onResetAll={handleOpenResetModal}
        isRefreshing={isRefreshing}
      />

      {/* ── View 1: Active Cases Mission Control Workspace ─────────────────── */}
      <main className={`flex-1 flex overflow-hidden ${activeTab === "active" ? "" : "hidden"}`}>
        {/* Left: Case List Sidebar */}
        <CaseListSidebar
          cases={activeCases}
          selectedCaseId={selectedCaseId}
          onSelectCase={(id) => setSelectedCaseId(id)}
        />

        {/* Center: Main Working Area */}
        <div className="flex-1 flex flex-col h-[calc(100vh-61px)] overflow-y-auto bg-slate-950 pb-20">
          {caseDetail && auditData ? (
            <div className="flex-1 flex flex-col">
              {/* Visual 9-State Machine Progress Stepper */}
              <StatePipelineVisualizer
                caseData={caseDetail}
                onRunStep={handleRunStep}
                onRunAutoPlay={handleRunAutoPlay}
                isAutoPlaying={isAutoPlaying}
                isProcessing={isProcessing}
              />

              {/* Plain-English Live Guidance & Action Banner */}
              <LiveGuidanceBanner
                caseData={caseDetail}
                onRunStep={handleRunStep}
                onRunAutoPlay={handleRunAutoPlay}
                onSimulateVendorReply={handleSimulateVendorReply}
                onApprove={handleApprove}
                isProcessing={isProcessing}
                isAutoPlaying={isAutoPlaying}
              />

              {/* Case Metadata Strip */}
              <CaseHeaderStrip
                caseData={caseDetail}
                onProcessTurn={handleProcessTurn}
                isProcessing={isProcessing || isAutoPlaying}
              />

              {/* Main Content Workspace Grid */}
              <div className="p-6 space-y-6 max-w-[1500px] w-full mx-auto">
                {/* Real-Time Agent Action Terminal */}
                <AgentActionTerminal
                  events={auditData.events}
                  isLive={backendOnline}
                />

                {/* Dual-Pane Vendor Communication & Remediation Hub */}
                <VendorCommunicationHub
                  caseData={caseDetail}
                  messages={vendorMessages}
                  onSimulateVendorReply={handleSimulateVendorReply}
                  isSending={isSendingReply || isProcessing || isAutoPlaying}
                />

                {/* Cryptographic Audit Ledger Table */}
                <AuditTimelineTable
                  events={auditData.events}
                  verification={auditData.verification}
                />
              </div>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center p-12 text-center text-slate-500 font-mono text-xs">
              Select an exception case from the left queue to inspect real-time agent reasoning.
            </div>
          )}
        </div>

        {/* Right: Context & Live Integrations Drawer */}
        {caseDetail && <ContextDrawer caseData={caseDetail} />}

        {/* Floating Level 3 Human Payout Authorization Modal */}
        {caseDetail && (
          <FloatingApprovalModal
            caseData={caseDetail}
            onApprove={handleApprove}
            onReject={handleReject}
            isSubmitting={isApproving}
          />
        )}
      </main>

      {/* ── View 2: Closed Cases Archive ──────────────────────────────────── */}
      <div className={`flex-1 ${activeTab === "closed" ? "" : "hidden"}`}>
        <ClosedCasesView cases={allCases} />
      </div>

      {/* ── View 3: Benchmark Evaluation Suite ────────────────────────────── */}
      <div className={`flex-1 ${activeTab === "evaluation" ? "" : "hidden"}`}>
        <EvaluationView />
      </div>

      {/* Simulate Exception Modal */}
      <SimulateCaseModal
        isOpen={isSimulateOpen}
        onClose={() => setIsSimulateOpen(false)}
        onCaseCreated={handleCaseCreated}
      />

      {/* In-App Confirmation Modal for Reset State */}
      <ResetConfirmModal
        isOpen={isResetModalOpen}
        onClose={() => setIsResetModalOpen(false)}
        onConfirm={handleConfirmReset}
        isResetting={isResetting}
      />
    </div>
  );
}
