# Client Analysis — Tiered Review Queue with Human-in-the-Loop Escalation

Three roles — junior analyst, senior analyst, wealth advisor — share the exact same
toolbelt against simulated Databricks Unity Catalog data, orchestrated with LangGraph,
under a real AutoPIL policy. Five customers sit in a review queue; every case starts at
junior_analyst and can progressively escalate through senior_analyst up to
wealth_advisor, with a human reviewing and dispositioning the proposed next action at
**each tier it reaches** — not just once at the end. See [DESIGN.md](./DESIGN.md) for
the full design rationale — this file is just setup + what to expect.

## What makes this different from a scripted demo

Every role is handed the **same 8 tools** — one per simulated Unity Catalog table —
regardless of what its AutoPIL policy actually authorizes. Nothing in the code
restricts a role's toolbelt; policy, not the tool layer, decides what succeeds. Each
tier's agent gathers data with a real tool-calling loop and proposes a concrete
next-best-action for the client (e.g. "SCHEDULE WEALTH PLANNING MEETING"), not a
governance label. A human reviewer then approves it, overrides it with a different
action, or escalates the case to the next tier for a second look. When a denial
happens, it's because a tier reasoned its way toward a source its task doesn't cover.

This means denials — and how far a case escalates — are **not guaranteed on every
run** — see "What to expect" below.

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

Runs all five customers (C001–C005) back to back, unattended. Model selection is
automatic here — Bedrock if `AWS_BEDROCK_MODEL_ID` is set, then Anthropic, then Gemini,
then Groq, then Ollama — see "Choosing a model" below. Each customer prints:

- the intake lookup (reason for review) and every tier the case actually reaches
- every tool call each tier's agent makes, tagged `[ok]` or `[DENIED]`
- each tier's proposed next action and the (auto-)reviewer's decision — approve,
  override, or escalate
- the final disposition — which tier closed the case, the full path of tiers visited,
  and the final action — grounded in the actual audit trail, not any tier's self-report
  alone (see "What to expect" below)
- the full AutoPIL audit trail per session, pulled from `guard.get_audit_trail()`

The CLI auto-approves each tier's review, unattended: it escalates if that tier's own
finding recommended escalation and a next tier exists, otherwise it approves. A single
customer can pause up to 3 times (once per tier) before the run completes — the CLI
loops over however many interrupts a given case produces.

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

**Description** (opens by default) — what the demo is, the tiered escalation flow
diagram, each role's actual AutoPIL policy (allowed/denied sources, max sensitivity,
session TTL — mirrored from `policies/financial_services/client_analysis.yaml`, not
invented for display), the regulations it maps to, and a summary of all 5 customers
in the queue. Read-only reference, no live connection to the server.

**Execution** — the live run:

1. **Pick a model** from the dropdown — Ollama (local) is the default; Bedrock, Gemini,
   Claude, and Groq are the other options. Whichever you pick must be configured
   server-side, or the run fails immediately with a clear error banner.
2. **Pull a customer from the queue** (C001–C005) to start a review.
3. **Watch the feed** populate live: green rows for allowed tool calls, red for denied
   (with the AutoPIL denial reason inline), plus routing and finding events as they
   stream in.
4. **Review each tier the case reaches**: the graph pauses with the tier's proposed
   action and denial history. Approve it, override it with a different action from the
   dropdown, or — if the case hasn't reached wealth_advisor yet — escalate it to the
   next tier. Each resolved tier stays resolved even if the case later pauses again at
   the next tier.
5. **Read the outcome banner** once the run closes — which tier closed the case, the
   full path of tiers visited, and every human decision along the way.

This talks to `langgraph dev`'s local API server (`http://localhost:2024` by default,
shared with the fraud investigation demo — `assistantId: "client_analysis"` in
`ExecutionTab.tsx` is what picks this graph) via `@langchain/langgraph-sdk`'s
`useStream()`.

### Choosing a model

Both the CLI and the live viewer go through one `_make_llm(provider)` function. The CLI
always calls it with `provider=""` — auto-picks the first of Bedrock, Anthropic, Gemini,
Groq, then Ollama that's configured, in that order. The live viewer's dropdown sets
`provider` explicitly per run, threaded through `ClientReviewState["provider"]`.

**Bedrock is opt-in via `AWS_BEDROCK_MODEL_ID`**, not ambient AWS credential detection —
setting it is what tells the demo to use Bedrock; having unrelated AWS credentials
configured on your machine for something else doesn't trigger it. You'll also need
model access enabled for that model ID in the Bedrock console (per-account, per-region).

All five providers accept the same tool-schema dicts used throughout this file — each
tier's `submit_finding` call goes through `run_tool_loop()`'s ordinary (unforced)
`bind_tools()`, same as every other role-agent turn in this demo. There's no
LLM-driven routing decision left to force a specific tool call for — `intake_node`
looks up the tier chain deterministically, and escalation is a human decision via
`interrupt()`, not a model one.

**Ollama quality is model-dependent — tested, not guessed**, same finding as the fraud
investigation demo. The default is `qwen2.5:7b`; smaller models like `llama3.2` tend to
skip tool calls entirely.

### A note on trusting the model's self-report

Live-tested with Ollama's `qwen2.5:7b`: not every model honors a required schema field
strictly. `proposed_action` came back missing/`None` on some turns despite being a
required enum field on `submit_finding` — `_run_role` coerces it to a safe default
(`FLAG FOR COMPLIANCE / RISK REVIEW`, with `recommend_escalation` forced `true`) rather
than letting an invalid action reach the review panel or final disposition.

## What to expect

- **Denials should show up in most runs** — every role's toolbelt includes sources its
  policy denies or restricts by task, and each tier's task is chosen to make reaching
  for that data plausible. But this is genuinely the model's call each run — if a run
  comes back with zero denials, that's a valid outcome, not a bug.
- **Four distinct enforcement paths are exercisable**: `denied_sources` (junior
  analyst/wealth advisor reaching for `customer_pii`), `task_bindings` purpose
  limitation (senior analyst's `customer_pii` access is allowed generally, but not for
  `credit_analysis`), the plain `allowed_sources` gap (junior/wealth advisor's toolbelt
  includes sources outside their `allowed_sources` list entirely), and the sensitivity
  ceiling (`stress_test_models` is `critical`, senior analyst's cap is `high`).
- **How far a case escalates is not guaranteed** — `CLIENT_REVIEWS[customer_id]`'s
  `tier_tasks` says what task a tier *would* work on if reached, but a case only gets
  there if that tier's own finding recommends escalating (or a human chooses to
  escalate anyway) — nothing forces a case designed to reach wealth_advisor to actually
  get there on every run, same non-determinism as everywhere else in this demo.
- **A human reviews every tier a case reaches**, not just the last one. The CLI
  auto-approves (mirroring each tier's own `recommend_escalation` signal); the live
  viewer's reviewer decides for real.

## Hosted AutoPIL SaaS trial mode (optional)

By default this demo runs entirely against the local embedded `ContextGuard` — no
account needed. To run it against a real hosted AutoPIL trial instead:

1. **Start a free trial** at [autopil.ai/trial](https://www.autopil.ai/trial).
2. **Get your keys** — once signed up, go to **Settings** in the dashboard and
   generate two API keys: one with **Admin** scope (used once, to register and
   approve this demo's agents, and to read the audit trail back) and one with
   **Evaluate** scope (used on every runtime decision call).
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
creating new ones each time. This matters more here than it did for the fraud
investigation demo: this tenant has **two** policies named for `wealth_advisor` (one
matching this demo's local policy, one an unrelated generic wealth-demo policy) — the
explicit pin avoids a silent wrong-policy binding. Everything else about the demo —
the CLI, the live viewer, the 5 customers — works identically either way; only where
the actual allow/deny decision comes from changes. See DESIGN.md's "Appendix: hosted
trial mode" for what's verified, including a disclosed gap
(`permitted_agent_ids`/`sensitivity_decay` aren't enforceable the same way against the
hosted API — inherited from fraud_investigation's own verification, same hosted API).

Unset either key (or leave both out of `.env`) to go back to local mode.

## Files

| File | What it is |
|---|---|
| `DESIGN.md` | Design rationale — why this demo exists, the reasoning-driven design approach, open questions |
| `simulated_uc_data.py` | Fixture data — 8 simulated Unity Catalog tables with `sensitivity_level`/`data_classification` tags, plus the 5-customer `CLIENT_REVIEWS` queue |
| `policies/financial_services/client_analysis.yaml` | The 3-role AutoPIL policy matrix |
| `client_analysis_demo.py` | The demo itself |
| `saas_guard.py` | Optional hosted-SaaS-trial guard + agent bootstrap — see "Hosted AutoPIL SaaS trial mode" above |
| `../../langgraph.json` | Exposes `client_analysis_demo.py:graph` to `langgraph dev` for the live viewer, alongside `fraud_investigation` |
| `frontend/` | Vite + React + TypeScript live audit-trail feed and model selector, via `@langchain/langgraph-sdk` |

## Known constraints (see DESIGN.md for the full list)

- `ContextGuard.protect()` is embedded-only — this runs against local SQLite, not a
  real Databricks Unity Catalog workspace or a hosted AutoPIL trial API. See DESIGN.md's
  appendix for what a real-workspace deployment would require.
- Non-determinism is a property of this demo, not a defect — a "clean" run with zero
  denials is a legitimate outcome, just a less interesting one to watch.
