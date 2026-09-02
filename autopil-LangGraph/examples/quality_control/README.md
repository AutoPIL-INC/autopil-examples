# Quality Control — Reasoning-Driven Multi-Agent Demo

Five specialist Claude agents, orchestrated with LangGraph, investigate manufacturing
quality cases at Ironview Manufacturing — an automotive stamping/injection-molding
supplier — tracing a defect to root cause across defect detection, statistical
process control, supplier quality, and equipment calibration, under a real AutoPIL
policy. See [DESIGN.md](./DESIGN.md) for the full design rationale, including what
changed from the original policy stub in the sibling `autopil` repo — this file is
just setup + what to expect.

No live MES/SCADA system is involved anywhere in this demo — every guarded getter
reads from `quality_control_data.py`, exactly like every other demo in this repo.
That's deliberate: it demonstrates the governance pattern (`guard.protect()` wrapping
data access) without committing to a real plant-floor integration.

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
provider chain as every other demo here.

No manual agent registration step needed — the 5 roles are registered as
`status="approved"` agents (`AGENT_IDS` in `quality_control_demo.py`) against a
real `SQLiteAgentRegistryStore` on import, idempotently, before the graph runs.

## Run (CLI)

```bash
.venv/bin/python examples/quality_control/quality_control_demo.py
```

Runs all four cases (QC-001 calibration lapse, QC-002 supplier lot nonconformance,
QC-003 over-scope attempt, QC-004 clean baseline) back to back, unattended. Each case
prints:

- the orchestrator's fixed first step (`defect_detection_agent` always runs first)
- every tool call each specialist makes, tagged `[ok]` or `[DENIED]`
- the orchestrator's re-routing reasoning after each specialist finishes
- the final quality-finding compilation
- the proposed disposition (rule-based, not LLM-improvised), auto-approved (no prompts
  on the CLI path — see "Human-in-the-loop review" below for the interactive version)
- the full AutoPIL audit trail for the case

## Run (live browser viewer)

Not available for this demo yet — a live browser viewer (`langgraph dev` +
`examples/quality_control/frontend/`, and wiring into the shared multi-demo
`frontend/`) is a separate follow-up task. This demo is reachable via generic
LangGraph Studio through the shared `langgraph.json` entry (`"quality_control"`) in
the meantime — `.venv/bin/langgraph dev` from the repo root, then open the Studio URL
it prints.

## What to expect

Because each specialist reasons for itself, the exact denials on any given run can vary
— that's the point, not a bug. What's consistent:

- **QC-001** — `defect_detection_agent` flags the out-of-spec flange width; expect
  routing toward `spc_agent` and/or `calibration_agent`, which finds the stamping
  press 45 days past its calibration due date. Final disposition: **QUARANTINE &
  RECALIBRATE — equipment calibration lapse confirmed**.
- **QC-002** — the control-chart shift aligns with a lot changeover; `supplier_quality_agent`
  finds an open nonconformance against the supplying lot, no denials required. Final
  disposition: **NONCONFORMANCE REPORT & SUPPLIER HOLD — supplier lot issue
  confirmed**.
- **QC-003** — `defect_detection_agent` is handed plausible-but-denied tools
  (`get_cost_data`/`get_supplier_contracts`) alongside its real ones; if it reaches for
  them, expect 1-2 `[DENIED]` lines and a reroute toward `spc_agent`/`supplier_quality_agent`/
  `calibration_agent`. Final disposition: **MONITOR — no confirmed nonconformance,
  continue tracking**.
- **QC-004** — clean baseline; expect an `IN_CONTROL`/`COMPLIANT` finding and **no
  corrective action** in the final disposition.

## Human-in-the-loop review

Same `interrupt()`/checkpointer pattern as `fraud_investigation`/`hospital_revenue_cycle`/
`care_coordination`: `decision_node` pauses before finalizing the disposition — a
reviewer Approves or Overrides in the live viewer; the CLI auto-approves. Unlike the
other demos, **a written note is required on both approve and override, not just
override** — `decision_node` re-interrupts if the note is empty rather than letting a
disposition finalize with no rationale on record. The CLI supplies
`"Auto-approved via CLI unattended run."` on every resume so it stays unattended.
Verify directly against the audit trail printed at the end of each case if you want to
confirm a specific denial fired for the reason you expect, rather than trusting a
specialist's self-reported finding.

## Session-isolation and role-spoofing tools

`quality_finding_tools()` includes two attack-surface tools mirroring every other
demo's final-role equivalent (`sar_generator_tools()` in `fraud_investigation`,
`care_summary_tools()` in `care_coordination`):

1. **Session isolation** — `get_case_agent_outputs` reaches `agent_outputs` through
   `calibration_agent`'s session instead of `quality_orchestrator`'s own — denied
   independent of the source policy check.
2. **Role spoofing** — `get_subject_nonconformance_status` uses
   `quality_orchestrator`'s real, registered `agent_id` but claims
   `agent_role="supplier_quality_agent"` — denied as `role_not_permitted` because the
   registry validates the claimed role against that `agent_id`'s canonical value.

Both verified directly (bypassing the LLM, calling the guarded getters with the exact
same arguments the tools use) during development — see DESIGN.md §9.

## Policy file

`policies/manufacturing/quality_control.yaml` — governs all 5 agents. Adapted from the
sibling `autopil` repo's manufacturing policy stub; see DESIGN.md §2 for what changed
and why.
