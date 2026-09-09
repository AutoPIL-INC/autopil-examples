// Mirrors TradingOpsState in trading_desk_ops_demo.py — only the fields the UI
// actually reads are typed strictly, the rest are left loose. `domain` is now
// populated with "equities" OR "fixed_income" at runtime (TRADING_DOMAINS has both
// built) — left as `string` here since the state shape itself didn't change, only the
// set of real values it takes on.
export interface TradingOpsState {
  [key: string]: unknown;
  case_id: string;
  provider: string;
  domain: string;
  trigger_type: string;
  case: Record<string, unknown>;
  route_plan: string[];
  specialists_run: string[];
  skipped_roles: string[];
  findings: Record<string, unknown>;
  compliance_report: Record<string, unknown>;
  denial_log: unknown[];
  orchestration_steps: number;
  tier: string;
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

// Both routing stages here are genuinely LLM-driven — unlike quality_control's fixed
// "initial" first step, trading_ops_orchestrator_node's classification call is a real
// decision (domain + trigger_type), and that classification is what decides which
// specialist runs first. Neither stage should render as a "FIXED STEP" badge; see
// RoutingRow in ExecutionTab.tsx. "initial" additionally carries `skipped` — roles the
// classification determined are genuinely not applicable to this trigger (e.g.
// order_intake_agent on a pm_rebalance trigger), rendered as a distinct SKIP row so a
// viewer can see EQ-004's path diverge from EQ-001's without reading raw JSON.
export interface RoutingEvent {
  type: "routing";
  stage: "initial" | "review";
  domain?: string;
  trigger_type?: string;
  route?: string[];
  skipped?: string[];
  next?: string;
  reasoning?: string;
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

// _collect_audit_summary()'s per-role shape — one row per policy decision, source is
// guard.get_audit_trail() directly. Same shape as every other demo in this repo.
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

// Mirrors decision_node's "disposition" _emit(...) call exactly — carries tier/
// tier_label and skipped_roles, neither of which any prior demo's DispositionEvent has.
// `action`/`proposed_action` are always one of PROPOSED_ACTIONS below (7 entries now —
// 4 Equities, 3 Fixed Income) — see classifyProposedAction() for how the UI keys off
// this exact string to distinguish break TYPES, since decision_node never emits a
// separate "break_type" field on this event directly.
export interface DispositionEvent {
  type: "disposition";
  case_id: string;
  action: string;
  proposed_action: string;
  tier: string;
  tier_label: string;
  human_approved: boolean;
  human_override_action: string | null;
  human_notes: string | null;
  specialists_run: string[];
  skipped_roles: string[];
  denial_count: number;
  audit_summary: AuditSummary;
}

export type FeedEvent = ToolCallEvent | RoutingEvent | FindingEvent | DispositionEvent;

// Mirrors the dict passed to interrupt(...) in decision_node exactly — the single
// disposition-approval pause this demo has (no second MCP/audit-source-choice pause,
// same as every other demo in this repo). notes_required is always true —
// decision_node loops on interrupt() until a non-empty notes field comes back on the
// resume payload, on BOTH approve and override, at BOTH tiers. The UI must enforce the
// same thing at the form layer (disable submit until non-empty).
//
// tier / tier_label is the field no sibling demo's interrupt payload has — which of the
// two reviewer tiers (ops-analyst vs. compliance-officer) this case requires, computed
// server-side from real fixture data (inventory_shortfall / break_type /
// pool_notification deadline / fails_charge_applicable), never from the case_id. The
// review form must render a visibly different tier, not just a different label — see
// ReviewPanel in ExecutionTab.tsx.
export interface ReviewInterruptPayload {
  case_id: string;
  domain: string;
  trigger_type: string;
  case: Record<string, unknown>;
  tier: string;
  tier_label: string;
  proposed_action: string;
  specialists_run: string[];
  skipped_roles: string[];
  findings: Record<string, { summary?: string; recommendation?: string }>;
  compliance_report: { summary?: string; recommendation?: string };
  denial_log: Array<{ agent_role: string; tool: string; reason: string }>;
  notes_required: true;
}

// Must match decision_node's exact TIER_LABELS strings. Tier 2's label now names both
// domains' own escalation mechanism (Reg SHO for equities, FICC Fails Charge for fixed
// income) — decision_node picks the same tier either way, just a different named
// penalty regime underneath, per its own docstring.
export const TIER_LABELS: Record<string, string> = {
  tier1_ops_analyst: "Tier 1 — Ops Analyst",
  tier2_compliance_officer: "Tier 2 — Compliance Officer (Reg SHO / FICC Fails Charge escalation)",
};

// Must match decision_node's exact PROPOSED_ACTIONS strings — the override dropdown
// can only pick one of these, so it can never drift from what the backend understands.
// First 4 are Equities' original set; last 3 are Fixed Income's additions.
export const OVERRIDE_ACTIONS = [
  "CLEAR TO SETTLE — clean straight-through processing, no exception",
  "CORRECT SSI & REPROCESS — stale settlement instruction confirmed",
  "INVESTIGATE TIMING LAG — affirmation discrepancy, no settlement risk",
  "ESCALATE — FAILS-TO-DELIVER RISK: obtain Reg SHO locate/borrow before settlement",
  "CORRECT DAY-COUNT & REPROCESS — accrued-interest cash break confirmed",
  "ESCALATE POOL NOTIFICATION — confirm PTN before the 48-hour SIFMA cutoff",
  "ESCALATE — TREASURY FAILS-TO-DELIVER: FICC Fails Charge applies, obtain funding/borrow before settlement",
] as const;

// classifyProposedAction() keys off the exact PROPOSED_ACTIONS string a disposition or
// interrupt payload actually carries — the only backend-emitted signal that reliably
// distinguishes break TYPE (a specialist's own free-text `recommendation`/`summary`
// isn't a fixed enum, so it can't be parsed reliably; decision_node's proposed_action
// is). Grounded directly in decision_node's own if/elif chain in
// trading_desk_ops_demo.py — not an invented distinction:
//   - "cash_break": FI-003 — a day-count/accrued-interest mismatch, genuinely distinct
//     from a quantity/SSI break (a different fixture field entirely, not a relabeling).
//   - "pool_notification_risk": FI-004 — fires on pool_notification_data.deadline_at_risk
//     BEFORE any break_type/inventory_shortfall check even runs — a proactive
//     escalation, not a reactive break investigation.
//   - "fails_to_deliver_fi": FI-005 — a genuine Treasury inventory_shortfall with
//     fails_charge_applicable true (FICC's named penalty, not Reg SHO).
//   - "fails_to_deliver_eq": EQ-005 — the same inventory_shortfall branch, but Reg SHO
//     locate-requirement logic instead (fails_charge_applicable is never true for an
//     equities case).
//   - "ssi_error" / "timing_lag": EQ-002 / EQ-003 — the two pre-existing Equities break
//     types, kept distinct from FI-003's cash_break above.
//   - "clean": every case's own no-exception straight-through disposition.
export type BreakKind =
  | "clean"
  | "ssi_error"
  | "timing_lag"
  | "fails_to_deliver_eq"
  | "cash_break"
  | "pool_notification_risk"
  | "fails_to_deliver_fi";

export interface BreakKindInfo {
  kind: BreakKind;
  label: string;
  proactive?: true; // fires before any fail/break — a fundamentally different framing
}

const BREAK_KIND_BY_ACTION: Record<string, BreakKindInfo> = {
  "CLEAR TO SETTLE — clean straight-through processing, no exception": {
    kind: "clean", label: "Clean — no exception",
  },
  "CORRECT SSI & REPROCESS — stale settlement instruction confirmed": {
    kind: "ssi_error", label: "SSI / quantity break",
  },
  "INVESTIGATE TIMING LAG — affirmation discrepancy, no settlement risk": {
    kind: "timing_lag", label: "Timing-lag break",
  },
  "ESCALATE — FAILS-TO-DELIVER RISK: obtain Reg SHO locate/borrow before settlement": {
    kind: "fails_to_deliver_eq", label: "Fails-to-deliver (Reg SHO)",
  },
  "CORRECT DAY-COUNT & REPROCESS — accrued-interest cash break confirmed": {
    kind: "cash_break", label: "Cash break (day-count)",
  },
  "ESCALATE POOL NOTIFICATION — confirm PTN before the 48-hour SIFMA cutoff": {
    kind: "pool_notification_risk", label: "Proactive — PTN deadline at risk", proactive: true,
  },
  "ESCALATE — TREASURY FAILS-TO-DELIVER: FICC Fails Charge applies, obtain funding/borrow before settlement": {
    kind: "fails_to_deliver_fi", label: "Fails-to-deliver (FICC Fails Charge)",
  },
};

export function classifyProposedAction(action: string): BreakKindInfo | undefined {
  return BREAK_KIND_BY_ACTION[action];
}

export const CASE_IDS = [
  "EQ-001", "EQ-002", "EQ-003", "EQ-004", "EQ-005",
  "FI-001", "FI-002", "FI-003", "FI-004", "FI-005",
] as const;

export const EQ_CASE_IDS = ["EQ-001", "EQ-002", "EQ-003", "EQ-004", "EQ-005"] as const;
export const FI_CASE_IDS = ["FI-001", "FI-002", "FI-003", "FI-004", "FI-005"] as const;

// Spoiler-light reference copy, same convention every sibling demo's CASE_INFO
// follows — adapted from trading_desk_ops_data.CASE_METADATA's own trigger_brief text,
// not invented. EQ-004's copy names the PM-rebalance trigger explicitly since that's
// the whole point of the scenario (watch the routing differ), not a spoiler about the
// eventual disposition or tier. FI-### copy follows the same non-spoiler convention —
// names the mechanism under test (instrument classification, day-count/accrued
// interest, Pass-Thru Notification timing), never the eventual tier or disposition.
export const CASE_INFO: Record<(typeof CASE_IDS)[number], { title: string; description: string; estimatedTime: string }> = {
  "EQ-001": {
    title: "New block order — 10,000 shares MSFT",
    description: "A new FIX order needs allocation across institutional sub-accounts, same-day affirmation, and DTCC/NSCC settlement verification, inside the T+1 window.",
    estimatedTime: "~1–2 min",
  },
  "EQ-002": {
    title: "Same-day affirmation exception — 10,000 shares NVDA",
    description: "One custodian account on file for this client base hasn't been re-verified in a long time — worth tracing before this trade affirms.",
    estimatedTime: "~1–2 min",
  },
  "EQ-003": {
    title: "Affirmation discrepancy — 10,000 shares AAPL",
    description: "Standard processing expected, flagged for review since affirmation doesn't match cleanly on the same trade-date.",
    estimatedTime: "~1–2 min",
  },
  "EQ-004": {
    title: "PM rebalance instruction — 4,000 shares AMZN",
    description: "An already-structured portfolio-manager rebalance instruction, not a raw FIX/email order — watch how the orchestrator routes this differently from a new order.",
    estimatedTime: "~1–2 min",
  },
  "EQ-005": {
    title: "Settlement desk flag — 10,000 shares GOOG",
    description: "The settlement desk flagged a possible inventory shortfall ahead of the settlement date — needs verification before it's confirmed as a real risk.",
    estimatedTime: "~1–2 min",
  },
  "FI-001": {
    title: "New corporate bond order — $5,000,000 face Apple 4.000% '33",
    description: "A new corporate bond order needs instrument classification, same-day affirmation (including day-count verification), and DTCC settlement verification, inside the T+1 window.",
    estimatedTime: "~1–2 min",
  },
  "FI-002": {
    title: "Instrument classification check — $2,000,000 face FNMA note",
    description: "The desk describes this as a standard agency note, but the CUSIP hasn't been cross-checked against security master yet — confirm instrument type and clearing corp before this is booked.",
    estimatedTime: "~1–2 min",
  },
  "FI-003": {
    title: "Accrued-interest verification — $10,000,000 face UST 4.125% '31",
    description: "Desk asks that accrued interest be confirmed independently before affirmation — flag if the settlement amount doesn't tie out under the correct day-count convention.",
    estimatedTime: "~1–2 min",
  },
  "FI-004": {
    title: "Pass-Thru Notification timing — $3,000,000 face FNMA TBA",
    description: "Pass-Thru Notification hasn't been filed for this pool yet — confirm timing against the 48-hour cutoff before the fixed SIFMA settlement date.",
    estimatedTime: "~1–2 min",
  },
  "FI-005": {
    title: "Settlement desk flag — $10,000,000 face UST 3.875% '30",
    description: "The settlement desk flagged a possible inventory shortfall against the FICC GSD obligation ahead of settlement — needs verification before it's confirmed as a real risk.",
    estimatedTime: "~1–2 min",
  },
};

// Mirrors trading_desk_ops_data.CASE_METADATA — kept in sync by hand, same "adapted
// from the real backend data" pattern as policyData.ts. `domain`/`quantityUnit` are
// reference/display fields only (not read off any live event) — quantityUnit mirrors
// CASE_METADATA's own real `quantity_unit` field ("shares" default for equities, "$
// face value" for every FI-### case), used to drive the case-queue's domain badge and
// avoid hardcoding "shares" for a fixed-income face-value quantity.
export interface CaseMeta {
  caseId: string;
  domain: "equities" | "fixed_income";
  symbol: string;
  side: string;
  totalQuantity: number;
  quantityUnit: string;
}

export const CASE_META: Record<(typeof CASE_IDS)[number], CaseMeta> = {
  "EQ-001": { caseId: "EQ-001", domain: "equities", symbol: "MSFT", side: "BUY", totalQuantity: 10000, quantityUnit: "shares" },
  "EQ-002": { caseId: "EQ-002", domain: "equities", symbol: "NVDA", side: "BUY", totalQuantity: 10000, quantityUnit: "shares" },
  "EQ-003": { caseId: "EQ-003", domain: "equities", symbol: "AAPL", side: "BUY", totalQuantity: 10000, quantityUnit: "shares" },
  "EQ-004": { caseId: "EQ-004", domain: "equities", symbol: "AMZN", side: "SELL", totalQuantity: 4000, quantityUnit: "shares" },
  "EQ-005": { caseId: "EQ-005", domain: "equities", symbol: "GOOG", side: "BUY", totalQuantity: 10000, quantityUnit: "shares" },
  "FI-001": { caseId: "FI-001", domain: "fixed_income", symbol: "AAPL 4.000% '33", side: "BUY", totalQuantity: 5000000, quantityUnit: "$ face value" },
  "FI-002": { caseId: "FI-002", domain: "fixed_income", symbol: "FNMA 30yr 5.000%", side: "BUY", totalQuantity: 2000000, quantityUnit: "$ face value" },
  "FI-003": { caseId: "FI-003", domain: "fixed_income", symbol: "UST 4.125% '31", side: "BUY", totalQuantity: 10000000, quantityUnit: "$ face value" },
  "FI-004": { caseId: "FI-004", domain: "fixed_income", symbol: "FNMA 30yr 5.500% TBA", side: "BUY", totalQuantity: 3000000, quantityUnit: "$ face value" },
  "FI-005": { caseId: "FI-005", domain: "fixed_income", symbol: "UST 3.875% '30", side: "BUY", totalQuantity: 10000000, quantityUnit: "$ face value" },
};

export const DOMAIN_LABELS: Record<CaseMeta["domain"], string> = {
  equities: "Equities",
  fixed_income: "Fixed Income",
};

// Must match _make_llm()'s provider strings in trading_desk_ops_demo.py.
// Ollama listed first (and used as the default selection) — fully local, no key, no
// external API to rate-limit or 503 on you. Same convention quality_control's own
// PROVIDERS list follows.
export const PROVIDERS = [
  { value: "ollama", label: "Ollama (local, free)" },
  { value: "gemini", label: "Gemini (Google, free tier)" },
  { value: "anthropic", label: "Claude (Anthropic)" },
  { value: "groq", label: "Groq (Llama, free tier)" },
] as const;

export function initialInput(caseId: string, provider: string): TradingOpsState {
  return {
    case_id: caseId,
    provider,
    domain: "",
    trigger_type: "",
    case: {},
    route_plan: [],
    specialists_run: [],
    skipped_roles: [],
    findings: {},
    compliance_report: {},
    denial_log: [],
    orchestration_steps: 0,
    tier: "",
    final_decision: "",
    audit_summary: {},
  };
}
