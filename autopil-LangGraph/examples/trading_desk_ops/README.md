# Trading Desk Ops (Equities) — Reasoning-Driven Multi-Agent Demo

Seven specialist Claude agents, orchestrated with LangGraph, handle a block equity
order (a distinct ticker per scenario — MSFT, NVDA, AAPL, AMZN, GOOG) at Meridian
Bank's Trading Unit — allocation across client sub-accounts, same-day
affirmation, DTCC/NSCC settlement verification, and (when something breaks) exception
investigation — inside a T+1 settlement window, under a real AutoPIL policy. See
[DESIGN.md](./DESIGN.md) for the full design rationale, including why no existing
autopil policy stub matched this domain — this file is just setup + what to expect.

No live OMS/EMS, custodian, or DTCC/NSCC feed is involved anywhere in this demo — every
guarded getter reads from `trading_desk_ops_data.py`, exactly like every other demo in
this repo.

This demo covers only the **Equities** sub-domain of a planned 5-sub-domain build (see
`/TRADING_OPS_ROADMAP.md`) — FX, Commodities, Fixed Income, and International are not
built yet. `TRADING_DOMAINS` is shaped so they can be added later as sibling entries
without restructuring the graph (see DESIGN.md §4).

## What makes this different from a scripted demo

Each specialist is a real Claude tool-calling loop, and each is handed a toolbelt
**wider** than what its AutoPIL policy actually authorizes. Nothing in the code tells a
specialist which of its tools are off-limits — it finds out the same way a production
agent would: it calls a tool, and `guard.protect()` either returns data or a denial
reason. When a denial happens, it's because the model reasoned its way toward an
out-of-scope source on its own, not because a scripted branch forced it to.

**The trigger classification step is a real LLM call, not a fixed branch** — unlike
`quality_control`'s fixed-first-step design, `trading_ops_orchestrator` genuinely
decides which specialist runs first based on the trigger type (see "What to expect"
below for EQ-004, the scenario that proves this).

This means denials — and which specialist runs first — are **not guaranteed identical
on every run** — see "What to expect" below.

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
provider chain as `fraud_investigation`/`aml_compliance`.

No manual agent registration step needed — the 7 roles are registered as
`status="approved"` agents (`AGENT_IDS` in `trading_desk_ops_demo.py`) against a real
`SQLiteAgentRegistryStore` on import, idempotently, before the graph runs.

## Run (CLI)

```bash
.venv/bin/python examples/trading_desk_ops/trading_desk_ops_demo.py
```

Runs all five EQ-### cases back to back, unattended. Each case prints:

- the orchestrator's trigger classification (domain + trigger_type) and which
  specialist that sends the case to first
- every tool call each specialist makes, tagged `[ok]` or `[DENIED]`
- the orchestrator's re-routing reasoning after each specialist finishes
- the compliance report compilation
- the proposed disposition (rule-based, not LLM-improvised) with which reviewer tier
  it requires, auto-approved (no prompts on the CLI path — see "Two-tier human-in-the-
  loop review" below for the interactive version)
- the full AutoPIL audit trail for the case

## Run (live browser viewer)

Not available for this demo yet — a live browser viewer (`langgraph dev` +
`examples/trading_desk_ops/frontend/`, and wiring into the shared multi-demo
`frontend/`) is a separate follow-up task. This demo is reachable via generic
LangGraph Studio through the shared `langgraph.json` entry (`"trading_desk_ops"`) in
the meantime — `.venv/bin/langgraph dev` from the repo root, then open the Studio URL
it prints.

## What to expect

Because each specialist reasons for itself, the exact denials on any given run can
vary — that's the point, not a bug. What's consistent:

- **EQ-001** — clean straight-through. `order_intake_agent` runs first (new-order
  trigger), allocation/affirmation/settlement all clean. Final disposition: **CLEAR TO
  SETTLE — clean straight-through processing, no exception**, Tier 1.
- **EQ-002** — `affirmation_matching_agent` flags a stale standing settlement
  instruction on one sub-account; expect a reroute to `exception_investigation_agent`,
  which triages it as a data/SSI error. Final disposition: **CORRECT SSI & REPROCESS —
  stale settlement instruction confirmed**, Tier 1.
- **EQ-003** — `affirmation_matching_agent` flags a same-trade-date price
  discrepancy (a timing lag). `exception_investigation_agent` is handed
  plausible-but-denied tools (`get_desk_pnl_data`/`get_commission_data`) alongside its
  real ones; if it reaches for them, expect 1-2 `[DENIED]` lines before it completes
  its finding from settlement/affirmation data alone. Final disposition: **INVESTIGATE
  TIMING LAG — affirmation discrepancy, no settlement risk**, Tier 1.
- **EQ-004** — PM rebalance trigger. **`order_intake_agent` never runs at all** — the
  orchestrator's classification step routes straight to `allocation_agent` since the
  instruction already arrived structured. This is the concrete proof that
  classification is genuinely dynamic, not a fixed edge (compare EQ-001's trace, where
  `order_intake_agent` runs first). Clean thereafter. Final disposition: **CLEAR TO
  SETTLE — clean straight-through processing, no exception**, Tier 1.
- **EQ-005** — `settlement_reconciliation_agent` surfaces a real inventory shortfall
  against the DTCC/NSCC obligation; `exception_investigation_agent` triages it as a
  genuine fails-to-deliver risk, pulling in Reg SHO locate-requirement data. Final
  disposition: **ESCALATE — FAILS-TO-DELIVER RISK: obtain Reg SHO locate/borrow before
  settlement** — the only one of the five routed to **Tier 2 (compliance officer)**.

## Two-tier human-in-the-loop review

New in this demo, not present in any sibling: `decision_node` classifies severity from
real underlying fixture data (an inventory-shortfall field, an SSI-staleness field —
never a role's self-reported finding, never a case_id → tier lookup) and routes the
`interrupt()` to one of two reviewer tiers:

- **Tier 1 — ops-analyst review** — routine corrections (EQ-001, EQ-002, EQ-003,
  EQ-004).
- **Tier 2 — compliance-officer review** — escalated settlement-risk events (EQ-005),
  invoking Reg SHO locate-requirement logic.

The interrupt payload carries `tier`/`tier_label` explicitly so a future frontend can
render a different reviewer form per tier. Same as `quality_control`'s
`decision_node`: **a written note is required on both approve and override, on both
tiers** — `decision_node` re-interrupts if the note is empty rather than letting a
disposition finalize with no rationale on record. The CLI supplies
`"Auto-approved via CLI unattended run."` on every resume so it stays unattended.
Verify directly against the audit trail printed at the end of each case if you want to
confirm a specific denial fired for the reason you expect, rather than trusting a
specialist's self-reported finding.

## Session-isolation and role-spoofing tools

`compliance_report_tools()` includes two attack-surface tools mirroring every other
demo's final-role equivalent (`sar_generator_tools()` in `fraud_investigation`,
`quality_finding_tools()` in `quality_control`):

1. **Session isolation** — `get_case_agent_outputs` reaches `agent_outputs` through
   `exception_investigation_agent`'s session instead of `compliance_reporting_agent`'s
   own — denied independent of the source policy check, *once that session has
   already been established under `exception_investigation_agent`* (i.e. that role has
   actually run earlier in the same case — true for EQ-002/EQ-003/EQ-005, where it
   does). See DESIGN.md §10 for the precondition this depends on.
2. **Role spoofing** — `get_subject_settlement_status` uses
   `compliance_reporting_agent`'s real, registered `agent_id` but claims
   `agent_role="settlement_reconciliation_agent"` to reach `dtcc_cns_data` — denied as
   `role_not_permitted` because the registry validates the claimed role against that
   `agent_id`'s canonical value, regardless of session state.

Both verified directly (bypassing the LLM, calling the guarded getters with the exact
same arguments the tools use) during development — see DESIGN.md §10.

## Hosted AutoPIL SaaS trial mode

Runs local-only (embedded `ContextGuard.protect()`) by default. Optional hosted
AutoPIL SaaS trial mode, same auto-detect (`AUTOPIL_ADMIN_KEY` + `AUTOPIL_EVALUATE_KEY`
both set) as the other 5 demos with this support — see `trading_desk_ops_saas_guard.py`'s
module docstring for what's confirmed live (none of this demo's 7 role names matched a
pre-seeded policy on the shared trial tenant, so `ensure_policy()` creates 7 dedicated
`demo_tdo_<role>_policy` policies) and DESIGN.md's "Appendix: hosted trial mode" for
the full writeup. **Known gap, prominent because it's an active local mechanism**:
`trading_desk_ops.yaml`'s `session_ttl_minutes: 1440` (24-hour cap, set on all 7 roles)
is not enforceable the same way against the hosted API — confirmed against the real
OpenAPI schema, which has no `session_ttl_minutes` (or `permitted_agent_ids`/
`sensitivity_decay`) field at all. Hosted mode is additive, not a replacement for that
local enforcement.

## Policy file

`policies/financial_services/trading_desk_ops.yaml` — governs all 7 agents, including a
`regulations:` metadata block mapping SEC Rule 15c6-1/15c6-2/15c3-3/17a-4, DTCC/NSCC
CNS, Reg SHO, FINRA CAT, FINRA Rule 5310, and information-barrier/MNPI policy directly
onto the roles and mechanisms that enforce them. See DESIGN.md §1/§5 for what changed
and why (no existing autopil stub matched this domain — designed from scratch, with the
`regulations:` block convention borrowed from `policies/financial_services/
clearing_settlement.yaml`).
