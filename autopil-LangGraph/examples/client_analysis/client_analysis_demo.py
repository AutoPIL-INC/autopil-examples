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

An orchestrator reads a natural-language client-analysis request, decides which role
should handle it and what task/purpose it falls under, then that role's agent tries to
fulfill it with a real tool-calling loop. Denials aren't scripted — they happen when
the model reasons its way toward a source its assigned task doesn't cover, exercising
four distinct AutoPIL enforcement paths: denied_sources, denied_tasks, task_bindings
(purpose limitation), and the sensitivity ceiling.

See DESIGN.md for the full design rationale.

Run:
    .venv/bin/python examples/client_analysis/client_analysis_demo.py
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
from langgraph.config import get_stream_writer
from langgraph.graph import END, StateGraph

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

AGENT_REGISTRY_STORE = SQLiteAgentRegistryStore(str(AUDIT_DB))

AGENT_IDS = {
    "governance_orchestrator": "governance-orchestrator-001",
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


_register_agents()

guard = ContextGuard(policy_path=str(POLICY_FILE), audit_db=str(AUDIT_DB), tenant_id=TENANT_ID,
                      agent_registry_store=AGENT_REGISTRY_STORE)

# Providers that support forcing a specific tool via tool_choice=<name>. Bedrock only
# supports it for some underlying models (verified: Anthropic-on-Bedrock does, a Llama
# Bedrock model raises ValueError at bind_tools() time) — same class of problem as
# Ollama's silent ignore, different failure mode (raises instead of no-ops), so it gets
# the same defensive fallback via _bind_forced() below rather than an assumption either
# way.
_ALWAYS_SUPPORTS_FORCED_CHOICE = {"anthropic", "gemini", "groq"}


def _make_llm(provider: str = ""):
    """Build the LLM for a run. provider is "bedrock", "anthropic", "gemini", "groq",
    "ollama", or "" (auto: first of the five with credentials configured, Ollama last
    since it needs no key) — the live viewer's model dropdown sets this explicitly per
    run via GovernanceState["provider"]; the CLI leaves it on auto.

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


def _bind_forced(llm, tools: list, tool_name: str):
    """Bind tools, forcing a specific tool call when the provider supports it, falling
    back to unforced binding otherwise. Ollama ignores tool_choice silently; some
    non-Anthropic Bedrock models raise ValueError at bind time instead — both are
    handled by the same fallback, and callers still need the `if response.tool_calls`
    guard below either way."""
    try:
        return llm.bind_tools(tools, tool_choice=tool_name)
    except ValueError:
        return llm.bind_tools(tools)


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

_FINDING_TOOL_SCHEMA = {
    "name": "submit_finding",
    "description": "Submit your final response to the business request and end your turn. Call this once you're done gathering data (or once you've determined you can't complete it with the sources available to you).",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "1-3 sentence summary of what you produced (or why you couldn't)"},
            "outcome": {"type": "string", "enum": ["COMPLETED", "BLOCKED"], "description": "COMPLETED if you produced the requested output using only sources that succeeded; BLOCKED if denials left you unable to complete it"},
            "sources_used": {"type": "array", "items": {"type": "string"}, "description": "sources you actually got data back from"},
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

class GovernanceState(TypedDict):
    request_id: str
    provider: str
    brief: str
    assigned_role: str
    task_type: str
    roles_attempted: list[str]
    escalated: bool
    finding: dict
    denial_log: list[DenialEvent]
    final_decision: str


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


# ── orchestrator ──────────────────────────────────────────────────────────────────

def orchestrator_node(state: GovernanceState) -> dict:
    _reset_sessions()
    print(f"\n{'─'*70}\n  GOVERNANCE ORCHESTRATOR  (session: {SESSIONS['orchestrator'][:8]}…)\n{'─'*70}")
    # Looked up server-side from request_id, same as the fraud demo's orchestrator_node
    # fetches the alert from case_id — the client only ever needs to send request_id.
    brief = ucdata.GOVERNANCE_REQUESTS[state["request_id"]]["brief"]
    print(f"  Request: {brief}")

    assign_schema = {
        "name": "assign_request",
        "description": "Decide which role should handle this business request, and what task/purpose it falls under.",
        "input_schema": {
            "type": "object",
            "properties": {
                "role": {"type": "string", "enum": ROLES},
                "task_type": {"type": "string", "enum": TASK_TYPES},
                "reasoning": {"type": "string"},
            },
            "required": ["role", "task_type"],
        },
    }
    bound = _bind_forced(_make_llm(state["provider"]), [assign_schema], "assign_request")
    prompt = (
        f"Business request:\n{brief}\n\n"
        f"Decide which role should handle this and what task/purpose it falls under. "
        f"Available roles: {ROLES}. Available task types: {TASK_TYPES}."
    )
    response = bound.invoke([SystemMessage(content="You are a governance orchestrator at a wealth management firm, assigning incoming requests to the right role."),
                              HumanMessage(content=prompt)])
    args = response.tool_calls[0]["args"] if response.tool_calls else {}
    role = args.get("role")
    if role not in ROLES:
        role = ROLES[0]
    task_type = args.get("task_type")
    # Not every model honors the enum constraint strictly — seen live: qwen2.5:7b
    # returned a list of candidate task types instead of picking one. Coerce to a
    # single valid value rather than passing a malformed task_type into every guarded
    # call downstream, which would deny everything for the wrong reason.
    if isinstance(task_type, list):
        task_type = next((t for t in task_type if t in TASK_TYPES), None)
    if task_type not in TASK_TYPES:
        task_type = TASK_TYPES[0]
    print(f"  → assigned to {role}  (task_type={task_type})  {args.get('reasoning','')}")
    _emit({"type": "routing", "stage": "initial", "role": role, "task_type": task_type, "reasoning": args.get("reasoning", "")})

    return {"brief": brief, "assigned_role": role, "task_type": task_type, "roles_attempted": [], "denial_log": [], "escalated": False}


def _run_role(role: str, state: GovernanceState) -> dict:
    print(f"\n{'─'*70}\n  {role.upper().replace('_',' ')}  (session: {SESSIONS[role][:8]}…)\n{'─'*70}")
    tools = role_tools(role, state["task_type"], key_hint="C001")
    brief = (
        f"You are the {role.replace('_',' ')} handling this business request:\n\n"
        f"{state['brief']}\n\n"
        f"Your assigned task type for this request is: {state['task_type']}.\n\n"
        f"Gather whatever data you need using the tools available to you, then call "
        f"submit_finding with your response."
    )
    denial_log = list(state["denial_log"])
    finding, _ = run_tool_loop(role, f"You are a {role.replace('_',' ')} at a wealth management firm.",
                                brief, tools, denial_log, _make_llm(state["provider"]))
    finding = finding or {"summary": "No finding submitted", "outcome": "BLOCKED"}
    roles_attempted = [*state["roles_attempted"], role]
    _emit({"type": "finding", "role": role, "finding": finding})
    return {"finding": finding, "roles_attempted": roles_attempted, "denial_log": denial_log}


def junior_analyst_node(state: GovernanceState) -> dict:
    return _run_role("junior_analyst", state)


def senior_analyst_node(state: GovernanceState) -> dict:
    return _run_role("senior_analyst", state)


def wealth_advisor_node(state: GovernanceState) -> dict:
    return _run_role("wealth_advisor", state)


def route_to_role(state: GovernanceState) -> str:
    return state["assigned_role"]


def orchestrator_review_node(state: GovernanceState) -> dict:
    """One optional escalation: if the assigned role hit denials serious enough that it
    couldn't complete the request, decide whether escalating to senior_analyst (the
    broadest role) is worth trying, or whether the outcome should stand as blocked.
    Mirrors the fraud investigation demo's re-route-after-denial pattern.
    """
    blocked = state["finding"].get("outcome") == "BLOCKED"
    recent_denials = [d for d in state["denial_log"] if d["agent_role"] == state["assigned_role"]]
    can_escalate = (not state["escalated"]) and state["assigned_role"] != "senior_analyst"

    if not (blocked and recent_denials) or not can_escalate:
        print(f"\n  [orchestrator review]  accepting outcome as final")
        _emit({"type": "routing", "stage": "review", "next": "decision", "reason": "no further escalation"})
        return {"final_decision": "route:decision"}

    decide_schema = {
        "name": "decide_next",
        "description": "Decide whether to escalate this request to a broader role.",
        "input_schema": {
            "type": "object",
            "properties": {
                "next": {"type": "string", "enum": ["escalate_to_senior_analyst", "accept_outcome"]},
                "reason": {"type": "string"},
            },
            "required": ["next"],
        },
    }
    bound = _bind_forced(_make_llm(state["provider"]), [decide_schema], "decide_next")
    prompt = (
        f"Request: {state['brief']}\n\n"
        f"{state['assigned_role']} attempted this and was blocked. Denials hit:\n"
        f"{json.dumps(recent_denials, indent=2)}\n\n"
        f"Should this be escalated to senior_analyst (broader access), or should the "
        f"outcome stand as blocked (requires human override)?"
    )
    response = bound.invoke([SystemMessage(content="You are a governance orchestrator deciding whether to escalate a blocked request."),
                              HumanMessage(content=prompt)])
    decision = response.tool_calls[0]["args"] if response.tool_calls else {"next": "accept_outcome"}
    nxt = decision.get("next")
    if nxt not in ("escalate_to_senior_analyst", "accept_outcome"):
        nxt = "accept_outcome"
    print(f"\n  [orchestrator review]  {nxt}  ({decision.get('reason','')})")
    _emit({"type": "routing", "stage": "review", "next": nxt, "reason": decision.get("reason", "")})

    if nxt == "escalate_to_senior_analyst":
        return {"final_decision": "route:senior_analyst", "assigned_role": "senior_analyst", "escalated": True}
    return {"final_decision": "route:decision"}


def route_after_review(state: GovernanceState) -> str:
    return state["final_decision"].split(":", 1)[1]


def decision_node(state: GovernanceState) -> dict:
    request = ucdata.GOVERNANCE_REQUESTS[state["request_id"]]
    classified = [{"agent_role": d["agent_role"], "tool": d["tool"], "reason": d["reason"],
                   "mechanism": _classify_denial(d["reason"])} for d in state["denial_log"]]
    mechanisms = sorted({c["mechanism"] for c in classified})

    # Don't just trust the model's self-reported outcome — an over-eager model can
    # claim COMPLETED after every single tool call was denied (seen live: qwen2.5:7b did
    # exactly this). Ground it in the actual audit trail for the role that ran last:
    # did it get ANY data back at all?
    audit_summary = _collect_audit_summary()
    last_role = state["roles_attempted"][-1] if state["roles_attempted"] else state["assigned_role"]
    last_role_audit = audit_summary["roles"].get(last_role, {"allowed": 0})
    got_data = last_role_audit["allowed"] > 0
    completed = state["finding"].get("outcome") == "COMPLETED" and got_data

    if completed and not state["denial_log"]:
        outcome = "COMPLETED — request fulfilled using only sources the role was authorized for."
    elif completed:
        outcome = f"COMPLETED WITH GOVERNANCE INTERVENTION — {len(state['denial_log'])} attempt(s) denied ({', '.join(mechanisms)}); role completed the request using authorized sources instead."
    elif state["escalated"]:
        outcome = f"ESCALATED THEN BLOCKED — request could not be completed even after escalating to {state['assigned_role']}; requires human override."
    else:
        outcome = f"BLOCKED — {state['roles_attempted'][0] if state['roles_attempted'] else 'assigned role'} could not complete the request within policy bounds ({', '.join(mechanisms) or 'no data gathered'})."

    print(f"\n{'─'*70}\n  OUTCOME  |  {state['request_id']}\n{'─'*70}")
    print(f"  Assigned role(s): {state['roles_attempted']}")
    print(f"  Task type: {state['task_type']}")
    print(f"  Expected role (ground truth): {request['expected_role']}")
    print(f"  Outcome: {outcome}")
    print(f"  Denials encountered: {len(state['denial_log'])}")
    for d in classified:
        print(f"    ✗  [{d['agent_role']}] {d['tool']}: {d['reason']}  ({d['mechanism']})")

    _emit({
        "type": "disposition", "request_id": state["request_id"], "outcome": outcome,
        "roles_attempted": state["roles_attempted"], "task_type": state["task_type"],
        "expected_role": request["expected_role"], "denial_count": len(state["denial_log"]),
        "denials": classified, "audit_summary": audit_summary,
    })
    return {"final_decision": outcome}


# ── graph ─────────────────────────────────────────────────────────────────────────

def build_graph():
    g = StateGraph(GovernanceState)
    g.add_node("orchestrator", orchestrator_node)
    g.add_node("junior_analyst", junior_analyst_node)
    g.add_node("senior_analyst", senior_analyst_node)
    g.add_node("wealth_advisor", wealth_advisor_node)
    g.add_node("orchestrator_review", orchestrator_review_node)
    g.add_node("decision", decision_node)

    g.set_entry_point("orchestrator")
    g.add_conditional_edges("orchestrator", route_to_role, {r: r for r in ROLES})
    for role in ROLES:
        g.add_edge(role, "orchestrator_review")
    g.add_conditional_edges("orchestrator_review", route_after_review, {
        **{r: r for r in ROLES}, "decision": "decision",
    })
    g.add_edge("decision", END)
    return g.compile()


# graph is compiled at import time so it's importable by the LangGraph dev server
# (see langgraph.json: "client_analysis": "...:graph").
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

def run_request(request_id: str) -> None:
    request = ucdata.GOVERNANCE_REQUESTS[request_id]
    print(f"\n{'━'*70}\n  REQUEST {request_id}  —  {request['title']}\n{'━'*70}")
    _reset_sessions()
    graph.invoke({
        "request_id": request_id, "provider": "", "brief": "",
        "assigned_role": "", "task_type": "", "roles_attempted": [], "escalated": False,
        "finding": {}, "denial_log": [], "final_decision": "",
    })
    print_audit_trail(request_id)


if __name__ == "__main__":
    for request_id in ["GOV-001", "GOV-002", "GOV-003"]:
        run_request(request_id)
