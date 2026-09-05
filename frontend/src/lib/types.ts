/**
 * types.ts
 * ────────
 * TypeScript definitions mirroring backend Pydantic models.
 */

export interface CaseListItem {
  id: string;
  case_number: string;
  payout_id: string;
  vendor_id?: string;
  vendor_name?: string;
  amount: number;
  amount_inr: number;
  failure_source: string;
  failure_reason: string;
  recovery_strategy?: string;
  state: string;
  risk_level: string;
  created_at: string;
  updated_at: string;
}

export interface CaseVendorContext {
  id: string;
  name: string;
  email?: string;
  phone?: string;
  zoho_vendor_id?: string;
}

export interface CasePayoutContext {
  id: string;
  razorpay_payout_id: string;
  amount: number;
  currency: string;
  status: string;
  mode: string;
}

export interface CaseApprovalContext {
  id: string;
  action: string;
  status: string;
  decision?: string;
  requested_at: string;
  decided_at?: string;
  decided_by?: string;
  payload?: {
    case_number?: string;
    vendor_id?: string;
    contact_id?: string;
    old_fund_account_id?: string;
    new_fund_account_id?: string;
    amount_paise?: number;
    amount_inr?: number;
    name_match_score?: number;
    validation_status?: string;
    notes?: string;
  };
}

export interface CaseDetail {
  id: string;
  case_number: string;
  state: string;
  risk_level: string;
  amount: number;
  amount_inr: number;
  failure_source: string;
  failure_reason: string;
  recovery_strategy?: string;
  invoice_reference?: string;
  action_count: number;
  human_intervention_count: number;
  created_at: string;
  updated_at: string;
  vendor?: CaseVendorContext;
  payout?: CasePayoutContext;
  approval?: CaseApprovalContext;
  audit_verification: {
    status: string;
    is_valid: boolean;
    total_events: number;
    details: string;
  };
}

export interface AuditEventItem {
  id: string;
  case_id: string;
  event_type: string;
  actor: string;
  action: string;
  target?: string;
  reason?: string;
  input_hash?: string;
  output_hash?: string;
  approval_required: boolean;
  previous_hash: string;
  event_hash: string;
  timestamp?: string;
}

export interface AuditChainResponse {
  case_id: string;
  verification: {
    case_id: string;
    status: string;
    is_valid: boolean;
    total_events: number;
    details: string;
  };
  events: AuditEventItem[];
}

export interface VendorMessage {
  id: string;
  case_id: string;
  vendor_id: string;
  direction: "outbound" | "inbound" | "OUTBOUND" | "INBOUND" | string;
  channel?: string;
  body?: string;
  message_body?: string;
  extracted_data?: Record<string, any>;
  timestamp?: string;
  created_at?: string;
}

export interface ScenarioDefinition {
  scenario_id: string;
  name: string;
  vendor_name: string;
  amount: number;
  invoice_reference: string;
  failure_source: string;
  failure_reason: string;
  expected_strategy: string;
  expected_final_state: string;
  vendor_reply_text?: string;
  override_settings?: Record<string, any>;
  is_adversarial: boolean;
}

export interface ScenarioExecutionResult {
  scenario_id: string;
  name: string;
  passed: boolean;
  initial_state: string;
  final_state: string;
  expected_final_state: string;
  failure_source: string;
  failure_reason: string;
  strategy_selected: string;
  expected_strategy: string;
  diagnosis_correct: boolean;
  strategy_correct: boolean;
  policy_compliant: boolean;
  unauthorized_financial_actions: number;
  data_extraction_correct: boolean;
  audit_chain_verified: boolean;
  total_agent_actions: number;
  execution_time_ms: number;
  error_message?: string;
  vendor_name?: string;
  amount?: number;
  invoice_reference?: string;
  vendor_reply_text?: string;
  actions?: Array<{
    id: string;
    tool_name: string;
    actor: string;
    policy_level: number;
    policy_decision: string;
    input_payload: any;
    output_payload: any;
    timestamp: string;
  }>;
  audit_events?: Array<{
    id: string;
    event_type: string;
    actor: string;
    action: string;
    target?: string;
    reason?: string;
    event_hash: string;
    previous_hash: string;
    approval_required: boolean;
    timestamp: string;
  }>;
  narrative?: string;
}

export interface EvaluationReport {
  timestamp: string;
  total_scenarios: number;
  passed_scenarios: number;
  failed_scenarios: number;
  overall_pass_rate_percent: number;
  diagnosis_accuracy_percent: number;
  strategy_accuracy_percent: number;
  policy_compliance_percent: number;
  data_extraction_accuracy_percent: number;
  unauthorized_financial_actions_count: number;
  all_targets_met: boolean;
  results: ScenarioExecutionResult[];
  summary_table: string;
}
