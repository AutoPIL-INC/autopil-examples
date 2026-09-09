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

// Order mirrors trading_desk_ops.yaml's own `policies:` list — trading_ops_orchestrator,
// order_intake_agent, instrument_classification_agent (NEW, Fixed Income only),
// allocation_agent (Equities only), affirmation_matching_agent,
// settlement_reconciliation_agent, exception_investigation_agent,
// compliance_reporting_agent. Every reused role's allowed/denied sources below were
// extended (not left untouched) to cover Fixed Income's new sources where that role's
// policy genuinely grew — see trading_desk_ops.yaml's own per-policy comments this
// mirrors.
export const AGENT_POLICIES: AgentPolicy[] = [
  {
    role: "trading_ops_orchestrator",
    displayName: "Trading Ops Orchestrator",
    description: "Classifies the incoming trigger (new order / amendment / cancellation / PM rebalance / corporate-action trade) AND the sub-domain (equities / fixed_income), then routes to specialists; orchestration only, no raw source access.",
    allowedSources: ["case_metadata", "agent_outputs"],
    deniedSources: ["raw_instructions", "security_master", "client_account_data", "client_position_data", "investment_restrictions", "trade_capture", "counterparty_records", "ssi_data", "dtcc_cns_data", "internal_position_ledger", "reg_sho_locate_data", "share_inventory_data", "desk_pnl_data", "commission_data", "pricing_data", "cross_client_position_data", "other_client_orders", "client_pii", "day_count_reference", "ficc_gsd_data", "ficc_mbsd_data", "pool_notification_data", "fails_charge_data"],
    maxSensitivity: "high",
    sessionTtlMinutes: 480,
  },
  {
    role: "order_intake_agent",
    displayName: "Order Intake Agent",
    description: "Parses raw instruction (email/FIX text) and security master reference data into a structured trade ticket; flags potential short-sale status. Skipped entirely on the Equities PM-rebalance path. Same job for fixed income — instrument classification is instrument_classification_agent's job, not this role's.",
    allowedSources: ["raw_instructions", "security_master"],
    deniedSources: ["client_account_data", "client_position_data", "pricing_data", "commission_data", "cross_client_position_data", "dtcc_cns_data", "internal_position_ledger", "day_count_reference", "ficc_gsd_data", "ficc_mbsd_data", "pool_notification_data", "fails_charge_data"],
    maxSensitivity: "medium",
    sessionTtlMinutes: 120,
  },
  {
    role: "instrument_classification_agent",
    displayName: "Instrument Classification Agent",
    description: "Fixed income only (NEW role). Resolves an instrument's type (Treasury / corporate / municipal / agency MBS-TBA) from CUSIP/security-master reference data into its settlement cycle and day-count convention — everything downstream depends on getting this right (FI-002 is what happens when it doesn't). No client account, position, pricing, or commission data access, and no downstream clearing/netting/penalty source access — classification is grounded in reference data alone.",
    allowedSources: ["security_master"],
    deniedSources: ["client_account_data", "client_position_data", "pricing_data", "commission_data", "cross_client_position_data", "dtcc_cns_data", "internal_position_ledger", "day_count_reference", "ficc_gsd_data", "ficc_mbsd_data", "pool_notification_data", "fails_charge_data"],
    maxSensitivity: "low",
    sessionTtlMinutes: 120,
  },
  {
    role: "allocation_agent",
    displayName: "Allocation Agent",
    description: "Equities only. Splits the order across sub-accounts respecting concentration limits and client restrictions, scoped to accounts in this block only. No FI-### scenario splits a block across sub-accounts, so this role plays no part in the fixed income domain.",
    allowedSources: ["client_account_data", "client_position_data", "investment_restrictions", "structured_orders"],
    deniedSources: ["pricing_data", "commission_data", "cross_client_position_data", "raw_instructions", "dtcc_cns_data", "internal_position_ledger"],
    maxSensitivity: "high",
    sessionTtlMinutes: 120,
  },
  {
    role: "affirmation_matching_agent",
    displayName: "Affirmation Matching Agent",
    description: "Matches internal trade capture vs. counterparty/custodian records and standing settlement instructions, same trade-date. For fixed income, also verifies the settlement amount's day-count convention against reference data to catch accrued-interest cash breaks — a genuinely different break type from a quantity/SSI mismatch. A mismatch is a flag, never a unilateral fix.",
    allowedSources: ["trade_capture", "counterparty_records", "ssi_data", "day_count_reference"],
    deniedSources: ["client_pii", "pricing_data", "commission_data", "client_account_data", "desk_pnl_data", "ficc_gsd_data", "ficc_mbsd_data", "pool_notification_data", "fails_charge_data"],
    maxSensitivity: "high",
    sessionTtlMinutes: 60,
  },
  {
    role: "settlement_reconciliation_agent",
    displayName: "Settlement Reconciliation Agent",
    description: "Verifies the firm's net settlement obligation — DTCC/NSCC for equities and corporate/municipal bonds, FICC GSD for Treasuries, FICC MBSD for agency MBS TBA — against the internal position ledger, and TBA pool-notification deadline status. No desk P&L, commission, day-count, or Fails Charge access.",
    allowedSources: ["dtcc_cns_data", "internal_position_ledger", "ficc_gsd_data", "ficc_mbsd_data", "pool_notification_data"],
    deniedSources: ["desk_pnl_data", "commission_data", "other_client_orders", "client_account_data", "pricing_data", "day_count_reference", "fails_charge_data"],
    maxSensitivity: "high",
    sessionTtlMinutes: 60,
  },
  {
    role: "exception_investigation_agent",
    displayName: "Exception Investigation Agent",
    description: "Triages a flagged break using whatever settlement/affirmation data is relevant — for equities: timing lag, data/SSI error, fails-to-deliver risk; for fixed income: a day-count cash break, a TBA pool-notification deadline at risk (proactive), or a genuine Treasury/Agency MBS fails-to-deliver (FICC Fails Charge). Widest reasoning scope of any role, but still denied desk P&L/commission — the information-barrier boundary.",
    allowedSources: ["dtcc_cns_data", "internal_position_ledger", "ssi_data", "trade_capture", "counterparty_records", "reg_sho_locate_data", "share_inventory_data", "day_count_reference", "ficc_gsd_data", "ficc_mbsd_data", "pool_notification_data", "fails_charge_data"],
    deniedSources: ["desk_pnl_data", "commission_data", "client_account_data", "client_pii", "pricing_data"],
    maxSensitivity: "high",
    sessionTtlMinutes: 120,
  },
  {
    role: "compliance_reporting_agent",
    displayName: "Compliance Reporting Agent",
    description: "Compiles the FINRA CAT-style audit record (equities) or the TRACE/MSRB-RTRS-style near-real-time record (fixed income) from compiled agent outputs only; never touches a raw trade/position/settlement source in either domain — the narrative style differs by domain, the access boundary does not.",
    allowedSources: ["agent_outputs"],
    deniedSources: ["case_metadata", "raw_instructions", "security_master", "client_account_data", "client_position_data", "investment_restrictions", "trade_capture", "counterparty_records", "ssi_data", "dtcc_cns_data", "internal_position_ledger", "reg_sho_locate_data", "share_inventory_data", "desk_pnl_data", "commission_data", "pricing_data", "cross_client_position_data", "other_client_orders", "client_pii", "day_count_reference", "ficc_gsd_data", "ficc_mbsd_data", "pool_notification_data", "fails_charge_data"],
    maxSensitivity: "high",
    sessionTtlMinutes: 60,
  },
];

// Mirrors trading_desk_ops.yaml's top-level `regulations:` metadata block — new to
// this demo, no sibling demo's policyData.ts has this shape. Each regulation names the
// applicable rule(s) and exactly which policy mechanism enforces it, so the
// Description tab can show a real compliance-framework table instead of a bare list
// of IDs (see REGULATIONS in quality_control's own policyData.ts for the simpler,
// pre-existing convention this extends). First 9 are the original Equities-era set;
// last 5 are Fixed Income's additions.
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
        rule: "Standard settlement of most securities transactions must occur on T+1 — since May 2024, this includes corporate and municipal bonds too, not just equities; Treasuries were already T+1",
        howEnforced: "The whole pipeline's time pressure — no role or task in this policy carries slack for manual exception handling; every task_binding assumes same-trade-date completion. Only agency MBS traded TBA settles on a different, fixed monthly SIFMA calendar instead (see FICC-MBSD-PTN below)",
      },
    ],
  },
  {
    id: "SEC-15C6-2",
    name: "SEC Rule 15c6-2 — Same-Day Affirmation (SDA) Mandate",
    applicableRules: [
      {
        rule: "Institutional trade affirmation must complete same trade-date",
        howEnforced: "affirmation_matching_agent_policy task_bindings restrict trade_matching/ssi_verification to trade_capture, counterparty_records, ssi_data, and (fixed income) day_count_reference only — no pricing or commission data can distract from the affirmation check",
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
        howEnforced: "order_intake_agent_policy task_bindings bind short_sale_flagging to security_master; exception_investigation_agent_policy task_bindings bind break_triage to reg_sho_locate_data for the fails-to-deliver escalation path — the Tier 2 review EQ-005 triggers. Equities only — does not apply to fixed income settlement at all (every FI-### case's reg_sho_locate_data carries an explicit 'not applicable' stub); see FICC-FAILS-CHARGE below for that domain's own mechanism",
      },
    ],
  },
  {
    id: "FINRA-CAT",
    name: "FINRA CAT — Consolidated Audit Trail",
    applicableRules: [
      {
        rule: "Every order event (receipt, route, modify, cancel, execute) reported with timestamps",
        howEnforced: "compliance_reporting_agent_policy task_bindings restrict its audit_compilation task (equities) to agent_outputs only — the FINRA CAT-style record is compiled from other agents' outputs, never a raw source, mapping directly onto AutoPIL's own tamper-evident audit log",
      },
    ],
  },
  {
    id: "SEC-17A-4",
    name: "SEC Rule 17a-4 — WORM Recordkeeping for Broker-Dealers",
    applicableRules: [
      {
        rule: "Records of investigation and settlement decisions must be tamper-evident",
        howEnforced: "cryptographic audit chain on every ALLOW/DENY event across all 8 roles (Equities and Fixed Income alike), same mechanism every demo in this repo relies on",
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
  {
    id: "FICC-GSD",
    name: "FICC Government Securities Division (GSD) — Treasury Clearing & Netting",
    applicableRules: [
      {
        rule: "Treasury trades clear and net through FICC's Government Securities Division, verified against internal books",
        howEnforced: "settlement_reconciliation_agent_policy and exception_investigation_agent_policy task_bindings bind settlement_verification/break_triage to ficc_gsd_data for Treasury net settlement obligations — FI-005's core check, this domain's analogue of DTCC/NSCC CNS above",
      },
    ],
  },
  {
    id: "FICC-MBSD-PTN",
    name: "FICC Mortgage-Backed Securities Division (MBSD) — Pass-Thru Notification (PTN)",
    applicableRules: [
      {
        rule: "Agency MBS traded TBA (To-Be-Announced) must clear a 48-hour Pass-Thru Notification before the fixed monthly SIFMA settlement date — a different clearing corp and settlement calendar than corporate/municipal bonds or Treasuries",
        howEnforced: "settlement_reconciliation_agent_policy and exception_investigation_agent_policy task_bindings bind to ficc_mbsd_data/pool_notification_data — FI-004's proactive deadline-escalation check, grounded in pool_notification_data.deadline_at_risk and fired BEFORE any fail occurs, not a reactive break investigation",
      },
    ],
  },
  {
    id: "FICC-FAILS-CHARGE",
    name: "FICC Fails Charge Trading Practice",
    applicableRules: [
      {
        rule: "A genuine Treasury or Agency MBS settlement fail triggers FICC's formula-based Fails Charge Trading Practice penalty",
        howEnforced: "exception_investigation_agent_policy task_bindings bind break_triage to fails_charge_data; decision_node routes any real inventory_shortfall on a fixed-income case where fails_charge_applicable is true to Tier 2 compliance-officer review — FI-005, this domain's own named penalty mechanism in place of Reg SHO",
      },
    ],
  },
  {
    id: "FINRA-TRACE-MSRB-G14",
    name: "FINRA Rule 6730 (TRACE) / MSRB Rule G-14 (RTRS) — Post-Trade Reporting",
    applicableRules: [
      {
        rule: "Corporate and municipal bond trades must be reported within 15 minutes of execution (TRACE for corporates, MSRB RTRS for municipals) — a materially tighter clock than equities' end-of-day FINRA CAT-style compile",
        howEnforced: "compliance_reporting_agent_policy's trace_compilation task compiles a TRACE/MSRB-RTRS-style near-real-time record for fixed income cases from agent_outputs only — same 'never touches a raw source' compiler pattern as its audit_compilation task for equities, just a different narrative style and a tighter implied clock",
      },
    ],
  },
  {
    id: "DAY-COUNT-CONVENTION",
    name: "Day-Count Convention Standards (Actual/Actual vs. 30/360)",
    applicableRules: [
      {
        rule: "Accrued interest must be computed using the correct day-count convention for the instrument type — Actual/Actual for Treasuries, 30/360 for corporate/municipal bonds and agency MBS",
        howEnforced: "affirmation_matching_agent_policy and exception_investigation_agent_policy task_bindings bind to day_count_reference — grounds FI-003's cash-break detection in a real reference table, not an LLM's own arithmetic",
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
  // Fixed income addition — settlement_reconciliation_agent_policy denies fails_charge_data
  // (the penalty calc is exception_investigation_agent's job once a real shortfall is
  // confirmed, not settlement_reconciliation_agent's); grounded in FICC-FAILS-CHARGE's
  // own how_enforced text naming exception_investigation_agent_policy as the binding owner.
  { tool: "get_fails_charge_data", role: "settlement_reconciliation_agent", regulationId: "FICC-FAILS-CHARGE" },
];

export function regulationForDenial(tool: string, role: string): Regulation | undefined {
  const match = REGULATION_BY_DENIAL.find(
    (m) => m.tool === tool && (m.role == null || m.role === role),
  );
  return match ? REGULATIONS.find((r) => r.id === match.regulationId) : undefined;
}
