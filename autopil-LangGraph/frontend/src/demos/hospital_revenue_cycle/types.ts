// Mirrors InvestigationState in hospital_revenue_cycle_demo.py — only the fields the
// UI actually reads are typed strictly, the rest are left loose.
export interface InvestigationState {
  [key: string]: unknown;
  case_id: string;
  provider: string;
  encounter: Record<string, unknown>;
  case_metadata: Record<string, unknown>;
  route_plan: string[];
  specialists_run: string[];
  findings: Record<string, unknown>;
  revenue_summary: Record<string, unknown>;
  denial_log: unknown[];
  orchestration_steps: number;
  final_decision: string;
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
// is guard.get_audit_trail() directly. This demo has no hosted-mode/MCP audit
// transport (see DESIGN.md §7), so there's only ever this one shape.
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
  revenue_recovery: number;
  specialists_run: string[];
  denial_count: number;
  audit_summary: AuditSummary;
}

export type FeedEvent = ToolCallEvent | RoutingEvent | FindingEvent | DispositionEvent;

// Mirrors the dict passed to interrupt(...) in decision_node — the single
// disposition-approval pause this demo has (no second MCP/audit-source pause, unlike
// splunk_secops — see DESIGN.md §7).
export interface ReviewInterruptPayload {
  case_id: string;
  encounter: Record<string, unknown>;
  proposed_action: string;
  revenue_recovery: number;
  action_required: string;
  specialists_run: string[];
  findings: Record<string, { summary?: string; recommendation?: string }>;
  revenue_summary: { summary?: string; recommendation?: string };
  denial_log: Array<{ agent_role: string; tool: string; reason: string }>;
}

// Must match decision_node's exact strings — the override dropdown can only pick one
// of these, so it can never drift from what the backend understands.
export const OVERRIDE_ACTIONS = [
  "REVENUE RECOVERY IDENTIFIED — claim correction required",
  "REVENUE RECOVERY IDENTIFIED — policy violation blocked during investigation",
  "ESCALATE TO REVENUE INTEGRITY — requires manual review before claim submission",
  "COMPLIANT — no additional revenue identified",
] as const;

export const CASE_IDS = ["ENC-001", "ENC-002", "ENC-003", "ENC-004"] as const;

// Spoiler-bearing reference copy — fine for the Description tab (a read-only "how this
// works" page), but never shown on the Execution tab's case queue (see ENCOUNTER_INFO
// below) since naming the exact finding before the agents investigate gives away the
// answer the investigation is supposed to work out.
// See hospital_revenue_cycle_data.py's module docstring for the underlying fixture data.
export const CASE_INFO: Record<(typeof CASE_IDS)[number], { title: string; description: string; estimatedTime: string }> = {
  "ENC-001": {
    title: "CDI gap — ICU respiratory failure stay",
    description: "Discharge coding may not reflect the full severity documented in clinical notes for a 7-day ICU stay.",
    estimatedTime: "~1–2 min",
  },
  "ENC-002": {
    title: "Possible missed charge — wound care",
    description: "A documented bedside procedure may not have made it onto the current claim.",
    estimatedTime: "~1–2 min",
  },
  "ENC-003": {
    title: "Possible missed charge — infusion therapy",
    description: "Documented infusion services may not have made it onto the draft claim.",
    estimatedTime: "~1–2 min",
  },
  "ENC-004": {
    title: "Routine review — post-surgical stay",
    description: "Standard revenue-cycle review of a short surgical admission.",
    estimatedTime: "~1–2 min",
  },
};

// Mirrors hospital_revenue_cycle_data.py's PATIENT_ENCOUNTERS — kept in sync by hand,
// same "adapted from the real backend data" pattern as policyData.ts.
export interface EncounterMeta {
  encounterId: string;
  patientName: string;
  unit: string;
  admissionDate: string;
  payer: string;
}

export const ENCOUNTER_META: Record<(typeof CASE_IDS)[number], EncounterMeta> = {
  "ENC-001": { encounterId: "ENC-001", patientName: "Robert Nguyen", unit: "ICU", admissionDate: "2026-03-28", payer: "Medicare" },
  "ENC-002": { encounterId: "ENC-002", patientName: "Gloria Martinez", unit: "Med/Surg", admissionDate: "2026-04-01", payer: "Blue Cross Blue Shield" },
  "ENC-003": { encounterId: "ENC-003", patientName: "Thomas Whitfield", unit: "Oncology", admissionDate: "2026-04-03", payer: "Aetna" },
  "ENC-004": { encounterId: "ENC-004", patientName: "Linda Osei", unit: "Surgical", admissionDate: "2026-04-05", payer: "UnitedHealthcare" },
};

// Must match _make_llm()'s provider strings in hospital_revenue_cycle_demo.py.
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
    encounter: {},
    case_metadata: {},
    route_plan: [],
    specialists_run: [],
    findings: {},
    revenue_summary: {},
    denial_log: [],
    orchestration_steps: 0,
    final_decision: "",
    audit_summary: {},
  };
}
