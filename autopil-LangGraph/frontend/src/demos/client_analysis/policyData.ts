// Mirrors policies/financial_services/client_analysis.yaml — kept in sync by
// hand. This is reference/display data only; the real enforcement happens server-side
// via AutoPIL's ContextGuard, not anything in this file.

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
    role: "junior_analyst",
    displayName: "Junior Analyst",
    description: "Market research and reporting only; PII denied outright regardless of task.",
    allowedSources: ["catalog.finance.market_data", "catalog.finance.public_reports"],
    deniedSources: ["catalog.finance.customer_pii", "catalog.finance.transaction_history", "catalog.finance.stress_test_models"],
    maxSensitivity: "medium",
    sessionTtlMinutes: 60,
  },
  {
    role: "senior_analyst",
    displayName: "Senior Analyst",
    description: "Broad source access, but task_bindings enforce purpose limitation — customer_pii is allowed generally, not for credit_analysis. Critical data blocked by the sensitivity ceiling (max_sensitivity: high), not a source denial.",
    allowedSources: [
      "catalog.finance.market_data", "catalog.finance.public_reports", "catalog.finance.customer_pii",
      "catalog.finance.transaction_history", "catalog.finance.credit_scores", "catalog.finance.risk_models",
      "catalog.finance.stress_test_models",
    ],
    deniedSources: [],
    maxSensitivity: "high",
    sessionTtlMinutes: 120,
  },
  {
    role: "wealth_advisor",
    displayName: "Wealth Advisor",
    description: "Portfolio-focused; raw customer PII denied (GDPR Art.5 data minimization) — must work from client_portfolios instead.",
    allowedSources: [
      "catalog.finance.client_portfolios", "catalog.finance.credit_scores", "catalog.finance.market_data",
      "catalog.finance.risk_models", "catalog.finance.public_reports",
    ],
    deniedSources: ["catalog.finance.customer_pii", "catalog.finance.transaction_history", "catalog.finance.stress_test_models"],
    maxSensitivity: "high",
    sessionTtlMinutes: 120,
  },
];

export const REGULATIONS = [
  { id: "GLBA", name: "Gramm-Leach-Bliley Act — Consumer Financial Data" },
  { id: "GDPR-Art5", name: "GDPR Art. 5(1)(b) — Purpose Limitation" },
  { id: "FCRA", name: "Fair Credit Reporting Act — Permissible Purpose" },
];
