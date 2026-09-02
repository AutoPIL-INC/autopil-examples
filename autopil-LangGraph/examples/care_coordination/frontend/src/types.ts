// Mirrors InvestigationState in care_coordination_demo.py — only the fields the UI
// actually reads are typed strictly, the rest are left loose.
export interface InvestigationState {
  [key: string]: unknown;
  case_id: string;
  provider: string;
  case: Record<string, unknown>;
  case_metadata: Record<string, unknown>;
  route_plan: string[];
  specialists_run: string[];
  findings: Record<string, unknown>;
  care_summary: Record<string, unknown>;
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
  specialists_run: string[];
  denial_count: number;
  audit_summary: AuditSummary;
}

export type FeedEvent = ToolCallEvent | RoutingEvent | FindingEvent | DispositionEvent;

// Mirrors the dict passed to interrupt(...) in decision_node — the single
// disposition-approval pause this demo has.
export interface ReviewInterruptPayload {
  case_id: string;
  case: Record<string, unknown>;
  proposed_action: string;
  reason: string;
  specialists_run: string[];
  findings: Record<string, { summary?: string; recommendation?: string }>;
  care_summary: { summary?: string; recommendation?: string };
  denial_log: Array<{ agent_role: string; tool: string; reason: string }>;
}

// Must match decision_node's exact strings — the override dropdown can only pick one
// of these, so it can never drift from what the backend understands.
export const OVERRIDE_ACTIONS = [
  "ESCALATE — refer for urgent care",
  "OUTREACH REQUIRED — care gap identified",
  "REFILL APPROVED — no interaction or contraindication found",
  "COMPLIANT — no action required",
] as const;

export const CASE_IDS = ["CC-001", "CC-002", "CC-003", "CC-004"] as const;

// Spoiler-bearing reference copy — fine for the Description tab (a read-only "how this
// works" page), but never shown on the Execution tab's case queue (see CASE_META
// below) since naming the exact finding before the agents investigate gives away the
// answer the investigation is supposed to work out.
// See care_coordination_data.py's module docstring for the underlying fixture data.
export const CASE_INFO: Record<(typeof CASE_IDS)[number], { title: string; description: string; estimatedTime: string }> = {
  "CC-001": {
    title: "Acute symptom call",
    description: "Patient calling in with new chest tightness and shortness of breath.",
    estimatedTime: "~1–2 min",
  },
  "CC-002": {
    title: "Chronic-care check-in",
    description: "Routine outreach call for a patient with a chronic condition on file.",
    estimatedTime: "~1–2 min",
  },
  "CC-003": {
    title: "Medication refill request",
    description: "Patient requesting a routine prescription refill.",
    estimatedTime: "~1–2 min",
  },
  "CC-004": {
    title: "Annual well-visit",
    description: "Routine annual visit, no current complaints.",
    estimatedTime: "~1–2 min",
  },
};

// Mirrors care_coordination_data.py's CASES — kept in sync by hand, same "adapted
// from the real backend data" pattern as policyData.ts.
export interface CaseMeta {
  caseId: string;
  patientName: string;
  age: number;
  sex: string;
}

export const CASE_META: Record<(typeof CASE_IDS)[number], CaseMeta> = {
  "CC-001": { caseId: "CC-001", patientName: "Marcus Whitfield", age: 58, sex: "M" },
  "CC-002": { caseId: "CC-002", patientName: "Dolores Kim", age: 64, sex: "F" },
  "CC-003": { caseId: "CC-003", patientName: "Andre Boucher", age: 45, sex: "M" },
  "CC-004": { caseId: "CC-004", patientName: "Priya Anand", age: 34, sex: "F" },
};

// Must match _make_llm()'s provider strings in care_coordination_demo.py.
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
    case: {},
    case_metadata: {},
    route_plan: [],
    specialists_run: [],
    findings: {},
    care_summary: {},
    denial_log: [],
    orchestration_steps: 0,
    final_decision: "",
    audit_summary: {},
  };
}
