# SOC / Splunk SecOps — Reasoning-Driven Multi-Agent Demo

Five specialist Claude agents, orchestrated with LangGraph, investigate security cases
raised over Splunk data that IBM mainframe tools forward from `z/OS` SMF (System
Management Facility) logs — under a real AutoPIL policy. See [DESIGN.md](./DESIGN.md)
for the full design rationale — this file is just setup + what to expect.

No live Splunk instance is involved anywhere in this demo — every guarded getter reads
from `splunk_secops_data.py`, exactly like every other demo in this repo. That's deliberate:
it demonstrates the governance pattern (`guard.protect()` wrapping data access) without
committing to a real Splunk SDK integration.

## What makes this different from a scripted demo

Each specialist is a real Claude tool-calling loop, and each is handed a toolbelt
**wider** than what its AutoPIL policy actually authorizes. Nothing in the code tells a
specialist which of its tools are off-limits — it finds out the same way a production
agent would: it calls a tool, and `guard.protect()` either returns data or a denial
reason. When a denial happens, it's because the model reasoned its way toward an
out-of-scope source on its own, not because a scripted branch forced it to.

This means denials are **not guaranteed on every run** — see "What to expect" below.

## Setup

From the repo root (`autopil-LangGraph/`) — this demo shares the same `.venv` and
`.env` as every other demo here; no separate setup needed if you've already run one.

```bash
# 1. Create the venv (python3.11) and install dependencies, including AutoPIL from PyPI
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Copy .env.example to .env and set at least one model API key
cp .env.example .env
```

You need **one** of these set: `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `GROQ_API_KEY`, or
a local `ollama serve` with `OLLAMA_MODEL` pulled (defaults to `qwen2.5:7b`) — same
provider chain as `fraud_investigation`. See that demo's README for details on each.

No manual agent registration step needed — the 5 roles are registered as
`status="approved"` agents (`AGENT_IDS` in `splunk_secops_demo.py`) against a real
`SQLiteAgentRegistryStore` on import, idempotently, before the graph runs.

## Run (CLI)

```bash
.venv/bin/python examples/splunk_secops/splunk_secops_demo.py
```

Runs all four cases (SEC-001 routine RACF sweep, SEC-002 active card-authorization
incident, SEC-003 compliance spot-check, SEC-004 general-ledger incident) back to back,
unattended. Each case prints:

- the orchestrator's initial routing decision and reasoning
- every tool call each specialist makes, tagged `[ok]` or `[DENIED]`
- the orchestrator's re-routing reasoning after each specialist finishes
- the threat synthesizer's tool calls
- the proposed disposition (rule-based, not LLM-improvised), auto-approved (no prompts
  — see "Human-in-the-loop review" below)
- the full AutoPIL audit trail per session, pulled from `guard.get_audit_trail()`

Audit events persist to `splunk_secops_audit.db` (SQLite, disposable — delete freely
between runs; each run resets session IDs via `_reset_sessions()`).

## Run (live viewer)

The same graph, watched running live in a browser instead of read from console output
afterward — every specialist's tool call, routing decision, and the final disposition
streams in as it happens, and you get an interactive SOC-review step the CLI skips.

```bash
# Terminal 1 — serve the graph (from the repo root, i.e. autopil-LangGraph/)
.venv/bin/langgraph dev

# Terminal 2 — the viewer
cd examples/splunk_secops/frontend
npm install
npm run dev
```

Open the printed Vite URL (`http://localhost:5173`). There are two tabs:

**Description** (opens by default) — what the demo is, a visual flow diagram of the 5
agents, each agent's actual AutoPIL policy (allowed/denied sources, max sensitivity,
session TTL — mirrored from `policies/SecOps/soc_mainframe_logs.yaml`, not invented for
display), the regulations it maps to, and a summary of all 4 cases. Read-only reference,
no live connection to the server.

**Execution** — the live run: pick a model from the dropdown, pull a case from the
queue, watch the feed populate live (green rows for allowed tool calls, red for denied,
with the AutoPIL denial reason inline), and review the proposed disposition before it's
finalized — Approve or Override with optional notes.

This demo is also wired into the shared `langgraph.json`, so the generic LangGraph
Studio view works too (`https://smith.langchain.com/studio/?baseUrl=http://localhost:2024`,
pick `splunk_secops` from the graph dropdown) — useful for stepping through nodes and
inspecting raw state, as an alternative to the purpose-built viewer above.

### Human-in-the-loop review

Before the final disposition is written, `decision_node` pauses via LangGraph's
`interrupt()` and waits for a SOC reviewer to Approve or Override it, with optional
notes — same pattern as every other demo in this repo. The CLI stays fully unattended
(auto-approves every case); interactive review only happens through the browser.

## What to expect

- **Denials should show up in most runs** — every specialist's toolbelt includes 1-3
  sources its policy denies, and the case briefs are written to make reaching for that
  data plausible. But this is genuinely the model's call each run — if a run comes back
  with zero denials, that's a valid outcome, not a bug.
- **`compliance_reporter` is the clearest denial to watch for** — its policy allows only
  `splunk_index_summery` (index-level retention/health rollups), but its toolbelt also
  offers `get_smf_security_events` and `get_smf_transactions` directly. If the model
  reaches for either "just to double-check," AutoPIL denies it — this is the demo's
  version of "an agent tries to read raw fields it was only supposed to summarize."
- **The session-isolation tool (`get_case_agent_outputs` on `splunk_threat_synthesizer`)**
  is the least likely to get triggered — it requires the model to reach for a second,
  redundant-sounding lookup tool it doesn't obviously need. If you want to see that
  mechanism fire deterministically (not depending on model choice), call it directly:

  ```python
  import sys; sys.path.insert(0, "examples/splunk_secops")
  import splunk_secops_demo as demo

  demo._reset_sessions()
  # claim the session as incident_triage first — session ownership is first-use.
  demo._safe_call(demo._make_getter("incident_triage", "smf_security", demo.SensitivityLevel.HIGH,
                                     "incident_triage", agent_id=demo.AGENT_IDS["incident_triage"],
                                     task_type="incident_investigation"), "MVSP02")
  tools = demo.splunk_threat_synthesizer_tools("SEC-002")
  stolen = next(t for t in tools if t.name == "get_case_agent_outputs")
  print(demo._safe_call(stolen.func, "SEC-002"))
  # {'status': 'denied', 'reason': "... Session '...' is owned by 'incident_triage' —
  #  'splunk_threat_synthesizer' cannot access another agent's context"}
  ```

  This confirms cross-agent session isolation is enforced independent of the source
  policy check — `agent_outputs` is a source `splunk_threat_synthesizer` **is**
  authorized for; the denial here is purely because the session belongs to a different
  role.
- **`get_subject_racf_status` (also on `splunk_threat_synthesizer`) is a role-spoofing
  attempt** — the underlying call uses `splunk_threat_synthesizer`'s own real registered
  `agent_id` but claims `agent_role="security_auditor"` to reach `smf_security` — a
  source `security_auditor_policy` genuinely allows. This tests the registry's role lock
  (`role_not_permitted`), not a source-based denial — proving the claimed `agent_role`
  is validated against the registry's canonical value for that `agent_id`, not trusted
  from the caller. Verified directly (bypassing the LLM) during development — see
  DESIGN.md.
- **The *proposed* disposition is always rule-based**, grounded directly in
  `smf_performance`/`smf_systems`/`smf_security` flags (`decision_node`), regardless of
  which denials occurred along the way or what any specialist's LLM concluded.

## Files

| File | What it is |
|---|---|
| `DESIGN.md` | Design rationale — why this demo exists, the reasoning-driven design approach |
| `splunk_secops_data.py` | Fixture data — 5 mainframe systems, RACF/performance/transaction/systems events, security alerts, pre-compiled agent outputs. SEC-001/002 are the original 2 cases; SEC-003/004 round out the compliance and multi-source-correlation scenarios |
| `policies/SecOps/soc_mainframe_logs.yaml` | The 5-role AutoPIL policy matrix, plus the PCI-DSS/SOX-ITGC/Internal-Security-Policy regulation mapping |
| `splunk_secops_demo.py` | The demo itself |
| `../../langgraph.json` | Exposes `splunk_secops_demo.py:graph` to `langgraph dev` |
| `frontend/` | Vite + React + TypeScript live audit-trail feed, model selector, and SOC-review panel, via `@langchain/langgraph-sdk` |

## Known constraints

- Runs local-only (embedded `ContextGuard.protect()`) by default. Optional hosted
  AutoPIL SaaS trial mode, same auto-detect (`AUTOPIL_ADMIN_KEY` +
  `AUTOPIL_EVALUATE_KEY` both set) as the other 4 demos — see `splunk_saas_guard.py`'s
  module docstring for what's confirmed vs. a known gap (`permitted_agent_ids`/
  `session_ttl_minutes`/`sensitivity_decay` aren't enforceable the same way remotely).
- No live Splunk connection, and none intended — see the top of this file.
- Non-determinism is a property of this demo, not a defect — a "clean" run with zero
  denials is a legitimate outcome, just a less interesting one to watch.
