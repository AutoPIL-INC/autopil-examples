"""
AutoPIL + LangGraph: AML & Compliance Investigation Demo
==========================================================
A 3-role governance boundary (aml_investigator / kyc_agent / compliance_officer) —
split out of institutional_portfolio_review's 11-role, two-policy-file demo, where
this financial-crime-governance workflow (SAR generation, sanctions screening,
cross-client audit) sat awkwardly split across both files despite being one coherent
story. One dedicated policy file here instead.

Every case runs the same fixed sequence — aml_investigator investigates transaction/
watchlist signal, kyc_agent verifies identity, compliance_officer reviews and signs
off — since there's no real reason the order would vary case to case (unlike the
fraud investigation demo's dynamically-routed specialists). Each role is handed a
toolbelt WIDER than its policy authorization; denials aren't scripted — they happen
when the model reasons its way toward an out-of-scope source on its own.

See DESIGN.md for the full design rationale.

Run:
    .venv/bin/python examples/aml_compliance/aml_compliance_demo.py
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
import aml_case_data as data

load_dotenv()

# ── config ──────────────────────────────────────────────────────────────────────
POLICY_FILE = ROOT / "policies" / "financial_services" / "aml_compliance.yaml"
AUDIT_DB    = ROOT / "aml_compliance_audit.db"
TENANT_ID   = "default"
MAX_TOOL_TURNS = 5   # per-role tool-calling loop cap

ROLE_ORDER = ["aml_investigator", "kyc_agent", "compliance_officer"]

AGENT_REGISTRY_STORE = SQLiteAgentRegistryStore(str(AUDIT_DB))
AGENT_IDS = {
    "aml_investigator": "aml-investigator-001",
    "kyc_agent": "kyc-agent-001",
    "compliance_officer": "compliance-officer-001",
}


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


_register_agents()

guard = ContextGuard(policy_path=str(POLICY_FILE), audit_db=str(AUDIT_DB), tenant_id=TENANT_ID,
                      agent_registry_store=AGENT_REGISTRY_STORE)


def _make_llm(provider: str = ""):
    """Same fallback chain as fraud_investigation_demo.py — Anthropic → Gemini →
    Groq → Ollama (default, no key)."""
    if not provider:
        provider = (
            "anthropic" if os.getenv("ANTHROPIC_API_KEY")
            else "gemini" if os.getenv("GOOGLE_API_KEY")
            else "groq" if os.getenv("GROQ_API_KEY")
            else "ollama"
        )
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


# Each role gets its own session — the isolation boundary AutoPIL enforces.
SESSIONS: dict[str, str] = {}


def _reset_sessions() -> None:
    for role in ["orchestrator", *ROLE_ORDER]:
        SESSIONS[role] = str(uuid.uuid4())


_reset_sessions()

# ── data sources ──────────────────────────────────────────────────────────────────
SOURCES = {
    "transaction_history":      data.TRANSACTION_HISTORY,
    "watchlist":                data.WATCHLIST,
    "counterparty_data":        data.COUNTERPARTY_DATA,
    "account_summaries":        data.ACCOUNT_SUMMARIES,
    "delinquency_records":      data.DELINQUENCY_RECORDS,
    "identity_records":         data.IDENTITY_RECORDS,
    "loan_history":             data.LOAN_HISTORY,
    "credit_scores":            data.CREDIT_SCORES,
    "audit_logs":                data.AUDIT_LOGS,
    "regulatory_filings":       data.REGULATORY_FILINGS,
    "client_profile":           data.CLIENT_PROFILE,
    "portfolio_holdings":       data.PORTFOLIO_HOLDINGS,
    "risk_models":              data.RISK_MODELS,
    "executive_communications": data.EXECUTIVE_COMMUNICATIONS,
}


def _make_getter(agent_role: str, source_id: str, sensitivity: SensitivityLevel, session_key: str,
                  agent_id: Optional[str] = None, task_type: Optional[str] = None):
    @guard.protect(agent_role=agent_role, user_id="aml_ops", source_id=source_id,
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


def _build_tool(name: str, description: str, agent_role: str, source_id: str,
                 sensitivity: SensitivityLevel, session_key: str,
                 agent_id: Optional[str] = None, task_type: Optional[str] = None):
    getter = _make_getter(agent_role, source_id, sensitivity, session_key,
                           agent_id=agent_id, task_type=task_type)

    @tool(name)
    def _t(key: str = "") -> str:
        """placeholder — .func is overridden below with the real guarded getter"""
        return ""
    _t.description = description
    _t.func = getter
    return _t


# ── per-role toolbelts (deliberately WIDER than each role's policy authorization) ─

def aml_investigator_tools(account_id_hint: str) -> list:
    role, aid = "aml_investigator", AGENT_IDS["aml_investigator"]
    acc = f"Call with key='{account_id_hint}' (the account_id)."
    _OVERSCOPE = "pattern_detection"
    return [
        _build_tool("get_transaction_history", f"Transaction history for an account. {acc}", role, "transaction_history", SensitivityLevel.CRITICAL, role, aid, "pattern_detection"),
        _build_tool("get_watchlist_screening", f"OFAC/SDN watchlist screening result for an account. {acc}", role, "watchlist", SensitivityLevel.HIGH, role, aid, "entity_resolution"),
        _build_tool("get_counterparty_data", "Counterparty and settlement data. Call with no key.", role, "counterparty_data", SensitivityLevel.MEDIUM, role, aid, "entity_resolution"),
        _build_tool("get_account_summary", f"Account summary — type, AUM, flags. {acc}", role, "account_summaries", SensitivityLevel.MEDIUM, role, aid, "sar_generation"),
        _build_tool("get_delinquency_records", f"Delinquency status on credit facilities. {acc}", role, "delinquency_records", SensitivityLevel.MEDIUM, role, aid, "pattern_detection"),
        # over-scope: NOT in aml_investigator_policy.allowed_sources
        _build_tool("get_identity_records", f"KYC identity verification status for the account holder. {acc}", role, "identity_records", SensitivityLevel.HIGH, role, aid, _OVERSCOPE),
    ]


def kyc_agent_tools(account_id_hint: str) -> list:
    role, aid = "kyc_agent", AGENT_IDS["kyc_agent"]
    acc = f"Call with key='{account_id_hint}' (the account_id)."
    _OVERSCOPE = "identity_verification"
    return [
        _build_tool("get_identity_records", f"KYC identity verification status for the account holder. {acc}", role, "identity_records", SensitivityLevel.HIGH, role, aid, "identity_verification"),
        _build_tool("get_loan_history", f"Credit facilities and loan history. {acc}", role, "loan_history", SensitivityLevel.HIGH, role, aid, "kyc_check"),
        _build_tool("get_credit_scores", f"Institutional credit rating. {acc}", role, "credit_scores", SensitivityLevel.HIGH, role, aid, "kyc_check"),
        # over-scope: explicitly denied
        _build_tool("get_risk_models", "Internal AML typology risk models. Call with no key.", role, "risk_models", SensitivityLevel.CRITICAL, role, aid, _OVERSCOPE),
        # over-scope: NOT in kyc_agent_policy.allowed_sources
        _build_tool("get_transaction_history", f"Full transaction history for an account. {acc}", role, "transaction_history", SensitivityLevel.CRITICAL, role, aid, _OVERSCOPE),
    ]


def compliance_officer_tools(account_id_hint: str) -> list:
    role, aid = "compliance_officer", AGENT_IDS["compliance_officer"]
    acc = f"Call with key='{account_id_hint}' (the account_id)."
    _OVERSCOPE = "compliance_review"
    return [
        _build_tool("get_account_summary", f"Account summary — type, AUM, flags. {acc}", role, "account_summaries", SensitivityLevel.MEDIUM, role, aid, "compliance_review"),
        _build_tool("get_credit_scores", f"Institutional credit rating. {acc}", role, "credit_scores", SensitivityLevel.HIGH, role, aid, "cross_client_audit"),
        _build_tool("get_audit_logs", "Internal audit-log integrity check summaries. Call with no key.", role, "audit_logs", SensitivityLevel.CRITICAL, role, aid, "sox_review"),
        _build_tool("get_regulatory_filings", f"SAR filing history for an account. {acc}", role, "regulatory_filings", SensitivityLevel.HIGH, role, aid, "compliance_review"),
        _build_tool("get_transaction_history", f"Full transaction history for an account. {acc}", role, "transaction_history", SensitivityLevel.CRITICAL, role, aid, "sar_filing"),
        _build_tool("get_client_profile", f"Client profile — entity type, relationship manager. {acc}", role, "client_profile", SensitivityLevel.MEDIUM, role, aid, "cross_client_audit"),
        _build_tool("get_portfolio_holdings", f"Portfolio holdings and asset mix. {acc}", role, "portfolio_holdings", SensitivityLevel.HIGH, role, aid, "fiduciary_review"),
        # over-scope: explicitly denied
        _build_tool("get_executive_communications", "Executive/committee communications. Call with no key.", role, "executive_communications", SensitivityLevel.CRITICAL, role, aid, _OVERSCOPE),
    ]


TOOL_BUILDERS = {
    "aml_investigator": aml_investigator_tools,
    "kyc_agent": kyc_agent_tools,
    "compliance_officer": compliance_officer_tools,
}


# ── shared tool-calling loop ──────────────────────────────────────────────────────

_FINDING_TOOL_SCHEMA = {
    "name": "submit_finding",
    "description": "Submit your final finding for this step and end your turn. Call this once you're done gathering data.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "1-3 sentence summary of what you found"},
            "risk_indicators": {"type": "array", "items": {"type": "string"}},
            "recommendation": {"type": "string", "description": "e.g. ESCALATE, CLEAR, HOLD, SAR_WARRANTED"},
            "sources_used": {"type": "array", "items": {"type": "string"}, "description": "sources you actually got data back from"},
        },
        "required": ["summary", "recommendation"],
    },
}


class Finding(TypedDict, total=False):
    summary: str
    risk_indicators: list[str]
    recommendation: str
    sources_used: list[str]


class DenialEvent(TypedDict):
    agent_role: str
    tool: str
    reason: str


def run_tool_loop(agent_role: str, system_prompt: str, user_brief: str,
                   tools: list, denial_log: list[DenialEvent], llm) -> tuple[Optional[Finding], list[DenialEvent]]:
    """Run one role's tool-calling loop to completion (or MAX_TOOL_TURNS)."""
    tool_map = {t.name: t for t in tools}
    bound = llm.bind_tools([*tools, _FINDING_TOOL_SCHEMA])
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_brief)]
    local_denials: list[DenialEvent] = []

    for _ in range(MAX_TOOL_TURNS):
        response = bound.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            messages.append(HumanMessage(
                content="Call a tool to gather data, or call submit_finding when you have enough to conclude."
            ))
            continue

        finding: Optional[Finding] = None
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

    denial_log.extend(local_denials)
    print(f"      [warn]    {agent_role} exhausted {MAX_TOOL_TURNS} turns without submit_finding")
    return None, local_denials


# ── LangGraph state ──────────────────────────────────────────────────────────────

class AMLCaseState(TypedDict):
    case_id: str
    provider: str
    account_id: str
    reason_for_review: str
    roles_completed: list[str]
    findings: dict[str, Finding]
    denial_log: list[DenialEvent]
    final_decision: str


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
    return "policy"


# ── intake ────────────────────────────────────────────────────────────────────────

def intake_node(state: AMLCaseState) -> dict:
    """Every case runs the same 3 roles in the same fixed order — no LLM
    classification needed, unlike fraud_investigation's dynamically-routed
    specialists. Looked up server-side from case_id, same pattern."""
    _reset_sessions()
    case = data.AML_CASES[state["case_id"]]
    print(f"\n{'─'*70}\n  INTAKE  (session: {SESSIONS['orchestrator'][:8]}…)\n{'─'*70}")
    print(f"  Case: {state['case_id']}  ·  {case['reason_for_review']}")
    _emit({"type": "routing", "stage": "initial", "route": ROLE_ORDER, "reason": case["reason_for_review"]})
    return {
        "account_id": case["account_id"], "reason_for_review": case["reason_for_review"],
        "roles_completed": [], "findings": {}, "denial_log": [],
    }


def _run_role(role: str, state: AMLCaseState) -> dict:
    print(f"\n{'─'*70}\n  {role.upper().replace('_',' ')}  (session: {SESSIONS[role][:8]}…)\n{'─'*70}")
    tools = TOOL_BUILDERS[role](state["account_id"])
    brief = (
        f"You are the {role.replace('_',' ')} handling this step of an AML case "
        f"review for account {state['account_id']}.\n\n"
        f"Reason for review: {state['reason_for_review']}\n\n"
        f"Gather whatever data you need using the tools available to you, then call "
        f"submit_finding with your assessment."
    )
    denial_log = list(state["denial_log"])
    finding, _ = run_tool_loop(role, f"You are a {role.replace('_',' ')} at a bank's financial crimes unit.",
                                brief, tools, denial_log, _make_llm(state["provider"]))
    finding = finding or {"summary": "No finding submitted", "recommendation": "UNKNOWN"}
    findings = dict(state["findings"])
    findings[role] = finding
    roles_completed = [*state["roles_completed"], role]
    _emit({"type": "finding", "role": role, "finding": finding})
    return {"findings": findings, "roles_completed": roles_completed, "denial_log": denial_log}


def _make_role_node(role: str):
    def _node(state: AMLCaseState) -> dict:
        return _run_role(role, state)
    return _node


# ── audit trail ───────────────────────────────────────────────────────────────────

def _collect_audit_summary() -> dict:
    summary: dict = {"roles": {}, "total": 0, "allowed": 0, "denied": 0}
    for role, sid in SESSIONS.items():
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


def print_audit_trail(case_id: str) -> None:
    print(f"\n{'═'*70}\n  AUTOPIL AUDIT TRAIL — {case_id}\n{'═'*70}")
    summary = _collect_audit_summary()
    for role, r in summary["roles"].items():
        print(f"\n  [{role.upper()} — session {r['session_id'][:8]}…]  {r['allowed']} allowed  {r['denied']} denied")
        for e in r["events"]:
            icon = "✓" if e["decision"] == "ALLOW" else "✗"
            print(f"    {icon} {e['decision']:<6} {e['source_id']:<24} policy={e['policy_name']}")
            if e["decision"] == "DENY":
                print(f"          reason: {e['reason']}")
    print(f"\n{'═'*70}\n  Total: {summary['total']} audit events | {summary['allowed']} allowed | {summary['denied']} denied\n{'═'*70}\n")


# A human reviewer can pick one of these instead of accepting the proposed outcome —
# same override-dropdown pattern as fraud_investigation_demo.py.
OVERRIDE_ACTIONS = [
    "SAR REQUIRED — structuring pattern confirmed",
    "SAR REQUIRED — sanctions match confirmed",
    "HOLD PENDING KYC REFRESH — beneficial ownership verification lapsed",
    "ESCALATE TO SENIOR COMPLIANCE — requires manual review before proceeding",
    "CLEARED — no further action required",
]


def decision_node(state: AMLCaseState) -> dict:
    """The compliance disposition is rule-based, not LLM-improvised, grounded in the
    real underlying signal data (not any role's self-reported finding) — but still
    goes through a human reviewer via interrupt() before it's final. Same pattern as
    fraud_investigation_demo.py's decision_node."""
    expected = data.get_expected_outcome(state["case_id"])
    account_id = state["account_id"]
    watchlist = data.WATCHLIST.get(account_id, {})
    identity = data.IDENTITY_RECORDS.get(account_id, {})
    txns = data.TRANSACTION_HISTORY.get(account_id, [])
    near_threshold = [t for t in txns if t["type"] == "wire_out" and 9_000 <= t["amount_usd"] < 10_000]

    if len(near_threshold) >= 3:
        proposed_action = "SAR REQUIRED — structuring pattern confirmed"
    elif watchlist.get("match_score", 0) > 0.5 and not watchlist.get("ofac_match"):
        proposed_action = "CLEARED — watchlist match resolved as false positive"
    elif identity.get("kyc_status") == "expired":
        proposed_action = "HOLD PENDING KYC REFRESH — beneficial ownership verification lapsed"
    elif account_id in data.REGULATORY_FILINGS:
        proposed_action = "CLEARED — cross-client audit confirms consistent handling"
    else:
        proposed_action = "CLEAR — NO FURTHER ACTION REQUIRED"

    # Everything above is pure/cheap — safe to re-run, since interrupt() re-executes
    # the node from the top on resume. Everything below only runs once, on resume.
    human_decision = interrupt({
        "case_id": state["case_id"], "account_id": account_id,
        "proposed_action": proposed_action, "roles_completed": state["roles_completed"],
        "findings": state["findings"], "denial_log": state["denial_log"],
    })
    approved = human_decision.get("approved", True)
    action = proposed_action if approved else (human_decision.get("override_action") or proposed_action)

    print(f"\n{'─'*70}\n  OUTCOME  |  {state['case_id']}\n{'─'*70}")
    print(f"  Proposed: {proposed_action}")
    print(f"  Reviewer: {'APPROVED' if approved else f'OVERRODE -> {action}'}")
    if human_decision.get("notes"):
        print(f"            {human_decision['notes']}")
    print(f"  Final: {action}")
    print(f"  Expected (ground truth): {expected['proposed_action']}")
    print(f"  Roles run: {state['roles_completed']}")
    print(f"  Denials encountered: {len(state['denial_log'])}")
    classified = [{"agent_role": d["agent_role"], "tool": d["tool"], "reason": d["reason"],
                   "mechanism": _classify_denial(d["reason"])} for d in state["denial_log"]]
    for d in classified:
        print(f"    ✗  [{d['agent_role']}] {d['tool']}: {d['reason']}  ({d['mechanism']})")

    _emit({
        "type": "disposition", "case_id": state["case_id"], "action": action,
        "proposed_action": proposed_action, "human_approved": approved,
        "human_override_action": human_decision.get("override_action"),
        "human_notes": human_decision.get("notes"), "roles_completed": state["roles_completed"],
        "denial_count": len(state["denial_log"]), "denials": classified,
        "audit_summary": _collect_audit_summary(),
    })
    return {"final_decision": action}


# ── graph ─────────────────────────────────────────────────────────────────────────

def build_graph(checkpointer=None):
    g = StateGraph(AMLCaseState)
    g.add_node("intake", intake_node)
    for role in ROLE_ORDER:
        g.add_node(role, _make_role_node(role))
    g.add_node("decision", decision_node)

    g.set_entry_point("intake")
    g.add_edge("intake", ROLE_ORDER[0])
    for i in range(len(ROLE_ORDER) - 1):
        g.add_edge(ROLE_ORDER[i], ROLE_ORDER[i + 1])
    g.add_edge(ROLE_ORDER[-1], "decision")
    g.add_edge("decision", END)
    return g.compile(checkpointer=checkpointer)


# graph is compiled at import time so it's importable by the LangGraph dev server
# (see langgraph.json: "aml_compliance": "...:graph"). No checkpointer here —
# decision_node's interrupt() needs one to persist state across the pause/resume
# boundary, but langgraph dev/LangGraph Platform refuses to load a graph pre-compiled
# with a custom checkpointer. run_case() below builds its own instance, with a
# checkpointer, for the CLI path.
graph = build_graph()


# ── run ───────────────────────────────────────────────────────────────────────────

def run_case(case_id: str) -> None:
    case = data.AML_CASES[case_id]
    print(f"\n{'━'*70}\n  CASE {case_id}  —  {case['reason_for_review']}\n{'━'*70}")
    _reset_sessions()
    cli_graph = build_graph(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": f"cli-{case_id}"}}
    result = cli_graph.invoke({
        "case_id": case_id, "provider": "", "account_id": "", "reason_for_review": "",
        "roles_completed": [], "findings": {}, "denial_log": [], "final_decision": "",
    }, config=config)
    if "__interrupt__" in result:
        # CLI stays unattended — auto-approve the proposed action. Interactive
        # review only happens through the browser (see the live viewer).
        cli_graph.invoke(Command(resume={"approved": True}), config=config)
    print_audit_trail(case_id)


if __name__ == "__main__":
    for case_id in ["AML-001", "AML-002", "AML-003", "AML-004", "AML-005"]:
        run_case(case_id)
