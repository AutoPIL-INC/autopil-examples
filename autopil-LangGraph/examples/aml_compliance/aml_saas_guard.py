"""
Hosted AutoPIL SaaS trial mode — a drop-in ContextGuard replacement that calls the
real hosted API (POST /v1/context/evaluate) instead of evaluating policy locally.

Named aml_saas_guard.py, not the generic saas_guard.py this file started as — every
demo with hosted-mode support had an identically-named saas_guard.py, which collided
under langgraph dev (whichever demo's graph loaded first "won," and every other demo
silently imported *that* demo's copy instead of its own, crashing the whole server
with an ImportError the day institutional_portfolio_review's copy diverged in shape
from the others). See fraud_investigation's own fraud_saas_guard.py for the fuller
writeup.

Activated automatically when AUTOPIL_ADMIN_KEY and AUTOPIL_EVALUATE_KEY are both set
(see aml_compliance_demo.py's guard construction) — same explicit-opt-in pattern as
the other 3 demos in this repo. Falls back to the embedded ContextGuard otherwise, so
nothing changes for anyone not opting into a hosted trial.

Verified live against a real trial tenant (base_url https://autopil-api.onrender.com,
2026-07-10):
  - POST /v1/context/evaluate requires agent_id unconditionally — an unregistered or
    unapproved agent_id is denied before policy ever runs (denial_type: "identity").
    The local SDK makes agent_id optional depending on the policy; the hosted API
    does not.
  - Agents are created with status "draft" and must be explicitly approved
    (PATCH /v1/agents/{id}/status) before they can evaluate anything.
  - **This demo's source names use catalog.wealth.*/catalog.risk.* FQNs, matching
    institutional_portfolio_review's convention — not this tenant's pre-seeded
    `aml_investigator_policy`/`kyc_agent_policy`/`compliance_officer_policy`, which
    use plain source names.** Binding to any of those pre-seeded policies as-is would
    deny every call for a naming mismatch, not real enforcement. `ensure_policy()`
    below creates 3 new `demo_aml_<role>_policy` policies instead — translated
    field-for-field from `policies/financial_services/aml_compliance.yaml` (see
    `aml_compliance_demo.py`'s `_POLICY_SPECS`), so this demo's own source naming
    never has to change between local and hosted mode.
  - **`bootstrap_agents()` must rebind `policy_name` on an existing agent, not just
    `owner_team`** — caught live switching this demo onto the FQN source names: this
    tenant's 3 agents already existed (registered under the old default
    `f"{role}_policy"` naming before the switch), and `PUT /v1/agents/{id}` accepting
    a new `policy_name` does *not* actually repoint what `/v1/context/evaluate`
    resolves for that agent_id — it stays pinned to whatever policy was bound at
    creation. The only fix that actually worked was deleting the 3 stale agents
    (`DELETE /v1/agents/{id}`) and letting `bootstrap_agents()` recreate them fresh,
    bound to `demo_aml_<role>_policy` from the start.
  - **Short eventual-consistency lag right after creating a new agent/policy.** The
    very first `evaluate()` calls against a just-created agent_id can still resolve
    against the old/wrong policy binding for a few seconds before settling — a run
    immediately after `bootstrap_agents()` created fresh agents showed 0 allowed
    across the board, while a direct diagnostic call against the same agent_id
    moments later correctly resolved to `demo_aml_<role>_policy` and allowed. A
    re-run once things settled came back with the expected healthy allow/deny mix.
    Not something this code works around — just something to expect if you're
    testing hosted mode immediately after (re)creating agents.
  - `aml_investigator`/`kyc_agent`/`compliance_officer` don't collide with any other
    demo's role names on this tenant (checked directly against the full policy
    list), so the generic `owner_tag="autopil-langgraph-demos"` is safe to reuse here
    — unlike institutional_portfolio_review's `wealth_advisor`, which does collide
    with client_analysis's role of the same name (see `ipr_saas_guard.py`).
  - GET /v1/audit/sessions/{id} requires the Admin key — an Evaluate-scoped key gets
    403 Forbidden calling it, even though that same key works fine for
    POST /v1/context/evaluate. RemoteContextGuard below needs both keys for exactly
    this reason: evaluate_key for decisions, admin_key for reading the trail back.
  - Known gap, disclosed rather than silently claimed as at-parity: the hosted policy
    schema (GET/POST /v1/policies) has no session_ttl_minutes or sensitivity_decay
    field — not exercised by this demo's own local policy either way, so no
    behavioral gap here specifically, just the same structural limitation
    fraud_investigation/client_analysis both disclose.
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


def ensure_policy(base_url: str, admin_key: str, name: str, agent_role: str, spec: dict) -> None:
    """Idempotently ensure a policy named `name` exists on the hosted tenant,
    creating it via POST /v1/policies if missing. Existing policies are left as-is —
    call sites should pick a name unlikely to collide with a pre-seeded one (e.g. the
    "demo_" prefix this file uses) if they need guaranteed content, since this
    function only checks for a name match, not content equality.

    `spec` is passed straight through as the rest of CreatePolicyRequest's body
    (allowed_sources/denied_sources/allowed_tasks/denied_tasks/max_sensitivity/
    task_bindings/require_task_for_sensitivity/description/...) — no session_ttl_minutes
    or sensitivity_decay field exists on this endpoint (confirmed against the real
    OpenAPI schema, same as ipr_saas_guard.py's copy of this function).
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
    existed. `policy_name` is kept in sync the same way — needed here specifically:
    this demo's roles were already registered on the shared tenant under the default
    `f"{role}_policy"` naming before it switched to dedicated `demo_aml_<role>_policy`
    policies (see `ensure_policy()`/module docstring), and reusing an existing agent
    without rebinding its policy would silently keep evaluating against the old
    plain-source-name policy — every call denied for a naming mismatch, not real
    enforcement. Caught live exactly this way the first time this ran post-rename.
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
        else:
            if agent.get("policy_name") != policy_name_for(role):
                resp = client.put(f"/v1/agents/{agent['agent_id']}", json={"policy_name": policy_name_for(role)})
                resp.raise_for_status()
                agent = resp.json()
            if owner_team is not None and agent.get("owner_team") != owner_team:
                resp = client.put(f"/v1/agents/{agent['agent_id']}", json={"owner_team": owner_team})
                resp.raise_for_status()
                agent = resp.json()
        if agent["status"] != "approved":
            resp = client.patch(f"/v1/agents/{agent['agent_id']}/status", json={"status": "approved"})
            resp.raise_for_status()
            agent = resp.json()
        result[role] = agent["agent_id"]
    return result
