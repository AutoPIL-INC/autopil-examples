// Mirrors policies/financial_services/portfolio_review_wealth.yaml and
// portfolio_review_risk.yaml — kept in sync by hand. This is reference/display data
// only; the real enforcement happens server-side via AutoPIL's ContextGuard, not
// anything in this file.

export interface AgentPolicy {
  role: string;
  displayName: string;
  description: string;
  policyFile: "wealth" | "risk";
  allowedSources: string[];
  deniedSources: string[];
  maxSensitivity: string;
  sessionTtlMinutes: number;
}

export const AGENT_POLICIES: AgentPolicy[] = [
  {
    role: "portfolio_orchestrator", displayName: "Portfolio Orchestrator", policyFile: "wealth",
    description: "Orchestrates institutional reviews; routes to sub-agents; no raw portfolio data access.",
    allowedSources: ["catalog.wealth.client_profile", "catalog.wealth.agent_outputs"],
    deniedSources: ["catalog.wealth.portfolio_holdings", "catalog.wealth.other_client_portfolios", "catalog.wealth.rebalancing_instructions"],
    maxSensitivity: "high", sessionTtlMinutes: 240,
  },
  {
    role: "wealth_advisor", displayName: "Wealth Advisor", policyFile: "wealth",
    description: "Client portfolio and market data for advisory; blocked from other clients' data (fiduciary wall) and pricing models.",
    allowedSources: ["catalog.wealth.portfolio_holdings", "catalog.wealth.market_data", "catalog.wealth.client_profile", "catalog.wealth.product_catalog", "catalog.wealth.research_reports"],
    deniedSources: ["catalog.wealth.other_client_portfolios", "catalog.wealth.internal_pricing_models", "catalog.wealth.executive_communications"],
    maxSensitivity: "high", sessionTtlMinutes: 240,
  },
  {
    role: "investment_analyst", displayName: "Investment Analyst", policyFile: "wealth",
    description: "Research and market data analysis; no client PII or portfolio holdings — but IS authorized for peer benchmarking (critical-sensitivity ceiling, scoped to that one source).",
    allowedSources: ["catalog.wealth.market_data", "catalog.wealth.research_reports", "catalog.wealth.macro_indicators", "catalog.wealth.sec_filings", "catalog.wealth.economic_indicators", "catalog.wealth.other_client_portfolios"],
    deniedSources: ["catalog.wealth.client_profile", "catalog.wealth.portfolio_holdings"],
    maxSensitivity: "critical", sessionTtlMinutes: 480,
  },
  {
    role: "macro_analyst", displayName: "Macro Analyst", policyFile: "wealth",
    description: "Macro and economic regime analysis; no client portfolio or profile data access.",
    allowedSources: ["catalog.wealth.macro_indicators", "catalog.wealth.economic_indicators", "catalog.wealth.market_data", "catalog.wealth.research_reports", "catalog.wealth.geopolitical_signals"],
    deniedSources: ["catalog.wealth.portfolio_holdings", "catalog.wealth.client_profile", "catalog.wealth.other_client_portfolios"],
    maxSensitivity: "medium", sessionTtlMinutes: 480,
  },
  {
    role: "rebalancing_agent", displayName: "Rebalancing Agent", policyFile: "wealth",
    description: "Per-client rebalancing analysis; scoped to the assigned client, no cross-client access.",
    allowedSources: ["catalog.wealth.portfolio_holdings", "catalog.wealth.rebalancing_instructions", "catalog.wealth.market_data", "catalog.wealth.product_catalog", "catalog.wealth.agent_outputs"],
    deniedSources: ["catalog.wealth.other_client_portfolios", "catalog.wealth.client_profile"],
    maxSensitivity: "high", sessionTtlMinutes: 240,
  },
  {
    role: "report_generator", displayName: "Report Generator", policyFile: "wealth",
    description: "Generates client reports from compiled agent outputs only; no raw portfolio data access.",
    allowedSources: ["catalog.wealth.agent_outputs", "catalog.wealth.research_reports", "catalog.wealth.regulatory_templates"],
    deniedSources: ["catalog.wealth.portfolio_holdings", "catalog.wealth.client_profile", "catalog.wealth.other_client_portfolios", "catalog.wealth.portfolio_metrics"],
    maxSensitivity: "critical", sessionTtlMinutes: 60,
  },
  {
    role: "credit_risk_analyst", displayName: "Credit Risk Analyst", policyFile: "risk",
    description: "Portfolio metrics and economic analysis for credit review; no client PII or board materials access.",
    allowedSources: ["catalog.risk.loan_history", "catalog.risk.credit_scores", "catalog.wealth.economic_indicators", "catalog.wealth.portfolio_metrics", "catalog.risk.delinquency_records"],
    deniedSources: ["catalog.wealth.executive_communications", "catalog.risk.board_materials", "catalog.wealth.client_profile"],
    maxSensitivity: "high", sessionTtlMinutes: 240,
  },
  {
    role: "settlement_agent", displayName: "Settlement Agent", policyFile: "risk",
    description: "Trade settlement and counterparty verification; no client PII or portfolio holdings access.",
    allowedSources: ["catalog.risk.trade_confirmations", "catalog.risk.counterparty_data"],
    deniedSources: ["catalog.wealth.portfolio_holdings", "catalog.wealth.client_profile"],
    maxSensitivity: "high", sessionTtlMinutes: 60,
  },
];

export const REGULATIONS = [
  { id: "INVESTMENT-ADVISERS-ACT", name: "Investment Advisers Act of 1940" },
  { id: "FINRA-2111", name: "FINRA Rule 2111 — Suitability" },
  { id: "REG-BI", name: "SEC Regulation Best Interest (Reg BI)" },
  { id: "FINRA-4511", name: "FINRA Rules 4511/4512 — Books and Records" },
  { id: "SOX", name: "Sarbanes-Oxley Act — Sections 302 and 404" },
  { id: "SR-11-7", name: "SR 11-7 — Model Risk Management Guidance" },
  { id: "SSAE-18", name: "SSAE 18 — Settlement and Custody Controls" },
];
