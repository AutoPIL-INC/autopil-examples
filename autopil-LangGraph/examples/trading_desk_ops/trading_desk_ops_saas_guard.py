"""
Hosted AutoPIL SaaS trial mode — a drop-in ContextGuard replacement that calls the
real hosted API (POST /v1/context/evaluate) instead of evaluating policy locally.

Activated automatically when AUTOPIL_ADMIN_KEY and AUTOPIL_EVALUATE_KEY are both set
(see trading_desk_ops_demo.py's guard construction) — same explicit-opt-in pattern as
the other 5 demos in this repo with hosted-mode support. Falls back to the embedded
ContextGuard otherwise, so nothing changes for anyone not opting into a hosted trial.

Named trading_desk_ops_saas_guard.py, not the generic saas_guard.py this pattern
started as — every demo with hosted-mode support has its own uniquely-named module for
exactly this reason: a shared name collides under langgraph dev, since all demos'
graphs load into one process and whichever demo's copy loads first "wins" the
sys.modules slot for every demo (see root CLAUDE.md's module-name-collision note, and
fraud_saas_guard.py's own module docstring for the incident that first surfaced it).

Confirmed live against the real hosted trial tenant (base_url
https://autopil-api.onrender.com):

  - **None of this demo's 7 role names match any pre-seeded policy on the shared
    trial tenant.** Checked GET /v1/policies (112 policies total at verification time)
    against all 7 agent_role values (trading_ops_orchestrator, order_intake_agent,
    allocation_agent, affirmation_matching_agent, settlement_reconciliation_agent,
    exception_investigation_agent, compliance_reporting_agent) — zero matches for any
    of them. Same situation institutional_portfolio_review and splunk_secops hit —
    ensure_policy() below creates 7 dedicated demo_tdo_<role>_policy policies,
    translated field-for-field from policies/financial_services/trading_desk_ops.yaml
    (via trading_desk_ops_demo.py's _hosted_spec_from_local(), which also folds each
    regulation's applicable_rules into the policy that regulation's own how_enforced
    text names — see that function's docstring), rather than assuming a pre-seeded
    match the way fraud_investigation's hosted mode does.
  - **CreatePolicyRequest's schema DOES include a `regulations` field** as of this
    check (confirmed against GET /openapi.json, not assumed) — `[{id, name,
    applicable_rules}]`, unlike what institutional_portfolio_review's and
    splunk_secops's own ensure_policy() docstrings documented when they checked
    (no regulations field existed then). This is a genuine schema change, not a retest
    of an old finding — trading_desk_ops_demo.py's translation passes real
    regulation data through for whichever policies each regulation's how_enforced text
    names, rather than only folding it into the description string.
  - **CreatePolicyRequest still has no permitted_agent_ids, session_ttl_minutes, or
    sensitivity_decay field** — confirmed against the same live OpenAPI schema check,
    same gap every other hosted-mode demo in this repo discloses. This demo's local
    policy just had every one of its 7 roles' session_ttl_minutes set to 1440 (24
    hours) in the prior commit — that cap is NOT enforceable the same way against this
    hosted API version. A session that would auto-expire locally after 24 hours stays
    evaluable indefinitely against the hosted tenant, as long as the bootstrapped
    agent_id stays approved. See DESIGN.md's "Appendix: hosted trial mode" for the
    full disclosure — don't let this read as at-parity with local enforcement.
  - Everything else confirmed for the other 5 demos' hosted mode applies here
    unchanged: agent_id is required unconditionally on every evaluate call; agents are
    created "draft" and need explicit approval before they can evaluate anything;
    GET /v1/audit/sessions/{id} needs the Admin key — an Evaluate-scoped key gets 403
    Forbidden there even though it works fine for POST /v1/context/evaluate.
"""

import json
import time
from pathlib import Path

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
    "demo_tdo_" prefix this demo uses) if they need guaranteed content, since this
    function only checks for a name match, not content equality.

    `spec` is passed straight through as the rest of CreatePolicyRequest's body
    (allowed_sources/denied_sources/allowed_tasks/denied_tasks/max_sensitivity/
    task_bindings/require_task_for_sensitivity/description/regulations/...) — no
    permitted_agent_ids, session_ttl_minutes, or sensitivity_decay field exists on
    this endpoint, confirmed against the real OpenAPI schema for this demo
    specifically, not assumed from an earlier demo's check.
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


def hosted_spec_from_local_policy(policy: dict, regulations: list) -> dict:
    """Translate one policy dict from trading_desk_ops.yaml's already-parsed
    `policies:` list (via autopil.policy_engine.PolicyEngine) into a CreatePolicyRequest
    body ensure_policy() can POST.

    Drops session_ttl_minutes — real on the local policy (set to 1440 on all 7 roles),
    but no field on the hosted schema can carry it (see this module's docstring).
    `industry`/`process_group` are passed through since CreatePolicyRequest does have
    those fields, even though PolicyEngine.__init__ never enforces them either — purely
    descriptive both places.

    `regulations` here is trading_desk_ops.yaml's top-level `regulations:` block (the
    full list, not yet filtered to this policy) — each regulation's `applicable_rules`
    entries are filtered down to the ones whose own `how_enforced` text names this
    policy by name, since that's exactly how the local YAML already documents which
    regulation each policy enforces (see trading_desk_ops.yaml's own regulations:
    block). A regulation contributes nothing to a policy its how_enforced text never
    mentions.
    """
    matched_regulations = []
    for reg in regulations:
        rules = [r for r in reg.get("applicable_rules", []) if policy["name"] in r.get("how_enforced", "")]
        if rules:
            matched_regulations.append({"id": reg["id"], "name": reg["name"], "applicable_rules": rules})

    return {
        "description": policy.get("description"),
        "allowed_sources": policy.get("allowed_sources", []),
        "denied_sources": policy.get("denied_sources", []),
        "max_sensitivity": policy.get("max_sensitivity", "high"),
        "allowed_tasks": policy.get("allowed_tasks", []),
        "denied_tasks": policy.get("denied_tasks", []),
        "require_task_for_sensitivity": policy.get("require_task_for_sensitivity"),
        "task_bindings": policy.get("task_bindings", []),
        "industry": policy.get("industry"),
        "process_group": policy.get("process_group"),
        "regulations": matched_regulations,
    }


_AGENT_ID_CACHE_PATH = Path(__file__).with_name(".trading_desk_ops_agent_ids.json")


def _load_agent_id_cache() -> dict:
    if _AGENT_ID_CACHE_PATH.exists():
        try:
            return json.loads(_AGENT_ID_CACHE_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_agent_id_cache(cache: dict) -> None:
    try:
        _AGENT_ID_CACHE_PATH.write_text(json.dumps(cache, indent=2, sort_keys=True))
    except OSError:
        pass  # best-effort; a missing cache just means re-discovery by role next time


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
    cache = _load_agent_id_cache()
    client = httpx.Client(base_url=base_url.rstrip("/"), headers={"X-API-Key": admin_key}, timeout=15.0)
    result = {}
    cache_dirty = False
    all_agents = None  # fetched lazily, only if at least one role misses the cache

    for role in roles:
        agent = None
        cached_id = cache.get(role)
        if cached_id:
            resp = client.get(f"/v1/agents/{cached_id}")
            if resp.status_code == 200:
                agent = resp.json()
            elif resp.status_code != 404:
                resp.raise_for_status()
            # 404 falls through to rediscovery -- the cached id is stale (agent
            # deleted on the tenant since we last saw it), not a code error.

        if agent is None:
            if all_agents is None:
                all_resp = client.get("/v1/agents", params={"framework": "langgraph"})
                all_resp.raise_for_status()
                all_agents = all_resp.json()
            candidates = [a for a in all_agents if a["agent_role"] == role]
            if len(candidates) == 1:
                agent = candidates[0]
            elif len(candidates) > 1:
                agent = next((a for a in candidates if a.get("owner") == owner_tag), candidates[0])
            else:
                resp = client.post("/v1/agents", json={
                    "agent_role": role, "display_name": role.replace("_", " ").title(),
                    "description": "Registered by the AutoPIL + LangGraph demos "
                                    "(github.com/AutoPIL-INC/autopil-examples)",
                    "owner": owner_tag, "owner_team": owner_team, "framework": "langgraph",
                    "policy_name": policy_name_for(role),
                })
                if resp.status_code == 409:
                    # A concurrent process (another langgraph dev instance starting at
                    # the same moment) created this agent_role between our search and
                    # this POST -- re-fetch rather than raising.
                    retry_resp = client.get("/v1/agents", params={"framework": "langgraph"})
                    retry_resp.raise_for_status()
                    agent = next((a for a in retry_resp.json() if a["agent_role"] == role), None)
                    if agent is None:
                        raise RuntimeError(
                            f"AutoPIL API returned 409 creating agent_role={role!r}, but no "
                            f"existing agent with that role could be found afterward -- a "
                            f"real conflict. Check the hosted tenant manually."
                        ) from None
                else:
                    resp.raise_for_status()
                    agent = resp.json()
            cache[role] = agent["agent_id"]
            cache_dirty = True

        if owner_team is not None and not agent.get("owner_team"):
            # Backfill only, on agents registered before this parameter existed --
            # never overwrite an owner_team a human already set, same
            # don't-fight-dashboard-edits principle as owner above.
            resp = client.put(f"/v1/agents/{agent['agent_id']}", json={"owner_team": owner_team})
            resp.raise_for_status()
            agent = resp.json()
        if agent["status"] != "approved":
            resp = client.patch(f"/v1/agents/{agent['agent_id']}/status", json={"status": "approved"})
            resp.raise_for_status()
            agent = resp.json()
        result[role] = agent["agent_id"]

    if cache_dirty:
        _save_agent_id_cache(cache)
    return result
