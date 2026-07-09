# AML & Compliance — Reasoning-Driven Multi-Agent Demo

Three specialist agents, orchestrated with LangGraph, work five AML cases under a
real AutoPIL policy — split out of `institutional_portfolio_review`, where this
financial-crime-governance workflow sat split across two policy files despite being
one coherent story. See [DESIGN.md](./DESIGN.md) for the full design rationale — this
file is just setup + what to expect.

## What makes this different from a scripted demo

Every role is handed a toolbelt **wider** than what its AutoPIL policy actually
authorizes. Nothing in the code tells a role which of its tools are off-limits — it
finds out the same way a production agent would: it calls a tool, and
`guard.protect()` either returns data or a denial reason. When a denial happens, it's
because the model reasoned its way toward an out-of-scope source on its own, not
because a scripted branch forced it to.

Unlike `fraud_investigation`'s dynamically-routed specialists, every case here runs
the same **fixed sequence** — `aml_investigator` → `kyc_agent` → `compliance_officer`
— since there's no real reason the order would vary for a linear KYC/AML
investigation. What varies case to case is what each role reaches for and whether it
crosses a boundary, not which roles run.

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

No manual agent registration step needed — `agent_id` is mandatory on every guarded
call as of autopil `0.10.0`, so the demo registers all 3 roles as `status="approved"`
agents (`AGENT_IDS` in `aml_compliance_demo.py`) against a real
`SQLiteAgentRegistryStore` on import, idempotently, before the graph runs.

## Run (CLI)

```bash
.venv/bin/python examples/aml_compliance/aml_compliance_demo.py
```

Runs all five cases (AML-001 structuring, AML-002 watchlist false positive, AML-003
stale KYC refresh, AML-004 cross-client audit, AML-005 clean case) back to back,
unattended. Model selection is automatic here — Anthropic if `ANTHROPIC_API_KEY` is
set, otherwise Gemini, then Groq, then Ollama. Each case prints:

- the intake lookup (case reason for review)
- every tool call each role makes, tagged `[ok]` or `[DENIED]`
- each role's finding
- the proposed disposition (rule-based, grounded in the real signal data, not
  LLM-improvised — see DESIGN.md §7.3), auto-approved (no prompts — see
  "Human-in-the-loop review" below)
- the full AutoPIL audit trail per session, pulled from `guard.get_audit_trail()`

Audit events persist to `aml_compliance_audit.db` (SQLite — delete freely between
runs; each run resets session IDs via `_reset_sessions()`).

## Run (live viewer)

The same graph, watched running live in a browser instead of read from console output
afterward.

```bash
# Terminal 1 — serve the graph (from the repo root, i.e. autopil-LangGraph/)
.venv/bin/langgraph dev

# Terminal 2 — the viewer
cd examples/aml_compliance/frontend
npm install
npm run dev
```

Open the printed Vite URL. There are two tabs:

**Description** (opens by default) — what the demo is, a visual flow diagram of the
investigation chain (intake → investigator → KYC → compliance → human review →
disposition), each role's actual AutoPIL policy (allowed/denied sources, max
sensitivity, session TTL — mirrored from
`policies/financial_services/aml_compliance.yaml`, not invented for display), the
regulations it maps to, and a summary of all 5 cases. Read-only reference, no live
connection to the server.

**Execution** — the live run:

1. **Pick a model** from the dropdown — Ollama (local) is the default; Gemini, Claude,
   and Groq are the other options. Whichever you pick must be configured
   server-side, or the run fails immediately with a clear error banner.
2. **Pull a case from the queue** (AML-001 through AML-005) to start an investigation.
3. **Watch the feed** populate live: green rows for allowed tool calls, red for denied
   (with the AutoPIL denial reason inline), plus the routing event and each role's
   finding as they stream in.
4. **Review the disposition** — before it's finalized, the run pauses and shows a
   review panel with the proposed action. Click **Approve** to accept it, or
   **Override…** to pick a different outcome (with optional notes).

This talks to `langgraph dev`'s local API server (`http://localhost:2024` by default,
shared with the other 3 demos — `assistantId: "aml_compliance"` in
`ExecutionTab.tsx` is what picks this graph) via `@langchain/langgraph-sdk`'s
`useStream()`.

### Choosing a model

Both the CLI and the live viewer go through one `_make_llm(provider)` function. The
CLI always calls it with `provider=""` — auto-picks the first of Anthropic, Gemini,
Groq, then Ollama that's configured. The live viewer's dropdown sets `provider`
explicitly per run, threaded through `AMLCaseState["provider"]`.

**Ollama's `bind_tools()` documents that `tool_choice` is ignored** — but unlike
`fraud_investigation`/`client_analysis`, this demo has no forced-tool-choice call to
begin with (see DESIGN.md §2), so that caveat doesn't apply here at all. Each role's
`run_tool_loop()` call just needs the model to eventually call `submit_finding`,
which it's nudged toward the same way every other demo in this repo handles it.

Default Ollama model: `qwen2.5:7b` — the same model verified live across this repo's
other 3 demos to reliably use tools; not re-verified independently for this demo
beyond the CLI runs in DESIGN.md §10.

### Human-in-the-loop review

Before the final disposition is written, `decision_node` pauses via LangGraph's
`interrupt()` and waits for a compliance reviewer to Approve or Override it, with
optional notes. The CLI stays fully unattended; the interactive review only happens in
the browser. `aml_compliance_demo.py:graph` (exposed to `langgraph dev`) and the graph
`run_case()` builds for the CLI are compiled differently for the same reason as every
other demo here: `interrupt()` needs a checkpointer, but `langgraph dev` manages
persistence itself and refuses to load a graph pre-compiled with one.

## What to expect

- **Denials should show up in most runs** — each role's toolbelt includes 1-2 sources
  its policy denies or doesn't authorize for the task at hand, and the case briefs are
  written to make reaching for that data plausible. But this is genuinely the model's
  call each run — if a run comes back with zero denials, that's a valid outcome, not
  a bug.
- **Three distinct enforcement paths are exercisable**: `task_bindings` purpose
  limitation (`aml_investigator` reaching for `identity_records` under
  `pattern_detection`, which isn't in that task's permitted sources), plain
  `denied_sources` (`kyc_agent` reaching for `risk_models`, explicitly denied), and the
  plain `allowed_sources` gap (`kyc_agent` reaching for `transaction_history`, never
  listed either way for that role).
- **The *proposed* disposition always matches the case's ground truth** in
  `aml_case_data.py` (`get_expected_outcome`) regardless of which denials occurred
  along the way — verified live across two full 5-case runs (DESIGN.md §10). The
  *final* disposition can still differ if a human reviewer overrides it in the live
  viewer; the CLI always auto-approves, so proposed and final match there.
- **No escalation or re-routing path exists** — unlike `fraud_investigation`'s
  orchestrator re-route-after-denial or `client_analysis`'s tiered escalation, every
  case runs the same fixed 3-role sequence start to finish (see DESIGN.md §11).

## Files

| File | What it is |
|---|---|
| `DESIGN.md` | Design rationale — why this demo exists, the reasoning-driven design approach, what was split out of `institutional_portfolio_review` and why |
| `aml_case_data.py` | Fixture data — 5 accounts, 5 AML cases mixed severity, plus the underlying transaction/watchlist/identity/audit tables |
| `policies/financial_services/aml_compliance.yaml` | The consolidated 3-role AutoPIL policy matrix |
| `aml_compliance_demo.py` | The demo itself |
| `../../langgraph.json` | Exposes `aml_compliance_demo.py:graph` to `langgraph dev` for the live viewer, alongside the other 3 demos |
| `frontend/` | Vite + React + TypeScript live audit-trail feed, model selector, and compliance-review panel, via `@langchain/langgraph-sdk` |

## Known constraints (see DESIGN.md for the full list)

- `ContextGuard.protect()` is embedded-only — this runs against local SQLite, not a
  real hosted AutoPIL instance. Hosted SaaS trial mode isn't wired for this demo yet
  (see DESIGN.md §3) — `fraud_investigation`/`client_analysis` both have it if you want
  to see the pattern.
- Non-determinism is a property of this demo, not a defect — a run with zero denials
  is a legitimate outcome, just a less interesting one to watch.
