// Mirrors InvestigationState in fraud_investigation_demo.py — only the fields the
// UI actually reads are typed strictly, the rest are left loose.
export interface InvestigationState {
  [key: string]: unknown;
  case_id: string;
  account_id: string;
  alert: Record<string, unknown>;
  case_metadata: Record<string, unknown>;
  route_plan: string[];
  specialists_run: string[];
  findings: Record<string, unknown>;
  sar_draft: Record<string, unknown>;
  denial_log: unknown[];
  orchestration_steps: number;
  final_decision: string;
}

export interface ToolCallEvent {
  type: "tool_call";
  role: string;
  tool: string;
  key: string;
  status: "allowed" | "denied";
  reason: string | null;
}

export interface RoutingEvent {
  type: "routing";
  stage: "initial" | "review";
  route?: string[];
  next?: string;
  reason?: string;
}

export interface FindingEvent {
  type: "finding";
  role: string;
  finding: {
    summary?: string;
    recommendation?: string;
    risk_indicators?: string[];
    sources_used?: string[];
  };
}

export interface AuditRoleSummary {
  session_id: string;
  allowed: number;
  denied: number;
  events: Array<{
    decision: "ALLOW" | "DENY";
    source_id: string;
    policy_name: string;
    reason: string | null;
  }>;
}

export interface AuditSummary {
  roles: Record<string, AuditRoleSummary>;
  total: number;
  allowed: number;
  denied: number;
}

export interface DispositionEvent {
  type: "disposition";
  case_id: string;
  action: string;
  proposed_action: string;
  human_approved: boolean;
  human_override_action: string | null;
  human_notes: string | null;
  expected_sar: boolean;
  specialists_run: string[];
  denial_count: number;
  audit_summary: AuditSummary;
}

export type FeedEvent = ToolCallEvent | RoutingEvent | FindingEvent | DispositionEvent;

// Mirrors the dict passed to interrupt(...) in decision_node.
export interface InterruptPayload {
  case_id: string;
  account_id: string;
  proposed_action: string;
  specialists_run: string[];
  findings: Record<string, { summary?: string; recommendation?: string }>;
  sar_draft: { summary?: string; recommendation?: string };
  denial_log: Array<{ agent_role: string; tool: string; reason: string }>;
}

// Must match decision_node's exact strings — the override dropdown can only pick one
// of these, so it can never drift from what the backend understands.
export const OVERRIDE_ACTIONS = [
  "SAR REQUIRED — synthetic identity bust-out confirmed",
  "SAR REQUIRED — structuring pattern confirmed",
  "FREEZE PENDING CONTACT — account takeover indicators",
  "MONITOR — no immediate action required",
] as const;

export const CASE_IDS = ["CASE-001", "CASE-002", "CASE-003"] as const;

export function initialInput(caseId: string): InvestigationState {
  return {
    case_id: caseId,
    account_id: "",
    alert: {},
    case_metadata: {},
    route_plan: [],
    specialists_run: [],
    findings: {},
    sar_draft: {},
    denial_log: [],
    orchestration_steps: 0,
    final_decision: "",
  };
}
