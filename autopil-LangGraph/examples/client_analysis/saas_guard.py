"""
Hosted AutoPIL SaaS trial mode — a drop-in ContextGuard replacement that calls the
real hosted API (POST /v1/context/evaluate) instead of evaluating policy locally.

Activated automatically when AUTOPIL_ADMIN_KEY and AUTOPIL_EVALUATE_KEY are both set
(see client_analysis_demo.py's guard construction) — same explicit-opt-in pattern as
this file's own AWS_BEDROCK_MODEL_ID. Falls back to the embedded ContextGuard
otherwise, so nothing changes for anyone not opting into a hosted trial.

Identical to fraud_investigation/saas_guard.py (kept as a per-demo copy, same
"standalone from pip install" convention as this repo's frontend files) except for
one client_analysis-specific finding:

  - This tenant has TWO policies with agent_role="wealth_advisor" —
    "demo_wealth_advisor_policy" (matches policies/financial_services/
    client_analysis.yaml's wealth_advisor_policy byte-for-byte — confirmed by diffing
    GET /v1/policies against the local YAML) and "wealth_advisor_policy" (an unrelated
    generic wealth-demo policy with entirely different source names, e.g.
    "portfolio_holdings" instead of "catalog.finance.client_portfolios"). The evaluate
    endpoint falls back to a role-scan when an agent has no explicit policy_name
    bound, which would non-deterministically risk binding to the wrong one of the
    two. client_analysis_demo.py's bootstrap call pins policy_name explicitly per
    role for exactly this reason — see _SAAS_POLICY_NAMES there.
  - junior_analyst_policy and senior_analyst_policy have no such collision and
    matched the local YAML exactly, same as fraud_investigation's 5 roles did.
  - GET /v1/audit/sessions/{id} requires the Admin key — an Evaluate-scoped key gets
    403 Forbidden calling it, even though that same key works fine for
    POST /v1/context/evaluate. RemoteContextGuard below needs both keys for exactly
    this reason: evaluate_key for decisions, admin_key for reading the trail back.

See fraud_investigation/DESIGN.md's "Appendix: hosted trial mode" for the fuller set
of things verified live against the real trial tenant (agent_id required
unconditionally, agents start draft and need explicit approval, role-spoofing checks
enforced identically, etc.) — all of that applies here too, since it's the same
hosted API and the same RemoteContextGuard implementation.
"""

import httpx


class _Decision:
    """Stand-in for autopil.models.Decision — just needs .value, matching how
    _collect_audit_summary() reads a local audit event (`e.decision.value`)."""

    def __init__(self, value: str):
        self.value = value


class _RemoteAuditEvent:
    """Matches the attributes _collect_audit_summary()/print_audit_trail() read off a
    local AuditEvent: .decision (with .value), .source_id, .policy_name, .reason."""

    def __init__(self, raw: dict):
        self.decision = _Decision(raw["decision"])
        self.source_id = raw["source_id"]
        self.policy_name = raw["policy_name"]
        self.reason = raw.get("reason")


class RemoteContextGuard:
    """Same .protect()/.get_audit_trail() surface as autopil.ContextGuard, backed by
    HTTP calls to a hosted AutoPIL trial instead of local policy evaluation. Callers
    (_make_getter, _collect_audit_summary) don't need to know which one they have.

    Needs both keys, not just the Evaluate one — confirmed live: GET
    /v1/audit/sessions/{id} returns 403 Forbidden with an Evaluate-scoped key (only
    POST /v1/context/evaluate accepts it); the Admin key is required to read the
    trail back. Evaluate-only calls (.protect()) still use the evaluate key, not the
    admin one, to match how this demo is meant to run day to day.
    """

    def __init__(self, base_url: str, evaluate_key: str, admin_key: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self._eval_client = httpx.Client(
            base_url=self.base_url, headers={"X-API-Key": evaluate_key}, timeout=timeout,
        )
        self._admin_client = httpx.Client(
            base_url=self.base_url, headers={"X-API-Key": admin_key}, timeout=timeout,
        )

    def protect(self, *, agent_role, user_id, source_id, sensitivity_level, session_id,
                agent_id=None, task_type=None):
        sensitivity_str = getattr(sensitivity_level, "value", sensitivity_level)

        def decorator(fn):
            def wrapped(*args, **kwargs):
                key = args[0] if args else kwargs.get("key", "")
                payload = {
                    "query": f"retrieve {source_id}" + (f" (key={key})" if key else ""),
                    "agent_role": agent_role, "user_id": user_id, "source_id": source_id,
                    "sensitivity_level": sensitivity_str, "session_id": session_id,
                    "agent_id": agent_id, "task_type": task_type,
                }
                resp = self._eval_client.post("/v1/context/evaluate", json=payload)
                resp.raise_for_status()
                data = resp.json()
                if data["decision"] == "DENY":
                    raise PermissionError(
                        f"[AutoPIL] DENIED | source='{source_id}' | agent='{agent_role}' | {data['reason']}"
                    )
                return fn(*args, **kwargs)
            return wrapped
        return decorator

    def get_audit_trail(self, session_id: str) -> list[_RemoteAuditEvent]:
        resp = self._admin_client.get(f"/v1/audit/sessions/{session_id}")
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        return [_RemoteAuditEvent(e) for e in resp.json()["events"]]


def bootstrap_agents(base_url: str, admin_key: str, roles: list[str], owner_tag: str,
                      policy_name_for: "callable[[str], str]" = lambda role: f"{role}_policy",
                      owner_team: "str | None" = None) -> dict[str, str]:
    """Idempotently ensure each role in `roles` has a real, approved agent registered
    on the hosted tenant, explicitly bound to its policy (never relying on the
    evaluate endpoint's role-scan fallback — see the module docstring on why that's
    risky on a shared trial tenant, especially for wealth_advisor here). Returns
    {agent_role: agent_id}.

    Reuses an existing agent (matching agent_role + owner_tag) if one's already
    registered from a prior run/process, rather than creating a new one every time —
    approves it first if it's still in "draft". `owner_tag` (stored in the `owner`
    field) is purely this lookup key, distinct from `owner_team` — the actual
    business-accountable team, e.g. "Wealth Team" — which is kept in sync via PUT on
    every call if it's out of date, including on agents that were registered before
    this parameter existed.
    """
    client = httpx.Client(base_url=base_url.rstrip("/"), headers={"X-API-Key": admin_key}, timeout=15.0)
    existing = client.get("/v1/agents", params={"framework": "langgraph", "owner": owner_tag}).json()
    by_role = {a["agent_role"]: a for a in existing}

    result = {}
    for role in roles:
        agent = by_role.get(role)
        if agent is None:
            resp = client.post("/v1/agents", json={
                "agent_role": role, "display_name": role.replace("_", " ").title(),
                "description": "Registered by the AutoPIL + LangGraph demos "
                                "(github.com/AutoPIL-INC/autopil-examples)",
                "owner": owner_tag, "owner_team": owner_team, "framework": "langgraph",
                "policy_name": policy_name_for(role),
            })
            resp.raise_for_status()
            agent = resp.json()
        elif owner_team is not None and agent.get("owner_team") != owner_team:
            resp = client.put(f"/v1/agents/{agent['agent_id']}", json={"owner_team": owner_team})
            resp.raise_for_status()
            agent = resp.json()
        if agent["status"] != "approved":
            resp = client.patch(f"/v1/agents/{agent['agent_id']}/status", json={"status": "approved"})
            resp.raise_for_status()
            agent = resp.json()
        result[role] = agent["agent_id"]
    return result
