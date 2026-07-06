# Fraud Investigation — Reasoning-Driven Multi-Agent Demo

Five specialist Claude agents, orchestrated with LangGraph, investigate three fraud
cases under a real AutoPIL policy. See [DESIGN.md](./DESIGN.md) for the full design
rationale — this file is just setup + what to expect.

## What makes this different from a scripted demo

Each specialist is a real Claude tool-calling loop, and each is handed a toolbelt
**wider** than what its AutoPIL policy actually authorizes. Nothing in the code tells a
specialist which of its tools are off-limits — it finds out the same way a production
agent would: it calls a tool, and `guard.protect()` either returns data or a denial
reason. When a denial happens, it's because the model reasoned its way toward an
out-of-scope source on its own, not because a scripted branch forced it to.

This means denials are **not guaranteed on every run** — see "What to expect" below.

## Setup

From the repo root:

```bash
# 1. Recreate the venv if needed (python3.11)
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Install AutoPIL core (editable, from the sibling autopil repo)
.venv/bin/pip install -e "<path-to-autopil>/packages/core[langgraph]"

# 3. Make sure ANTHROPIC_API_KEY is set in .env at the repo root
```

No manual agent registration step needed — `agent_id` is mandatory on every guarded call
as of autopil `main`@`485ccb7`, so the demo registers all 5 roles as `status="approved"`
agents (`AGENT_IDS` in `fraud_investigation_demo.py`) against a real `SQLiteAgentRegistryStore`
on import, idempotently, before the graph runs.

## Run

```bash
.venv/bin/python examples/fraud_investigation/fraud_investigation_demo.py
```

Runs all three cases (CASE-001 structuring, CASE-002 account takeover, CASE-003
synthetic identity) back to back. Each prints:

- the orchestrator's initial routing decision and reasoning
- every tool call each specialist makes, tagged `[ok]` or `[DENIED]`
- the orchestrator's re-routing reasoning after each specialist finishes
- the SAR generator's tool calls
- the deterministic final disposition (rule-based, not LLM-improvised — see DESIGN.md §7.4)
- the full AutoPIL audit trail per session, pulled from `guard.get_audit_trail()`

Audit events persist to `fraud_investigation_audit.db` (SQLite, gitignored-equivalent —
delete freely between runs; each run resets session IDs via `_reset_sessions()`).

## Live viewer

The same graph can be watched running live in a browser instead of read from console
output afterward — every specialist's `[ok]`/`[DENIED]` tool call, routing decision, and
the final disposition streams in as it happens.

```bash
# Terminal 1 — serve the graph (from the repo root, i.e. autopil-LangGraph/)
.venv/bin/langgraph dev

# Terminal 2 — the viewer
cd examples/fraud_investigation/frontend
npm install
npm run dev
```

Open the printed Vite URL (usually `http://localhost:5173`), pick a case, and watch the
feed populate. This talks to `langgraph dev`'s local API server (`http://localhost:2024`
by default) via `@langchain/langgraph-sdk`'s `useStream()` — no changes to the CLI path
above; `fraud_investigation_demo.py:graph` (module-level, compiled at import) is exposed
to the server via `langgraph.json`, and every node emits the same events to
`get_stream_writer()` that it prints to the console, so the two are always in sync.

**Human-in-the-loop review**: before the final disposition is written, the run pauses
and waits for a compliance reviewer to Approve or Override it, with optional notes — see
the review panel that appears in the feed once a case reaches its outcome. The CLI stays
fully unattended (`python fraud_investigation_demo.py` auto-approves every case, no
prompts); the interactive review only happens in the browser. This is why
`fraud_investigation_demo.py:graph` (the one exposed to `langgraph dev`) and the graph
`run_case()` builds for the CLI are compiled differently: `interrupt()` needs a
checkpointer to pause/resume, but `langgraph dev` manages persistence itself and refuses
to load a graph pre-compiled with one — so the module-level `graph` has none, and
`run_case()` builds its own per case with an in-memory checkpointer.

## What to expect

- **Denials should show up in most runs** — every specialist's toolbelt includes 1-2
  sources its policy denies (e.g. `transaction_analyst` can see `identity_data`'s tool
  even though its policy forbids the source), and the case briefs are written to make
  reaching for that data plausible. But this is genuinely the model's call each run —
  if a run comes back with zero denials, that's a valid outcome, not a bug.
- **The session-isolation tool (`get_case_agent_outputs` on `sar_generator`) is the
  least likely to get triggered** — it requires the model to reach for a second,
  redundant-sounding lookup tool it doesn't obviously need. If you want to see that
  mechanism fire deterministically (not depending on model choice), call it directly:

  ```python
  import sys; sys.path.insert(0, "examples/fraud_investigation")
  import fraud_investigation_demo as demo

  demo._reset_sessions()
  # claim the session as transaction_analyst first — session ownership is first-use.
  # agent_id is required here too (transaction_analyst_policy.permitted_agent_ids).
  demo._safe_call(demo._make_getter("transaction_analyst", "transaction_history",
                                     demo.SensitivityLevel.MEDIUM, "transaction_analyst",
                                     agent_id=demo.TRANSACTION_ANALYST_AGENT_ID,
                                     task_type="pattern_analysis"), "ACC_8821")
  tools = demo.sar_generator_tools("CASE-001")
  stolen = next(t for t in tools if t.name == "get_case_agent_outputs")
  print(demo._safe_call(stolen.func, "CASE-001"))
  # {'status': 'denied', 'reason': "... Session '...' is owned by 'transaction_analyst' —
  #  'sar_generator' cannot access another agent's context"}
  ```

  This confirms cross-agent session isolation is enforced independent of the source
  policy check — `agent_outputs` is a source `sar_generator` **is** authorized for; the
  denial here is purely because the session belongs to a different role.
- **`get_subject_identity_check` (also on `sar_generator`) is a role-spoofing attempt,
  and triggers far more reliably** than the session-isolation tool above — 6/6 across two
  full runs. The underlying call uses `sar_generator`'s own real registered `agent_id`
  but claims `agent_role="kyc_specialist"` to reach `identity_data` — a source
  `kyc_specialist_policy` genuinely allows, so this tests the registry's role lock
  (`role_not_permitted`), not a source-based denial. This is the live version of the
  gap closed by autopil `main`@`485ccb7` — see DESIGN.md §12 item 4.
- **The *proposed* disposition always matches the case's ground truth** in
  `simulated_data.py` (`get_expected_outcome`) regardless of which denials occurred along
  the way — that's the point of keeping `decision_node`'s rule-based logic deterministic
  rather than LLM-driven. The *final* disposition can still differ from that if a human
  reviewer overrides it in the live viewer (see "Live viewer" above); the CLI always
  auto-approves, so proposed and final match there.

## Files

| File | What it is |
|---|---|
| `DESIGN.md` | Design rationale — why this demo exists, what's different from AutoPIL's original scripted version, open questions |
| `simulated_data.py` | Fixture data, reused as-is from `autopil/examples/fraud_investigation` — 5 accounts, 50 transactions, 3 fraud alerts, KYC records |
| `policies/financial_services/fraud_investigation.yaml` | Otherwise-unmodified copy of the original policy — see the file header for a fix that had to land upstream in `autopil` (`task_type` support on `protect()`) before `require_task_for_sensitivity` could work through the SDK path |
| `fraud_investigation_demo.py` | The demo itself |
| `../../langgraph.json` | Exposes `fraud_investigation_demo.py:graph` to `langgraph dev` for the live viewer |
| `frontend/` | Minimal Vite + React + TypeScript live audit-trail feed, via `@langchain/langgraph-sdk` |

## Known constraints (see DESIGN.md §10-11 for the full list)

- `ContextGuard.protect()` is embedded-only — this runs against local SQLite, not the
  hosted AutoPIL trial API. See DESIGN.md's appendix for what hosted-mode would require.
- Non-determinism is a property of this demo, not a defect — a "clean" run with zero
  denials is a legitimate outcome, just a less interesting one to watch.
