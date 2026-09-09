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


_AGENT_ID_CACHE_PATH = Path(__file__).with_name(".splunk_secops_agent_ids.json")


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

    Agent identity is tracked via a small local JSON cache
    (`.splunk_secops_agent_ids.json`, gitignored) mapping role -> agent_id, not by a
    live GET filtered by `owner`. A cache hit is confirmed with a direct
    `GET /v1/agents/{id}` (self-heals via rediscovery if that specific agent was
    ever deleted). A cache miss searches by `agent_role` alone, tenant-wide;
    `owner_tag` is used only as a soft tie-breaking hint on an ambiguous multi-match,
    never as a hard filter. `owner`/`owner_team` are written once, at creation, and
    never touched again by this function.

    This matters because `owner` used to be the lookup mechanism itself — a real
    incident, 2026-09-08/09, hit `fraud_investigation` and `trading_desk_ops`
    independently (see either module's own docstring for the full incident) when a
    human edited `owner` directly in the AutoPIL dashboard, the owner-scoped GET then
    found nothing, `bootstrap_agents()` tried to recreate every role, got 409
    Conflict on all of them, and the unhandled exception took down `langgraph dev`'s
    entire startup (every graph in `langgraph.json`, not just the edited demo).
    This demo wasn't the one that surfaced the bug, but carried the identical
    owner-based-lookup design and was fixed proactively at the same time, not left
    for its own turn to hit it.
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
