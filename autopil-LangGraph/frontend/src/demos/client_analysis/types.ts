// Mirrors ClientReviewState in client_analysis_demo.py — only the fields the UI
// actually reads are typed strictly, the rest are left loose.
export interface ClientReviewState {
  [key: string]: unknown;
  customer_id: string;
  provider: string;
  reason_for_review: string;
  current_tier: string;
  tiers_visited: string[];
  findings: Record<string, unknown>;
  human_decisions: Record<string, unknown>;
  denial_log: unknown[];
  final_action: string;
  closed_at_tier: string;
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
  tier?: string;
  next?: string;
  reason?: string;
}

export interface FindingEvent {
  type: "finding";
  role: string;
  finding: {
    summary?: string;
    proposed_action?: string;
    recommend_escalation?: boolean;
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

export interface HumanDecision {
  decision: "approve" | "override" | "escalate";
  override_action: string | null;
  notes: string | null;
}

export interface DispositionEvent {
  type: "disposition";
  customer_id: string;
  final_action: string;
  closed_at_tier: string;
  tiers_visited: string[];
  human_decisions: Record<string, HumanDecision>;
  denial_count: number;
  denials: Array<{ agent_role: string; tool: string; reason: string; mechanism: string }>;
  audit_summary: AuditSummary;
}

export type FeedEvent = ToolCallEvent | RoutingEvent | FindingEvent | DispositionEvent;

// Mirrors the dict passed to interrupt(...) in each tier's review node.
export interface InterruptPayload {
  customer_id: string;
  tier: string;
  reason_for_review: string;
  finding: { summary?: string; proposed_action?: string; recommend_escalation?: boolean };
  denial_log: Array<{ agent_role: string; tool: string; reason: string }>;
  can_escalate: boolean;
  next_tier: string | null;
}

// Must match _FINDING_TOOL_SCHEMA's CLIENT_ACTIONS in client_analysis_demo.py — the
// override dropdown can only pick one of these, so it can never drift from what the
// backend understands.
export const OVERRIDE_ACTIONS = [
  "NO ACTION NEEDED — CLIENT IN GOOD STANDING",
  "SEND MARKET UPDATE / RESEARCH TO CLIENT",
  "SCHEDULE PORTFOLIO REVIEW CALL",
  "RECOMMEND PORTFOLIO REBALANCING",
  "SCHEDULE WEALTH PLANNING MEETING",
  "ESCALATE FOR CREDIT REVIEW",
  "FLAG FOR COMPLIANCE / RISK REVIEW",
] as const;

export const TIER_LABELS: Record<string, string> = {
  junior_analyst: "Junior Analyst",
  senior_analyst: "Senior Analyst",
  wealth_advisor: "Wealth Advisor",
};

export const CUSTOMER_IDS = ["C001", "C002", "C003", "C004", "C005"] as const;

// Mirrors simulated_uc_data.py's CLIENT_REVIEWS — kept in sync by hand, same "adapted
// from the real backend data" pattern as policyData.ts. Deliberately excludes
// `tier_tasks` — that would give away how far a case is designed to escalate, the
// same spoiler-free framing the fraud demo's CASE_ALERTS uses. This is what the
// Execution tab's review queue actually shows.
export interface ClientReviewInfo {
  customerId: string;
  priority: string;
  opened: string;
  reasonForReview: string;
}

export const CLIENT_REVIEWS: Record<(typeof CUSTOMER_IDS)[number], ClientReviewInfo> = {
  "C001": {
    customerId: "C001", priority: "LOW", opened: "2026-06-01T09:00:00Z",
    reasonForReview: "Annual portfolio check-in ahead of Q3 rebalancing window.",
  },
  "C002": {
    customerId: "C002", priority: "MEDIUM", opened: "2026-06-02T13:00:00Z",
    reasonForReview: "Requested a market outlook memo; also asked about a potential personal credit line increase.",
  },
  "C003": {
    customerId: "C003", priority: "HIGH", opened: "2026-06-01T11:30:00Z",
    reasonForReview: "Comprehensive wealth plan update requested, including a credit exposure review ahead of the retirement/estate discussion.",
  },
  "C004": {
    customerId: "C004", priority: "MEDIUM", opened: "2026-06-03T08:45:00Z",
    reasonForReview: "Unusual transaction pattern flagged for review — possible risk exposure.",
  },
  "C005": {
    customerId: "C005", priority: "LOW", opened: "2026-06-02T10:15:00Z",
    reasonForReview: "Client requested a market update on holdings ahead of a call next week.",
  },
};

// Must match _make_llm()'s provider strings in client_analysis_demo.py.
// Ollama listed first (and used as the default selection) — fully local, no key, no
// AWS account needed. Bedrock requires AWS_BEDROCK_MODEL_ID configured server-side.
export const PROVIDERS = [
  { value: "ollama", label: "Ollama (local, free)" },
  { value: "bedrock", label: "AWS Bedrock" },
  { value: "anthropic", label: "Claude (Anthropic)" },
  { value: "gemini", label: "Gemini (Google, free tier)" },
  { value: "groq", label: "Groq (Llama, free tier)" },
] as const;

export function initialInput(customerId: string, provider: string): ClientReviewState {
  return {
    customer_id: customerId,
    provider,
    reason_for_review: "",
    current_tier: "",
    tiers_visited: [],
    findings: {},
    human_decisions: {},
    denial_log: [],
    final_action: "",
    closed_at_tier: "",
  };
}
