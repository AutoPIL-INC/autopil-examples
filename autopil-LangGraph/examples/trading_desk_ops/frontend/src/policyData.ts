// Mirrors policies/financial_services/trading_desk_ops.yaml — kept in sync by hand.
// This is reference/display data only; the real enforcement happens server-side via
// AutoPIL's ContextGuard, not anything in this file.

export interface AgentPolicy {
  role: string;
  displayName: string;
  description: string;
  allowedSources: string[];
  deniedSources: string[];
  maxSensitivity: string;
  sessionTtlMinutes: number;
}

export const AGENT_POLICIES: AgentPolicy[] = [
  {
    role: "trading_ops_orchestrator",
    displayName: "Trading Ops Orchestrator",
    description: "Classifies the incoming trigger (new order / amendment / cancellation / PM rebalance / corporate-action trade) and routes to specialists; orchestration only, no raw source access.",
    allowedSources: ["case_metadata", "agent_outputs"],
    deniedSources: ["raw_instructions", "security_master", "client_account_data", "client_position_data", "investment_restrictions", "trade_capture", "counterparty_records", "ssi_data", "dtcc_cns_data", "internal_position_ledger", "reg_sho_locate_data", "share_inventory_data", "desk_pnl_data", "commission_data", "pricing_data", "cross_client_position_data", "other_client_orders", "client_pii"],
    maxSensitivity: "high",
    sessionTtlMinutes: 480,
  },
  {
    role: "order_intake_agent",
    displayName: "Order Intake Agent",
    description: "Parses raw instruction (email/FIX text) and security master reference data into a structured trade ticket; flags potential short-sale status. Skipped entirely on the PM-rebalance path.",
    allowedSources: ["raw_instructions", "security_master"],
    deniedSources: ["client_account_data", "client_position_data", "pricing_data", "commission_data", "cross_client_position_data", "dtcc_cns_data", "internal_position_ledger"],
    maxSensitivity: "medium",
    sessionTtlMinutes: 120,
  },
  {
    role: "allocation_agent",
    displayName: "Allocation Agent",
    description: "Splits the order across sub-accounts respecting concentration limits and client restrictions, scoped to accounts in this block only.",
    allowedSources: ["client_account_data", "client_position_data", "investment_restrictions", "structured_orders"],
    deniedSources: ["pricing_data", "commission_data", "cross_client_position_data", "raw_instructions", "dtcc_cns_data", "internal_position_ledger"],
    maxSensitivity: "high",
    sessionTtlMinutes: 120,
  },
  {
    role: "affirmation_matching_agent",
    displayName: "Affirmation Matching Agent",
    description: "Matches internal trade capture vs. counterparty/custodian records and standing settlement instructions, same trade-date. A mismatch is a flag, never a unilateral fix.",
    allowedSources: ["trade_capture", "counterparty_records", "ssi_data"],
    deniedSources: ["client_pii", "pricing_data", "commission_data", "client_account_data", "desk_pnl_data"],
    maxSensitivity: "high",
    sessionTtlMinutes: 60,
  },
  {
    role: "settlement_reconciliation_agent",
    displayName: "Settlement Reconciliation Agent",
    description: "Verifies the firm's net DTCC/NSCC settlement obligation against the internal position ledger.",
    allowedSources: ["dtcc_cns_data", "internal_position_ledger"],
    deniedSources: ["desk_pnl_data", "commission_data", "other_client_orders", "client_account_data", "pricing_data"],
    maxSensitivity: "high",
    sessionTtlMinutes: 60,
  },
  {
    role: "exception_investigation_agent",
    displayName: "Exception Investigation Agent",
    description: "Triages a flagged break (timing lag, data/SSI error, fails-to-deliver risk) using whatever settlement/affirmation data is relevant to that specific break. Widest reasoning scope of any role, but still denied desk P&L/commission — the information-barrier boundary.",
    allowedSources: ["dtcc_cns_data", "internal_position_ledger", "ssi_data", "trade_capture", "counterparty_records", "reg_sho_locate_data", "share_inventory_data"],
    deniedSources: ["desk_pnl_data", "commission_data", "client_account_data", "client_pii", "pricing_data"],
    maxSensitivity: "high",
    sessionTtlMinutes: 120,
  },
  {
    role: "compliance_reporting_agent",
    displayName: "Compliance Reporting Agent",
    description: "Compiles the FINRA CAT-style audit record from compiled agent outputs only; never touches a raw trade/position/settlement source.",
    allowedSources: ["agent_outputs"],
    deniedSources: ["case_metadata", "raw_instructions", "security_master", "client_account_data", "client_position_data", "investment_restrictions", "trade_capture", "counterparty_records", "ssi_data", "dtcc_cns_data", "internal_position_ledger", "reg_sho_locate_data", "share_inventory_data", "desk_pnl_data", "commission_data", "pricing_data", "cross_client_position_data", "other_client_orders", "client_pii"],
    maxSensitivity: "high",
    sessionTtlMinutes: 60,
  },
];

// Mirrors trading_desk_ops.yaml's top-level `regulations:` metadata block — new to
// this demo, no sibling demo's policyData.ts has this shape. Each regulation names the
// applicable rule(s) and exactly which policy mechanism enforces it, so the
// Description tab can show a real compliance-framework table instead of a bare list
// of IDs (see REGULATIONS in quality_control's own policyData.ts for the simpler,
// pre-existing convention this extends).
export interface RegulationRule {
  rule: string;
  howEnforced: string;
}

export interface Regulation {
  id: string;
  name: string;
  applicableRules: RegulationRule[];
}

export const REGULATIONS: Regulation[] = [
  {
    id: "SEC-15C6-1",
    name: "SEC Rule 15c6-1 — T+1 Settlement Cycle",
    applicableRules: [
      {
        rule: "Standard settlement of most securities transactions must occur on T+1",
        howEnforced: "The whole pipeline's time pressure — no role or task in this policy carries slack for manual exception handling; every task_binding assumes same-trade-date completion",
      },
    ],
  },
  {
    id: "SEC-15C6-2",
    name: "SEC Rule 15c6-2 — Same-Day Affirmation (SDA) Mandate",
    applicableRules: [
      {
        rule: "Institutional trade affirmation must complete same trade-date",
        howEnforced: "affirmation_matching_agent_policy task_bindings restrict trade_matching/ssi_verification to trade_capture, counterparty_records, and ssi_data only — no pricing or commission data can distract from the affirmation check",
      },
    ],
  },
  {
    id: "DTCC-NSCC-CNS",
    name: "DTCC/NSCC Continuous Net Settlement (CNS)",
    applicableRules: [
      {
        rule: "Firm's netted settlement obligation must be verified against internal books",
        howEnforced: "settlement_reconciliation_agent_policy task_bindings bind settlement_verification to dtcc_cns_data and internal_position_ledger only — a mismatch here is EQ-005's fails-to-deliver scenario",
      },
    ],
  },
  {
    id: "SEC-15C3-3",
    name: "SEC Rule 15c3-3 — Customer Protection Rule",
    applicableRules: [
      {
        rule: "Client assets and positions must stay segregated, including internally",
        howEnforced: "allocation_agent_policy denied_sources blocks cross_client_position_data — one client's allocation is never visible to any agent not handling that specific block",
      },
    ],
  },
  {
    id: "REG-SHO",
    name: "Regulation SHO — Locate Requirement",
    applicableRules: [
      {
        rule: "A locate must be obtained before executing (or covering) a short sale / delivery shortfall",
        howEnforced: "order_intake_agent_policy task_bindings bind short_sale_flagging to security_master; exception_investigation_agent_policy task_bindings bind break_triage to reg_sho_locate_data for the fails-to-deliver escalation path — the Tier 2 review EQ-005 triggers",
      },
    ],
  },
  {
    id: "FINRA-CAT",
    name: "FINRA CAT — Consolidated Audit Trail",
    applicableRules: [
      {
        rule: "Every order event (receipt, route, modify, cancel, execute) reported with timestamps",
        howEnforced: "compliance_reporting_agent_policy task_bindings restrict audit_compilation to agent_outputs only — the FINRA CAT-style record is compiled from other agents' outputs, never a raw source, mapping directly onto AutoPIL's own tamper-evident audit log",
      },
    ],
  },
  {
    id: "SEC-17A-4",
    name: "SEC Rule 17a-4 — WORM Recordkeeping for Broker-Dealers",
    applicableRules: [
      {
        rule: "Records of investigation and settlement decisions must be tamper-evident",
        howEnforced: "cryptographic audit chain on every ALLOW/DENY event across all 7 roles, same mechanism every demo in this repo relies on",
      },
    ],
  },
  {
    id: "INFO-BARRIER-MNPI",
    name: "Information Barriers / MNPI Policy",
    applicableRules: [
      {
        rule: "Trading-side agents must not access desk P&L, commission, or other-desk data",
        howEnforced: "settlement_reconciliation_agent_policy and exception_investigation_agent_policy both list desk_pnl_data and commission_data in denied_sources — grounds the EQ-003 over-scope denial in a real regulatory boundary, not an arbitrary rule",
      },
    ],
  },
  {
    id: "FINRA-5310",
    name: "FINRA Rule 5310 — Best Execution",
    applicableRules: [
      {
        rule: "Obligation to seek best execution when allocating and working a client order",
        howEnforced: "Contextual reasoning input for allocation_agent's block_allocation/concentration_check tasks — not a hard denial anywhere in this policy",
      },
    ],
  },
];

// Client-side display mapping only — grounds a live denial in whichever regulation the
// DESIGN.md compliance table already ties that tool's source to (see REGULATIONS
// above), so the Execution tab can surface "why this matters," not just "what was
// denied." Keyed by (tool name, denying role) since get_internal_position_ledger is a
// legitimately allowed tool for settlement_reconciliation_agent/
// exception_investigation_agent but an over-scope bypass tool when
// compliance_reporting_agent reaches for it. Nothing invented here — every entry
// traces to a denied_sources/task_bindings line actually present in
// trading_desk_ops.yaml (see AGENT_POLICIES above) or the regulations block itself.
export const REGULATION_BY_DENIAL: Array<{ tool: string; role?: string; regulationId: string }> = [
  { tool: "get_desk_pnl_data", regulationId: "INFO-BARRIER-MNPI" },
  { tool: "get_commission_data", regulationId: "INFO-BARRIER-MNPI" },
  { tool: "get_cross_client_position_data", regulationId: "SEC-15C3-3" },
  { tool: "get_internal_position_ledger", role: "compliance_reporting_agent", regulationId: "FINRA-CAT" },
];

export function regulationForDenial(tool: string, role: string): Regulation | undefined {
  const match = REGULATION_BY_DENIAL.find(
    (m) => m.tool === tool && (m.role == null || m.role === role),
  );
  return match ? REGULATIONS.find((r) => r.id === match.regulationId) : undefined;
}
