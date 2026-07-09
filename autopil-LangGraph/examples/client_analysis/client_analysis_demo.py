"""
AutoPIL + LangGraph + AWS Bedrock: Client Analysis Demo (Databricks Unity Catalog)
====================================================================================
Three roles (junior_analyst, senior_analyst, wealth_advisor) share the exact same
toolbelt — all 8 Unity Catalog tables are offered to every role. Nothing in the tool
layer restricts what a role can reach for; AutoPIL's guard.protect() decides what
actually succeeds, based on the real policy matrix in
policies/financial_services/client_analysis.yaml. "You don't give each role a
different tool set. You give every agent the same tools and let policy control what
succeeds." — that's the whole point of this demo.

Every customer review starts at junior_analyst and can progressively escalate to
senior_analyst and then wealth_advisor — a human reviews and dispositions each tier's
proposed next-best-action before the case closes or moves up. Each tier's agent tries
to fulfill its task with a real tool-calling loop. Denials aren't scripted — they
happen when the model reasons its way toward a source its assigned task doesn't cover,
exercising four distinct AutoPIL enforcement paths: denied_sources, denied_tasks,
task_bindings (purpose limitation), and the sensitivity ceiling.

See DESIGN.md for the full design rationale.

Run:
    .venv/bin/python examples/client_analysis/client_analysis_demo.py
"""

import json
import os
import re
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
import simulated_uc_data as ucdata

load_dotenv()

# ── config ──────────────────────────────────────────────────────────────────────
POLICY_FILE = ROOT / "policies" / "financial_services" / "client_analysis.yaml"
AUDIT_DB    = ROOT / "client_analysis_audit.db"
TENANT_ID   = "default"
MAX_TOOL_TURNS = 5   # per-role tool-calling loop cap
ROLES = ["junior_analyst", "senior_analyst", "wealth_advisor"]
TASK_TYPES = ["market_research", "portfolio_review", "client_reporting", "credit_analysis",
              "risk_assessment", "wealth_planning"]
# Tier order and what each tier escalates to — None means "top of the chain."
NEXT_TIER = {"junior_analyst": "senior_analyst", "senior_analyst": "wealth_advisor", "wealth_advisor": None}
# A case's `tier_tasks` (simulated_uc_data.CLIENT_REVIEWS) only defines a task for the
# tiers it's designed to reach. The human reviewer can still escalate any case past
# that, though — these are the task each tier falls back to in that situation.
DEFAULT_TIER_TASK = {"junior_analyst": "portfolio_review", "senior_analyst": "portfolio_review",
                      "wealth_advisor": "wealth_planning"}

AGENT_REGISTRY_STORE = SQLiteAgentRegistryStore(str(AUDIT_DB))

AGENT_IDS = {
    "junior_analyst": "junior-analyst-001",
    "senior_analyst": "senior-analyst-001",
    "wealth_advisor": "wealth-advisor-001",
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


# Hosted AutoPIL SaaS trial mode — opt in by setting both AUTOPIL_ADMIN_KEY and
# AUTOPIL_EVALUATE_KEY (same explicit-opt-in pattern as this file's own
# AWS_BEDROCK_MODEL_ID, and as fraud_investigation_demo.py). Verified live against a
# real trial tenant — see saas_guard.py's module docstring. Falls back to the
# embedded, local ContextGuard otherwise.
_SAAS_MODE = bool(os.getenv("AUTOPIL_ADMIN_KEY")) and bool(os.getenv("AUTOPIL_EVALUATE_KEY"))

# wealth_advisor needs an explicit pin: this tenant has TWO policies with
# agent_role="wealth_advisor" ("demo_wealth_advisor_policy", which matches this
# demo's local policy, and an unrelated "wealth_advisor_policy") — relying on the
# evaluate endpoint's role-scan fallback would risk silently binding to the wrong
# one. junior_analyst/senior_analyst have no such collision.
_SAAS_POLICY_NAMES = {
    "junior_analyst": "junior_analyst_policy",
    "senior_analyst": "senior_analyst_policy",
    "wealth_advisor": "demo_wealth_advisor_policy",
}

if _SAAS_MODE:
    from client_analysis_saas_guard import RemoteContextGuard, bootstrap_agents
    _API_URL = os.getenv("AUTOPIL_API_URL", "https://autopil-api.onrender.com")
    # AGENT_IDS' local string values (e.g. "junior-analyst-001") aren't registered
    # anywhere on a hosted tenant. bootstrap_agents mints/reuses a real, approved agent
    # per role there and swaps in its real agent_id, so every downstream
    # _make_getter()/_build_tool() call below (unchanged) carries an id the hosted API
    # actually recognizes.
    AGENT_IDS.update(bootstrap_agents(
        _API_URL, os.environ["AUTOPIL_ADMIN_KEY"], roles=list(AGENT_IDS),
        owner_tag="autopil-langgraph-demos",
        policy_name_for=lambda role: _SAAS_POLICY_NAMES[role],
        owner_team="Wealth Team",
    ))
    guard = RemoteContextGuard(_API_URL, os.environ["AUTOPIL_EVALUATE_KEY"], os.environ["AUTOPIL_ADMIN_KEY"])
else:
    _register_agents()
    guard = ContextGuard(policy_path=str(POLICY_FILE), audit_db=str(AUDIT_DB), tenant_id=TENANT_ID,
                          agent_registry_store=AGENT_REGISTRY_STORE)


def _make_llm(provider: str = ""):
    """Build the LLM for a run. provider is "bedrock", "anthropic", "gemini", "groq",
    "ollama", or "" (auto: first of the five with credentials configured, Ollama last
    since it needs no key) — the live viewer's model dropdown sets this explicitly per
    run via ClientReviewState["provider"]; the CLI leaves it on auto.

    AWS_BEDROCK_MODEL_ID (not ambient AWS credential sniffing) is the explicit opt-in
    signal for Bedrock — consistent with every other provider's presence check, and
    avoids silently trying (and slowly failing) Bedrock just because unrelated
    ~/.aws/credentials happen to exist on the machine.
    """
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
        # No key needed — just `ollama serve` running locally with OLLAMA_MODEL pulled
        # (default: qwen2.5:7b — verified live, in the fraud investigation demo, to
        # actually use tools reliably; smaller models like llama3.2 tend to skip tool
        # calls entirely).
        return ChatOllama(model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"))
    raise ValueError(f"Unknown provider: {provider!r}")


# Each role gets its own session — the isolation boundary AutoPIL enforces.
SESSIONS: dict[str, str] = {}


def _reset_sessions() -> None:
    for role in ["orchestrator", *ROLES]:
        SESSIONS[role] = str(uuid.uuid4())


_reset_sessions()

# ── data sources — the exact same 8 tables offered to every role, regardless of
#    what that role's policy actually authorizes ──────────────────────────────────
SOURCES = {
    "catalog.finance.customer_pii":       ucdata.CUSTOMER_PII,
    "catalog.finance.transaction_history": ucdata.TRANSACTION_HISTORY,
    "catalog.finance.market_data":         ucdata.MARKET_DATA,
    "catalog.finance.credit_scores":       ucdata.CREDIT_SCORES,
    "catalog.finance.risk_models":         ucdata.RISK_MODELS,
    "catalog.finance.public_reports":      ucdata.PUBLIC_REPORTS,
    "catalog.finance.client_portfolios":   ucdata.CLIENT_PORTFOLIOS,
    "catalog.finance.stress_test_models":  ucdata.STRESS_TEST_MODELS,
}

# (tool_name, description, source_id, sensitivity) — same list handed to every role.
UC_TABLES = [
    ("get_customer_pii", "Customer PII — name, SSN last 4, balance, credit tier.",
     "catalog.finance.customer_pii", SensitivityLevel.HIGH),
    ("get_transaction_history", "Transaction history for a customer.",
     "catalog.finance.transaction_history", SensitivityLevel.HIGH),
    ("get_market_data", "Market price data for a ticker.",
     "catalog.finance.market_data", SensitivityLevel.LOW),
    ("get_credit_scores", "Credit bureau score for a customer.",
     "catalog.finance.credit_scores", SensitivityLevel.HIGH),
    ("get_risk_models", "Internal risk model metadata.",
     "catalog.finance.risk_models", SensitivityLevel.HIGH),
    ("get_public_reports", "Published research reports.",
     "catalog.finance.public_reports", SensitivityLevel.LOW),
    ("get_client_portfolios", "Client portfolio allocation and AUM.",
     "catalog.finance.client_portfolios", SensitivityLevel.HIGH),
    ("get_stress_test_models", "Internal stress-test scenario models.",
     "catalog.finance.stress_test_models", SensitivityLevel.CRITICAL),
]


def _make_getter(agent_role: str, source_id: str, sensitivity: SensitivityLevel, session_key: str,
                  agent_id: Optional[str] = None, task_type: Optional[str] = None):
    """Build a guard.protect()-wrapped getter for `source_id`, keyed on `SESSIONS[session_key]`.

    task_type is the SAME value for every tool call in a role's run — it's assigned
    once by the orchestrator (the role's business purpose for this request), not
    hardcoded per tool. That's what lets task_bindings (purpose limitation) fire: a
    source can be in a role's allowed_sources generally, but not bound to the specific
    task_type assigned for this request.
    """
    @guard.protect(agent_role=agent_role, user_id="governance_ops", source_id=source_id,
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
    """The exact same 8 tools for every role — only role/agent_id/task_type differ.
    Policy, not the tool layer, decides what succeeds."""
    agent_id = AGENT_IDS[role]
    return [
        _build_tool(name, f"{desc} Call with key='{key_hint}'.", role, source_id, sensitivity,
                    role, agent_id, task_type)
        for name, desc, source_id, sensitivity in UC_TABLES
    ]


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


# ── shared tool-calling loop ──────────────────────────────────────────────────────

CLIENT_ACTIONS = [
    "NO ACTION NEEDED — CLIENT IN GOOD STANDING",
    "SEND MARKET UPDATE / RESEARCH TO CLIENT",
    "SCHEDULE PORTFOLIO REVIEW CALL",
    "RECOMMEND PORTFOLIO REBALANCING",
    "SCHEDULE WEALTH PLANNING MEETING",
    "ESCALATE FOR CREDIT REVIEW",
    "FLAG FOR COMPLIANCE / RISK REVIEW",
]

_FINDING_TOOL_SCHEMA = {
    "name": "submit_finding",
    "description": "Submit your recommended next action for this client and end your turn. Call this once you're done gathering data (or once you've determined you can't gather what you need with the sources available to you).",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "1-3 sentence summary of what you found and why you're recommending this action"},
            "proposed_action": {"type": "string", "enum": CLIENT_ACTIONS, "description": "the concrete next action you recommend for this client"},
            "recommend_escalation": {"type": "boolean", "description": "true if this case needs a broader-access role's review before acting on it"},
            "sources_used": {"type": "array", "items": {"type": "string"}, "description": "sources you actually got data back from"},
        },
        "required": ["summary", "proposed_action", "recommend_escalation"],
    },
}


class DenialEvent(TypedDict):
    agent_role: str
    tool: str
    reason: str


def run_tool_loop(agent_role: str, system_prompt: str, user_brief: str,
                   tools: list, denial_log: list, llm) -> tuple[Optional[dict], list]:
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

    denial_log.extend(local_denials)
    print(f"      [warn]    {agent_role} exhausted {MAX_TOOL_TURNS} turns without submit_finding")
    return None, local_denials


# ── LangGraph state ──────────────────────────────────────────────────────────────

class ClientReviewState(TypedDict):
    customer_id: str
    provider: str
    reason_for_review: str
    current_tier: str
    tiers_visited: list[str]
    findings: dict
    human_decisions: dict
    denial_log: list[DenialEvent]
    final_action: str
    closed_at_tier: str


# ── denial classification — grounded in AutoPIL's actual reason strings ──────────

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

def intake_node(state: ClientReviewState) -> dict:
    """Every case starts at junior_analyst — no LLM classification needed, since
    which task a tier works on is pre-designed per case (CLIENT_REVIEWS.tier_tasks).
    Looked up server-side from customer_id, same as the fraud demo's orchestrator_node
    fetches the alert from case_id — the client only ever needs to send customer_id."""
    _reset_sessions()
    review = ucdata.CLIENT_REVIEWS[state["customer_id"]]
    print(f"\n{'─'*70}\n  INTAKE  (session: {SESSIONS['orchestrator'][:8]}…)\n{'─'*70}")
    print(f"  Customer: {state['customer_id']}  ·  {review['reason_for_review']}")
    _emit({"type": "routing", "stage": "initial", "tier": "junior_analyst", "reason": review["reason_for_review"]})
    return {
        "reason_for_review": review["reason_for_review"], "current_tier": "junior_analyst",
        "tiers_visited": [], "findings": {}, "human_decisions": {}, "denial_log": [],
        "final_action": "", "closed_at_tier": "",
    }


def _clean_finding_text(text: str) -> str:
    """Some local models leak tool-call formatting into free-text fields — seen live:
    qwen2.5:7b's summary once trailed off into `...to complete the review.</parameter>
    <parameter name="proposed_action">SCHEDULE PORTFOLIO REVIEW CALL`, a fragment of its
    own tool-call syntax bleeding into the value instead of stopping at the field
    boundary. Truncate at the first such tag rather than surface it raw everywhere
    this text gets shown (live feed, disposition banner, escalation reason)."""
    match = re.search(r"</?\w[^>]*>", text)
    return text[:match.start()].strip() if match else text


def _run_role(role: str, state: ClientReviewState) -> dict:
    customer_id = state["customer_id"]
    review = ucdata.CLIENT_REVIEWS[customer_id]
    task_type = review["tier_tasks"].get(role, DEFAULT_TIER_TASK[role])
    print(f"\n{'─'*70}\n  {role.upper().replace('_',' ')}  (session: {SESSIONS[role][:8]}…)  task={task_type}\n{'─'*70}")
    tools = role_tools(role, task_type, key_hint=customer_id)
    brief = (
        f"You are the {role.replace('_',' ')} reviewing client {customer_id}.\n\n"
        f"Reason for review: {state['reason_for_review']}\n\n"
        f"Your task for this review is: {task_type}.\n\n"
        f"Gather whatever data you need using the tools available to you, then call "
        f"submit_finding with your recommended next action for this client."
    )
    denial_log = list(state["denial_log"])
    finding, _ = run_tool_loop(role, f"You are a {role.replace('_',' ')} at a wealth management firm.",
                                brief, tools, denial_log, _make_llm(state["provider"]))
    finding = finding or {"summary": "No finding submitted", "proposed_action": "FLAG FOR COMPLIANCE / RISK REVIEW",
                           "recommend_escalation": True}
    # Not every model honors the enum constraint strictly — seen live: qwen2.5:7b
    # omitted proposed_action outright on some turns despite it being a required
    # field. Coerce to a safe default rather than let a None/invalid action reach the
    # review panel and final disposition.
    if finding.get("proposed_action") not in CLIENT_ACTIONS:
        finding = {**finding, "proposed_action": "FLAG FOR COMPLIANCE / RISK REVIEW", "recommend_escalation": True}
    if finding.get("summary"):
        finding = {**finding, "summary": _clean_finding_text(finding["summary"])}
    findings = {**state["findings"], role: finding}
    tiers_visited = [*state["tiers_visited"], role]
    _emit({"type": "finding", "role": role, "finding": finding})
    return {"findings": findings, "tiers_visited": tiers_visited, "denial_log": denial_log, "current_tier": role}


def _make_role_node(role: str):
    def _node(state: ClientReviewState) -> dict:
        return _run_role(role, state)
    return _node


def _escalation_reason(role: str, finding: dict, tier_denials: list) -> str:
    """Grounds *why* a tier escalated in the same signal the decision was actually
    based on — the CLI's auto-approve never types a note, and a live reviewer clicking
    "Escalate" often won't either, so without this the routing event's reason is blank."""
    role_label = role.replace("_", " ")
    parts = []
    summary = finding.get("summary")
    if summary and summary != "No finding submitted":
        parts.append(summary)
    elif summary == "No finding submitted":
        parts.append(f"{role_label} didn't submit a usable finding within {MAX_TOOL_TURNS} tool turns")
    if tier_denials:
        mechanisms = sorted({_classify_denial(d["reason"]) for d in tier_denials})
        parts.append(f"{len(tier_denials)} denial(s) at this tier ({', '.join(mechanisms)})")
    if finding.get("recommend_escalation") and not parts:
        parts.append(f"{role_label} recommended escalation to a broader-access role")
    return " — ".join(parts) if parts else "escalated for a broader-access review"


def _make_review_node(role: str, next_role: Optional[str]):
    """Human review after `role`'s tool-calling turn. `interrupt()`s with that tier's
    finding and denial history; on resume, "approve" finalizes with the tier's own
    proposed_action, "override" finalizes with the human's chosen action, and
    "escalate" (only offered when next_role is not None) routes to next_role's node.
    """
    def _node(state: ClientReviewState) -> dict:
        finding = state["findings"][role]
        tier_denials = [d for d in state["denial_log"] if d["agent_role"] == role]

        human_decision = interrupt({
            "customer_id": state["customer_id"], "tier": role,
            "reason_for_review": state["reason_for_review"], "finding": finding,
            "denial_log": tier_denials, "can_escalate": next_role is not None,
            "next_tier": next_role,
        })
        decision = human_decision.get("decision", "approve")
        if decision not in ("approve", "override", "escalate") or (decision == "escalate" and next_role is None):
            decision = "approve"

        notes = human_decision.get("notes") or None
        if decision == "escalate" and not notes:
            notes = _escalation_reason(role, finding, tier_denials)

        human_decisions = {**state["human_decisions"], role: {
            "decision": decision, "override_action": human_decision.get("override_action"),
            "notes": notes,
        }}

        print(f"\n{'─'*70}\n  REVIEW  |  {role}\n{'─'*70}")
        print(f"  Proposed: {finding.get('proposed_action')}")
        print(f"  Reviewer: {decision.upper()}")
        if notes:
            print(f"            {notes}")

        if decision == "escalate":
            print(f"  → escalating to {next_role}")
            _emit({"type": "routing", "stage": "review", "tier": role, "next": next_role, "reason": notes or ""})
            return {"human_decisions": human_decisions, "current_tier": next_role}

        final_action = finding.get("proposed_action") if decision == "approve" else (
            human_decision.get("override_action") or finding.get("proposed_action"))
        return _finalize(state, role, final_action, human_decisions)
    return _node


def _route_after_review(state: ClientReviewState) -> str:
    if state.get("closed_at_tier"):
        return "end"
    return state["current_tier"]


def _finalize(state: ClientReviewState, closed_at_tier: str, final_action: str,
              human_decisions: dict) -> dict:
    audit_summary = _collect_audit_summary()
    all_classified = [{"agent_role": d["agent_role"], "tool": d["tool"], "reason": d["reason"],
                        "mechanism": _classify_denial(d["reason"])} for d in state["denial_log"]]

    print(f"\n{'─'*70}\n  OUTCOME  |  {state['customer_id']}\n{'─'*70}")
    print(f"  Tiers visited: {state['tiers_visited']}")
    print(f"  Closed at: {closed_at_tier}")
    print(f"  Final action: {final_action}")
    print(f"  Denials encountered: {len(state['denial_log'])}")
    for d in all_classified:
        print(f"    ✗  [{d['agent_role']}] {d['tool']}: {d['reason']}  ({d['mechanism']})")

    _emit({
        "type": "disposition", "customer_id": state["customer_id"], "final_action": final_action,
        "closed_at_tier": closed_at_tier, "tiers_visited": state["tiers_visited"],
        "human_decisions": human_decisions, "denial_count": len(state["denial_log"]),
        "denials": all_classified, "audit_summary": audit_summary,
    })
    return {"final_action": final_action, "closed_at_tier": closed_at_tier, "human_decisions": human_decisions}


# ── graph ─────────────────────────────────────────────────────────────────────────

def build_graph(checkpointer=None):
    g = StateGraph(ClientReviewState)
    g.add_node("intake", intake_node)
    g.add_node("junior_analyst", _make_role_node("junior_analyst"))
    g.add_node("junior_review", _make_review_node("junior_analyst", "senior_analyst"))
    g.add_node("senior_analyst", _make_role_node("senior_analyst"))
    g.add_node("senior_review", _make_review_node("senior_analyst", "wealth_advisor"))
    g.add_node("wealth_advisor", _make_role_node("wealth_advisor"))
    g.add_node("wealth_review", _make_review_node("wealth_advisor", None))

    g.set_entry_point("intake")
    g.add_edge("intake", "junior_analyst")
    g.add_edge("junior_analyst", "junior_review")
    g.add_conditional_edges("junior_review", _route_after_review, {"senior_analyst": "senior_analyst", "end": END})
    g.add_edge("senior_analyst", "senior_review")
    g.add_conditional_edges("senior_review", _route_after_review, {"wealth_advisor": "wealth_advisor", "end": END})
    g.add_edge("wealth_advisor", "wealth_review")
    g.add_conditional_edges("wealth_review", _route_after_review, {"end": END})
    return g.compile(checkpointer=checkpointer)


# graph is compiled without a checkpointer at import time so it's importable by the
# LangGraph dev server (see langgraph.json: "client_analysis": "...:graph"), which
# manages its own persistence and refuses a pre-compiled custom checkpointer.
graph = build_graph()


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

def run_request(customer_id: str) -> None:
    review = ucdata.CLIENT_REVIEWS[customer_id]
    print(f"\n{'━'*70}\n  CUSTOMER {customer_id}  —  {review['reason_for_review']}\n{'━'*70}")
    _reset_sessions()
    # The CLI needs its own checkpointed graph — interrupt()/Command(resume=...) require
    # one, and the module-level `graph` above is deliberately checkpointer-free for
    # langgraph dev. Same split as fraud_investigation_demo.py and
    # institutional_portfolio_review_demo.py.
    cli_graph = build_graph(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": f"cli-{customer_id}"}}
    result = cli_graph.invoke({
        "customer_id": customer_id, "provider": "", "reason_for_review": "",
        "current_tier": "", "tiers_visited": [], "findings": {}, "human_decisions": {},
        "denial_log": [], "final_action": "", "closed_at_tier": "",
    }, config=config)

    # A single run can now pause up to 3 times (junior → senior → wealth_advisor), so
    # unlike every other demo's single `if "__interrupt__" in result`, this has to loop.
    # Auto-decision mirrors what the tier itself recommended.
    while "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        finding = payload["finding"]
        auto_decision = "escalate" if finding.get("recommend_escalation") and payload["can_escalate"] else "approve"
        result = cli_graph.invoke(Command(resume={"decision": auto_decision}), config=config)

    print_audit_trail(customer_id)


if __name__ == "__main__":
    for customer_id in ["C001", "C002", "C003", "C004", "C005"]:
        run_request(customer_id)
