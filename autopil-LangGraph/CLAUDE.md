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
- `examples/client_analysis/` — a tiered review queue: 5 customers, each starting at
  junior_analyst and able to progressively escalate through senior_analyst to
  wealth_advisor, with a human reviewing/dispositioning the proposed next action at
  every tier a case reaches (up to 3 review points per case). All 3 roles share the
  exact same Databricks Unity Catalog toolbelt; AutoPIL's policy — not the tool
  layer — decides what each role can actually reach, including `task_bindings` purpose
  limitation and a sensitivity-ceiling case. AWS Bedrock-first provider chain. See its
  [DESIGN.md](./examples/client_analysis/DESIGN.md) and
  [README.md](./examples/client_analysis/README.md).
- `examples/institutional_portfolio_review/` — 8 roles (one orchestrator, seven
  specialists) enforced under **two** real AutoPIL policy files at once
  (`portfolio_review_wealth.yaml` + `portfolio_review_risk.yaml`). Which file governs a
  role is a property of the role, not the source it's reaching for — `credit_scores`/
  `loan_history`/`risk_models` are referenced by roles from both files. Used to be 11
  roles — the AML/KYC/compliance-officer workflow moved to its own demo (below). See
  its [DESIGN.md](./examples/institutional_portfolio_review/DESIGN.md) and
  [README.md](./examples/institutional_portfolio_review/README.md).
- `examples/aml_compliance/` — 3 roles (`aml_investigator`, `kyc_agent`,
  `compliance_officer`) run a fixed investigation chain, split out of
  `institutional_portfolio_review` where this financial-crime-governance workflow sat
  split across two policy files despite being one coherent story. One dedicated policy
  file; human-in-the-loop sign-off before the disposition is final, same pattern as
  `fraud_investigation` (its closest sibling). See its
  [DESIGN.md](./examples/aml_compliance/DESIGN.md) and
  [README.md](./examples/aml_compliance/README.md).
- `frontend/` — a sixth, **additive** frontend covering every demo from one
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
- **Every demo's per-demo Python module names must be globally unique across this repo,
  not just within its own directory.** `langgraph dev` loads every graph in
  `langgraph.json` into one Python process, and each demo does
  `sys.path.insert(0, str(ROOT))` with its own directory — if two demos both have a
  same-named file (e.g. two `simulated_uc_data.py`), Python's `sys.modules` cache means
  whichever demo's graph loads first "wins," and the second demo silently gets the
  *first* demo's module instead of its own (`AttributeError` on whatever the second
  demo's module has that the first's doesn't). This only shows up under `langgraph dev`
  — running a demo's own script directly (`python foo_demo.py`) is a fresh process each
  time and never collides. Caught live exactly this way when
  `institutional_portfolio_review` was added — its data module is
  `portfolio_review_uc_data.py`, not `simulated_uc_data.py`, specifically to avoid
  colliding with `client_analysis`'s file of that name. Same reasoning for
  `aml_compliance`'s data module — `aml_case_data.py`, not `simulated_data.py`, which
  `fraud_investigation` already has. When adding a new demo, check its module names
  against every existing demo's, then verify with `langgraph dev` (not just the
  demo's own CLI script) before calling it done.
- **A live, unfixed instance of the above exists today**: `fraud_investigation` and
  `client_analysis` each have their own `saas_guard.py` (added when hosted SaaS trial
  mode was wired into both — see their own DESIGN.md appendices), and those two files
  do collide under this exact rule. Currently harmless — both copies define the
  identical `RemoteContextGuard`/`bootstrap_agents()` interface, so whichever one
  `sys.modules` caches first is functionally interchangeable with the other — but if
  the two copies are ever edited independently without staying in sync, one demo will
  silently run the other's code under `langgraph dev` with no error. Not fixed as
  part of the `aml_compliance` split (out of scope for that change); worth a real fix
  (e.g. a shared package, or distinct per-demo names) before either copy's behavior is
  meant to diverge.

## Working with the fraud investigation demo

- It's intentionally non-deterministic — see DESIGN.md §9. A run with zero denials, or
  different denials than a previous run, is a valid outcome, not a regression.
- The audit database `examples/fraud_investigation/fraud_investigation_audit.db` is
  disposable — safe to delete between runs.
- **Optional hosted AutoPIL SaaS trial mode**, auto-detected from env vars
  (`AUTOPIL_ADMIN_KEY` + `AUTOPIL_EVALUATE_KEY` both set → hosted; either unset → local
  embedded `ContextGuard`, unchanged) — see `saas_guard.py` and DESIGN.md's "Appendix:
  hosted trial mode" for what's verified. Two things worth knowing if you're touching
  this: (1) `langgraph dev`'s hot-reload re-evaluates that env check on every reload —
  if both keys are in `.env`, an *already-running* dev server silently starts sending
  live runs to the real hosted tenant on its next reload, not just future process
  starts (confirmed live: checked `/v1/audit/events` and saw a test run's events land
  there in real time). (2) The hosted API requires `agent_id` unconditionally and only
  evaluates approved agents — `bootstrap_agents()` handles registration/approval
  idempotently, always pinning `policy_name` explicitly rather than relying on the
  hosted API's role-scan fallback (which is real and risky on a shared trial tenant —
  some `agent_role` values there resolve to more than one policy).

## Working with the client_analysis demo

- Also intentionally non-deterministic, same reasoning as the fraud demo. Every case
  starts at junior_analyst and can progressively escalate through senior_analyst to
  wealth_advisor — deterministic per case (`simulated_uc_data.CLIENT_REVIEWS[id]
  ["tier_tasks"]` says what task a tier works on *if* it's reached), but whether a case
  actually reaches the tier it's designed for depends on what each tier's own finding
  recommends and what the human reviewer decides at each step.
- Don't trust a tier's self-reported `proposed_action` at face value — live-tested with
  Ollama's qwen2.5:7b, which omitted `proposed_action` outright on some turns despite it
  being a required enum field on `submit_finding`. `_run_role` coerces it to a safe
  default (`FLAG FOR COMPLIANCE / RISK REVIEW`, forcing `recommend_escalation: True`)
  before it reaches the review panel or final disposition.
- **The CLI's auto-approve has to loop, not fire once.** Every other human-in-the-loop
  demo in this repo (fraud, portfolio-review) pauses at most once per run, so a single
  `if "__interrupt__" in result: ...` is enough. Here a case can pause up to 3 times
  (once per tier it reaches), so `run_request()` uses
  `while "__interrupt__" in result: result = graph.invoke(Command(resume=...), ...)` —
  live-tested across all 5 customers via Ollama, confirming this correctly drives
  1-tier, 2-tier, and 3-tier runs to completion without hanging. Also verified directly
  against the real streaming API (not just the CLI path): created a thread, ran C003,
  resumed twice with `{"decision": "escalate"}` to walk it through all 3 tiers,
  confirmed each interrupt's `next_tier`/`can_escalate` fields were correct, then
  resumed with `{"decision": "approve"}` and confirmed the disposition showed
  `closed_at_tier: "wealth_advisor"` with all 3 tiers in `tiers_visited`.
- Bedrock (`ChatBedrockConverse` via `langchain-aws`) is the flagship provider here,
  opted into via `AWS_BEDROCK_MODEL_ID` being set (not ambient AWS credential sniffing).
- No LLM-driven routing decision remains in this demo (the old orchestrator's role/task
  assignment and its escalation decision are both gone — replaced by a deterministic
  `intake_node` lookup and human `interrupt()`s), so the forced-`tool_choice`
  handling (`_bind_forced()`) that lived here previously was removed as dead code. That
  Bedrock/Ollama `tool_choice` divergence is still real — see the fraud and
  portfolio-review demos, which still force a tool for their own single-decision
  nodes — just no longer exercised in this one.
- The audit database `examples/client_analysis/client_analysis_audit.db` is
  disposable — safe to delete between runs.
- **Optional hosted AutoPIL SaaS trial mode**, same auto-detect/`RemoteContextGuard`
  design as fraud_investigation's — see `saas_guard.py` and DESIGN.md's "Appendix:
  hosted trial mode" for what's verified. One thing specific to this demo: the
  shared trial tenant has **two** policies named for `wealth_advisor` (one matches
  this demo's local policy, one doesn't) — `bootstrap_agents()` is called with an
  explicit per-role `policy_name_for` override (`_SAAS_POLICY_NAMES` in
  `client_analysis_demo.py`) rather than the naive `f"{role}_policy"` default fraud
  investigation's call uses, specifically to avoid resolving to the wrong one. Also
  caught here (and retrofitted into fraud_investigation's copy too):
  `GET /v1/audit/sessions/{id}` needs the **Admin** key — an Evaluate-scoped key gets
  `403 Forbidden` on that endpoint even though it works fine for
  `POST /v1/context/evaluate` — so `RemoteContextGuard` takes both keys, not just one.

## Working with the institutional_portfolio_review demo

- **Two `ContextGuard` instances, selected by role, not by source.** `wealth_guard`
  (`portfolio_review_wealth.yaml`) and `risk_guard` (`portfolio_review_risk.yaml`) are
  both live; `ROLE_GUARD` maps each of the 8 roles to whichever file its own policy
  lives in. `credit_scores`/`loan_history`/`risk_models` are reachable by roles from
  *both* files — same source, different guard, depending on who's asking.
- **27-tool toolbelt needs a stronger conclude-now nudge than the other demos.**
  Live-tested with Ollama's qwen2.5:7b: with this many tools available, it tends to call
  most/all of them in one big batch per turn and doesn't reliably include
  `submit_finding` in that batch — it will repeat the *same* batch turn after turn
  instead of concluding. `run_tool_loop()` here appends an explicit, increasingly
  urgent message after every turn without a finding (not just when the model calls no
  tools at all, which is all the smaller-toolbelt demos needed) — on the last turn it
  explicitly forbids further tool calls. If you shrink or grow this toolbelt, re-verify
  convergence live rather than assuming the nudge still suffices. (Was 32 tools before
  the `aml_compliance` split removed 5 sources — `watchlist`, `personal_hr_records`,
  `marketing_data`, `internal_risk_models`, `identity_records` — that were only ever
  used by the roles that moved.)
- **Keep `REVIEW_TYPES` role chains short (max ~4 roles).** An earlier 6-role
  `quarterly_review` chain converged poorly — live-tested, most runs ended up only
  `PARTIALLY BLOCKED` because every extra role in a chain is another chance for one
  step to stall. Split into a 4-role `quarterly_review` plus a separate
  `trade_settlement_check` (2 roles) for `macro_analyst`/`settlement_agent`. (A fifth
  chain, `aml_case`, also existed at the time for the same reason — spreading 11 roles
  across 5 shorter chains instead of 4 longer ones — but has since moved to its own
  demo; see `examples/aml_compliance/`.) Also added `ROLE_FOCUS_HINTS` — a one-line
  steer per role toward the *category* of relevant data (not which tool to call) —
  the fraud/client_analysis demos never needed this since their toolbelts are small
  enough to converge on a generic brief alone. Together these took live-tested runs
  from mostly-partial to mostly-clean completions; don't revert either change without
  re-verifying live.
- Also intentionally non-deterministic; `decision_node` grounds each role's
  self-reported outcome in its own audit trail (same fix as `client_analysis`), applied
  per-role across the whole review rather than once per request.
- **Human-in-the-loop review**, same `interrupt()`/checkpointer pattern as
  `fraud_investigation_demo.py`: `decision_node` pauses before finalizing the outcome,
  a supervisor Approves or Overrides (with notes) in the live viewer, the CLI
  auto-approves. Verified live against the real streaming API (not just the CLI path)
  — created a thread via `POST /threads`, confirmed the interrupt payload shape, then
  resumed with an override and confirmed the `disposition` event reflects it exactly.
- The audit database
  `examples/institutional_portfolio_review/institutional_portfolio_review_audit.db` is
  disposable — safe to delete between runs.

## Working with the aml_compliance demo

- Split out of `institutional_portfolio_review`'s `aml_case` review type — see its
  own DESIGN.md for the full split rationale. One dedicated policy file for all 3
  roles instead of inheriting from two.
- **No LLM-driven routing decision exists in this demo at all.** Every case runs the
  same fixed sequence (`aml_investigator` → `kyc_agent` → `compliance_officer`) —
  `intake_node` is a plain dict lookup, same as `client_analysis_demo.py`'s own
  `intake_node`. No `_bind_forced()`/forced-`tool_choice` machinery anywhere in this
  file for the same reason it was removed from `client_analysis_demo.py`.
- Per-role curated toolbelts (`aml_investigator_tools()`, `kyc_agent_tools()`,
  `compliance_officer_tools()`) — real authorized sources plus 1-2 deliberate
  over-scope tools each, mirroring `fraud_investigation`'s `*_tools()` functions, not
  `client_analysis`/`institutional_portfolio_review`'s "identical full toolbelt for
  everyone" pattern.
- **A real bug caught during verification**: `compliance_officer`'s
  `get_regulatory_filings` tool was initially bound to `task_type="sar_filing"`, but
  that task's `task_bindings.permitted_sources` doesn't include `regulatory_filings`
  — meaning the tool was denied on every call regardless of model behavior,
  contradicting the "denials aren't scripted" design this whole repo follows. Fixed to
  `task_type="compliance_review"`. If you add or rewire a tool here, verify its
  `task_type` actually appears in that task's `task_bindings.permitted_sources` in
  `aml_compliance.yaml` — a mismatch fails silently (always-denied) rather than
  erroring, so it won't surface unless you check the live audit trail.
- `decision_node` is rule-based, grounded in the real underlying signal data
  (`aml_case_data.WATCHLIST`/`IDENTITY_RECORDS`/`TRANSACTION_HISTORY`) — not any
  role's self-reported finding — same principle as every other demo's decision node.
- Hosted AutoPIL SaaS trial mode is **not wired for this demo** (unlike
  `fraud_investigation`/`client_analysis`) — deliberate, same "prove local mode first"
  sequencing those two demos followed before adding it.
- The audit database `examples/aml_compliance/aml_compliance_audit.db` is disposable
  — safe to delete between runs.
