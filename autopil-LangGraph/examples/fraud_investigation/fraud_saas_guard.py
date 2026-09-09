"""
Hosted AutoPIL SaaS trial mode — a drop-in ContextGuard replacement that calls the
real hosted API (POST /v1/context/evaluate) instead of evaluating policy locally.

Named fraud_saas_guard.py, not the generic saas_guard.py this file started as —
every demo with hosted-mode support had an identically-named saas_guard.py, which
collided under langgraph dev exactly like this repo's other per-demo module-naming
rule warns about (see root CLAUDE.md): whichever demo's graph loaded first "won,"
and every other demo silently imported *that* demo's saas_guard.py instead of its
own. Caught live when institutional_portfolio_review's saas_guard.py (the only copy
with an ensure_policy() function) got shadowed by this file's copy, crashing the
whole langgraph dev server with an ImportError on startup — not a subtle bug.

Activated automatically when AUTOPIL_ADMIN_KEY and AUTOPIL_EVALUATE_KEY are both set
(see fraud_investigation_demo.py's guard construction) — same explicit-opt-in pattern
as client_analysis_demo.py's AWS_BEDROCK_MODEL_ID. Falls back to the embedded
ContextGuard otherwise, so nothing changes for anyone not opting into a hosted trial.

Verified live against a real trial tenant (base_url https://autopil-api.onrender.com,
2026-07-09):
  - POST /v1/context/evaluate requires agent_id unconditionally — an unregistered or
    unapproved agent_id is denied before policy ever runs (denial_type: "identity").
    The local SDK makes agent_id optional depending on the policy; the hosted API
    does not.
  - Agents are created with status "draft" and must be explicitly approved
    (PATCH /v1/agents/{id}/status) before they can evaluate anything.
  - This tenant's pre-seeded financial_services policies already match
    policies/financial_services/fraud_investigation.yaml byte-for-byte for all 5 roles
    used here (allowed/denied sources, tasks, max_sensitivity, task_bindings) — no
    policy translation needed. Confirmed by diffing GET /v1/policies against the local
    YAML directly, not assumed.
  - Some agent_role names exist on more than one policy on a shared trial tenant
    (seen live: "wealth_advisor", "risk_agent", "compliance_agent" each have 2) — the
    evaluate endpoint falls back to a role-scan when an agent has no explicit
    policy_name bound, which can silently bind to the wrong one. bootstrap_agents()
    below always pins policy_name explicitly rather than relying on that fallback.
    None of this demo's 5 roles are affected; client_analysis's wealth_advisor is
    (see its own client_analysis_saas_guard.py copy).
  - GET /v1/audit/sessions/{id} requires the Admin key — an Evaluate-scoped key gets
    403 Forbidden calling it, even though that same key works fine for
    POST /v1/context/evaluate. RemoteContextGuard below needs both keys for exactly
    this reason: evaluate_key for decisions, admin_key for reading the trail back.
  - Known gap, disclosed rather than silently claimed as at-parity: the hosted policy
    schema (GET/POST /v1/policies) has no permitted_agent_ids or sensitivity_decay
    field. transaction_analyst_policy's local permitted_agent_ids restriction (see
    fraud_investigation.yaml) is therefore not enforceable the same way against this
    hosted API version — a call that would be denied locally for using the wrong
    agent identity may succeed remotely as long as the bootstrapped agent_id is
    approved and bound to the right policy.
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


_AGENT_ID_CACHE_PATH = Path(__file__).with_name(".fraud_investigation_agent_ids.json")


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
    evaluate endpoint's role-scan fallback — see the module docstring on why that's
    risky on a shared trial tenant). Returns {agent_role: agent_id}.

    Real incident, 2026-09-08, in two parts. First: this function used to look up
    each agent via a live GET filtered by `owner=owner_tag`. The user edited `owner`
    directly in the AutoPIL dashboard (a completely normal admin action) to a
    business-meaningful label ("Fraud Operations") — the owner-scoped GET then found
    nothing, so bootstrap_agents() tried to recreate all 5 agents, got 409 Conflict
    on every one (they already existed, just under the new owner value), and the
    unhandled exception took down langgraph dev's ENTIRE startup — every graph in
    langgraph.json, not just this one — since module-level bootstrap_agents() calls
    run at graph-import time. Second, worse: the first fix made the 409 path
    self-heal by overwriting `owner` back to `owner_tag` — which silently reverted
    the user's deliberate dashboard edit on every subsequent process start.

    The actual fix: stop using `owner` for lookup at all. `owner`/`owner_team` are
    now written only once, at creation, and never touched again by this function —
    from a human's perspective, editing either field in the dashboard is completely
    safe going forward, and won't be fought or reverted on the next run.

    Agent identity is tracked instead via a small local JSON cache
    (`.fraud_investigation_agent_ids.json`, gitignored, next to this module) mapping
    role -> agent_id. A cache hit is confirmed with a direct `GET /v1/agents/{id}`
    (cheap, and self-heals if that specific agent was ever deleted on the tenant —
    falls through to rediscovery below rather than erroring). A cache miss (fresh
    clone, or a never-before-seen role) searches by `agent_role` alone, tenant-wide —
    if that's ambiguous (more than one agent already has this role; seen live on the
    shared trial tenant for "wealth_advisor"/"risk_agent"/"compliance_agent" — see
    the module docstring), `owner_tag` is used only as a soft tie-breaking hint, not
    a hard filter, never as the primary lookup mechanism.
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
