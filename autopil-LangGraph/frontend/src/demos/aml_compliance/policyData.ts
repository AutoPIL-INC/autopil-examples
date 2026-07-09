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
    allowedSources: ["transaction_history", "watchlist", "counterparty_data", "account_summaries", "delinquency_records"],
    deniedSources: ["risk_models", "executive_communications"],
    maxSensitivity: "critical",
    sessionTtlMinutes: 60,
  },
  {
    role: "kyc_agent",
    displayName: "KYC Agent",
    description: "Identity verification and sanctions screening; no transaction data or internal risk models. Longest session TTL of the three — a KYC refresh workflow runs longer than a single investigation step.",
    allowedSources: ["identity_records", "loan_history", "credit_scores"],
    deniedSources: ["risk_models", "executive_communications"],
    maxSensitivity: "high",
    sessionTtlMinutes: 240,
  },
  {
    role: "compliance_officer",
    displayName: "Compliance Officer",
    description: "Broad audit, regulatory, and cross-client review access — the sign-off role. Reaches into client-profile/portfolio data as well as risk-catalog sources for cross-client audit; restricted only from executive communications.",
    allowedSources: ["account_summaries", "credit_scores", "audit_logs", "regulatory_filings", "transaction_history", "client_profile", "portfolio_holdings"],
    deniedSources: ["executive_communications"],
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
