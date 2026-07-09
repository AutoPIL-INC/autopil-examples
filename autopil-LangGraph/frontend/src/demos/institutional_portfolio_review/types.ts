// Mirrors ReviewState in institutional_portfolio_review_demo.py — only the fields the
// UI actually reads are typed strictly, the rest are left loose.
export interface ReviewState {
  [key: string]: unknown;
  request_id: string;
  provider: string;
  client_id: string;
  brief: string;
  review_type: string;
  roles_plan: [string, string][];
  roles_completed: string[];
  escalated: boolean;
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
  stage: "initial" | "review";
  review_type?: string;
  plan?: string[];
  next?: string;
  reasoning?: string;
  reason?: string;
}

export interface FindingEvent {
  type: "finding";
  role: string;
  finding: {
    summary?: string;
    outcome?: "COMPLETED" | "BLOCKED";
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
  request_id: string;
  outcome: string;
  proposed_outcome: string;
  human_approved: boolean;
  human_override_outcome: string | null;
  human_notes: string | null;
  review_type: string;
  roles_completed: string[];
  escalated: boolean;
  denial_count: number;
  denials: Array<{ agent_role: string; tool: string; reason: string; mechanism: string }>;
  audit_summary: AuditSummary;
}

export type FeedEvent = ToolCallEvent | RoutingEvent | FindingEvent | DispositionEvent;

// Mirrors the dict passed to interrupt(...) in decision_node.
export interface InterruptPayload {
  request_id: string;
  review_type: string;
  roles_completed: string[];
  proposed_outcome: string;
  denial_log: Array<{ agent_role: string; tool: string; reason: string }>;
  escalated: boolean;
}

// Must match decision_node's actual override options — the dropdown can only pick one
// of these, so it can never drift from what the backend understands.
export const OVERRIDE_ACTIONS = [
  "ESCALATE TO SENIOR COMPLIANCE — requires manual review before proceeding",
  "HOLD — do not proceed until blocked steps are resolved",
  "APPROVE WITH CONDITIONS — proceed, flag for follow-up review",
  "REJECT — return to originating role for rework",
] as const;

export const REQUEST_IDS = ["PORT-001", "PORT-002", "PORT-003", "PORT-004", "PORT-005"] as const;

// See portfolio_review_uc_data.py's PORTFOLIO_REVIEW_REQUESTS for the underlying brief text.
export const REQUEST_INFO: Record<(typeof REQUEST_IDS)[number], { title: string; description: string; estimatedTime: string }> = {
  "PORT-001": {
    title: "Quarterly Review",
    description: "Harrington Endowment's quarterly review — research, advisory, rebalancing, and the client-facing report.",
    estimatedTime: "~1-2 min",
  },
  "PORT-002": {
    title: "Fiduciary Benchmark Request",
    description: "A benchmarking ask for Harrington Endowment tempts the fiduciary wall — peer portfolios are off-limits to the advisor.",
    estimatedTime: "~1 min",
  },
  "PORT-003": {
    title: "AML Case & Compliance Audit",
    description: "A monitoring alert on Meridian Foundation triggers an AML investigation, KYC check, and cross-client compliance audit.",
    estimatedTime: "~1-2 min",
  },
  "PORT-004": {
    title: "Credit Limit Review",
    description: "Cascade Pension Trust requests a credit facility increase — tests purpose limitation on the credit risk review.",
    estimatedTime: "~1 min",
  },
  "PORT-005": {
    title: "Trade Settlement & Macro Check",
    description: "A macro regime check ahead of settling Harrington Endowment's pending trade — exercises the settlement_agent role added in this version.",
    estimatedTime: "~1 min",
  },
};

// Must match _make_llm()'s provider strings in institutional_portfolio_review_demo.py.
export const PROVIDERS = [
  { value: "ollama", label: "Ollama (local, free)" },
  { value: "bedrock", label: "AWS Bedrock" },
  { value: "anthropic", label: "Claude (Anthropic)" },
  { value: "gemini", label: "Gemini (Google, free tier)" },
  { value: "groq", label: "Groq (Llama, free tier)" },
] as const;

export function initialInput(requestId: string, provider: string): ReviewState {
  return {
    request_id: requestId,
    provider,
    client_id: "",
    brief: "",
    review_type: "",
    roles_plan: [],
    roles_completed: [],
    escalated: false,
    findings: {},
    denial_log: [],
    final_decision: "",
  };
}
