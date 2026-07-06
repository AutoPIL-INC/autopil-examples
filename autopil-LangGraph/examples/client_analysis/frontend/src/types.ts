// Mirrors GovernanceState in client_analysis_demo.py — only the fields the UI
// actually reads are typed strictly, the rest are left loose.
export interface GovernanceState {
  [key: string]: unknown;
  request_id: string;
  provider: string;
  brief: string;
  assigned_role: string;
  task_type: string;
  roles_attempted: string[];
  escalated: boolean;
  finding: Record<string, unknown>;
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
  role?: string;
  task_type?: string;
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
  roles_attempted: string[];
  task_type: string;
  expected_role: string;
  denial_count: number;
  denials: Array<{ agent_role: string; tool: string; reason: string; mechanism: string }>;
  audit_summary: AuditSummary;
}

export type FeedEvent = ToolCallEvent | RoutingEvent | FindingEvent | DispositionEvent;

export const REQUEST_IDS = ["GOV-001", "GOV-002", "GOV-003"] as const;

// See simulated_uc_data.py's GOVERNANCE_REQUESTS for the underlying brief text.
export const REQUEST_INFO: Record<(typeof REQUEST_IDS)[number], { title: string; description: string; estimatedTime: string }> = {
  "GOV-001": {
    title: "Market outlook memo",
    description: "A wealth advisor wants a personalized market memo for a client — tempts toward customer data outside market research's scope.",
    estimatedTime: "~1–2 min",
  },
  "GOV-002": {
    title: "Credit exposure review",
    description: "A credit limit increase review for a platinum client — tests purpose limitation on an otherwise-allowed source.",
    estimatedTime: "~1–2 min",
  },
  "GOV-003": {
    title: "Retirement plan update",
    description: "A tailored wealth plan draft for a longtime client — tempts toward raw PII instead of portfolio data.",
    estimatedTime: "~1–2 min",
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

export function initialInput(requestId: string, provider: string): GovernanceState {
  return {
    request_id: requestId,
    provider,
    brief: "",
    assigned_role: "",
    task_type: "",
    roles_attempted: [],
    escalated: false,
    finding: {},
    denial_log: [],
    final_decision: "",
  };
}
