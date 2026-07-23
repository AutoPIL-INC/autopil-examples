"""
Hosted AutoPIL SaaS trial mode — a drop-in ContextGuard replacement that calls the
real hosted API (POST /v1/context/evaluate) instead of evaluating policy locally.

Activated automatically when AUTOPIL_ADMIN_KEY and AUTOPIL_EVALUATE_KEY are both set
(see institutional_portfolio_review_demo.py's guard construction) — same
explicit-opt-in pattern as the other 3 demos in this repo. Falls back to the embedded
ContextGuard(s) otherwise, so nothing changes for anyone not opting into a hosted
trial.

Named ipr_saas_guard.py, not the generic saas_guard.py this file started as — every
demo with hosted-mode support had an identically-named saas_guard.py, which collided
under langgraph dev (whichever demo's graph loaded first "won," and every other demo
silently imported *that* demo's copy instead of its own). Caught live: this file's
own ensure_policy() function got shadowed by fraud_investigation's saas_guard.py copy
(which doesn't have one), crashing the whole langgraph dev server with an
ImportError on startup. See fraud_investigation's own fraud_saas_guard.py for the
fuller writeup.

Three things are specific to this demo, confirmed live against a real trial tenant
(base_url https://autopil-api.onrender.com, 2026-07-10), none shared by
fraud_investigation/client_analysis's own hosted-mode copies:

  - **None of this demo's 8 pre-seeded role policies on the shared trial tenant
    actually match.** Every one of them (`portfolio_orchestrator_policy`,
    `wealth_advisor_policy`, `investment_analyst_policy`, `macro_analyst_policy`,
    `rebalancing_agent_policy`, `report_generator_policy`,
    `credit_risk_analyst_policy`, `settlement_agent_policy`) uses *plain* source
    names (`client_profile`, `portfolio_holdings`) — this demo's local YAML uses
    `catalog.wealth.*`/`catalog.risk.*` prefixed names (a real Unity-Catalog-style
    convention, unlike fraud_investigation/client_analysis's flatter naming). Binding
    to any pre-seeded policy as-is would deny every call for a naming mismatch, not
    real enforcement. `ensure_policy()` below creates 8 new policies instead —
    translated field-for-field from
    `portfolio_review_wealth.yaml`/`portfolio_review_risk.yaml`, so the demo's own
    source naming never has to change.
  - **`wealth_advisor` also collides with client_analysis's own role of the same
    name** — caught live: a first attempt using the generic `owner_tag=
    "autopil-langgraph-demos"` and `demo_<role>_policy` naming (matching
    client_analysis's own convention) silently reused client_analysis's existing
    wealth_advisor agent and would have skipped creating this demo's own
    demo_wealth_advisor_policy, since that name already existed (bound to
    client_analysis's `catalog.finance.*` sources, not this demo's
    `catalog.wealth.*` ones). Fixed with a demo-specific `owner_tag`
    (`Investments-team`) and policy prefix (`demo_ipr_<role>_policy`) — see
    `institutional_portfolio_review_demo.py`'s `_SAAS_MODE` block. Any *new* demo
    added to this repo needs its own distinct owner_tag/policy-prefix scheme too, not
    just a unique role-name check — role names **will** repeat across demos over
    time.
  - **Two `ContextGuard` instances collapse into one in SaaS mode.** Locally,
    `wealth_guard`/`risk_guard` are separate because they read two different local
    YAML files; the hosted API is one tenant with one evaluate endpoint regardless of
    which file a policy conceptually belongs to, so in SaaS mode both variables just
    point at the same `RemoteContextGuard` instance. `ROLE_GUARD`'s construction
    doesn't need to change either way.

Everything else confirmed for the other two demos' hosted mode applies here
unchanged (agent_id required unconditionally, agents start draft and need explicit
approval, GET /v1/audit/sessions/{id} needs the Admin key not the Evaluate key, no
`sensitivity_decay`/`permitted_agent_ids`/`session_ttl_minutes` field on
`CreatePolicyRequest` either — so those three local mechanisms aren't enforceable the
same way remotely, same disclosed gap as before).
"""

import time

import httpx

_EVALUATE_MAX_ATTEMPTS = 3
_EVALUATE_BACKOFF_SECONDS = 1.0


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
                resp = None
                for attempt in range(_EVALUATE_MAX_ATTEMPTS):
                    try:
                        resp = self._eval_client.post("/v1/context/evaluate", json=payload)
                    except httpx.TransportError:
                        if attempt == _EVALUATE_MAX_ATTEMPTS - 1:
                            raise
                        time.sleep(_EVALUATE_BACKOFF_SECONDS * (2 ** attempt))
                        continue
                    if resp.status_code < 500 or attempt == _EVALUATE_MAX_ATTEMPTS - 1:
                        break
                    time.sleep(_EVALUATE_BACKOFF_SECONDS * (2 ** attempt))
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


def ensure_policy(base_url: str, admin_key: str, name: str, agent_role: str, spec: dict) -> None:
    """Idempotently ensure a policy named `name` exists on the hosted tenant,
    creating it via POST /v1/policies if missing. Existing policies are left as-is —
    call sites should pick a name unlikely to collide with a pre-seeded one (e.g. the
    "demo_" prefix this file uses) if they need guaranteed content, since this
    function only checks for a name match, not content equality.

    `spec` is passed straight through as the rest of CreatePolicyRequest's body
    (allowed_sources/denied_sources/allowed_tasks/denied_tasks/max_sensitivity/
    task_bindings/require_task_for_sensitivity/description/...) — no session_ttl_minutes
    or sensitivity_decay field exists on this endpoint, confirmed against the real
    OpenAPI schema, not assumed.
    """
    client = httpx.Client(base_url=base_url.rstrip("/"), headers={"X-API-Key": admin_key}, timeout=15.0)
    existing_resp = client.get("/v1/policies")
    if existing_resp.is_error:
        raise RuntimeError(
            f"AutoPIL API error listing policies ({existing_resp.status_code}): "
            f"{existing_resp.text} — check AUTOPIL_ADMIN_KEY in .env"
        )
    if any(p.get("name") == name for p in existing_resp.json()):
        return
    resp = client.post("/v1/policies", json={"name": name, "agent_role": agent_role, **spec})
    resp.raise_for_status()


def bootstrap_agents(base_url: str, admin_key: str, roles: list[str], owner_tag: str,
                      policy_name_for: "callable[[str], str]" = lambda role: f"{role}_policy",
                      owner_team: "str | None" = None) -> dict[str, str]:
    """Idempotently ensure each role in `roles` has a real, approved agent registered
    on the hosted tenant, explicitly bound to its policy (never relying on the
    evaluate endpoint's role-scan fallback — see the module docstring on why that's
    risky on a shared trial tenant). Returns {agent_role: agent_id}.

    Reuses an existing agent (matching agent_role + owner_tag) if one's already
    registered from a prior run/process, rather than creating a new one every time —
    approves it first if it's still in "draft". `owner_tag` (stored in the `owner`
    field) is purely this lookup key, distinct from `owner_team` — the actual
    business-accountable team — which is kept in sync via PUT on every call if it's
    out of date, including on agents that were registered before this parameter
    existed.
    """
    client = httpx.Client(base_url=base_url.rstrip("/"), headers={"X-API-Key": admin_key}, timeout=15.0)
    existing_resp = client.get("/v1/agents", params={"framework": "langgraph", "owner": owner_tag})
    if existing_resp.is_error:
        raise RuntimeError(
            f"AutoPIL API error listing agents ({existing_resp.status_code}): "
            f"{existing_resp.text} — check AUTOPIL_ADMIN_KEY in .env"
        )
    by_role = {a["agent_role"]: a for a in existing_resp.json()}

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
