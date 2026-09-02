// Mirrors InvestigationState in quality_control_demo.py — only the fields the UI
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
  quality_finding: Record<string, unknown>;
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

// "initial" is quality_orchestrator_node's fixed first step (route_plan is always
// exactly ["defect_detection_agent"] — a plain assignment, not an LLM decision).
// "review" is orchestrator_review_node's real LLM-driven re-routing choice among the
// 3 follow-up specialists. The UI must not present both stages the same way — see
// RoutingRow in ExecutionTab.tsx.
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
// transport, so there's only ever this one shape.
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

// Mirrors decision_node's "disposition" _emit(...) call exactly — no revenue/dollar
// field on this demo (unlike hospital_revenue_cycle's DispositionEvent).
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
// disposition-approval pause this demo has (no second MCP/audit-source-choice pause,
// same as hospital_revenue_cycle/aml_compliance/fraud_investigation).
// notes_required is always true here — decision_node loops on interrupt() until a
// non-empty notes field comes back on the resume payload, on BOTH approve and
// override, not just override. The UI must enforce the same thing at the form layer
// (disable submit until non-empty) rather than relying on the backend's own retry loop.
export interface ReviewInterruptPayload {
  case_id: string;
  case: Record<string, unknown>;
  proposed_action: string;
  reason: string;
  specialists_run: string[];
  findings: Record<string, { summary?: string; recommendation?: string }>;
  quality_finding: { summary?: string; recommendation?: string };
  denial_log: Array<{ agent_role: string; tool: string; reason: string }>;
  notes_required: true;
}

// Must match decision_node's exact PROPOSED_ACTIONS strings — the override dropdown
// can only pick one of these, so it can never drift from what the backend understands.
export const OVERRIDE_ACTIONS = [
  "QUARANTINE & RECALIBRATE — equipment calibration lapse confirmed",
  "NONCONFORMANCE REPORT & SUPPLIER HOLD — supplier lot issue confirmed",
  "MONITOR — no confirmed nonconformance, continue tracking",
  "COMPLIANT — no corrective action required",
  "ESCALATE TO QUALITY MANAGER — root cause inconclusive",
] as const;

export const CASE_IDS = ["QC-001", "QC-002", "QC-003", "QC-004"] as const;

// Spoiler-light reference copy — fine for the Description tab (a read-only "how this
// works" page) and the Execution tab's case queue alike (same convention this
// template's own CASE_INFO follows in practice), since naming the exact root cause
// before the agents investigate would give away the answer the investigation is
// supposed to work out.
// See quality_control_data.py's module docstring for the underlying fixture data.
export const CASE_INFO: Record<(typeof CASE_IDS)[number], { title: string; description: string; estimatedTime: string }> = {
  "QC-001": {
    title: "Dimensional defect — stamped bracket flange width",
    description: "A vision-system flag on Press Line 3 needs tracing to root cause — internal process, equipment, or supplier.",
    estimatedTime: "~1–2 min",
  },
  "QC-002": {
    title: "Dimensional defect — molded housing mounting hole",
    description: "A control-chart shift on Molding Cell 2 lines up with a recent lot changeover — worth tracing to the incoming material.",
    estimatedTime: "~1–2 min",
  },
  "QC-003": {
    title: "Minor dimensional variance — stamped bracket flange width",
    description: "A borderline vision-system flag on Press Line 1 needs tracing to root cause before any corrective action is warranted.",
    estimatedTime: "~1–2 min",
  },
  "QC-004": {
    title: "Routine SPC review — molded housing",
    description: "Standard statistical-process-control check on Molding Cell 1, no defect reported.",
    estimatedTime: "~1–2 min",
  },
};

// Mirrors quality_control_data.CASES — kept in sync by hand, same "adapted from the
// real backend data" pattern as policyData.ts.
export interface CaseMeta {
  caseId: string;
  product: string;
  line: string;
  defectType: string | null;
}

export const CASE_META: Record<(typeof CASE_IDS)[number], CaseMeta> = {
  "QC-001": { caseId: "QC-001", product: "Stamped Brackets", line: "Press Line 3", defectType: "Dimensional out-of-spec (flange width)" },
  "QC-002": { caseId: "QC-002", product: "Injection-Molded Housings", line: "Molding Cell 2", defectType: "Dimensional out-of-spec (mounting-hole diameter)" },
  "QC-003": { caseId: "QC-003", product: "Stamped Brackets", line: "Press Line 1", defectType: "Minor dimensional variance (flange width)" },
  "QC-004": { caseId: "QC-004", product: "Injection-Molded Housings", line: "Molding Cell 1", defectType: null },
};

// Must match _make_llm()'s provider strings in quality_control_demo.py.
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
    quality_finding: {},
    denial_log: [],
    orchestration_steps: 0,
    final_decision: "",
    audit_summary: {},
  };
}
