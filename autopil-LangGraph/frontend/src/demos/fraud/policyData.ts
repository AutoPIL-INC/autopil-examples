// Mirrors policies/financial_services/fraud_investigation.yaml — kept in sync by hand.
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
    role: "fraud_orchestrator",
    displayName: "Fraud Orchestrator",
    description: "Routes fraud alerts and coordinates sub-agents; orchestration only, no raw data access.",
    allowedSources: ["fraud_alerts", "case_metadata", "agent_outputs"],
    deniedSources: [
      "transaction_history", "transaction_patterns", "account_pii", "account_summaries",
      "identity_data", "kyc_records", "sanctions_list", "adverse_media",
      "merchant_codes", "amount_thresholds",
    ],
    maxSensitivity: "medium",
    sessionTtlMinutes: 480,
  },
  {
    role: "transaction_analyst",
    displayName: "Transaction Analyst",
    description: "Payment patterns and velocity analysis; no identity or account PII access.",
    allowedSources: ["transaction_history", "transaction_patterns", "amount_thresholds", "merchant_codes", "velocity_signals"],
    deniedSources: ["account_pii", "identity_data", "kyc_records", "sanctions_list", "adverse_media", "account_summaries"],
    maxSensitivity: "critical",
    sessionTtlMinutes: 60,
  },
  {
    role: "account_profiler",
    displayName: "Account Profiler",
    description: "Account-level risk signals and tenure analysis; no transaction detail or identity data.",
    allowedSources: ["account_summaries", "account_flags", "risk_scores", "product_holdings", "account_tenure"],
    deniedSources: ["transaction_history", "transaction_patterns", "identity_data", "kyc_records", "sanctions_list", "account_pii"],
    maxSensitivity: "critical",
    sessionTtlMinutes: 60,
  },
  {
    role: "kyc_specialist",
    displayName: "KYC Specialist",
    description: "Identity verification and watchlist screening; no transaction or account data access.",
    allowedSources: ["identity_data", "kyc_records", "sanctions_list", "adverse_media", "pep_registry"],
    deniedSources: ["transaction_history", "transaction_patterns", "account_summaries", "account_flags", "risk_scores", "merchant_codes"],
    maxSensitivity: "critical",
    sessionTtlMinutes: 60,
  },
  {
    role: "sar_generator",
    displayName: "SAR Generator",
    description: "Generates reports from processed agent outputs only; no raw data source access.",
    allowedSources: ["agent_outputs", "case_metadata", "regulatory_templates"],
    deniedSources: [
      "transaction_history", "transaction_patterns", "account_pii", "account_summaries",
      "identity_data", "kyc_records", "sanctions_list", "adverse_media",
      "merchant_codes", "amount_thresholds", "risk_scores", "account_flags", "velocity_signals",
    ],
    maxSensitivity: "critical",
    sessionTtlMinutes: 60,
  },
];

export const REGULATIONS = [
  { id: "BSA-AML", name: "Bank Secrecy Act — Anti-Money Laundering (31 CFR Part 1020)" },
  { id: "FINCEN-CDD", name: "FinCEN Customer Due Diligence Rule (31 CFR 1010.230)" },
  { id: "OFAC", name: "OFAC Sanctions Screening Requirements" },
  { id: "USA-PATRIOT", name: "USA PATRIOT Act — Section 326 Customer Identification Program" },
  { id: "FINRA-4511", name: "FINRA Rules 4511/4512 — Books and Records" },
];
