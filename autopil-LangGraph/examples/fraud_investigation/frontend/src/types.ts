// Mirrors InvestigationState in fraud_investigation_demo.py — only the fields the
// UI actually reads are typed strictly, the rest are left loose.
export interface InvestigationState {
  [key: string]: unknown;
  case_id: string;
  provider: string;
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
  "SAR REQUIRED — elder financial exploitation confirmed",
  "FREEZE PENDING CONTACT — suspected money mule activity",
  "MONITOR — no immediate action required",
] as const;

export const CASE_IDS = ["CASE-001", "CASE-002", "CASE-003", "CASE-004", "CASE-005"] as const;

// Spoiler-bearing reference copy — fine for the Description tab (a read-only "how this
// works" page), but never shown on the Execution tab's case queue (see CASE_ALERTS
// below) since naming the pattern before the agents investigate gives away the answer
// the investigation is supposed to work out.
// See simulated_data.py's module docstring for the underlying fixture data.
export const CASE_INFO: Record<(typeof CASE_IDS)[number], { title: string; description: string; estimatedTime: string }> = {
  "CASE-001": {
    title: "Structuring",
    description: "Deposits kept just under the $10,000 CTR reporting threshold, followed by an outbound wire.",
    estimatedTime: "~1–2 min",
  },
  "CASE-002": {
    title: "Account takeover",
    description: "Sudden transaction velocity spike from a new device, with a geographic anomaly.",
    estimatedTime: "~1–2 min",
  },
  "CASE-003": {
    title: "Synthetic identity",
    description: "A new, thin-file account jumps straight to high-value activity with no prior history.",
    estimatedTime: "~1–2 min",
  },
  "CASE-004": {
    title: "Elder financial exploitation",
    description: "A brand-new authorized signer on a 25-year account diverts funds to their own account.",
    estimatedTime: "~1–2 min",
  },
  "CASE-005": {
    title: "Money mule / check kiting",
    description: "Third-party checks from unrelated remitters, each withdrawn before the hold would release.",
    estimatedTime: "~1–2 min",
  },
};

// Mirrors simulated_data.py's FRAUD_ALERTS — kept in sync by hand, same "adapted from
// the real backend data" pattern as policyData.ts. Deliberately excludes `alert_type`
// — that's the fraud category, i.e. the answer the investigation is supposed to work
// out, not something a real analyst would see on the ticket before opening the case.
// This is what the Execution tab's case queue actually shows.
export interface CaseAlert {
  alertId: string;
  accountId: string;
  triggeredAt: string;
  ruleName: string;
  description: string;
  priority: string;
}

export const CASE_ALERTS: Record<(typeof CASE_IDS)[number], CaseAlert> = {
  "CASE-001": {
    alertId: "ALERT-001", accountId: "ACC_8821", triggeredAt: "2026-03-29T14:22:00Z",
    ruleName: "CTR_AVOIDANCE_PATTERN",
    description: "12 cash deposits in 8 days, all between $9,100-$9,800. Cumulative total $112,500. Single outbound wire $87,400 to BVI entity immediately follows deposit pattern.",
    priority: "HIGH",
  },
  "CASE-002": {
    alertId: "ALERT-002", accountId: "ACC_3347", triggeredAt: "2026-03-29T16:47:00Z",
    ruleName: "GEO_VELOCITY_ANOMALY",
    description: "Austin TX → Miami FL → New York NY in 97 minutes. All three transactions from unrecognized device DEV_NEW_9921. $16,100 total debits in 4-hour window vs. $380 prior daily average.",
    priority: "CRITICAL",
  },
  "CASE-003": {
    alertId: "ALERT-003", accountId: "ACC_5590", triggeredAt: "2026-03-30T09:15:00Z",
    ruleName: "BUST_OUT_PATTERN",
    description: "Account opened 38 days ago. Minimal opening activity, then $25,100 in purchases over 20 days across mass retailers. NSF returned today. SSN matches prior declined application under different name.",
    priority: "HIGH",
  },
  "CASE-004": {
    alertId: "ALERT-004", accountId: "ACC_6634", triggeredAt: "2026-03-28T11:05:00Z",
    ruleName: "AUTHORIZED_SIGNER_FUND_DIVERSION",
    description: "New authorized signer added 2026-03-17 to a 25-year, historically low-activity retirement account. $34,500 in transfers to that signer's personal account over the following 11 days — no comparable activity anywhere in the account's prior history.",
    priority: "HIGH",
  },
  "CASE-005": {
    alertId: "ALERT-005", accountId: "ACC_7743", triggeredAt: "2026-03-27T15:30:00Z",
    ruleName: "RAPID_CHECK_DEPOSIT_WITHDRAWAL",
    // Trimmed one clause vs. the real alert text ("...Classic money-mule / check-kiting
    // signature.") — the real data names the pattern outright there, which would defeat
    // the point on the one screen meant to withhold it. Full text still appears verbatim
    // via the live feed once the agents actually pull this alert.
    description: "Five third-party check deposits totaling $42,000 over 7 days, each from a different, unrelated remitter, followed same-day by withdrawal before standard hold periods release.",
    priority: "HIGH",
  },
};

// Must match _make_llm()'s provider strings in fraud_investigation_demo.py.
// Ollama listed first (and used as the default selection) — fully local, no key,
// no external API to rate-limit or 503 on you. See README's "Choosing a model" for
// the tradeoff: reliability depends on which local model you've pulled.
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
