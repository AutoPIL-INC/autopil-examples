# Client Analysis — Reasoning-Driven Multi-Agent Demo

Three roles — junior analyst, senior analyst, wealth advisor — share the exact same
toolbelt against simulated Databricks Unity Catalog data, orchestrated with LangGraph,
under a real AutoPIL policy, to work client analysis requests (market research, credit
review, wealth planning). See [DESIGN.md](./DESIGN.md) for the full design rationale —
this file is just setup + what to expect.

## What makes this different from a scripted demo

Every role is handed the **same 8 tools** — one per simulated Unity Catalog table —
regardless of what its AutoPIL policy actually authorizes. Nothing in the code
restricts a role's toolbelt; policy, not the tool layer, decides what succeeds. An
orchestrator reads a natural-language business request and decides which role should
handle it and what task/purpose (`task_type`) it falls under — a real model decision,
not a lookup table. When a denial happens, it's because the assigned role reasoned its
way toward a source its task doesn't cover.

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

You need **one** of these five set up (having several is fine too — see "Choosing a
model" below):

| Provider | Env var | Cost |
|---|---|---|
| AWS Bedrock | `AWS_BEDROCK_MODEL_ID` (+ AWS credentials) | Paid — requires AWS account + Bedrock model access enabled |
| Google Gemini | `GOOGLE_API_KEY` | Free — get a key at https://aistudio.google.com/apikey |
| Anthropic Claude | `ANTHROPIC_API_KEY` | Paid — requires Anthropic API credits |
| Groq | `GROQ_API_KEY` | Free — get a key at https://console.groq.com/keys |
| Ollama | *(none — local)* | Free — needs `ollama serve` running and a model pulled |

No manual agent registration step needed — `agent_id` is mandatory on every guarded call
as of autopil `0.10.0`, so the demo registers all 4 roles (orchestrator + 3) as
`status="approved"` agents (`AGENT_IDS` in `client_analysis_demo.py`) against a
real `SQLiteAgentRegistryStore` on import, idempotently, before the graph runs.

## Run (CLI)

```bash
.venv/bin/python examples/client_analysis/client_analysis_demo.py
```

Runs all three requests (GOV-001 market outlook memo, GOV-002 credit exposure review,
GOV-003 retirement plan update) back to back, unattended. Model selection is automatic
here — Bedrock if `AWS_BEDROCK_MODEL_ID` is set, then Anthropic, then Gemini, then Groq,
then Ollama — see "Choosing a model" below. Each request prints:

- the orchestrator's role/task assignment and reasoning
- every tool call the assigned role makes, tagged `[ok]` or `[DENIED]`
- the orchestrator's escalation decision if the role was blocked
- the outcome classification (completed / completed with governance intervention /
  blocked / escalated then blocked), grounded in the actual audit trail — not the
  model's self-report alone (see "What to expect" below)
- the full AutoPIL audit trail per session, pulled from `guard.get_audit_trail()`

Audit events persist to `client_analysis_audit.db` (SQLite — delete freely
between runs; each run resets session IDs via `_reset_sessions()`).

## Run (live viewer)

The same graph, watched running live in a browser instead of read from console output
afterward.

```bash
# Terminal 1 — serve the graph (from the repo root, i.e. autopil-LangGraph/)
.venv/bin/langgraph dev

# Terminal 2 — the viewer
cd examples/client_analysis/frontend
npm install
npm run dev
```

Open the printed Vite URL (`http://localhost:5173` — if the fraud investigation demo's
frontend is also running, Vite will pick the next free port instead). There are two
tabs:

**Description** (opens by default) — what the demo is, an orchestration flow diagram,
each role's actual AutoPIL policy (allowed/denied sources, max sensitivity, session
TTL — mirrored from `policies/financial_services/client_analysis.yaml`, not
invented for display), the regulations it maps to, and a summary of all 3 requests.
Read-only reference, no live connection to the server.

**Execution** — the live run:

1. **Pick a model** from the dropdown — Ollama (local) is the default; Bedrock, Gemini,
   Claude, and Groq are the other options. Whichever you pick must be configured
   server-side, or the run fails immediately with a clear error banner.
2. **Pick a request** (GOV-001 through GOV-003) to start a run.
3. **Watch the feed** populate live: green rows for allowed tool calls, red for denied
   (with the AutoPIL denial reason inline), plus the routing decision and the role's
   finding as they stream in.
4. **Read the outcome banner** once the run finishes — which role(s) handled it, the
   assigned `task_type`, and the classification of what happened.

This talks to `langgraph dev`'s local API server (`http://localhost:2024` by default,
shared with the fraud investigation demo — `assistantId: "client_analysis"` in
`ExecutionTab.tsx` is what picks this graph) via `@langchain/langgraph-sdk`'s
`useStream()`.

### Choosing a model

Both the CLI and the live viewer go through one `_make_llm(provider)` function. The CLI
always calls it with `provider=""` — auto-picks the first of Bedrock, Anthropic, Gemini,
Groq, then Ollama that's configured, in that order. The live viewer's dropdown sets
`provider` explicitly per run, threaded through `GovernanceState["provider"]`.

**Bedrock is opt-in via `AWS_BEDROCK_MODEL_ID`**, not ambient AWS credential detection —
setting it is what tells the demo to use Bedrock; having unrelated AWS credentials
configured on your machine for something else doesn't trigger it. You'll also need
model access enabled for that model ID in the Bedrock console (per-account, per-region).

All five providers accept the same tool-schema dicts used throughout this file — with
one caveat verified directly against the installed `langchain-aws` source: forcing a
specific tool via `tool_choice=<name>` works for Anthropic-on-Bedrock models, but
**raises `ValueError` at `bind_tools()` time** for models whose
`supports_tool_choice_values` doesn't include `"tool"` (e.g. Llama-family Bedrock
models) — a different failure mode than Ollama's silent ignore (Ollama's `bind_tools()`
documents that `tool_choice` is just ignored). `_bind_forced()` catches both cases and
falls back to unforced binding, and `orchestrator_node`/`orchestrator_review_node`
still check `if response.tool_calls` before indexing into it either way.

**Ollama quality is model-dependent — tested, not guessed**, same finding as the fraud
investigation demo. The default is `qwen2.5:7b`; smaller models like `llama3.2` tend to
skip tool calls entirely.

### A note on trusting the model's self-report

`decision_node` does **not** take a role's self-reported `outcome` (`COMPLETED`/
`BLOCKED`) at face value — live-tested with Ollama's `qwen2.5:7b`, which once claimed
`COMPLETED` immediately after every single tool call in its run had been denied.
`decision_node` cross-checks against the real audit trail (did the role get any `ALLOW`
at all) before trusting a `COMPLETED` claim, falling back to a `BLOCKED`-family
classification otherwise.

## What to expect

- **Denials should show up in most runs** — every role's toolbelt includes sources its
  policy denies or restricts by task, and the request briefs are written to make
  reaching for that data plausible. But this is genuinely the model's call each run —
  if a run comes back with zero denials, that's a valid outcome, not a bug.
- **Four distinct enforcement paths are exercisable**: `denied_sources` (junior
  analyst/wealth advisor reaching for `customer_pii`), `task_bindings` purpose
  limitation (senior analyst's `customer_pii` access is allowed generally, but not for
  `credit_analysis`), the plain `allowed_sources` gap (junior/wealth advisor's toolbelt
  includes sources outside their `allowed_sources` list entirely), and the sensitivity
  ceiling (`stress_test_models` is `critical`, senior analyst's cap is `high` —
  see DESIGN.md's non-goals for when this one is and isn't reachable given the current
  3 request briefs).
- **One escalation attempt is possible**: if the assigned role is fully blocked,
  `orchestrator_review_node` can escalate once to `senior_analyst` (the broadest role).
  Escalating doesn't guarantee success — see GOV-003 in DESIGN.md's verification notes,
  where senior_analyst was denied for a different reason after escalation.

## Files

| File | What it is |
|---|---|
| `DESIGN.md` | Design rationale — why this demo exists, the reasoning-driven design approach, open questions |
| `simulated_uc_data.py` | Fixture data — 8 simulated Unity Catalog tables with `sensitivity_level`/`data_classification` tags, plus the 3 governance request briefs |
| `policies/financial_services/client_analysis.yaml` | The 3-role AutoPIL policy matrix |
| `client_analysis_demo.py` | The demo itself |
| `../../langgraph.json` | Exposes `client_analysis_demo.py:graph` to `langgraph dev` for the live viewer, alongside `fraud_investigation` |
| `frontend/` | Vite + React + TypeScript live audit-trail feed and model selector, via `@langchain/langgraph-sdk` |

## Known constraints (see DESIGN.md for the full list)

- `ContextGuard.protect()` is embedded-only — this runs against local SQLite, not a
  real Databricks Unity Catalog workspace or a hosted AutoPIL trial API. See DESIGN.md's
  appendix for what a real-workspace deployment would require.
- Non-determinism is a property of this demo, not a defect — a "clean" run with zero
  denials is a legitimate outcome, just a less interesting one to watch.
