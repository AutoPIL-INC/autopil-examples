// Mirrors policies/financial_services/aml_compliance.yaml — kept in sync by hand.
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
    role: "aml_investigator",
    displayName: "AML Investigator",
    description: "Transaction and watchlist analysis for AML; strict isolation from identity/KYC and unrelated internal data.",
    allowedSources: ["catalog.risk.transaction_history", "catalog.risk.watchlist", "catalog.risk.counterparty_data", "catalog.risk.account_summaries", "catalog.risk.delinquency_records"],
    deniedSources: ["catalog.risk.risk_models", "catalog.wealth.executive_communications"],
    maxSensitivity: "critical",
    sessionTtlMinutes: 60,
  },
  {
    role: "kyc_agent",
    displayName: "KYC Agent",
    description: "Identity verification and sanctions screening; no transaction data or internal risk models. Longest session TTL of the three — a KYC refresh workflow runs longer than a single investigation step.",
    allowedSources: ["catalog.risk.identity_records", "catalog.risk.loan_history", "catalog.risk.credit_scores"],
    deniedSources: ["catalog.risk.risk_models", "catalog.wealth.executive_communications"],
    maxSensitivity: "high",
    sessionTtlMinutes: 240,
  },
  {
    role: "compliance_officer",
    displayName: "Compliance Officer",
    description: "Broad audit, regulatory, and cross-client review access — the sign-off role. Reaches into client-profile/portfolio data as well as risk-catalog sources for cross-client audit; restricted only from executive communications.",
    allowedSources: ["catalog.risk.account_summaries", "catalog.risk.credit_scores", "catalog.risk.audit_logs", "catalog.risk.regulatory_filings", "catalog.risk.transaction_history", "catalog.wealth.client_profile", "catalog.wealth.portfolio_holdings"],
    deniedSources: ["catalog.wealth.executive_communications"],
    maxSensitivity: "critical",
    sessionTtlMinutes: 60,
  },
];

export const REGULATIONS = [
  { id: "BSA-AML", name: "Bank Secrecy Act — Anti-Money Laundering (31 CFR Part 1020)" },
  { id: "FINCEN-CDD", name: "FinCEN Customer Due Diligence Rule (31 CFR 1010.230)" },
  { id: "OFAC", name: "OFAC Sanctions Screening Requirements" },
  { id: "SOX", name: "Sarbanes-Oxley Act — Sections 302 and 404" },
  { id: "FINRA-4511", name: "FINRA Rules 4511/4512 — Books and Records" },
];
