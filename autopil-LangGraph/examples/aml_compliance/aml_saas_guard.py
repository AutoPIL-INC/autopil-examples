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
  - **This tenant's pre-seeded `aml_investigator_policy`/`kyc_agent_policy`/
    `compliance_officer_policy` are a close, but not exact, match** for
    `policies/financial_services/aml_compliance.yaml`. `aml_investigator_policy`
    matches byte-for-byte. `kyc_agent_policy` matches except one extra denied source
    (`application_forms`, not present locally — harmless, since this demo never
    reaches for it anyway). `compliance_officer_policy` has real drift: the hosted
    version's `allowed_sources` additionally includes `loan_history`/
    `portfolio_metrics` (present in the *original* institutional_portfolio_review
    policy this was split from, but trimmed from this demo's own YAML since no tool
    here exercises them), and its `sar_filing`/`cross_client_audit`/
    `fiduciary_review` task_bindings differ slightly. Reused as-is rather than
    creating a dedicated `demo_`-prefixed policy (unlike institutional_portfolio_
    review's `ipr_saas_guard.py`, which had to, since none of *its* pre-seeded
    policies matched at all) — this is a deliberate "good enough, disclosed" call,
    not an oversight: `compliance_officer` in SaaS mode has marginally broader real
    access than local mode, never narrower, so no local-mode-only denial becomes a
    false ALLOW remotely.
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
