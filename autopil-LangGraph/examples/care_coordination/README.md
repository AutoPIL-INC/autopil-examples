# Care Coordination — Reasoning-Driven Multi-Agent Demo

Five specialist Claude agents, orchestrated with LangGraph, review care-coordination
cases — triage, chart review, medication management, and chronic-care outreach — under
a real AutoPIL policy. See [DESIGN.md](./DESIGN.md) for the full design rationale,
including what changed from the original policy file in the core AutoPIL SDK repo —
this file is just setup + what to expect.

No live EHR or pharmacy system is involved anywhere in this demo — every guarded getter
reads from `care_coordination_data.py`, exactly like every other demo in this repo.
That's deliberate: it demonstrates the governance pattern (`guard.protect()` wrapping
data access) without committing to a real EHR/pharmacy integration.

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
`status="approved"` agents (`AGENT_IDS` in `care_coordination_demo.py`) against a
real `SQLiteAgentRegistryStore` on import, idempotently, before the graph runs.

## Run (CLI)

```bash
.venv/bin/python examples/care_coordination/care_coordination_demo.py
```

Runs all four cases (CC-001 acute symptom call, CC-002 care-gap outreach, CC-003
medication refill, CC-004 clean well-visit) back to back, unattended. Each case prints:

- the coordinator's initial routing decision and reasoning
- every tool call each specialist makes, tagged `[ok]` or `[DENIED]`
- the coordinator's re-routing reasoning after each specialist finishes
- the final care-summary compilation
- the proposed disposition (rule-based, not LLM-improvised), auto-approved (no prompts
  on the CLI path — see "Human-in-the-loop review" below for the interactive version)
- the full AutoPIL audit trail for the case

## Run (live browser viewer)

```bash
# Terminal 1 — serve the graph (from the repo root, i.e. autopil-LangGraph/)
.venv/bin/langgraph dev

# Terminal 2 — this demo's own frontend
cd examples/care_coordination/frontend
npm install
npm run dev
```

Open the printed Vite URL. Pick a case card, watch the live feed of tool calls and
denials stream in, and approve or override the proposed disposition when prompted.

This demo is also wired into the shared multi-demo frontend
(`autopil-LangGraph/frontend/`) if you'd rather run every demo from one server — see
that directory's own README.

## What to expect

Because each specialist reasons for itself, the exact denials on any given run can vary
— that's the point, not a bug. What's consistent:

- **CC-001** — `triage_agent` flags an escalation concern; expect routing toward
  `clinical_summary_agent` next, then `medication_review_agent` to check
  anticoagulation status. Final disposition: **ESCALATE — refer for urgent care**.
- **CC-002** — `care_gap_agent` finds the overdue A1C recheck legitimately, no denials
  required. Final disposition: **OUTREACH REQUIRED — care gap identified**.
- **CC-003** — `medication_review_agent` is handed plausible-but-denied tools
  (`get_ehr_summary`/`get_lab_results`) alongside its real ones; if it reaches for
  them, expect 1-2 `[DENIED]` lines. Final disposition: **REFILL APPROVED — no
  interaction or contraindication found**.
- **CC-004** — clean baseline; expect a `COMPLIANT` finding and **no escalation or
  outreach** in the final disposition.

## Human-in-the-loop review

Same `interrupt()`/checkpointer pattern as `fraud_investigation`/`aml_compliance`/
`hospital_revenue_cycle`: `decision_node` pauses before finalizing the disposition — a
reviewer Approves or Overrides (with notes) in the live viewer; the CLI auto-approves.
Verify directly against the audit trail printed at the end of each case if you want to
confirm a specific denial fired for the reason you expect, rather than trusting a
specialist's self-reported finding.

## Session-isolation and role-spoofing tools

`care_summary_tools()` includes two attack-surface tools mirroring every other demo's
final-role equivalent (`sar_generator_tools()` in `fraud_investigation`,
`revenue_summary_tools()` in `hospital_revenue_cycle`):

1. **Session isolation** — `get_case_agent_outputs` reaches `agent_outputs` through
   `clinical_summary_agent`'s session instead of `care_coordinator`'s own — denied
   independent of the source policy check.
2. **Role spoofing** — `get_subject_medication_status` uses `care_coordinator`'s real,
   registered `agent_id` but claims `agent_role="medication_review_agent"` — denied as
   `role_not_permitted` because the registry validates the claimed role against that
   `agent_id`'s canonical value.

Both verified directly (bypassing the LLM, calling the guarded getters with the exact
same arguments the tools use) during development — see DESIGN.md §8.

## Policy file

`policies/healthcare/clinical_operations.yaml` — governs all 5 agents. Adapted from the
core AutoPIL SDK repo's healthcare policy library; see DESIGN.md §2 for what changed
and why.
