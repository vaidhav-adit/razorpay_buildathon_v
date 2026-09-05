/**
 * api.ts
 * ──────
 * HTTP API client for communication with the FastAPI backend.
 */

import {
  CaseListItem,
  CaseDetail,
  AuditChainResponse,
  VendorMessage,
  ScenarioDefinition,
  EvaluationReport,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
  });

  if (!res.ok) {
    let errorDetail = "API Error";
    try {
      const err = await res.json();
      errorDetail = err.detail || err.message || JSON.stringify(err);
    } catch {
      errorDetail = `HTTP ${res.status}: ${res.statusText}`;
    }
    throw new Error(errorDetail);
  }

  return res.json() as Promise<T>;
}

// ── Health Check ─────────────────────────────────────────────────────────────
export async function getHealth(): Promise<{ status: string }> {
  return fetchJSON<{ status: string }>(`${API_BASE}/health`);
}

// ── Case Management ──────────────────────────────────────────────────────────
export async function getCases(state?: string): Promise<CaseListItem[]> {
  const url = state ? `${API_BASE}/cases?state=${encodeURIComponent(state)}` : `${API_BASE}/cases`;
  return fetchJSON<CaseListItem[]>(url);
}

export async function getCaseDetail(caseId: string): Promise<CaseDetail> {
  return fetchJSON<CaseDetail>(`${API_BASE}/cases/${caseId}`);
}

export async function approveCase(
  caseId: string,
  notes?: string,
  decidedBy = "finance_controller"
): Promise<any> {
  return fetchJSON(`${API_BASE}/cases/${caseId}/approve`, {
    method: "POST",
    body: JSON.stringify({ decided_by: decidedBy, notes }),
  });
}

export async function rejectCase(
  caseId: string,
  reason: string,
  decidedBy = "finance_controller"
): Promise<any> {
  return fetchJSON(`${API_BASE}/cases/${caseId}/reject`, {
    method: "POST",
    body: JSON.stringify({ reason, decided_by: decidedBy }),
  });
}

export async function processCase(
  caseId: string,
  vendorReply?: string
): Promise<CaseDetail> {
  return fetchJSON<CaseDetail>(`${API_BASE}/cases/${caseId}/process`, {
    method: "POST",
    body: JSON.stringify({ vendor_reply: vendorReply || null }),
  });
}

export async function stepCase(
  caseId: string,
  vendorReply?: string
): Promise<CaseDetail> {
  return fetchJSON<CaseDetail>(`${API_BASE}/cases/${caseId}/step`, {
    method: "POST",
    body: JSON.stringify({ vendor_reply: vendorReply || null, single_step: true }),
  });
}

export async function simulateCase(payload: {
  vendor_name?: string;
  contact_id?: string;
  zoho_vendor_id?: string;
  amount?: number;
  failure_source?: string;
  failure_reason?: string;
  invoice_reference?: string;
  auto_run_turn1?: boolean;
}): Promise<CaseDetail> {
  return fetchJSON<CaseDetail>(`${API_BASE}/cases/simulate`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function resetCases(): Promise<{ status: string; message: string }> {
  return fetchJSON<{ status: string; message: string }>(`${API_BASE}/cases/reset`, {
    method: "POST",
  });
}

// ── Audit Ledger ─────────────────────────────────────────────────────────────
export async function getCaseAudit(caseId: string): Promise<AuditChainResponse> {
  return fetchJSON<AuditChainResponse>(`${API_BASE}/cases/${caseId}/audit`);
}

// ── Vendor Communication ─────────────────────────────────────────────────────
export async function getCaseMessages(caseId: string): Promise<VendorMessage[]> {
  return fetchJSON<VendorMessage[]>(`${API_BASE}/vendor/messages/${caseId}`);
}

export async function sendVendorMessage(
  caseId: string,
  vendorId: string,
  messageBody: string
): Promise<VendorMessage> {
  return fetchJSON<VendorMessage>(`${API_BASE}/vendor/message/send`, {
    method: "POST",
    body: JSON.stringify({
      case_id: caseId,
      vendor_id: vendorId,
      message_body: messageBody,
    }),
  });
}

export async function receiveVendorMessage(
  caseId: string,
  vendorId: string,
  messageBody: string
): Promise<VendorMessage> {
  return fetchJSON<VendorMessage>(`${API_BASE}/vendor/message/receive`, {
    method: "POST",
    body: JSON.stringify({
      case_id: caseId,
      vendor_id: vendorId,
      message_body: messageBody,
    }),
  });
}

// ── Evaluation Benchmark ─────────────────────────────────────────────────────
export async function getEvaluationScenarios(): Promise<ScenarioDefinition[]> {
  return fetchJSON<ScenarioDefinition[]>(`${API_BASE}/evaluation/scenarios`);
}

export async function runEvaluation(scenarioId?: string): Promise<EvaluationReport> {
  const url = scenarioId
    ? `${API_BASE}/evaluation/run?scenario_id=${encodeURIComponent(scenarioId)}`
    : `${API_BASE}/evaluation/run`;
  return fetchJSON<EvaluationReport>(url, {
    method: "POST",
    body: JSON.stringify({ scenario_id: scenarioId || null }),
  });
}
