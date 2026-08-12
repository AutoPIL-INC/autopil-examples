# Hospital Revenue Cycle — Reasoning-Driven Multi-Agent Demo

Six specialist Claude agents, orchestrated with LangGraph, review hospital revenue-cycle
encounters — clinical documentation, coding, charge reconciliation, and billing
compliance — under a real AutoPIL policy. See [DESIGN.md](./DESIGN.md) for the full
design rationale, including what changed from the original scripted version of this
demo in the core AutoPIL SDK repo — this file is just setup + what to expect.

No live EHR or billing system is involved anywhere in this demo — every guarded getter
reads from `hospital_revenue_cycle_data.py`, exactly like every other demo in this repo.
That's deliberate: it demonstrates the governance pattern (`guard.protect()` wrapping
data access) without committing to a real EHR/billing integration.

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

No manual agent registration step needed — the 6 roles are registered as
`status="approved"` agents (`AGENT_IDS` in `hospital_revenue_cycle_demo.py`) against a
real `SQLiteAgentRegistryStore` on import, idempotently, before the graph runs.

## Run (CLI)

```bash
.venv/bin/python examples/hospital_revenue_cycle/hospital_revenue_cycle_demo.py
```

Runs all four encounters (ENC-001 CDI gap, ENC-002 missed charge, ENC-003 missed charge
with an over-scope attempt, ENC-004 clean baseline) back to back, unattended. Each
encounter prints:

- the orchestrator's initial routing decision and reasoning
- every tool call each specialist makes, tagged `[ok]` or `[DENIED]`
- the orchestrator's re-routing reasoning after each specialist finishes
- billing compliance's tool calls and the final revenue-summary compilation
- the proposed disposition (rule-based, not LLM-improvised), auto-approved (no prompts
  on the CLI path — see "Human-in-the-loop review" below for the interactive version)
- the full AutoPIL audit trail for the encounter

## Run (live browser viewer)

```bash
# Terminal 1 — serve the graph (from the repo root, i.e. autopil-LangGraph/)
.venv/bin/langgraph dev

# Terminal 2 — this demo's own frontend
cd examples/hospital_revenue_cycle/frontend
npm install
npm run dev
```

Open the printed Vite URL. Pick an encounter card, watch the live feed of tool calls and
denials stream in, and approve or override the proposed disposition when prompted.

This demo is also wired into the shared multi-demo frontend
(`autopil-LangGraph/frontend/`) if you'd rather run every demo from one server — see
that directory's own README.

## What to expect

Because each specialist reasons for itself, the exact denials on any given run can vary
— that's the point, not a bug. What's consistent:

- **ENC-001** — `clinical_documentation_agent` finds the coding gap; expect routing
  toward `cdi_specialist_agent`/`medical_coding_agent` next. Final disposition:
  **+$1,800 revenue recovery** (CDI query -> code update).
- **ENC-002** — `charge_reconciliation_agent` finds the missed charge legitimately, no
  denials required. Final disposition: **+$650 revenue recovery**.
- **ENC-003** — `charge_reconciliation_agent` is handed plausible-but-denied tools
  (`get_ehr_summary`/`get_clinical_notes`) alongside its real ones; if it reaches for
  them, expect 1-2 `[DENIED]` lines and an orchestrator reroute to
  `clinical_documentation_agent`. Final disposition: **+$1,750 revenue recovery**, with
  the policy violation noted in the proposed action.
- **ENC-004** — clean baseline; expect a `COMPLIANT` finding and **no revenue
  recovery** in the final disposition.

## Human-in-the-loop review

Same `interrupt()`/checkpointer pattern as `fraud_investigation`/`aml_compliance`:
`decision_node` pauses before finalizing the disposition — a reviewer Approves or
Overrides (with notes) in the live viewer; the CLI auto-approves. Verify directly
against the audit trail printed at the end of each encounter if you want to confirm a
specific denial fired for the reason you expect, rather than trusting a specialist's
self-reported finding.

## Session-isolation and role-spoofing tools

`revenue_summary_tools()` includes two attack-surface tools mirroring every other
demo's final-role equivalent (`sar_generator_tools()` in `fraud_investigation`,
`splunk_threat_synthesizer_tools()` in `splunk_secops`):

1. **Session isolation** — `get_case_agent_outputs` reaches `agent_outputs` through
   `billing_compliance_agent`'s session instead of `revenue_orchestrator`'s own —
   denied independent of the source policy check.
2. **Role spoofing** — `get_subject_billing_status` uses `revenue_orchestrator`'s real,
   registered `agent_id` but claims `agent_role="billing_compliance_agent"` — denied as
   `role_not_permitted` because the registry validates the claimed role against that
   `agent_id`'s canonical value.

Both verified directly (bypassing the LLM, calling the guarded getters with the exact
same arguments the tools use) during development — see DESIGN.md §8.

## Policy file

`policies/healthcare/revenue_cycle.yaml` — governs all 6 agents. Adapted from the core
AutoPIL SDK repo's healthcare policy library; see DESIGN.md §2 for what changed and why.
