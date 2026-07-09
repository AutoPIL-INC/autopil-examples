"""
AutoPIL + LangGraph: Institutional Portfolio Review Demo (8 roles, two policy files)
========================================================================================
Eight roles — one orchestrator plus seven specialists (investment_analyst,
macro_analyst, wealth_advisor, rebalancing_agent, report_generator,
credit_risk_analyst, settlement_agent) — enforced under TWO real AutoPIL policy files
at once: policies/financial_services/portfolio_review_wealth.yaml (wealth-advisory
roles) and portfolio_review_risk.yaml (risk/compliance roles). Which policy file
governs a role is a property of the role, not the source it's reaching for —
credit_scores, loan_history, and risk_models are referenced by roles from *both*
files, evaluated under whichever file that specific role's policy lives in.

The AML/KYC/cross-client-audit workflow (aml_investigator, kyc_agent,
compliance_officer) that used to live here as the `aml_case` review type has moved to
its own standalone demo — examples/aml_compliance/ — since it's a thematically
distinct financial-crime-governance story that sat awkwardly split across both policy
files. See that demo's DESIGN.md for the split rationale.

Every role is handed the same full toolbelt across both catalogs — no restriction in the
tool layer at all. AutoPIL's guard.protect() (one of two ContextGuard instances,
depending on the calling role) decides what actually succeeds.

An orchestrator reads a natural-language review request and decides which review_type it
falls under; that maps to a known ordered sequence of (role, task) steps — modeling how
an institutional review actually flows (research → advisory → rebalancing → settlement →
reporting), not a scripted violation. Each role in the sequence runs a real tool-calling
loop; denials happen when the model reasons its way toward a source its role or task
doesn't cover. A single escalation path exists for the fiduciary-boundary review type,
mirroring the source demo's Scenario 2.

See DESIGN.md for the full design rationale.

Run:
    .venv/bin/python examples/institutional_portfolio_review/institutional_portfolio_review_demo.py
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, TypedDict

from dotenv import load_dotenv

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.config import get_stream_writer
from langgraph.graph import END, StateGraph
from langgraph.types import Command, interrupt

from autopil import ContextGuard, SensitivityLevel
from autopil.db.sqlite import SQLiteAgentRegistryStore
from autopil.models import AgentRegistryEntry
import portfolio_review_uc_data as ucdata

load_dotenv()

# ── config ──────────────────────────────────────────────────────────────────────
WEALTH_POLICY_FILE = ROOT / "policies" / "financial_services" / "portfolio_review_wealth.yaml"
RISK_POLICY_FILE    = ROOT / "policies" / "financial_services" / "portfolio_review_risk.yaml"
AUDIT_DB            = ROOT / "institutional_portfolio_review_audit.db"
TENANT_ID           = "default"
MAX_TOOL_TURNS      = 6

SPECIALIST_ROLES = [
    "investment_analyst", "macro_analyst", "wealth_advisor", "rebalancing_agent",
    "report_generator", "credit_risk_analyst", "settlement_agent",
]

# Which policy file (and therefore which ContextGuard) governs each role. This is a
# property of the role, not of the source it's reaching for — credit_scores/
# loan_history/risk_models are referenced by roles from both files, evaluated under
# whichever file the calling role's own policy lives in.
WEALTH_ROLES = {"portfolio_orchestrator", "wealth_advisor", "investment_analyst",
                 "macro_analyst", "rebalancing_agent", "report_generator"}
RISK_ROLES   = {"credit_risk_analyst", "settlement_agent"}

AGENT_REGISTRY_STORE = SQLiteAgentRegistryStore(str(AUDIT_DB))
AGENT_IDS = {role: f"{role.replace('_', '-')}-001" for role in ["portfolio_orchestrator", *SPECIALIST_ROLES]}


def _register_agents() -> None:
    now = datetime.now(timezone.utc)
    for role, agent_id in AGENT_IDS.items():
        AGENT_REGISTRY_STORE.create(
            AgentRegistryEntry(
                agent_id=agent_id, tenant_id=TENANT_ID, agent_role=role,
                display_name=role.replace("_", " ").title(), status="approved",
                version="1.0.0", created_at=now, updated_at=now,
            ),
            TENANT_ID,
        )


# Hosted AutoPIL SaaS trial mode — opt in by setting both AUTOPIL_ADMIN_KEY and
# AUTOPIL_EVALUATE_KEY (same explicit-opt-in pattern as the other 3 demos). Verified
# live against a real trial tenant — see saas_guard.py's module docstring: none of
# this demo's 8 pre-seeded role policies on the shared tenant actually match (they
# use plain source names; this demo's local policy uses catalog.wealth./catalog.risk.
# prefixed names), so _POLICY_SPECS below gets translated into 8 brand-new
# "demo_<role>_policy" policies via ensure_policy() rather than reusing anything
# pre-seeded.
_SAAS_MODE = bool(os.getenv("AUTOPIL_ADMIN_KEY")) and bool(os.getenv("AUTOPIL_EVALUATE_KEY"))

# Field-for-field translation of portfolio_review_wealth.yaml/portfolio_review_risk.yaml
# into CreatePolicyRequest bodies — source names kept exactly as this demo already
# sends them (catalog.wealth.*/catalog.risk.* prefixed), so no other code here needs
# to change for SaaS mode. session_ttl_minutes/sensitivity_decay are omitted — no such
# field exists on this endpoint (confirmed against the real OpenAPI schema).
_POLICY_SPECS = {
    "portfolio_orchestrator": {
        "description": "Orchestrates institutional reviews; routes to sub-agents; no raw portfolio data access",
        "allowed_sources": ["catalog.wealth.client_profile", "catalog.wealth.agent_outputs"],
        "denied_sources": ["catalog.wealth.portfolio_holdings", "catalog.wealth.other_client_portfolios",
                            "catalog.wealth.rebalancing_instructions", "catalog.risk.credit_scores"],
        "allowed_tasks": ["portfolio_review", "agent_routing", "workflow_orchestration"],
        "denied_tasks": ["trade_execution", "credit_decision"],
        "max_sensitivity": "high", "require_task_for_sensitivity": "high",
        "task_bindings": [
            {"task": "portfolio_review", "permitted_sources": ["catalog.wealth.client_profile", "catalog.wealth.agent_outputs"]},
            {"task": "agent_routing", "permitted_sources": ["catalog.wealth.client_profile"]},
            {"task": "workflow_orchestration", "permitted_sources": ["catalog.wealth.client_profile", "catalog.wealth.agent_outputs"]},
        ],
    },
    "wealth_advisor": {
        "description": "Client portfolio and market data for advisory; blocked from other clients and pricing models",
        "allowed_sources": ["catalog.wealth.portfolio_holdings", "catalog.wealth.market_data",
                             "catalog.wealth.client_profile", "catalog.wealth.product_catalog",
                             "catalog.wealth.research_reports"],
        "denied_sources": ["catalog.wealth.other_client_portfolios", "catalog.wealth.internal_pricing_models",
                            "catalog.wealth.executive_communications", "catalog.risk.credit_scores"],
        "allowed_tasks": ["portfolio_review", "rebalancing_recommendation", "product_pitch", "client_report"],
        "denied_tasks": ["trade_execution", "account_freeze", "credit_decision"],
        "max_sensitivity": "high", "require_task_for_sensitivity": "high",
        "task_bindings": [
            {"task": "portfolio_review", "permitted_sources": ["catalog.wealth.portfolio_holdings", "catalog.wealth.client_profile"]},
            {"task": "rebalancing_recommendation", "permitted_sources": ["catalog.wealth.portfolio_holdings", "catalog.wealth.market_data", "catalog.wealth.product_catalog"]},
            {"task": "product_pitch", "permitted_sources": ["catalog.wealth.product_catalog", "catalog.wealth.research_reports", "catalog.wealth.client_profile"]},
            {"task": "client_report", "permitted_sources": ["catalog.wealth.client_profile", "catalog.wealth.portfolio_holdings", "catalog.wealth.market_data", "catalog.wealth.research_reports"]},
        ],
    },
    "investment_analyst": {
        "description": "Research and market data analysis; no client PII or portfolio holdings access",
        "allowed_sources": ["catalog.wealth.market_data", "catalog.wealth.research_reports",
                             "catalog.wealth.macro_indicators", "catalog.wealth.sec_filings",
                             "catalog.wealth.economic_indicators", "catalog.wealth.other_client_portfolios"],
        "denied_sources": ["catalog.wealth.client_profile", "catalog.wealth.portfolio_holdings", "catalog.risk.credit_scores"],
        "allowed_tasks": ["market_analysis", "report_generation", "sector_review", "benchmarking"],
        "denied_tasks": ["trade_execution", "credit_decision", "product_recommendation"],
        "max_sensitivity": "critical",
        "task_bindings": [
            {"task": "market_analysis", "permitted_sources": ["catalog.wealth.market_data", "catalog.wealth.macro_indicators", "catalog.wealth.economic_indicators"]},
            {"task": "report_generation", "permitted_sources": ["catalog.wealth.research_reports", "catalog.wealth.market_data", "catalog.wealth.sec_filings", "catalog.wealth.economic_indicators"]},
            {"task": "sector_review", "permitted_sources": ["catalog.wealth.market_data", "catalog.wealth.research_reports", "catalog.wealth.sec_filings"]},
            {"task": "benchmarking", "permitted_sources": ["catalog.wealth.other_client_portfolios", "catalog.wealth.market_data", "catalog.wealth.research_reports"]},
        ],
    },
    "macro_analyst": {
        "description": "Macro and economic analysis; no client portfolio or profile data access",
        "allowed_sources": ["catalog.wealth.macro_indicators", "catalog.wealth.economic_indicators",
                             "catalog.wealth.market_data", "catalog.wealth.research_reports",
                             "catalog.wealth.geopolitical_signals"],
        "denied_sources": ["catalog.wealth.portfolio_holdings", "catalog.wealth.client_profile",
                            "catalog.wealth.other_client_portfolios", "catalog.risk.credit_scores",
                            "catalog.wealth.rebalancing_instructions"],
        "allowed_tasks": ["macro_analysis", "market_outlook", "regime_assessment", "scenario_modeling"],
        "denied_tasks": ["trade_execution", "credit_decision", "product_recommendation", "client_report"],
        "max_sensitivity": "medium",
        "task_bindings": [
            {"task": "macro_analysis", "permitted_sources": ["catalog.wealth.macro_indicators", "catalog.wealth.economic_indicators", "catalog.wealth.geopolitical_signals"]},
            {"task": "market_outlook", "permitted_sources": ["catalog.wealth.market_data", "catalog.wealth.macro_indicators", "catalog.wealth.economic_indicators"]},
            {"task": "regime_assessment", "permitted_sources": ["catalog.wealth.macro_indicators", "catalog.wealth.geopolitical_signals", "catalog.wealth.research_reports"]},
            {"task": "scenario_modeling", "permitted_sources": ["catalog.wealth.macro_indicators", "catalog.wealth.economic_indicators", "catalog.wealth.market_data", "catalog.wealth.geopolitical_signals"]},
        ],
    },
    "rebalancing_agent": {
        "description": "Per-client rebalancing analysis; scoped to assigned client, no cross-client access",
        "allowed_sources": ["catalog.wealth.portfolio_holdings", "catalog.wealth.rebalancing_instructions",
                             "catalog.wealth.market_data", "catalog.wealth.product_catalog", "catalog.wealth.agent_outputs"],
        "denied_sources": ["catalog.wealth.other_client_portfolios", "catalog.wealth.client_profile",
                            "catalog.risk.credit_scores", "catalog.wealth.macro_indicators"],
        "allowed_tasks": ["rebalancing_recommendation", "drift_analysis", "trade_proposal"],
        "denied_tasks": ["trade_execution", "credit_decision", "client_report", "cross_client_comparison"],
        "max_sensitivity": "high", "require_task_for_sensitivity": "high",
        "task_bindings": [
            {"task": "rebalancing_recommendation", "permitted_sources": ["catalog.wealth.portfolio_holdings", "catalog.wealth.rebalancing_instructions", "catalog.wealth.market_data", "catalog.wealth.product_catalog"]},
            {"task": "drift_analysis", "permitted_sources": ["catalog.wealth.portfolio_holdings", "catalog.wealth.market_data"]},
            {"task": "trade_proposal", "permitted_sources": ["catalog.wealth.portfolio_holdings", "catalog.wealth.rebalancing_instructions", "catalog.wealth.market_data", "catalog.wealth.product_catalog"]},
        ],
    },
    "report_generator": {
        "description": "Generates client reports from compiled agent outputs only; no raw portfolio data access",
        "allowed_sources": ["catalog.wealth.agent_outputs", "catalog.wealth.research_reports", "catalog.wealth.regulatory_templates"],
        "denied_sources": ["catalog.wealth.portfolio_holdings", "catalog.wealth.client_profile",
                            "catalog.wealth.other_client_portfolios", "catalog.wealth.portfolio_metrics",
                            "catalog.wealth.rebalancing_instructions"],
        "allowed_tasks": ["client_report", "portfolio_summary", "quarterly_review"],
        "denied_tasks": ["trade_execution", "cross_client_comparison", "rebalancing_recommendation"],
        "max_sensitivity": "critical", "require_task_for_sensitivity": "high",
        "task_bindings": [
            {"task": "client_report", "permitted_sources": ["catalog.wealth.agent_outputs", "catalog.wealth.research_reports", "catalog.wealth.regulatory_templates"]},
            {"task": "portfolio_summary", "permitted_sources": ["catalog.wealth.agent_outputs"]},
            {"task": "quarterly_review", "permitted_sources": ["catalog.wealth.agent_outputs", "catalog.wealth.research_reports", "catalog.wealth.regulatory_templates"]},
        ],
    },
    "credit_risk_analyst": {
        "description": "Portfolio metrics and economic analysis; no client PII or board materials access",
        "allowed_sources": ["catalog.risk.loan_history", "catalog.risk.credit_scores",
                             "catalog.wealth.economic_indicators", "catalog.wealth.portfolio_metrics",
                             "catalog.risk.delinquency_records"],
        "denied_sources": ["catalog.wealth.executive_communications", "catalog.risk.board_materials", "catalog.wealth.client_profile"],
        "allowed_tasks": ["stress_test", "pd_modeling", "limit_review", "risk_report"],
        "denied_tasks": ["credit_decision", "account_freeze"],
        "max_sensitivity": "high", "require_task_for_sensitivity": "high",
        "task_bindings": [
            {"task": "stress_test", "permitted_sources": ["catalog.risk.loan_history", "catalog.risk.credit_scores", "catalog.wealth.portfolio_metrics", "catalog.wealth.economic_indicators"]},
            {"task": "pd_modeling", "permitted_sources": ["catalog.risk.loan_history", "catalog.risk.credit_scores", "catalog.risk.delinquency_records"]},
            {"task": "limit_review", "permitted_sources": ["catalog.risk.loan_history", "catalog.risk.credit_scores", "catalog.wealth.portfolio_metrics"]},
            {"task": "risk_report", "permitted_sources": ["catalog.wealth.portfolio_metrics", "catalog.risk.delinquency_records", "catalog.wealth.economic_indicators"]},
        ],
    },
    "settlement_agent": {
        "description": "Trade settlement and counterparty verification; no client PII or portfolio holdings access",
        "allowed_sources": ["catalog.risk.trade_confirmations", "catalog.risk.counterparty_data"],
        "denied_sources": ["catalog.wealth.portfolio_holdings", "catalog.wealth.client_profile", "catalog.risk.credit_scores"],
        "allowed_tasks": ["trade_settlement", "counterparty_verification"],
        "denied_tasks": ["trade_execution", "credit_decision"],
        "max_sensitivity": "high", "require_task_for_sensitivity": "high",
        "task_bindings": [
            {"task": "trade_settlement", "permitted_sources": ["catalog.risk.trade_confirmations"]},
            {"task": "counterparty_verification", "permitted_sources": ["catalog.risk.counterparty_data"]},
        ],
    },
}

if _SAAS_MODE:
    from ipr_saas_guard import RemoteContextGuard, bootstrap_agents, ensure_policy
    _API_URL = os.getenv("AUTOPIL_API_URL", "https://autopil-api.onrender.com")
    # owner_tag/policy names must be demo-specific, not the generic "autopil-langgraph-
    # demos" tag fraud_investigation/client_analysis use — this demo's "wealth_advisor"
    # role name collides with client_analysis's own, and bootstrap_agents() only
    # de-dupes by (agent_role, owner_tag), not by which demo is asking. Caught live: a
    # first attempt with the generic tag silently bound this demo's wealth_advisor
    # agent to client_analysis's existing one (and would have skipped creating this
    # demo's own demo_wealth_advisor_policy for the same reason, since ensure_policy()
    # only checks for a name match). ipr_-prefixed tag/policy names below avoid it.
    for role, spec in _POLICY_SPECS.items():
        ensure_policy(_API_URL, os.environ["AUTOPIL_ADMIN_KEY"], f"demo_ipr_{role}_policy", role, spec)
    AGENT_IDS.update(bootstrap_agents(
        _API_URL, os.environ["AUTOPIL_ADMIN_KEY"], roles=list(AGENT_IDS),
        owner_tag="Investments-team",
        policy_name_for=lambda role: f"demo_ipr_{role}_policy",
    ))
    _remote_guard = RemoteContextGuard(_API_URL, os.environ["AUTOPIL_EVALUATE_KEY"], os.environ["AUTOPIL_ADMIN_KEY"])
    wealth_guard = _remote_guard
    risk_guard = _remote_guard
else:
    _register_agents()
    wealth_guard = ContextGuard(policy_path=str(WEALTH_POLICY_FILE), audit_db=str(AUDIT_DB),
                                 tenant_id=TENANT_ID, agent_registry_store=AGENT_REGISTRY_STORE)
    risk_guard   = ContextGuard(policy_path=str(RISK_POLICY_FILE), audit_db=str(AUDIT_DB),
                                 tenant_id=TENANT_ID, agent_registry_store=AGENT_REGISTRY_STORE)

ROLE_GUARD = {role: (wealth_guard if role in WEALTH_ROLES else risk_guard)
              for role in [*WEALTH_ROLES, *RISK_ROLES]}


def _make_llm(provider: str = ""):
    """Same fallback chain as client_analysis_demo.py — Bedrock (opt-in via
    AWS_BEDROCK_MODEL_ID) → Anthropic → Gemini → Groq → Ollama (default, no key)."""
    if not provider:
        provider = (
            "bedrock" if os.getenv("AWS_BEDROCK_MODEL_ID")
            else "anthropic" if os.getenv("ANTHROPIC_API_KEY")
            else "gemini" if os.getenv("GOOGLE_API_KEY")
            else "groq" if os.getenv("GROQ_API_KEY")
            else "ollama"
        )
    if provider == "bedrock":
        if not os.getenv("AWS_BEDROCK_MODEL_ID"):
            raise RuntimeError("AWS_BEDROCK_MODEL_ID not set (see .env.example)")
        from langchain_aws import ChatBedrockConverse
        return ChatBedrockConverse(model=os.getenv("AWS_BEDROCK_MODEL_ID"),
                                    region_name=os.getenv("AWS_REGION", "us-east-1"))
    if provider == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY not set (see .env.example)")
        return ChatAnthropic(model="claude-opus-4-8", api_key=os.getenv("ANTHROPIC_API_KEY"))
    if provider == "gemini":
        if not os.getenv("GOOGLE_API_KEY"):
            raise RuntimeError("GOOGLE_API_KEY not set (see .env.example)")
        return ChatGoogleGenerativeAI(model="gemini-3.5-flash", api_key=os.getenv("GOOGLE_API_KEY"))
    if provider == "groq":
        if not os.getenv("GROQ_API_KEY"):
            raise RuntimeError("GROQ_API_KEY not set (see .env.example)")
        return ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY"))
    if provider == "ollama":
        return ChatOllama(model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"))
    raise ValueError(f"Unknown provider: {provider!r}")


def _bind_forced(llm, tools: list, tool_name: str):
    """Force a tool_choice where supported, falling back to unforced binding when the
    provider ignores it (Ollama) or raises (some non-Anthropic Bedrock models) — same
    helper as client_analysis_demo.py."""
    try:
        return llm.bind_tools(tools, tool_choice=tool_name)
    except ValueError:
        return llm.bind_tools(tools)


SESSIONS: dict[str, str] = {}


def _reset_sessions() -> None:
    for role in ["orchestrator", *SPECIALIST_ROLES]:
        SESSIONS[role] = str(uuid.uuid4())


_reset_sessions()

# ── data sources — every role is offered the full toolbelt across both catalogs ──
SOURCES = {
    "catalog.wealth.client_profile":            ucdata.CLIENTS,
    "catalog.wealth.portfolio_holdings":         ucdata.PORTFOLIO_HOLDINGS,
    "catalog.wealth.other_client_portfolios":    ucdata.OTHER_CLIENT_PORTFOLIOS,
    "catalog.wealth.rebalancing_instructions":   ucdata.REBALANCING_INSTRUCTIONS,
    "catalog.wealth.market_data":                ucdata.MARKET_DATA,
    "catalog.wealth.product_catalog":            ucdata.PRODUCT_CATALOG,
    "catalog.wealth.research_reports":           ucdata.RESEARCH_REPORTS,
    "catalog.wealth.internal_pricing_models":    ucdata.INTERNAL_PRICING_MODELS,
    "catalog.wealth.executive_communications":   ucdata.EXECUTIVE_COMMUNICATIONS,
    "catalog.wealth.macro_indicators":           ucdata.MACRO_INDICATORS,
    "catalog.wealth.economic_indicators":        ucdata.ECONOMIC_INDICATORS,
    "catalog.wealth.sec_filings":                ucdata.SEC_FILINGS,
    "catalog.wealth.geopolitical_signals":       ucdata.GEOPOLITICAL_SIGNALS,
    "catalog.wealth.regulatory_templates":       ucdata.REGULATORY_TEMPLATES,
    "catalog.wealth.agent_outputs":              ucdata.AGENT_OUTPUTS,
    "catalog.wealth.portfolio_metrics":          ucdata.PORTFOLIO_METRICS,
    "catalog.risk.account_summaries":            ucdata.ACCOUNT_SUMMARIES,
    "catalog.risk.audit_logs":                   ucdata.AUDIT_LOGS,
    "catalog.risk.regulatory_filings":           ucdata.REGULATORY_FILINGS,
    "catalog.risk.transaction_history":          ucdata.TRANSACTION_HISTORY,
    "catalog.risk.delinquency_records":          ucdata.DELINQUENCY_RECORDS,
    "catalog.risk.board_materials":              ucdata.BOARD_MATERIALS,
    "catalog.risk.counterparty_data":            ucdata.COUNTERPARTY_DATA,
    "catalog.risk.trade_confirmations":          ucdata.TRADE_CONFIRMATIONS,
    "catalog.risk.credit_scores":                ucdata.CREDIT_SCORES,
    "catalog.risk.loan_history":                 ucdata.LOAN_HISTORY,
    "catalog.risk.risk_models":                  ucdata.RISK_MODELS,
}

# (tool_name, description, source_id, sensitivity) — same list handed to every role.
UC_TABLES = [
    ("get_client_profile", "Client profile — type, AUM, risk tolerance, relationship manager.", "catalog.wealth.client_profile", SensitivityLevel.HIGH),
    ("get_portfolio_holdings", "Portfolio holdings and asset allocation for a client.", "catalog.wealth.portfolio_holdings", SensitivityLevel.HIGH),
    ("get_other_client_portfolios", "Summarized holdings for OTHER institutional clients (peer benchmarking).", "catalog.wealth.other_client_portfolios", SensitivityLevel.CRITICAL),
    ("get_rebalancing_instructions", "Pending rebalancing instructions for a client.", "catalog.wealth.rebalancing_instructions", SensitivityLevel.HIGH),
    ("get_market_data", "Shared market data snapshot.", "catalog.wealth.market_data", SensitivityLevel.LOW),
    ("get_product_catalog", "Investment product catalog.", "catalog.wealth.product_catalog", SensitivityLevel.LOW),
    ("get_research_reports", "Sell-side research reports by sector.", "catalog.wealth.research_reports", SensitivityLevel.LOW),
    ("get_internal_pricing_models", "Internal proprietary pricing models.", "catalog.wealth.internal_pricing_models", SensitivityLevel.CRITICAL),
    ("get_executive_communications", "Executive/board communications.", "catalog.wealth.executive_communications", SensitivityLevel.CRITICAL),
    ("get_macro_indicators", "Macro regime and sector outlook indicators.", "catalog.wealth.macro_indicators", SensitivityLevel.LOW),
    ("get_economic_indicators", "GDP growth, inflation, and global growth indicators.", "catalog.wealth.economic_indicators", SensitivityLevel.LOW),
    ("get_sec_filings", "Relevant SEC filings for managers/funds.", "catalog.wealth.sec_filings", SensitivityLevel.MEDIUM),
    ("get_geopolitical_signals", "Geopolitical risk signals and hotspots.", "catalog.wealth.geopolitical_signals", SensitivityLevel.MEDIUM),
    ("get_regulatory_templates", "Regulatory report templates.", "catalog.wealth.regulatory_templates", SensitivityLevel.LOW),
    ("get_agent_outputs", "Compiled findings from other agents for this client.", "catalog.wealth.agent_outputs", SensitivityLevel.HIGH),
    ("get_portfolio_metrics", "Aggregate portfolio risk/performance metrics (no PII).", "catalog.wealth.portfolio_metrics", SensitivityLevel.MEDIUM),
    ("get_account_summaries", "Thin cross-client account summary (AUM, type).", "catalog.risk.account_summaries", SensitivityLevel.MEDIUM),
    ("get_audit_logs", "Internal audit-log integrity check summaries.", "catalog.risk.audit_logs", SensitivityLevel.CRITICAL),
    ("get_regulatory_filings", "Regulatory filings (Form 5500, PBGC, etc.) for a client.", "catalog.risk.regulatory_filings", SensitivityLevel.HIGH),
    ("get_transaction_history", "Large institutional transaction history for a client.", "catalog.risk.transaction_history", SensitivityLevel.HIGH),
    ("get_delinquency_records", "Delinquency status on credit facilities for a client.", "catalog.risk.delinquency_records", SensitivityLevel.HIGH),
    ("get_board_materials", "Board and risk-committee materials.", "catalog.risk.board_materials", SensitivityLevel.CRITICAL),
    ("get_counterparty_data", "Settlement counterparty and custodian data.", "catalog.risk.counterparty_data", SensitivityLevel.HIGH),
    ("get_trade_confirmations", "Trade confirmation and settlement status for a client.", "catalog.risk.trade_confirmations", SensitivityLevel.HIGH),
    ("get_credit_scores", "Institutional credit rating for a client.", "catalog.risk.credit_scores", SensitivityLevel.HIGH),
    ("get_loan_history", "Credit facilities and loan history for a client.", "catalog.risk.loan_history", SensitivityLevel.HIGH),
    ("get_risk_models", "Internal credit risk models.", "catalog.risk.risk_models", SensitivityLevel.CRITICAL),
]


def _make_getter(guard: ContextGuard, agent_role: str, source_id: str, sensitivity: SensitivityLevel,
                  session_key: str, agent_id: Optional[str] = None, task_type: Optional[str] = None):
    """Build a guard.protect()-wrapped getter. Which guard evaluates the call is a
    property of the calling role (ROLE_GUARD), not of the source's catalog schema —
    credit_scores/loan_history/risk_models are reachable by roles from both policy
    files, each evaluated under its own file's policy for that role."""
    @guard.protect(agent_role=agent_role, user_id="portfolio_ops", source_id=source_id,
                   sensitivity_level=sensitivity, session_id=SESSIONS[session_key],
                   agent_id=agent_id, task_type=task_type)
    def _get(key: str = "") -> dict:
        table = SOURCES[source_id]
        return table.get(key, table) if key else table
    return _get


def _safe_call(fn, key: str = "") -> dict:
    try:
        result = fn(key) if key else fn()
        return {"status": "allowed", "data": result}
    except PermissionError as e:
        return {"status": "denied", "reason": str(e)}


def _emit(event: dict) -> None:
    get_stream_writer()(event)


def role_tools(role: str, task_type: str, key_hint: str) -> list:
    """The exact same toolbelt for every role, across both catalogs — only
    role/agent_id/task_type/guard differ."""
    guard = ROLE_GUARD[role]
    agent_id = AGENT_IDS[role]
    return [
        _build_tool(guard, name, f"{desc} Call with key='{key_hint}'.", role, source_id, sensitivity,
                    role, agent_id, task_type)
        for name, desc, source_id, sensitivity in UC_TABLES
    ]


def _build_tool(guard: ContextGuard, name: str, description: str, agent_role: str, source_id: str,
                 sensitivity: SensitivityLevel, session_key: str,
                 agent_id: Optional[str] = None, task_type: Optional[str] = None):
    getter = _make_getter(guard, agent_role, source_id, sensitivity, session_key,
                           agent_id=agent_id, task_type=task_type)

    @tool(name)
    def _t(key: str = "") -> str:
        """placeholder — .func is overridden below with the real guarded getter"""
        return ""
    _t.description = description
    _t.func = getter
    return _t


# ── shared tool-calling loop ──────────────────────────────────────────────────────

_FINDING_TOOL_SCHEMA = {
    "name": "submit_finding",
    "description": "Submit your final response for this step and end your turn. Call this once you're done gathering data (or once you've determined you can't complete it with the sources available to you).",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "1-3 sentence summary of what you produced (or why you couldn't)"},
            "outcome": {"type": "string", "enum": ["COMPLETED", "BLOCKED"], "description": "COMPLETED if you produced the requested output using only sources that succeeded; BLOCKED if denials left you unable to complete it"},
            "sources_used": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["summary", "outcome"],
    },
}


class DenialEvent(TypedDict):
    agent_role: str
    tool: str
    reason: str


def run_tool_loop(agent_role: str, system_prompt: str, user_brief: str,
                   tools: list, denial_log: list, llm) -> tuple[Optional[dict], list]:
    """With a toolbelt this large (32 tools across both catalogs), smaller local models
    (verified live: Ollama's qwen2.5:7b) tend to call most/all tools in one big batch per
    turn rather than a few at a time, and don't reliably include submit_finding in that
    batch — repeating the same batch turn after turn instead of concluding. Unlike the
    fraud/client_analysis demos' smaller toolbelts (this doesn't happen there), an
    explicit, increasingly urgent nudge after every turn without a finding is needed —
    a generic "call a tool or conclude" message (their approach) isn't enough here."""
    tool_map = {t.name: t for t in tools}
    bound = llm.bind_tools([*tools, _FINDING_TOOL_SCHEMA])
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_brief)]
    local_denials: list[DenialEvent] = []

    for turn in range(MAX_TOOL_TURNS):
        response = bound.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            messages.append(HumanMessage(
                content="Call a tool to gather data, or call submit_finding when you have enough to conclude."
            ))
            continue

        finding: Optional[dict] = None
        for call in response.tool_calls:
            if call["name"] == "submit_finding":
                finding = call["args"]
                messages.append(ToolMessage(content="Finding recorded.", tool_call_id=call["id"]))
                continue

            tool_fn = tool_map[call["name"]]
            key = call["args"].get("key", "")
            result = _safe_call(tool_fn.func, key)

            if result["status"] == "denied":
                entry: DenialEvent = {"agent_role": agent_role, "tool": call["name"], "reason": result["reason"]}
                local_denials.append(entry)
                print(f"      [DENIED]  {agent_role} -> {call['name']}({key})")
                print(f"                {result['reason']}")
            else:
                print(f"      [ok]      {agent_role} -> {call['name']}({key})")

            _emit({
                "type": "tool_call", "role": agent_role, "tool": call["name"], "key": key,
                "status": result["status"], "reason": result.get("reason"),
            })

            messages.append(ToolMessage(content=json.dumps(result, default=str), tool_call_id=call["id"]))

        if finding is not None:
            denial_log.extend(local_denials)
            return finding, local_denials

        turns_left = MAX_TOOL_TURNS - turn - 1
        if turns_left <= 1:
            messages.append(HumanMessage(
                content="You must call submit_finding now, based on what you've gathered so far. Do not call any more data tools."
            ))
        else:
            messages.append(HumanMessage(
                content="You now have results from the tools you called. If you have enough to respond, call "
                        "submit_finding now instead of repeating tools you've already called."
            ))

    denial_log.extend(local_denials)
    print(f"      [warn]    {agent_role} exhausted {MAX_TOOL_TURNS} turns without submit_finding")
    return None, local_denials


# ── LangGraph state ──────────────────────────────────────────────────────────────

class ReviewState(TypedDict):
    request_id: str
    provider: str
    client_id: str
    brief: str
    review_type: str
    roles_plan: list       # list of [role, task_type] pairs remaining to run
    roles_completed: list
    escalated: bool
    findings: dict
    denial_log: list
    final_decision: str


# ── review types — orchestrator picks ONE; the role/task sequence within it models a
#    real institutional workflow (research -> advisory -> rebalancing -> settlement ->
#    reporting), not a scripted violation. What each role reaches for WITHIN its step
#    stays fully emergent. ────────────────────────────────────────────────────────────

REVIEW_TYPES = {
    "quarterly_review": [
        ["investment_analyst", "market_analysis"],
        ["wealth_advisor", "portfolio_review"],
        ["rebalancing_agent", "rebalancing_recommendation"],
        ["report_generator", "quarterly_review"],
    ],
    "fiduciary_benchmark": [
        ["wealth_advisor", "portfolio_review"],
    ],
    "credit_limit_review": [
        ["credit_risk_analyst", "limit_review"],
    ],
    "trade_settlement_check": [
        ["macro_analyst", "macro_analysis"],
        ["settlement_agent", "trade_settlement"],
    ],
}

# The one escalation path this demo models — mirrors the source's Scenario 2 exactly:
# wealth_advisor denied on the fiduciary boundary re-routes to investment_analyst, which
# has real benchmarking authorization other_client_portfolios that wealth_advisor never has.
ESCALATION = {
    "fiduciary_benchmark": ["investment_analyst", "benchmarking"],
}

# A human reviewer can pick one of these instead of accepting the proposed outcome —
# same override-dropdown pattern as fraud_investigation_demo.py, kept in sync with
# decision_node's own logic so the choices always make sense next to the proposal.
OVERRIDE_ACTIONS = [
    "ESCALATE TO SENIOR COMPLIANCE — requires manual review before proceeding",
    "HOLD — do not proceed until blocked steps are resolved",
    "APPROVE WITH CONDITIONS — proceed, flag for follow-up review",
    "REJECT — return to originating role for rework",
]


def _classify_denial(reason: str) -> str:
    if "is not permitted to access source" in reason:
        return "task_bindings (purpose limitation)"
    if "exceeds ceiling" in reason or "exceeds effective ceiling" in reason:
        return "sensitivity ceiling"
    if reason.startswith("Task") and "explicitly denied" in reason:
        return "denied_tasks"
    if reason.startswith("Source") and "explicitly denied" in reason:
        return "denied_sources"
    if "not in the allowed list" in reason:
        return "denied_sources (not in allowed_sources)"
    if "isolation" in reason.lower() or "owned by" in reason:
        return "session isolation"
    if "not permitted to act as" in reason:
        return "role_not_permitted"
    return "policy"


# ── orchestrator ──────────────────────────────────────────────────────────────────

def orchestrator_node(state: ReviewState) -> dict:
    _reset_sessions()
    print(f"\n{'─'*70}\n  PORTFOLIO ORCHESTRATOR  (session: {SESSIONS['orchestrator'][:8]}…)\n{'─'*70}")
    request = ucdata.PORTFOLIO_REVIEW_REQUESTS[state["request_id"]]
    brief = request["brief"]
    print(f"  Request: {brief}")

    review_types = list(REVIEW_TYPES.keys())
    assign_schema = {
        "name": "classify_review",
        "description": "Decide which review type this request falls under.",
        "input_schema": {
            "type": "object",
            "properties": {
                "review_type": {"type": "string", "enum": review_types},
                "reasoning": {"type": "string"},
            },
            "required": ["review_type"],
        },
    }
    bound = _bind_forced(_make_llm(state["provider"]), [assign_schema], "classify_review")
    prompt = (
        f"Institutional review request:\n{brief}\n\n"
        f"Decide which review type this falls under. Available review types: {review_types}."
    )
    response = bound.invoke([SystemMessage(content="You are a portfolio review orchestrator at an institutional wealth management firm, classifying incoming requests."),
                              HumanMessage(content=prompt)])
    args = response.tool_calls[0]["args"] if response.tool_calls else {}
    review_type = args.get("review_type")
    if isinstance(review_type, list):
        review_type = next((r for r in review_type if r in REVIEW_TYPES), None)
    if review_type not in REVIEW_TYPES:
        review_type = review_types[0]

    roles_plan = [list(step) for step in REVIEW_TYPES[review_type]]
    print(f"  → review_type: {review_type}  {args.get('reasoning', '')}")
    print(f"  → plan: {roles_plan}")
    _emit({"type": "routing", "stage": "initial", "review_type": review_type,
           "plan": [r for r, _ in roles_plan], "reasoning": args.get("reasoning", "")})

    return {
        "client_id": request["client_id"], "brief": brief, "review_type": review_type,
        "roles_plan": roles_plan, "roles_completed": [], "escalated": False,
        "findings": {}, "denial_log": [],
    }


# A one-line steer toward the CATEGORY of data each role's step is actually about —
# not which tool to call. With 32 tools on offer, a generic "gather what you need"
# brief (which is all the fraud/client_analysis demos' smaller toolbelts ever needed)
# left roles scattershotting; this narrows the search space without picking the tool
# for the model or ruling out reaching into other categories if it judges that useful.
ROLE_FOCUS_HINTS = {
    "investment_analyst": "Focus on market and macro context relevant to this client's holdings.",
    "macro_analyst": "Focus on the macro regime and economic backdrop relevant to this decision.",
    "wealth_advisor": "Focus on this client's own portfolio and profile — never a peer client's.",
    "rebalancing_agent": "Focus on this client's drift from target allocation and the pending rebalancing instruction.",
    "report_generator": "You compile this report from what OTHER agents have already found — check compiled agent outputs before reaching for anything else.",
    "settlement_agent": "Focus on the trade confirmation and counterparty details for the pending trade.",
    "credit_risk_analyst": "Focus on this client's credit profile and loan history.",
}


def _run_role(role: str, state: ReviewState) -> dict:
    task_type = state["roles_plan"][0][1]
    print(f"\n{'─'*70}\n  {role.upper().replace('_',' ')}  (session: {SESSIONS[role][:8]}…)  task={task_type}\n{'─'*70}")
    tools = role_tools(role, task_type, key_hint=state["client_id"])
    brief = (
        f"You are the {role.replace('_',' ')} handling this step of an institutional "
        f"portfolio review for client {state['client_id']}.\n\n"
        f"Overall request:\n{state['brief']}\n\n"
        f"Your specific task for this step is: {task_type}. {ROLE_FOCUS_HINTS.get(role, '')}\n\n"
        f"Gather whatever data you need using the tools available to you, then call "
        f"submit_finding with your response."
    )
    denial_log = list(state["denial_log"])
    finding, _ = run_tool_loop(role, f"You are a {role.replace('_',' ')} at an institutional wealth management firm.",
                                brief, tools, denial_log, _make_llm(state["provider"]))
    finding = finding or {"summary": "No finding submitted", "outcome": "BLOCKED"}
    findings = dict(state["findings"])
    findings[role] = finding
    roles_completed = [*state["roles_completed"], role]
    remaining_plan = state["roles_plan"][1:]
    _emit({"type": "finding", "role": role, "finding": finding})
    return {"findings": findings, "roles_completed": roles_completed, "denial_log": denial_log, "roles_plan": remaining_plan}


def _make_role_node(role: str):
    def _node(state: ReviewState) -> dict:
        return _run_role(role, state)
    return _node


def route_from_plan(state: ReviewState) -> str:
    return state["roles_plan"][0][0] if state["roles_plan"] else "decision"


def orchestrator_review_node(state: ReviewState) -> dict:
    """After each role's step, decide whether to continue the plan, escalate once (only
    the fiduciary_benchmark review type has an escalation path — mirrors the source
    demo's Scenario 2 exactly), or move to decision if the plan is exhausted."""
    last_role = state["roles_completed"][-1]
    last_finding = state["findings"][last_role]
    blocked = last_finding.get("outcome") == "BLOCKED"

    escalation = ESCALATION.get(state["review_type"])
    if blocked and escalation and not state["escalated"] and not state["roles_plan"]:
        print(f"\n  [orchestrator review]  {last_role} blocked — escalating to {escalation[0]} ({escalation[1]})")
        _emit({"type": "routing", "stage": "review", "next": escalation[0], "reason": f"{last_role} blocked, escalating"})
        return {"roles_plan": [escalation], "escalated": True}

    nxt = route_from_plan(state)
    print(f"\n  [orchestrator review]  next -> {nxt}")
    _emit({"type": "routing", "stage": "review", "next": nxt, "reason": ""})
    return {"final_decision": f"route:{nxt}"}


def route_after_review(state: ReviewState) -> str:
    return state["final_decision"].split(":", 1)[1] if state["final_decision"].startswith("route:") else route_from_plan(state)


# ── audit trail ───────────────────────────────────────────────────────────────────

def _collect_audit_summary() -> dict:
    summary: dict = {"roles": {}, "total": 0, "allowed": 0, "denied": 0}
    for role, sid in SESSIONS.items():
        guard = ROLE_GUARD.get(role, wealth_guard)
        events = guard.get_audit_trail(sid)
        if not events:
            continue
        a = sum(1 for e in events if e.decision.value == "ALLOW")
        d = sum(1 for e in events if e.decision.value == "DENY")
        summary["total"] += len(events)
        summary["allowed"] += a
        summary["denied"] += d
        summary["roles"][role] = {
            "session_id": sid, "allowed": a, "denied": d,
            "events": [
                {"decision": e.decision.value, "source_id": e.source_id,
                 "policy_name": e.policy_name, "reason": e.reason if e.decision.value == "DENY" else None}
                for e in events
            ],
        }
    return summary


def decision_node(state: ReviewState) -> dict:
    """Everything through `proposed_outcome` is pure/cheap — safe to re-run, since
    interrupt() re-executes the node from the top on resume (same rule as
    fraud_investigation_demo.py's decision_node). Everything after interrupt() only
    runs once, on the resume pass."""
    classified = [{"agent_role": d["agent_role"], "tool": d["tool"], "reason": d["reason"],
                   "mechanism": _classify_denial(d["reason"])} for d in state["denial_log"]]
    mechanisms = sorted({c["mechanism"] for c in classified})
    audit_summary = _collect_audit_summary()

    # Don't trust each role's self-reported outcome alone — ground it in whether that
    # role's own session actually got any ALLOW at all (same fix as client_analysis_demo.py).
    completed_roles, blocked_roles = [], []
    for role in state["roles_completed"]:
        role_audit = audit_summary["roles"].get(role, {"allowed": 0})
        self_reported_ok = state["findings"][role].get("outcome") == "COMPLETED"
        if self_reported_ok and role_audit["allowed"] > 0:
            completed_roles.append(role)
        else:
            blocked_roles.append(role)

    if blocked_roles:
        proposed_outcome = (f"PARTIALLY BLOCKED — {', '.join(blocked_roles)} could not complete their step "
                    f"({', '.join(mechanisms) or 'no data gathered'}); {len(completed_roles)}/{len(state['roles_completed'])} "
                    f"steps completed" + (" after escalation" if state["escalated"] else "") + ".")
    elif state["denial_log"]:
        proposed_outcome = (f"COMPLETED WITH GOVERNANCE INTERVENTION — {len(state['denial_log'])} attempt(s) denied "
                    f"({', '.join(mechanisms)}); all {len(completed_roles)} steps completed using authorized sources.")
    else:
        proposed_outcome = f"COMPLETED — all {len(completed_roles)} steps completed using only authorized sources."

    human_decision = interrupt({
        "request_id": state["request_id"], "review_type": state["review_type"],
        "roles_completed": state["roles_completed"], "proposed_outcome": proposed_outcome,
        "denial_log": state["denial_log"], "escalated": state["escalated"],
    })
    approved = human_decision.get("approved", True)
    outcome = proposed_outcome if approved else (human_decision.get("override_outcome") or proposed_outcome)

    print(f"\n{'─'*70}\n  OUTCOME  |  {state['request_id']}\n{'─'*70}")
    print(f"  Review type: {state['review_type']}")
    print(f"  Roles run: {state['roles_completed']}")
    print(f"  Proposed: {proposed_outcome}")
    print(f"  Reviewer: {'APPROVED' if approved else f'OVERRODE -> {outcome}'}")
    if human_decision.get("notes"):
        print(f"            {human_decision['notes']}")
    print(f"  Denials encountered: {len(state['denial_log'])}")
    for d in classified:
        print(f"    ✗  [{d['agent_role']}] {d['tool']}: {d['reason']}  ({d['mechanism']})")

    _emit({
        "type": "disposition", "request_id": state["request_id"], "outcome": outcome,
        "proposed_outcome": proposed_outcome, "human_approved": approved,
        "human_override_outcome": human_decision.get("override_outcome"),
        "human_notes": human_decision.get("notes"),
        "review_type": state["review_type"], "roles_completed": state["roles_completed"],
        "escalated": state["escalated"], "denial_count": len(state["denial_log"]),
        "denials": classified, "audit_summary": audit_summary,
    })
    return {"final_decision": outcome}


# ── graph ─────────────────────────────────────────────────────────────────────────

def build_graph(checkpointer=None):
    g = StateGraph(ReviewState)
    g.add_node("orchestrator", orchestrator_node)
    for role in SPECIALIST_ROLES:
        g.add_node(role, _make_role_node(role))
    g.add_node("orchestrator_review", orchestrator_review_node)
    g.add_node("decision", decision_node)

    g.set_entry_point("orchestrator")
    g.add_conditional_edges("orchestrator", route_from_plan, {**{r: r for r in SPECIALIST_ROLES}, "decision": "decision"})
    for role in SPECIALIST_ROLES:
        g.add_edge(role, "orchestrator_review")
    g.add_conditional_edges("orchestrator_review", route_after_review, {**{r: r for r in SPECIALIST_ROLES}, "decision": "decision"})
    g.add_edge("decision", END)
    return g.compile(checkpointer=checkpointer)


# graph is compiled at import time so it's importable by the LangGraph dev server
# (see langgraph.json: "institutional_portfolio_review": "...:graph"). No checkpointer
# here — decision_node's interrupt() needs one to persist state across the pause/resume
# boundary, but langgraph dev/LangGraph Platform refuses to load a graph pre-compiled
# with a custom checkpointer (it manages persistence itself). run_request() below builds
# its own separate instance, with a checkpointer, for the CLI path.
graph = build_graph()


def print_audit_trail(request_id: str) -> None:
    print(f"\n{'═'*70}\n  AUTOPIL AUDIT TRAIL — {request_id}\n{'═'*70}")
    summary = _collect_audit_summary()
    for role, r in summary["roles"].items():
        print(f"\n  [{role.upper()} — session {r['session_id'][:8]}…]  {r['allowed']} allowed  {r['denied']} denied")
        for e in r["events"]:
            icon = "✓" if e["decision"] == "ALLOW" else "✗"
            print(f"    {icon} {e['decision']:<6} {e['source_id']:<32} policy={e['policy_name']}")
            if e["decision"] == "DENY":
                print(f"          reason: {e['reason']}")
    print(f"\n{'═'*70}\n  Total: {summary['total']} audit events | {summary['allowed']} allowed | {summary['denied']} denied\n{'═'*70}\n")


# ── run ───────────────────────────────────────────────────────────────────────────

def run_request(request_id: str) -> None:
    request = ucdata.PORTFOLIO_REVIEW_REQUESTS[request_id]
    print(f"\n{'━'*70}\n  REQUEST {request_id}  —  {request['title']}\n{'━'*70}")
    _reset_sessions()
    # Own checkpointer per request — the module-level `graph` is deliberately
    # checkpointer-free (see build_graph()); interrupt() needs one for the CLI path.
    cli_graph = build_graph(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": f"cli-{request_id}"}}
    result = cli_graph.invoke({
        "request_id": request_id, "provider": "", "client_id": "", "brief": "",
        "review_type": "", "roles_plan": [], "roles_completed": [], "escalated": False,
        "findings": {}, "denial_log": [], "final_decision": "",
    }, config=config)
    if "__interrupt__" in result:
        # CLI stays unattended — auto-approve the proposed outcome. Interactive
        # review only happens through the browser (see the live viewer).
        cli_graph.invoke(Command(resume={"approved": True}), config=config)
    print_audit_trail(request_id)


if __name__ == "__main__":
    for request_id in ["PORT-001", "PORT-002", "PORT-004", "PORT-005"]:
        run_request(request_id)
