"""
Demonstrates AutoPIL's MCP server as a third governance transport, alongside the
direct-SDK ContextGuard (source_type="sdk") and hosted RemoteContextGuard
(source_type="api") already used by this demo.

get_session_status is the pick here: it's the simplest MCP tool with a guaranteed
non-empty result right after a case runs, since it reads the same audit_log
records the local ContextGuard already wrote during run_case() — just through a
spawned `autopil-mcp` subprocess (stdio) instead of guard.get_audit_trail()'s
direct Python call.

collect_all_session_statuses_via_mcp*() calls get_session_status once per role,
over one shared MCP connection (one subprocess/HTTP connection for all 5 roles,
not five), so the result can stand in for guard.get_audit_trail()'s all-roles
summary — see decision_node()'s audit-source choice in splunk_secops_demo.py.

Three transports:
  - collect_all_session_statuses_via_mcp() spawns `autopil-mcp --policy ... --db
    ...`, same direct-DB access the local ContextGuard uses.
  - collect_all_session_statuses_via_mcp_remote() spawns `autopil-mcp --api-url
    ...` over stdio — proxies the same two tools over HTTP to a hosted tenant.
  - collect_all_session_statuses_via_mcp_http() instead connects to an
    already-running `autopil-mcp --api-url ... --http-port ...` server over
    Streamable HTTP — no per-call subprocess spawn. That server is a standalone,
    separately-run process (like autopil-serve itself), not something this demo
    starts — see the AUTOPIL_MCP_HTTP_URL comment in .env.example for how to run it.

All three proxy the same scoped-down tool set — see
autopil.mcp_server.create_remote_mcp_server()'s docstring for why it's just
evaluate_context/get_session_status rather than all 10.

Requires: pip install "autopil[mcp]" (adds the `mcp` package + httpx).
"""

import asyncio
import json
import os
import shutil
import sys
from typing import Optional

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.client.streamable_http import streamablehttp_client
    _MCP_AVAILABLE = True
except ImportError:
    _MCP_AVAILABLE = False

# Exposed so callers can tell "mcp package not installed" apart from "installed,
# but every session happened to come back empty" before deciding how to report it.
MCP_AVAILABLE = _MCP_AVAILABLE


def _autopil_mcp_command() -> str:
    """Resolve the `autopil-mcp` console script. Prefer PATH, but fall back to the
    directory this interpreter's own executable lives in — pip installs console
    scripts alongside whichever python they were installed for, and a bare
    `.venv/bin/python script.py` invocation (no `source .venv/bin/activate`) never
    puts `.venv/bin` on PATH, even though the script is right there. Confirmed live:
    a fresh shell with only `.venv/bin/python` on PATH raised FileNotFoundError on
    the bare command name until this fallback was added."""
    found = shutil.which("autopil-mcp")
    if found:
        return found
    candidate = os.path.join(os.path.dirname(sys.executable), "autopil-mcp")
    return candidate if os.path.exists(candidate) else "autopil-mcp"


def _parse_session_status(text: str) -> Optional[dict]:
    """get_session_status's success reply is "<sentence>\\n\\n<json>"; its
    no-events reply is a plain "Error: ..." sentence with no JSON at all. Return
    None for the latter (and for any other unparseable reply) rather than raising
    — a session with zero events isn't a failure, just an empty result."""
    start = text.find("{")
    if start == -1:
        return None
    try:
        return json.loads(text[start:])
    except json.JSONDecodeError:
        return None


async def _call_all_statuses(session: "ClientSession", sessions: dict[str, str]) -> dict[str, Optional[dict]]:
    statuses: dict[str, Optional[dict]] = {}
    for role, session_id in sessions.items():
        result = await session.call_tool("get_session_status", arguments={"session_id": session_id})
        statuses[role] = _parse_session_status(result.content[0].text)
    return statuses


async def _collect_via_stdio(server_params: "StdioServerParameters", sessions: dict[str, str]) -> dict[str, Optional[dict]]:
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await _call_all_statuses(session, sessions)


async def _collect_via_http(mcp_url: str, sessions: dict[str, str], agent_id: str) -> dict[str, Optional[dict]]:
    # x-autopil-agent-id: the same header autopil's grpc_authz.py reads for gRPC
    # ext_authz identity resolution (normally injected by an EnvoyFilter from a Pod
    # annotation, not set by a Python client) — set here so a case run through this
    # transport doubles as the wire-compatibility check
    # docs/WIP/agentgateway-integration-plan.md calls for. Harmless to send against
    # a plain `autopil-mcp --http-port` server with no agentgateway/Envoy in front
    # of it — get_session_status's own arguments (session_id) are unaffected either way.
    async with streamablehttp_client(mcp_url, headers={"X-Autopil-Agent-Id": agent_id}) as (read, write, _get_session_id):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await _call_all_statuses(session, sessions)


def collect_all_session_statuses_via_mcp(policy_path: str, audit_db: str, tenant_id: str,
                                          sessions: dict[str, str]) -> dict[str, Optional[dict]]:
    """One role -> session_id per SESSIONS entry, all fetched over a single spawned
    `autopil-mcp --policy ... --db ...` subprocess (local mode)."""
    if not _MCP_AVAILABLE:
        print(f"\n  [mcp]  skipped — `mcp` package not installed (pip install \"autopil[mcp]\")")
        return {}
    server_params = StdioServerParameters(
        command=_autopil_mcp_command(),
        args=["--policy", policy_path, "--db", audit_db, "--tenant-id", tenant_id],
    )
    try:
        return asyncio.run(_collect_via_stdio(server_params, sessions))
    except Exception as e:
        print(f"\n  [mcp]  call failed: {e}")
        return {}


def collect_all_session_statuses_via_mcp_remote(api_url: str, evaluate_key: str, admin_key: str,
                                                 sessions: dict[str, str]) -> dict[str, Optional[dict]]:
    """Same as collect_all_session_statuses_via_mcp(), but proxied over HTTP to a
    hosted tenant (remote/SaaS mode, stdio transport to the local autopil-mcp
    subprocess which itself talks HTTP to the hosted API)."""
    if not _MCP_AVAILABLE:
        print(f"\n  [mcp]  skipped — `mcp` package not installed (pip install \"autopil[mcp]\")")
        return {}
    server_params = StdioServerParameters(
        command=_autopil_mcp_command(),
        args=["--api-url", api_url, "--evaluate-key", evaluate_key, "--admin-key", admin_key],
    )
    try:
        return asyncio.run(_collect_via_stdio(server_params, sessions))
    except Exception as e:
        print(f"\n  [mcp]  call failed: {e}")
        return {}


def collect_all_session_statuses_via_mcp_http(mcp_url: str, sessions: dict[str, str],
                                               agent_id: str) -> dict[str, Optional[dict]]:
    """Same as the other two, but over Streamable HTTP against an already-running
    `autopil-mcp --http-port` server — no per-call subprocess spawn."""
    if not _MCP_AVAILABLE:
        print(f"\n  [mcp]  skipped — `mcp` package not installed (pip install \"autopil[mcp]\")")
        return {}
    try:
        return asyncio.run(_collect_via_http(mcp_url, sessions, agent_id))
    except Exception as e:
        print(f"\n  [mcp]  call failed: {e} — is `autopil-mcp --http-port` running at {mcp_url}?")
        return {}
