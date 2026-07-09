// Mirrors AMLCaseState in aml_compliance_demo.py — only the fields the UI actually
// reads are typed strictly, the rest are left loose.
export interface AMLCaseState {
  [key: string]: unknown;
  case_id: string;
  provider: string;
  account_id: string;
  reason_for_review: string;
  roles_completed: string[];
  findings: Record<string, unknown>;
  denial_log: unknown[];
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
  stage: "initial";
  route?: string[];
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
  roles_completed: string[];
  denial_count: number;
  audit_summary: AuditSummary;
}

export type FeedEvent = ToolCallEvent | RoutingEvent | FindingEvent | DispositionEvent;

// Mirrors the dict passed to interrupt(...) in decision_node.
export interface InterruptPayload {
  case_id: string;
  account_id: string;
  proposed_action: string;
  roles_completed: string[];
  findings: Record<string, { summary?: string; recommendation?: string }>;
  denial_log: Array<{ agent_role: string; tool: string; reason: string }>;
}

// Must match decision_node's exact strings — the override dropdown can only pick one
// of these, so it can never drift from what the backend understands.
export const OVERRIDE_ACTIONS = [
  "SAR REQUIRED — structuring pattern confirmed",
  "SAR REQUIRED — sanctions match confirmed",
  "HOLD PENDING KYC REFRESH — beneficial ownership verification lapsed",
  "ESCALATE TO SENIOR COMPLIANCE — requires manual review before proceeding",
  "CLEARED — no further action required",
] as const;

export const CASE_IDS = ["AML-001", "AML-002", "AML-003", "AML-004", "AML-005"] as const;

// Spoiler-bearing reference copy — fine for the Description tab (a read-only "how this
// works" page), but never shown on the Execution tab's case queue (see CASE_ALERTS
// below) since naming the pattern before the agents investigate gives away the answer
// the investigation is supposed to work out.
// See aml_case_data.py's module docstring for the underlying fixture data.
export const CASE_INFO: Record<(typeof CASE_IDS)[number], { title: string; description: string; estimatedTime: string }> = {
  "AML-001": {
    title: "Structuring",
    description: "Repeated wire transfers kept just under the $10,000 CTR reporting threshold.",
    estimatedTime: "~1–2 min",
  },
  "AML-002": {
    title: "Watchlist false positive",
    description: "A fuzzy OFAC/SDN name match that resolves to a different legal entity on verification.",
    estimatedTime: "~1–2 min",
  },
  "AML-003": {
    title: "Stale KYC refresh",
    description: "Beneficial ownership verification lapsed well past the policy renewal window.",
    estimatedTime: "~1–2 min",
  },
  "AML-004": {
    title: "Cross-client audit",
    description: "A routine consistency check confirming AML handling is applied uniformly across the book.",
    estimatedTime: "~1–2 min",
  },
  "AML-005": {
    title: "Clean case",
    description: "No prior flags — clears at every step.",
    estimatedTime: "~1–2 min",
  },
};

// Mirrors aml_case_data.py's AML_CASES — kept in sync by hand, same "adapted from
// the real backend data" pattern as policyData.ts. Deliberately excludes the
// underlying signal data (transaction/watchlist/identity records) — that's the
// answer the investigation is supposed to work out, not something a real analyst
// would see on the case ticket before opening it. This is what the Execution tab's
// case queue actually shows.
export interface CaseAlert {
  accountId: string;
  openedAt: string;
  priority: string;
  reasonForReview: string;
}

export const CASE_ALERTS: Record<(typeof CASE_IDS)[number], CaseAlert> = {
  "AML-001": {
    accountId: "ACCT-AML-001", openedAt: "2026-06-06T09:00:00Z", priority: "HIGH",
    reasonForReview: "Transaction monitoring alert: repeated wire transfers just under the $10,000 CTR reporting threshold within a 4-day window.",
  },
  "AML-002": {
    accountId: "ACCT-AML-002", openedAt: "2026-06-10T14:00:00Z", priority: "MEDIUM",
    reasonForReview: "OFAC/SDN watchlist screening returned a fuzzy name match requiring manual clearance before the account can be marked clean.",
  },
  "AML-003": {
    accountId: "ACCT-AML-003", openedAt: "2026-06-08T11:30:00Z", priority: "MEDIUM",
    reasonForReview: "Periodic KYC refresh review — beneficial ownership verification due for renewal per policy cycle.",
  },
  "AML-004": {
    accountId: "ACCT-AML-004", openedAt: "2026-06-01T08:00:00Z", priority: "LOW",
    reasonForReview: "Quarterly cross-client consistency audit requested by internal audit — confirm AML handling is applied uniformly across the institutional book.",
  },
  "AML-005": {
    accountId: "ACCT-AML-005", openedAt: "2026-06-09T10:15:00Z", priority: "LOW",
    reasonForReview: "Routine annual AML case review — no prior flags on this account.",
  },
};

// Must match _make_llm()'s provider strings in aml_compliance_demo.py.
// Ollama listed first (and used as the default selection) — fully local, no key,
// no external API to rate-limit or 503 on you.
export const PROVIDERS = [
  { value: "ollama", label: "Ollama (local, free)" },
  { value: "gemini", label: "Gemini (Google, free tier)" },
  { value: "anthropic", label: "Claude (Anthropic)" },
  { value: "groq", label: "Groq (Llama, free tier)" },
] as const;

export function initialInput(caseId: string, provider: string): AMLCaseState {
  return {
    case_id: caseId,
    provider,
    account_id: "",
    reason_for_review: "",
    roles_completed: [],
    findings: {},
    denial_log: [],
    final_decision: "",
  };
}
