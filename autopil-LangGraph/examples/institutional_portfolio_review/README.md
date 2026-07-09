# Institutional Portfolio Review — 11-Role Multi-Agent Demo

One orchestrator plus ten specialists, enforced under **two real AutoPIL policy files
at once**, review institutional client portfolios end to end — research, advisory,
rebalancing, settlement, and compliance. See [DESIGN.md](./DESIGN.md) for the full
design rationale — this file is just setup + what to expect.

## What makes this different from a scripted demo

Every role is handed the exact same toolbelt — all sources across both catalog
schemas — regardless of what its policy actually authorizes. An orchestrator reads a
natural-language review request and classifies it into a review type, which maps to a
real institutional workflow (a sequence of roles doing a real job — research →
advisory → rebalancing → settlement → reporting), not a scripted violation. What each
role reaches for *within* its step stays fully emergent — denials happen when the
model reasons its way toward a source its role or task doesn't cover.

This means denials are **not guaranteed on every run** — see "What to expect" below.

## Setup

From the repo root (`autopil-LangGraph/`):

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Same 5 model providers as the other two demos — see their README for the provider
table. Agent registration is automatic and idempotent, same pattern as
`client_analysis`/`fraud_investigation`.

## Run (CLI)

```bash
.venv/bin/python examples/institutional_portfolio_review/institutional_portfolio_review_demo.py
```

Runs all 5 review requests back to back, unattended. Each prints:

- the orchestrator's review-type classification and the resulting role/task plan
- every tool call each role makes, tagged `[ok]` or `[DENIED]`
- the one escalation path this demo models (fiduciary benchmark → investment analyst)
- the proposed outcome, auto-approved (no prompts — see "Human-in-the-loop review"
  below), grounded in the real audit trail per role, not each role's self-report alone
  (see "A note on trusting the model's self-report" below)
- the full AutoPIL audit trail per session, across both policy files

Audit events persist to `institutional_portfolio_review_audit.db` (SQLite — delete
freely between runs).

## Run (live viewer)

```bash
# Terminal 1 — serve the graph (from the repo root)
.venv/bin/langgraph dev

# Terminal 2 — the viewer
cd examples/institutional_portfolio_review/frontend
npm install
npm run dev
```

Same Description/Execution tab structure as the other two demos. The Description tab
splits policy cards by which file they come from (`portfolio_review_wealth.yaml` vs
`portfolio_review_risk.yaml`). The live viewer also gets an interactive step the CLI
skips — see "Human-in-the-loop review" below.

## Human-in-the-loop review

Before the outcome is finalized, `decision_node` pauses via LangGraph's `interrupt()`
and waits for a supervisor to Approve or Override it, with optional notes — same
mechanism as the fraud investigation demo's compliance review. The CLI stays fully
unattended (auto-approves every request); the interactive review only happens in the
browser. This is also why `institutional_portfolio_review_demo.py:graph` (the one
exposed to `langgraph dev`) and the graph `run_request()` builds for the CLI are
compiled differently: `interrupt()` needs a checkpointer to pause/resume, but
`langgraph dev` manages persistence itself and refuses to load a graph pre-compiled
with one — so the module-level `graph` has none, and `run_request()` builds its own
per request with an in-memory checkpointer.

## The two policy files, and why a role's *file* matters more than its data

`portfolio_review_wealth.yaml` governs the wealth-advisory roles (`portfolio_orchestrator`,
`wealth_advisor`, `investment_analyst`, `kyc_agent`, `macro_analyst`,
`rebalancing_agent`, `report_generator`). `portfolio_review_risk.yaml` governs the
risk/compliance roles (`compliance_officer`, `credit_risk_analyst`, `aml_investigator`,
`settlement_agent`). Which file evaluates a guarded call is a property of the
**calling role**, not the source's catalog schema: `credit_scores`, `loan_history`,
`identity_records`, and `risk_models` all live under `catalog.risk.*`, but `kyc_agent`
(a wealth-file role) reaches them through `wealth_guard`, while `credit_risk_analyst`
(a risk-file role) reaches the *same* sources through `risk_guard` — each evaluated
under that role's own file, independently.

### A note on trusting the model's self-report

`decision_node` does not take a role's self-reported `outcome` at face value — same
fix as `client_analysis`, applied per-role across a whole review. A role only counts
as `COMPLETED` if it both self-reported `COMPLETED` *and* its own audit trail shows at
least one real `ALLOW`.

### A note on toolbelt size

With 32 tools available (every source across both catalogs), Ollama's `qwen2.5:7b`
needs a stronger "conclude now" nudge than the other two demos' smaller toolbelts
required — verified live: without it, the model tends to call most/all tools in one
big batch per turn and never includes `submit_finding`, repeating the same batch
instead of concluding. `run_tool_loop()` here appends an explicit, increasingly urgent
message after every turn without a finding (see `CLAUDE.md` for the full finding).

Review-type role chains are also kept short (max 4 roles — `quarterly_review`'s chain)
rather than the single 6-role chain an earlier version used. Live-tested: shorter
chains converge far more reliably — every extra role in a chain is another chance for
one step to stall, and a 6-role chain compounded that risk badly enough that most runs
ended up only partially complete. All 11 roles are still exercised, just spread across
5 shorter review types instead of 4 longer ones.

## What to expect

- **Denials should show up in most runs**, across all four enforcement paths:
  `denied_sources`, `denied_tasks`, `task_bindings` purpose limitation, and the
  sensitivity ceiling (`investment_analyst_policy` is capped at `critical` specifically
  so its one genuinely-authorized critical-sensitivity source —
  `other_client_portfolios` — isn't accidentally blocked by its own ceiling; every
  other source it might reach for stays governed by `allowed_sources`/`task_bindings`).
- **The fiduciary-boundary escalation is the signature scenario** (PORT-002):
  `wealth_advisor` is denied `other_client_portfolios` outright (fiduciary wall), the
  orchestrator escalates once to `investment_analyst`, which succeeds at the same
  source under a `benchmarking` task — the same mechanism, `guard.protect()`,
  producing opposite outcomes for two different roles on the same data.
- **Roles can end a step self-reporting `BLOCKED` even after real successful calls** —
  live-tested: a role sometimes judges it doesn't have *enough* of what it needs even
  after getting real data back, and stops rather than gathering more. This is a
  legitimate, conservative model judgment, not a bug — `decision_node` still reports it
  accurately (a completed step needs both a `COMPLETED` self-report and real data).

## Hosted AutoPIL SaaS trial mode (optional)

By default this demo runs entirely against the local embedded `ContextGuard`s — no
account needed. To run it against a real hosted AutoPIL trial instead:

1. **Start a free trial** at [autopil.ai/trial](https://www.autopil.ai/trial).
2. **Get your keys** — go to **Settings** in the dashboard and generate an **Admin**
   key and an **Evaluate** key.
3. **Set both in `.env`** (see `.env.example`) — every run then automatically
   switches to calling the real hosted API instead of the local one:

```bash
AUTOPIL_ADMIN_KEY=your-admin-key-here
AUTOPIL_EVALUATE_KEY=your-evaluate-key-here
# AUTOPIL_API_URL=https://autopil-api.onrender.com   # override if your trial lives elsewhere
```

This demo needed one thing the other three didn't: none of its 8 roles' pre-seeded
policies on a shared trial tenant actually match (they use plain source names; this
demo's own policy uses `catalog.wealth.*`/`catalog.risk.*` prefixed names), so on
first run it creates 8 dedicated `demo_ipr_<role>_policy` policies via
`POST /v1/policies`, translated field-for-field from the two local YAML files — no
change to this demo's own source naming required. `wealth_guard`/`risk_guard`
collapse into the same remote guard instance in SaaS mode, since the hosted API is
one tenant regardless of which local file a policy conceptually belongs to. See
`ipr_saas_guard.py`'s module docstring for what's verified, including a cross-demo
agent/policy naming collision this demo's `wealth_advisor` role hit against
`client_analysis`'s role of the same name (fixed with a demo-specific tag).

Unset either key (or leave both out of `.env`) to go back to local mode.

## Files

| File | What it is |
|---|---|
| `DESIGN.md` | Design rationale — what's real vs. aspirational in the source this was adapted from, the two-policy-file design, open questions |
| `portfolio_review_uc_data.py` | Fixture data — two simulated Unity Catalog schemas (`catalog.wealth.*`, `catalog.risk.*`), 3 institutional clients, plus the review-request briefs |
| `policies/financial_services/portfolio_review_wealth.yaml` | Wealth-advisory policy matrix (6 roles) |
| `policies/financial_services/portfolio_review_risk.yaml` | Risk/compliance policy matrix (2 roles: `credit_risk_analyst`, `settlement_agent`) |
| `institutional_portfolio_review_demo.py` | The demo itself |
| `ipr_saas_guard.py` | Optional hosted-SaaS-trial guard + policy/agent bootstrap — see "Hosted AutoPIL SaaS trial mode" above |
| `../../langgraph.json` | Exposes `institutional_portfolio_review_demo.py:graph` alongside the other demos |
| `frontend/` | Vite + React + TypeScript live audit-trail feed and model selector |

## Known constraints (see DESIGN.md for the full list)

- `ContextGuard.protect()` is embedded-only — local SQLite, not a real Databricks
  Unity Catalog workspace. A hosted AutoPIL trial API is supported as an optional
  mode (see above).
- `require_principal_entitlements` (present in the real policy files this was adapted
  from) is not ported — it only evaluates via the hosted REST API's principal-claims
  layer, which the embedded SDK path this demo uses never populates. See DESIGN.md.
- Non-determinism is a property of this demo, not a defect.
