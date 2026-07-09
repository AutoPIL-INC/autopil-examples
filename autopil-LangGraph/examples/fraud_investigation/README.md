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

From the repo root (`autopil-LangGraph/`):

```bash
# 1. Create the venv (python3.11) and install dependencies, including AutoPIL from PyPI
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Copy .env.example to .env and set at least one model API key
cp .env.example .env
```

You need **one** of these four set up (having several is fine too — see "Choosing a
model" below):

| Provider | Env var | Cost |
|---|---|---|
| Google Gemini | `GOOGLE_API_KEY` | Free — get a key at https://aistudio.google.com/apikey |
| Anthropic Claude | `ANTHROPIC_API_KEY` | Paid — requires Anthropic API credits |
| Groq | `GROQ_API_KEY` | Free — get a key at https://console.groq.com/keys |
| Ollama | *(none — local)* | Free — needs `ollama serve` running and a model pulled |

No manual agent registration step needed — `agent_id` is mandatory on every guarded call
as of autopil `0.10.0`, so the demo registers all 5 roles as `status="approved"`
agents (`AGENT_IDS` in `fraud_investigation_demo.py`) against a real `SQLiteAgentRegistryStore`
on import, idempotently, before the graph runs.

## Run (CLI)

```bash
.venv/bin/python examples/fraud_investigation/fraud_investigation_demo.py
```

Runs all five cases (CASE-001 structuring, CASE-002 account takeover, CASE-003 synthetic
identity, CASE-004 elder financial exploitation, CASE-005 money mule / check kiting) back
to back, unattended. Model selection is automatic here —
Anthropic if `ANTHROPIC_API_KEY` is set, otherwise Gemini — see "Choosing a model"
below for how the live viewer differs. Each case prints:

- the orchestrator's initial routing decision and reasoning
- every tool call each specialist makes, tagged `[ok]` or `[DENIED]`
- the orchestrator's re-routing reasoning after each specialist finishes
- the SAR generator's tool calls
- the proposed disposition (rule-based, not LLM-improvised — see DESIGN.md §7.4),
  auto-approved (no prompts — see "Human-in-the-loop review" below)
- the full AutoPIL audit trail per session, pulled from `guard.get_audit_trail()`

Audit events persist to `fraud_investigation_audit.db` (SQLite, gitignored-equivalent —
delete freely between runs; each run resets session IDs via `_reset_sessions()`).

## Run (live viewer)

The same graph, watched running live in a browser instead of read from console output
afterward — every specialist's tool call, routing decision, and the final disposition
streams in as it happens, and you get an interactive compliance-review step the CLI
skips.

```bash
# Terminal 1 — serve the graph (from the repo root, i.e. autopil-LangGraph/)
.venv/bin/langgraph dev

# Terminal 2 — the viewer
cd examples/fraud_investigation/frontend
npm install
npm run dev
```

Open the printed Vite URL (`http://localhost:5173`). There are two tabs:

**Description** (opens by default) — what the demo is, a visual flow diagram of the 5
agents (orchestrator → 3 specialists → SAR generator → human review → disposition), each
agent's actual AutoPIL policy (allowed/denied sources, max sensitivity, session TTL —
mirrored from `policies/financial_services/fraud_investigation.yaml`, not invented for
display), the regulations it maps to, and a summary of all 5 cases. Read-only reference,
no live connection to the server.

**Execution** — the live run:

1. **Pick a model** from the dropdown — Ollama (local) is the default; Gemini, Claude,
   and Groq are the other options. Whichever you pick must be configured server-side
   (API key in `.env`, or `ollama serve` running with the model pulled), or the run
   fails immediately with a clear error banner instead of hanging — see "Choosing a
   model" below.
2. **Pick a case** (CASE-001 through CASE-005) to start a run.
3. **Watch the feed** populate live: green rows for allowed tool calls, red for denied
   (with the AutoPIL denial reason inline), plus routing decisions and specialist
   findings as they stream in.
4. **Review the disposition** — before it's finalized, the run pauses and shows a review
   panel with the proposed action. Click **Approve** to accept it, or **Override…** to
   pick a different outcome (with optional notes) — the disposition banner at the top
   will show whichever you chose, alongside the AutoPIL audit trail totals.

This talks to `langgraph dev`'s local API server (`http://localhost:2024` by default)
via `@langchain/langgraph-sdk`'s `useStream()`. `fraud_investigation_demo.py:graph`
(module-level, compiled at import) is exposed to the server via `langgraph.json`, and
every node emits the same events to `get_stream_writer()` that it prints to the console,
so the CLI and the live viewer are always showing the same underlying run.

### Choosing a model

Both the CLI and the live viewer go through one `_make_llm(provider)` function. The CLI
always calls it with `provider=""` — auto-picks the first of Anthropic, Gemini, Groq,
then Ollama that's configured, in that order (Ollama last since it needs no key, just a
local server, so it's the fallback of last resort). The live viewer's dropdown sets
`provider` explicitly per run (`"anthropic"`, `"gemini"`, `"groq"`, or `"ollama"`),
threaded through `InvestigationState["provider"]` to every node that calls the LLM.

All four accept the same tool-schema dicts used throughout this file — with one caveat:
**Ollama's `bind_tools()` documents that `tool_choice` is ignored**, so it can't be forced
to call a specific tool the way `orchestrator_node`'s routing decision and
`orchestrator_review_node`'s re-routing decision expect. Both nodes check
`if response.tool_calls` before indexing into it and fall back to a sane default
(route to all specialists; stop routing and move to `sar_generator`) if the model didn't
call the tool at all — otherwise a local model skipping the tool call would crash the run
instead of just degrading.

**Ollama quality is model-dependent — tested, not guessed.** The default is
`qwen2.5:7b` (`ollama pull qwen2.5:7b`), verified live to gather data properly: all
3 specialists made real tool calls, including 3 legitimate AutoPIL denials on over-scope
reaches. The smaller `llama3.2` (3B) was tried first and failed this same test —
2 of 3 specialists skipped tool calls entirely and jumped straight to a finding with no
data gathered, which defeats the point of the demo (AutoPIL has nothing to enforce if the
model never asks for data). If `qwen2.5:7b` still isn't reliable enough on your machine,
try `llama3.1:8b` or a larger `qwen2.5` variant via `OLLAMA_MODEL` in `.env`. Anthropic
and Gemini did not show this problem in testing.

The live viewer's dropdown defaults to Ollama (it's the one that can't rate-limit or
503 on you — see below), followed by Gemini, Claude, then Groq.

### Human-in-the-loop review

Before the final disposition is written, `decision_node` pauses via LangGraph's
`interrupt()` and waits for a compliance reviewer to Approve or Override it, with
optional notes. The CLI stays fully unattended (auto-approves every case, no prompts);
the interactive review only happens in the browser. This is also why
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
  (`role_not_permitted`), not a source-based denial — proving the claimed `agent_role`
  is validated against the registry's canonical value for that `agent_id`, not trusted
  from the caller.
- **The *proposed* disposition always matches the case's ground truth** in
  `simulated_data.py` (`get_expected_outcome`) regardless of which denials occurred along
  the way — that's the point of keeping `decision_node`'s rule-based logic deterministic
  rather than LLM-driven. The *final* disposition can still differ from that if a human
  reviewer overrides it in the live viewer (see "Human-in-the-loop review" above); the
  CLI always auto-approves, so proposed and final match there.

## Hosted AutoPIL SaaS trial mode (optional)

By default this demo runs entirely against the local embedded `ContextGuard` — no
account needed. To run it against a real hosted AutoPIL trial instead:

1. **Start a free trial** at [autopil.ai/trial](https://www.autopil.ai/trial).
2. **Get your keys** — once signed up, go to **Settings** in the dashboard and
   generate two API keys: one with **Admin** scope (used once, to register and
   approve this demo's agents) and one with **Evaluate** scope (used on every
   runtime decision call).
3. **Set both in `.env`** (see `.env.example`) — every run then automatically
   switches to calling the real hosted API instead of the local one:

```bash
AUTOPIL_ADMIN_KEY=your-admin-key-here
AUTOPIL_EVALUATE_KEY=your-evaluate-key-here
# AUTOPIL_API_URL=https://autopil-api.onrender.com   # override if your trial lives elsewhere
```

On first run, `bootstrap_agents()` (in `saas_guard.py`) registers and approves one
agent per role on your tenant, explicitly bound to the matching policy — idempotent,
so re-running (or `langgraph dev`'s hot-reload) reuses the same agents rather than
creating new ones each time. Everything else about the demo — the CLI, the live
viewer, the 5 cases — works identically either way; only where the actual
allow/deny decision comes from changes. See DESIGN.md's "Appendix: hosted trial mode"
for what's verified to work identically and one disclosed gap (`permitted_agent_ids`/
`sensitivity_decay` aren't enforceable the same way against the hosted API).

Unset either key (or leave both out of `.env`) to go back to local mode.

## Files

| File | What it is |
|---|---|
| `DESIGN.md` | Design rationale — why this demo exists, the reasoning-driven design approach, open questions |
| `simulated_data.py` | Fixture data — 7 accounts, 72 transactions, 5 fraud alerts, KYC records. CASE-001/002/003 cover structuring, account takeover, and synthetic identity; CASE-004 (elder financial exploitation) and CASE-005 (money mule / check kiting) were added later |
| `policies/financial_services/fraud_investigation.yaml` | The 5-role AutoPIL policy matrix — see the file header for a fix that had to land upstream in `autopil` (`task_type` support on `protect()`) before `require_task_for_sensitivity` could work through the SDK path |
| `fraud_investigation_demo.py` | The demo itself |
| `saas_guard.py` | Optional hosted-SaaS-trial guard + agent bootstrap — see "Hosted AutoPIL SaaS trial mode" above |
| `../../langgraph.json` | Exposes `fraud_investigation_demo.py:graph` to `langgraph dev` for the live viewer |
| `frontend/` | Vite + React + TypeScript live audit-trail feed, model selector, and compliance-review panel, via `@langchain/langgraph-sdk` |

## Known constraints (see DESIGN.md §10-11 for the full list)

- `ContextGuard.protect()` is embedded-only — this runs against local SQLite, not the
  hosted AutoPIL trial API. See DESIGN.md's appendix for what hosted-mode would require.
- Non-determinism is a property of this demo, not a defect — a "clean" run with zero
  denials is a legitimate outcome, just a less interesting one to watch.
