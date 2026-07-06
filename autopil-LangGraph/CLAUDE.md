# autopil-LangGraph — CLAUDE.md

Sample implementations showing AutoPIL used with LangGraph. Part of the
`AutoPIL-INC/autopil-examples` repo — see the root [README](../README.md) for the repo
as a whole.

## What's here

- `01_basics.py` — minimal LangGraph nodes/edges/routing example, no AutoPIL involved.
- `examples/fraud_investigation/` — the main demo: 5 specialist Claude agents,
  orchestrated with LangGraph, investigate fraud cases under a real AutoPIL policy. See
  its [DESIGN.md](./examples/fraud_investigation/DESIGN.md) for the full design rationale
  and [README.md](./examples/fraud_investigation/README.md) for setup/run instructions,
  including the live browser viewer (`langgraph dev` + `examples/fraud_investigation/frontend/`).

## Setup notes

- Shared `.venv` at the repo root for both examples. It's tied to this absolute path —
  recreate it (`python3.11 -m venv .venv`) if this directory ever moves.
- `autopil` is installed editable from a **sibling repo**
  (`../autopil/packages/core[langgraph]`), not from PyPI. That sibling repo is not part
  of this examples repo and won't exist on a machine that only clones
  `autopil-examples` — anyone setting this up elsewhere needs their own clone of
  `autopil` alongside it, or `pip install autopil` from PyPI once the demo no longer
  needs an unreleased fix.
- `ANTHROPIC_API_KEY` (and friends) live in `.env`, which is gitignored — never commit
  it. `.env.example` documents the required keys.

## Working with the fraud investigation demo

- It's intentionally non-deterministic — see DESIGN.md §9. A run with zero denials, or
  different denials than a previous run, is a valid outcome, not a regression.
- The audit database `examples/fraud_investigation/fraud_investigation_audit.db` is
  disposable — safe to delete between runs.
