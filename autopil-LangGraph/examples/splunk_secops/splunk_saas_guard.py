"""
Hosted AutoPIL SaaS trial mode — a drop-in ContextGuard replacement that calls the
real hosted API (POST /v1/context/evaluate) instead of evaluating policy locally.

Activated automatically when AUTOPIL_ADMIN_KEY and AUTOPIL_EVALUATE_KEY are both set
(see splunk_secops_demo.py's guard construction) — same explicit-opt-in pattern as
the other 4 demos in this repo. Falls back to the embedded ContextGuard otherwise, so
nothing changes for anyone not opting into a hosted trial.

Named splunk_saas_guard.py, not the generic saas_guard.py this pattern started as —
every demo with hosted-mode support has an identically-named module of its own for
exactly this reason: a shared name collides under langgraph dev, since all demos'
graphs load into one process and whichever demo's copy loads first "wins" the
sys.modules slot for every demo (see root CLAUDE.md's module-name-collision note, and
fraud_saas_guard.py's own module docstring for the incident that first surfaced it).

This demo's own hosted-mode wiring is UNVERIFIED against a real trial tenant — unlike
the other 4 demos, splunk_secops shipped local-only by design (see DESIGN.md §7), so
there's no "confirmed live" claim to make here yet. Two things worth knowing before
trusting this against a real tenant:
  - The shared trial tenant's pre-seeded policies are financial_services-domain
    (fraud_investigation/client_analysis/institutional_portfolio_review/aml_compliance
    role names) — none of this demo's 5 SOC role names
    (soc_orchestrator/security_auditor/incident_triage/compliance_reporter/
    splunk_threat_synthesizer) are likely to have a matching pre-seeded policy.
    splunk_secops_demo.py therefore calls ensure_policy() (below) to create 5
    dedicated demo_splunk_<role>_policy policies, translated field-for-field from
    policies/SecOps/soc_mainframe_logs.yaml, rather than assuming a pre-seeded match
    the way fraud_investigation's hosted mode does.
  - Known gap, disclosed rather than silently claimed as at-parity (same pattern as
    every other demo's hosted-mode gap list): CreatePolicyRequest has no
    permitted_agent_ids, session_ttl_minutes, or sensitivity_decay field. This drops
    three local mechanisms this demo's policy relies on —
    security_auditor_policy's permitted_agent_ids lock to a named service identity,
    incident_triage_policy's session_ttl_minutes + 2-step sensitivity_decay, and
    splunk_threat_synthesizer_policy's own sensitivity_decay — none of which are
    enforceable the same way against the hosted API.
  - Everything confirmed for the other demos' hosted mode should still apply
    unchanged (agent_id required unconditionally, agents start "draft" and need
    explicit approval, GET /v1/audit/sessions/{id} needs the Admin key not the
    Evaluate key) but hasn't been separately re-verified for this demo specifically.
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

    Needs both keys, not just the Evaluate one — confirmed live (for the other 4
    demos; see this module's docstring on why that hasn't been separately re-verified
    here): GET /v1/audit/sessions/{id} returns 403 Forbidden with an Evaluate-scoped
    key (only POST /v1/context/evaluate accepts it); the Admin key is required to
    read the trail back. Evaluate-only calls (.protect()) still use the evaluate key,
    not the admin one, to match how this demo is meant to run day to day.
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
    "demo_splunk_" prefix this demo uses) if they need guaranteed content, since this
    function only checks for a name match, not content equality.

    `spec` is passed straight through as the rest of CreatePolicyRequest's body
    (allowed_sources/denied_sources/allowed_tasks/denied_tasks/max_sensitivity/
    task_bindings/require_task_for_sensitivity/description/...) — no
    permitted_agent_ids, session_ttl_minutes, or sensitivity_decay field exists on
    this endpoint (per institutional_portfolio_review's ipr_saas_guard.py, confirmed
    there against the real OpenAPI schema).
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
    evaluate endpoint's role-scan fallback — risky on a shared trial tenant where
    more than one policy can share an agent_role). Returns {agent_role: agent_id}.

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
