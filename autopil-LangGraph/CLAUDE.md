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
- `examples/client_analysis/` — 3 roles (junior/senior analyst, wealth advisor) share
  the exact same Databricks Unity Catalog toolbelt; AutoPIL's policy — not the tool
  layer — decides what each role can actually reach, including `task_bindings` purpose
  limitation and a sensitivity-ceiling case. AWS Bedrock-first provider chain. See its
  [DESIGN.md](./examples/client_analysis/DESIGN.md) and
  [README.md](./examples/client_analysis/README.md).
- `frontend/` — a third, **additive** frontend covering both demos from one
  `langgraph dev` server, so you don't need two `npm run dev` processes. Each demo's
  own standalone frontend (`examples/*/frontend/`) is untouched and still works
  independently — see [frontend/README.md](./frontend/README.md). The demo-specific
  files under `frontend/src/demos/<name>/` are copies of each standalone frontend's
  `src/` (not shared via a package), so a change to one needs to be copied to the
  other by hand if it should apply everywhere.

## Setup notes

- Shared `.venv` at the repo root for both examples. It's tied to this absolute path —
  recreate it (`python3.11 -m venv .venv`) if this directory ever moves.
- `autopil[langgraph]>=0.10.0` is installed straight from PyPI, listed in
  `requirements.txt`. `0.10.0` is the first PyPI release with `task_type` support on
  `ContextGuard.protect()`, which this demo requires.
- `ANTHROPIC_API_KEY` (and friends) live in `.env`, which is gitignored — never commit
  it. `.env.example` documents the required keys.
- Both scripts pick a model via a `_make_llm()` helper. The fraud demo's version tries,
  in order: `ChatAnthropic` (`ANTHROPIC_API_KEY`) → `ChatGoogleGenerativeAI`
  (`GOOGLE_API_KEY`, `gemini-3.5-flash`) → `ChatGroq` (`GROQ_API_KEY`,
  `llama-3.3-70b-versatile`) → `ChatOllama` (no key, local server, `OLLAMA_MODEL` or
  `qwen2.5:7b` default). All four accept the same tool-schema dicts, so no other code
  needs to change when switching providers — **except** `tool_choice`: Ollama's
  `bind_tools()` documents that it's ignored, so `orchestrator_node` and
  `orchestrator_review_node` guard every `response.tool_calls[0]` index with
  `if response.tool_calls` and fall back to a default routing decision instead of
  crashing when a model (Ollama, in practice) doesn't call the forced tool.
  `_make_llm(provider)` also takes an explicit override, threaded through
  `InvestigationState["provider"]` — that's what the live viewer's model dropdown sets
  per run (defaults to `"ollama"` there — see `frontend/src/types.ts`'s `PROVIDERS`).
  `01_basics.py`'s `_make_llm()` is simpler (Anthropic/Gemini only, no override, always
  auto-detect) since it has no dropdown to serve.
- **Ollama's default model matters a lot, and it's been live-tested both ways** —
  `llama3.2` (3B), tried first, completes without crashing but 2 of 3 specialists skipped
  tool calls entirely and jumped straight to a finding with no data gathered. Swapped the
  default to `qwen2.5:7b`, which passed the same live test cleanly (all 3 specialists
  called tools, 3 legitimate AutoPIL denials fired). Don't reintroduce `llama3.2` as the
  default without re-verifying — "runs to completion" is not the same as "worked well"
  for this provider.

## Working with the fraud investigation demo

- It's intentionally non-deterministic — see DESIGN.md §9. A run with zero denials, or
  different denials than a previous run, is a valid outcome, not a regression.
- The audit database `examples/fraud_investigation/fraud_investigation_audit.db` is
  disposable — safe to delete between runs.

## Working with the client_analysis demo

- Also intentionally non-deterministic, same reasoning as the fraud demo. Don't trust a
  role's self-reported `outcome` (COMPLETED/BLOCKED) at face value in `decision_node` —
  live-tested with Ollama's qwen2.5:7b and it claimed COMPLETED once after every single
  tool call in its run had been denied. `decision_node` cross-checks against the actual
  audit trail (did the role get any ALLOW at all) before trusting a COMPLETED claim.
- Bedrock (`ChatBedrockConverse` via `langchain-aws`) is the flagship provider here,
  opted into via `AWS_BEDROCK_MODEL_ID` being set (not ambient AWS credential sniffing).
  Verified directly against the installed `langchain-aws` source, not assumed: forcing a
  specific tool via `tool_choice=<name>` works for Anthropic-on-Bedrock models but
  **raises `ValueError` at `bind_tools()` time** for models whose
  `supports_tool_choice_values` doesn't include `"tool"` (e.g. Llama-family Bedrock
  models) — a different failure mode than Ollama's silent ignore. `_bind_forced()`
  catches this and falls back to unforced binding either way, so `orchestrator_node`'s
  `if response.tool_calls` guard still matters regardless of which provider produced the
  response.
- The audit database `examples/client_analysis/client_analysis_audit.db` is
  disposable — safe to delete between runs.
