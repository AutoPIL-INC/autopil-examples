// Mirrors InvestigationState in splunk_secops_demo.py — only the fields the UI
// actually reads are typed strictly, the rest are left loose.
export interface InvestigationState {
  [key: string]: unknown;
  case_id: string;
  provider: string;
  system_id: string;
  alert: Record<string, unknown>;
  case_metadata: Record<string, unknown>;
  route_plan: string[];
  specialists_run: string[];
  findings: Record<string, unknown>;
  threat_report: Record<string, unknown>;
  denial_log: unknown[];
  orchestration_steps: number;
  final_decision: string;
  audit_source: string;
  audit_summary: Record<string, unknown>;
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

// _collect_audit_summary()'s per-role shape — one row per policy decision, source
// is guard.get_audit_trail() directly.
export interface LocalAuditRoleSummary {
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

// _collect_audit_summary_via_mcp()'s per-role shape — one get_session_status MCP
// call per role. Aggregate counts only; no per-decision policy_name/reason.
export interface McpAuditRoleSummary {
  session_id: string;
  owner_role: string;
  total_events: number;
  allowed: number;
  denied: number;
  sources_accessed: string[];
  first_event: string;
  last_event: string;
}

export interface AuditSummary {
  roles: Record<string, LocalAuditRoleSummary | McpAuditRoleSummary>;
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
  incident_report_warranted: boolean;
  specialists_run: string[];
  denial_count: number;
  audit_source: "mcp" | "local";
  audit_summary: AuditSummary;
}

export type FeedEvent = ToolCallEvent | RoutingEvent | FindingEvent | DispositionEvent;

// Mirrors the first dict passed to interrupt(...) in decision_node — the
// disposition-approval pause.
export interface ReviewInterruptPayload {
  case_id: string;
  system_id: string;
  proposed_action: string;
  specialists_run: string[];
  findings: Record<string, { summary?: string; recommendation?: string }>;
  threat_report: { summary?: string; recommendation?: string };
  denial_log: Array<{ agent_role: string; tool: string; reason: string }>;
}

// Mirrors the second dict passed to interrupt(...) in decision_node — the
// audit-source-choice pause that immediately follows the review one.
export interface AuditSourceInterruptPayload {
  ask: "audit_source";
  case_id: string;
  options: Array<"mcp" | "local">;
}

export type InterruptPayload = ReviewInterruptPayload | AuditSourceInterruptPayload;

export function isAuditSourceAsk(payload: InterruptPayload): payload is AuditSourceInterruptPayload {
  return "ask" in payload && payload.ask === "audit_source";
}

// Must match decision_node's exact strings — the override dropdown can only pick one
// of these, so it can never drift from what the backend understands.
export const OVERRIDE_ACTIONS = [
  "INCIDENT REPORT REQUIRED — unauthorized activity correlated with an unscheduled restart",
  "FREEZE PENDING REVIEW — privilege escalation correlated with a workload anomaly",
  "MONITOR — access-violation pattern below incident threshold",
  "COMPLIANT — no incident indicators",
] as const;

export const CASE_IDS = ["SEC-001", "SEC-002", "SEC-003", "SEC-004"] as const;

// Spoiler-bearing reference copy — fine for the Description tab (a read-only "how this
// works" page), but never shown on the Execution tab's case queue (see CASE_ALERTS
// below) since naming the pattern before the agents investigate gives away the answer
// the investigation is supposed to work out.
// See splunk_secops_data.py's module docstring for the underlying fixture data.
export const CASE_INFO: Record<(typeof CASE_IDS)[number], { title: string; description: string; estimatedTime: string }> = {
  "SEC-001": {
    title: "Routine RACF sweep",
    description: "Daily scheduled RACF access-violation review flags a below-threshold pattern from a batch service userid.",
    estimatedTime: "~1–2 min",
  },
  "SEC-002": {
    title: "Card-authorization incident",
    description: "An unauthorized RACF privilege grant correlated with a CPU spike and abending high-value transactions.",
    estimatedTime: "~1–2 min",
  },
  "SEC-003": {
    title: "Compliance spot-check",
    description: "Quarterly retention/integrity certification across all Splunk indices for a clean payroll system.",
    estimatedTime: "~1–2 min",
  },
  "SEC-004": {
    title: "General-ledger incident",
    description: "Unauthorized batch postings outside the change window plus an unscheduled subsystem restart on a SOX-scoped system.",
    estimatedTime: "~1–2 min",
  },
};

// Mirrors splunk_secops_data.py's SECURITY_ALERTS — kept in sync by hand, same
// "adapted from the real backend data" pattern as policyData.ts. Deliberately softens
// the most conclusive clause on SEC-002/SEC-004 (e.g. "anomalous RACF activity" instead
// of "unauthorized privilege grant") — that's the root-cause verdict the investigation
// is supposed to work out, not something a real SOC analyst would see on the ticket
// before opening the case. Full text still appears verbatim via the live feed once the
// agents actually pull this alert.
export interface CaseAlert {
  alertId: string;
  systemId: string;
  triggeredAt: string;
  ruleName: string;
  description: string;
  priority: string;
}

export const CASE_ALERTS: Record<(typeof CASE_IDS)[number], CaseAlert> = {
  "SEC-001": {
    alertId: "SEC-001", systemId: "MVSP01", triggeredAt: "2026-07-24T02:11:03Z",
    ruleName: "RACF_DAILY_SWEEP_FINDING",
    description: "Daily scheduled RACF sweep flagged repeated INSUFFICIENT_AUTHORITY events from a batch service userid against a payroll dataset.",
    priority: "LOW",
  },
  "SEC-002": {
    alertId: "SEC-002", systemId: "MVSP02", triggeredAt: "2026-07-24T23:47:02Z",
    ruleName: "RACF_CPU_TXN_CORRELATION",
    description: "Card-authorization LPAR showing anomalous RACF activity correlated with a CPU spike and abending high-value transactions.",
    priority: "CRITICAL",
  },
  "SEC-003": {
    alertId: "SEC-003", systemId: "MVSP03", triggeredAt: "2026-07-24T09:15:00Z",
    ruleName: "COMPLIANCE_SPOT_CHECK",
    description: "Scheduled quarterly compliance spot-check — certify index retention and integrity health for the payroll/HR LPAR.",
    priority: "LOW",
  },
  "SEC-004": {
    alertId: "SEC-004", systemId: "MVSP04", triggeredAt: "2026-07-24T21:30:05Z",
    ruleName: "GL_POSTING_WINDOW_VIOLATION",
    description: "General-ledger LPAR showing batch postings outside the change window plus an unscheduled subsystem restart — SOX-scoped financial-reporting system.",
    priority: "CRITICAL",
  },
};

// Must match _make_llm()'s provider strings in splunk_secops_demo.py.
// Ollama listed first (and used as the default selection) — fully local, no key,
// no external API to rate-limit or 503 on you.
export const PROVIDERS = [
  { value: "ollama", label: "Ollama (local, free)" },
  { value: "gemini", label: "Gemini (Google, free tier)" },
  { value: "anthropic", label: "Claude (Anthropic)" },
  { value: "groq", label: "Groq (Llama, free tier)" },
] as const;

export function initialInput(caseId: string, provider: string): InvestigationState {
  return {
    case_id: caseId,
    provider,
    system_id: "",
    alert: {},
    case_metadata: {},
    route_plan: [],
    specialists_run: [],
    findings: {},
    threat_report: {},
    denial_log: [],
    orchestration_steps: 0,
    final_decision: "",
    audit_source: "",
    audit_summary: {},
  };
}
