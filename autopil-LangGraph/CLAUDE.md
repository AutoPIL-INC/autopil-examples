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
- `examples/splunk_secops/` — 5 roles (`soc_orchestrator`, `security_auditor`,
  `incident_triage`, `compliance_reporter`, `splunk_threat_synthesizer`) governing
  Splunk data that IBM mainframe tools forward from `z/OS` SMF logs. Same
  reasoning-driven design as `fraud_investigation` (its closest sibling — the
  synthesizer role plays the exact same part `sar_generator` does), moved into a
  security-operations domain instead of financial services. Optional hosted SaaS
  trial mode, added after the initial round (see its DESIGN.md's "Appendix: hosted
  trial mode" and `splunk_saas_guard.py`). Has its own standalone
  `frontend/`, mirroring `fraud_investigation/frontend/`'s structure, and is also
  wired into the shared `frontend/src/demos/splunk_secops/` (see that directory's note
  below on hand-syncing if either copy ever needs to change).
  Its own data module is `splunk_secops_data.py`, not `simulated_data.py` — see the
  module-name-collision note below for why. See its
  [DESIGN.md](./examples/splunk_secops/DESIGN.md) and
  [README.md](./examples/splunk_secops/README.md).
- `examples/hospital_revenue_cycle/` — 6 roles (`revenue_orchestrator`,
  `clinical_documentation_agent`, `cdi_specialist_agent`, `medical_coding_agent`,
  `charge_reconciliation_agent`, `billing_compliance_agent`) governing hospital
  revenue-cycle data (clinical documentation, coding, charge reconciliation, billing).
  Adapted from a fully **scripted**, REST-only demo in the core AutoPIL SDK repo into
  this repo's reasoning-driven pattern — see its DESIGN.md §2 for exactly what changed
  and why. First demo in this repo outside Financial Services — its own module is
  `hospital_revenue_cycle_data.py`, checked against every existing demo's module names
  before being added (see the module-name-collision note below). See its
  [DESIGN.md](./examples/hospital_revenue_cycle/DESIGN.md) and
  [README.md](./examples/hospital_revenue_cycle/README.md).
- `examples/care_coordination/` — 5 roles (`care_coordinator`, `triage_agent`,
  `clinical_summary_agent`, `medication_review_agent`, `care_gap_agent`) governing
  point-of-care patient data (triage, chart review, medication management, chronic-care
  outreach) — the second Healthcare demo, covering the front-of-house half of that
  vertical's AI governance surface where `hospital_revenue_cycle` covers the back
  office. Adapted from the core AutoPIL SDK repo's `policies/healthcare/
  clinical_operations.yaml` — a policy file with no orchestrator role and no
  `task_bindings` anywhere in it — see its DESIGN.md §2 for exactly what changed and
  why. Its own module is `care_coordination_data.py`, checked against every existing
  demo's module names before being added. See its
  [DESIGN.md](./examples/care_coordination/DESIGN.md) and
  [README.md](./examples/care_coordination/README.md).
- `examples/quality_control/` — 5 roles (`quality_orchestrator`,
  `defect_detection_agent`, `spc_agent`, `supplier_quality_agent`,
  `calibration_agent`) governing manufacturing quality-investigation data (defect
  detection, statistical process control, supplier audit/nonconformance,
  calibration) at Ironview Manufacturing — the third vertical this repo covers,
  after Financial Services and Healthcare. Adapted from the sibling `autopil` repo's
  `policies/manufacturing/quality_control.yaml` — a policy stub with no orchestrator
  role and no `task_bindings` anywhere in it — see its DESIGN.md §2 for exactly what
  changed and why. `defect_detection_agent` always runs first via a fixed graph edge
  (not an LLM choice, unlike every other role in this demo or in `care_coordination`)
  since every case starts the same way; the LLM-driven re-routing loop only kicks in
  afterward, among the 3 follow-up specialists. Its own module is
  `quality_control_data.py`, checked against every existing demo's module names
  before being added. Has its own standalone `frontend/`, mirroring
  `hospital_revenue_cycle/frontend/`'s structure, and is also wired into the shared
  `frontend/src/demos/quality_control/` (see that directory's note below on
  hand-syncing if either copy ever needs to change). See its
  [DESIGN.md](./examples/quality_control/DESIGN.md) and
  [README.md](./examples/quality_control/README.md).
- `examples/trading_desk_ops/` — 8 roles (`trading_ops_orchestrator`,
  `order_intake_agent`, `allocation_agent`, `instrument_classification_agent`,
  `affirmation_matching_agent`, `settlement_reconciliation_agent`,
  `exception_investigation_agent`, `compliance_reporting_agent`) governing two
  sub-domains at Meridian Bank's Trading Unit: Equities (a block equity order — a
  distinct ticker per scenario, MSFT/NVDA/AAPL/AMZN/GOOG — through allocation,
  same-day affirmation, DTCC/NSCC settlement verification, and exception
  investigation, inside a T+1 window) and Fixed Income (a fixed income trade — a
  distinct instrument per scenario, a corporate bond/an agency MBS TBA pool/two
  Treasury notes — through instrument classification, same-day affirmation including
  day-count/accrued-interest cash-break detection, FICC GSD/MBSD settlement
  verification including TBA pool-notification deadline risk, and exception
  investigation including FICC's Fails Charge Trading Practice penalty). Two of a
  planned 5-sub-domain build (`/TRADING_OPS_ROADMAP.md`; FX/Commodities/International
  remain unbuilt) — `TRADING_DOMAINS` is shaped so they can be added later as sibling
  entries without restructuring the graph, same relationship
  `institutional_portfolio_review`'s `REVIEW_TYPES` has to its own workflow types;
  Fixed Income is the first domain to actually exercise that extensibility (see its
  own CLAUDE.md section below and DESIGN.md §4 for exactly what had to generalize —
  `orchestrator_review_node`'s candidate list and re-routing prompt, `build_graph()`'s
  node/edge set, `_reset_sessions()` — vs. what didn't:
  `trading_ops_orchestrator_node`'s classification call itself needed no changes,
  since `domain` was already an LLM-reasoned field, not a fixed harness-level
  selection). `allocation_agent` is Equities-only; `instrument_classification_agent`
  is Fixed-Income-only — each domain's `specialist_roles` differs by exactly the one
  role that domain's own workflow doesn't share with the other. Two departures from
  every prior demo, both present since the Equities build: the orchestrator's trigger
  classification is a genuinely dynamic LLM call (not a fixed first step, unlike
  `quality_control`), and `decision_node` routes to one of **two** human review tiers
  (ops-analyst vs. compliance-officer) based on real underlying fixture data, not the
  case ID — extended for Fixed Income with two more real fixture-grounded signals
  (a pool-notification deadline field, a Fails-Charge-applicable field) on the same
  two tiers. No existing autopil policy stub matched this domain — designed from
  scratch, though its `regulations:` metadata-block convention was borrowed from
  `policies/financial_services/clearing_settlement.yaml`. Its own module is
  `trading_desk_ops_data.py`, checked against every existing demo's module names
  before being added. Has its own standalone `frontend/`, mirroring
  `quality_control/frontend/`'s structure, and is also wired into the shared
  `frontend/src/demos/trading_desk_ops/` (see that directory's note below on
  hand-syncing if either copy ever needs to change) — **frontend still covers
  Equities only as of this round; Fixed Income was added backend-only, a separate
  follow-up task extends the frontend**. Optional hosted SaaS trial mode, added after
  the initial round (see its DESIGN.md's "Appendix: hosted trial mode" and
  `trading_desk_ops_saas_guard.py`). See its
  [DESIGN.md](./examples/trading_desk_ops/DESIGN.md) and
  [README.md](./examples/trading_desk_ops/README.md).
- `frontend/` — a tenth, **additive** frontend covering every demo from one
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
  demo's own CLI script) before calling it done. **Caught again adding `splunk_secops`**
  — its first draft used `simulated_data.py` (copying `fraud_investigation`'s pattern
  too literally) and `langgraph dev` failed with exactly this `AttributeError` on
  startup; renamed to `splunk_secops_data.py` and re-verified with a full 5-graph
  `langgraph dev` load before calling it done.
- **This exact collision actually happened, live, once all 4 demos had hosted SaaS
  trial mode.** Each demo's own `saas_guard.py` was identically named — harmless while
  they were all functionally interchangeable, but the moment
  `institutional_portfolio_review`'s copy grew an `ensure_policy()` function the
  others didn't have, `langgraph dev` crashed on startup (`ImportError: cannot import
  name 'ensure_policy'`) because whichever demo's graph loaded first "won" the
  `sys.modules['saas_guard']` slot for every demo. Fixed by renaming every copy to a
  demo-specific module name — `fraud_saas_guard.py`, `client_analysis_saas_guard.py`,
  `ipr_saas_guard.py`, `aml_saas_guard.py` — and updating each demo's `from saas_guard
  import ...` to match. Any *new* per-demo module needs a name check against every
  existing demo's before it's added, not just an assumption that "it hasn't collided
  yet" means it's safe.

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
- **Optional hosted AutoPIL SaaS trial mode** — the one demo whose pre-seeded role
  policies on the shared trial tenant *don't* match at all (plain source names vs.
  this demo's `catalog.wealth.*`/`catalog.risk.*` prefixed convention), so
  `ipr_saas_guard.py`'s `ensure_policy()` creates 8 dedicated `demo_ipr_<role>_policy`
  policies instead of reusing anything. Also the demo that caught the cross-demo
  `wealth_advisor` agent/policy-name collision with `client_analysis` — see
  `ipr_saas_guard.py`'s module docstring and the module-name-collision note above for
  both incidents this demo's SaaS wiring surfaced. `wealth_guard`/`risk_guard`
  collapse into the same `RemoteContextGuard` instance in SaaS mode, since the hosted
  API is one tenant regardless of which local YAML a policy conceptually belongs to.

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
- **Optional hosted AutoPIL SaaS trial mode**, same auto-detect design as the other 3
  demos — see `aml_saas_guard.py` and its own module docstring. Unlike
  `institutional_portfolio_review`, this demo's 3 pre-seeded role policies on the
  shared trial tenant are close enough to reuse as-is (`aml_investigator_policy`
  matches byte-for-byte; `kyc_agent_policy`/`compliance_officer_policy` have minor,
  disclosed drift) — no dedicated policy creation needed here.
- The audit database `examples/aml_compliance/aml_compliance_audit.db` is disposable
  — safe to delete between runs.

## Working with the splunk_secops demo

- Follows `fraud_investigation`'s exact architecture (LLM-driven `soc_orchestrator`
  routing, `orchestrator_review_node` re-routing loop, `splunk_threat_synthesizer`
  playing the same role `sar_generator` does, rule-based `decision_node` + human
  `interrupt()`) — the closest sibling of any demo in this repo, just moved into a
  security-operations domain (Splunk data forwarded from `z/OS` SMF mainframe logs)
  instead of financial services.
- **Optional hosted AutoPIL SaaS trial mode**, same auto-detect/`RemoteContextGuard`
  design as the other 4 demos — see `splunk_saas_guard.py` and DESIGN.md's "Appendix:
  hosted trial mode". Unlike `fraud_investigation`, none of this demo's 5 SOC role
  names match a pre-seeded policy on the shared trial tenant, so
  `splunk_secops_demo.py` calls `ensure_policy()` to create 5 dedicated
  `demo_splunk_<role>_policy` policies translated from `soc_mainframe_logs.yaml`,
  same approach as `institutional_portfolio_review`'s `ipr_saas_guard.py`. Confirmed
  live: an authorized read allowed, an over-scope read denied, the audit trail read
  back correctly. Known gap: the hosted policy schema has no `permitted_agent_ids`/
  `session_ttl_minutes`/`sensitivity_decay` field, so those three local mechanisms
  aren't enforceable the same way remotely.
- **Has its own standalone `examples/splunk_secops/frontend/`**, added after the
  initial round — same Vite + React + TypeScript structure as
  `fraud_investigation/frontend/` (Description tab from `policyData.ts`/`types.ts`,
  Execution tab via `useStream()` with `assistantId: "splunk_secops"`). Also copied into
  the shared multi-demo `frontend/src/demos/splunk_secops/` (5th tab in
  `frontend/src/App.tsx`'s `DEMOS` record) — both copies are byte-identical right now;
  see the module immediately above this one for what "keep in sync by hand" means if
  either one changes later. Also reachable via generic LangGraph Studio, through the
  same `langgraph.json` entry every demo shares.
- **`security_auditor`'s "daily scheduled" framing is a design fact, not literal cron
  code** — no demo in this repo runs anything on an actual schedule (confirmed
  nothing in this repo uses cron/APScheduler/celery/a timer of any kind). It's modeled
  via `permitted_agent_ids` on `security_auditor_policy`, locking that role to a named,
  approved service-agent identity (`soc-security-auditor-prod`), the same mechanism
  `transaction_analyst_policy` uses in `fraud_investigation.yaml`.
- **The original source-allow/deny spec had self-contradictions** (the same source
  listed as both allowed and denied for a role — copy-paste artifacts from listing
  "everything except what's allowed" by hand) — resolved by treating each role's
  allowed list as authoritative and computing `denied_sources` as the complement over
  the full 9-source set. See DESIGN.md §6 for the full reconciliation if the policy
  YAML ever looks like it's missing an entry someone expected.
- Two attack-surface tools on `splunk_threat_synthesizer_tools()` mirror
  `sar_generator_tools()`'s exactly: `get_case_agent_outputs` (session isolation —
  reaches `agent_outputs` through `incident_triage`'s session instead of its own) and
  `get_subject_racf_status` (role spoofing — synthesizer's real `agent_id` claiming
  `agent_role="security_auditor"` to reach `smf_security`). Both verified directly
  (bypassing the LLM) during development, same as fraud_investigation's README
  documents for its own equivalents.
- The audit database `examples/splunk_secops/splunk_secops_audit.db` is disposable —
  safe to delete between runs.

## Working with the hospital_revenue_cycle demo

- Follows `fraud_investigation`/`splunk_secops`'s exact architecture (LLM-driven
  `revenue_orchestrator` routing, `orchestrator_review_node` re-routing loop, a fixed
  final specialist before the synthesizer step, rule-based `decision_node` + human
  `interrupt()`) — moved into a healthcare revenue-cycle domain instead of financial
  services or security operations. See its DESIGN.md §2 for the full "adapted from a
  scripted demo" rationale — this is the one demo in the repo ported from an existing
  (but non-reasoning-driven) example rather than designed from scratch.
- **No separate synthesizer role — `revenue_orchestrator` plays both parts.** Unlike
  `sar_generator`/`splunk_threat_synthesizer`, this demo's final revenue-summary
  compilation (`revenue_summary_node`) reuses `revenue_orchestrator`'s own agent_id and
  policy rather than introducing a 7th role, since the original scripted demo's
  `revenue_orchestrator_policy` already had `agent_outputs`/`revenue_summary` as its
  own real task — see DESIGN.md §2 for why a 7th role wasn't added just to mirror the
  other demos' shape.
- `billing_compliance_agent` is the fixed final specialist (always runs after the
  4 LLM-routed specialists, before `revenue_summary`) — same slot `sar_generator`/
  `splunk_threat_synthesizer` occupy in their own demos, just not the same node that
  also does the final compilation here.
- **A real bug caught during verification**: `revenue_orchestrator_policy` and
  `billing_compliance_agent_policy` were both initially written with
  `max_sensitivity: medium`, and `cdi_specialist_agent_policy` with `high` — but each
  role's own real, allowed sources (`agent_outputs`/`billing_records` rated `high`,
  `clinical_notes` rated `critical`) exceeded that ceiling, so every legitimate call
  those three roles made was denied on a sensitivity mismatch regardless of model
  behavior — same failure shape `aml_compliance`'s own caught bug has (a task_type/
  task_bindings mismatch there; a sensitivity-ceiling mismatch here), silently
  always-denying rather than erroring. Fixed by raising each role's `max_sensitivity`
  to match its own highest-rated real source. If you add or rewire a tool here, check
  the `sensitivity_level` you're passing against that role's own `max_sensitivity` in
  `revenue_cycle.yaml` — a mismatch fails the same way and won't surface unless you
  check the live audit trail.
- `decision_node` is rule-based, grounded in the real underlying signal data
  (`hospital_revenue_cycle_data.EXPECTED_OUTCOMES`) — not any role's self-reported
  finding — same principle as every other demo's decision node. `proposed_action` is
  one of a small **fixed** set of labels (same convention as
  `aml_compliance_demo.py`'s `OVERRIDE_ACTIONS`) — the dollar amount and required
  action are carried as separate structured fields on the interrupt/disposition
  payload (`revenue_recovery`/`action_required`), not baked into the label string,
  so the frontend's override dropdown can exact-match against a small enum.
- Two attack-surface tools on `revenue_summary_tools()` mirror
  `sar_generator_tools()`/`splunk_threat_synthesizer_tools()`'s exactly:
  `get_case_agent_outputs` (session isolation — reaches `agent_outputs` through
  `billing_compliance_agent`'s session instead of its own) and
  `get_subject_billing_status` (role spoofing — `revenue_orchestrator`'s real
  `agent_id` claiming `agent_role="billing_compliance_agent"` to reach
  `billing_records`). Both verified directly during development, same as the other
  demos' equivalents — see DESIGN.md §8.
- No hosted AutoPIL SaaS trial mode, unlike the other 5 demos — out of scope for this
  round, see DESIGN.md §7.
- **Has its own standalone `examples/hospital_revenue_cycle/frontend/`** — same
  Vite + React + TypeScript structure as `splunk_secops/frontend/`, minus the
  MCP/audit-source-choice second interrupt (this demo has only the one disposition
  interrupt, same as `fraud_investigation`/`aml_compliance`). Also copied into the
  shared multi-demo `frontend/src/demos/hospital_revenue_cycle/` (see the module
  immediately above this one for what "keep in sync by hand" means if either one
  changes later).
- The audit database `examples/hospital_revenue_cycle/hospital_revenue_cycle_audit.db`
  is disposable — safe to delete between runs.

## Working with the care_coordination demo

- Follows `fraud_investigation`/`hospital_revenue_cycle`'s exact architecture
  (LLM-driven `care_coordinator` routing, `orchestrator_review_node` re-routing loop,
  rule-based `decision_node` + human `interrupt()`) — moved into a point-of-care
  healthcare domain instead of financial services or revenue-cycle billing. See its
  DESIGN.md §2 for the full "adapted from a policy file with no orchestrator and no
  task_bindings at all" rationale.
- **No fixed final specialist, unlike every other orchestrated demo in this repo.**
  `fraud_investigation`/`splunk_secops`/`hospital_revenue_cycle` all have one role that
  always runs last before the synthesizer step (`sar_generator`,
  `splunk_threat_synthesizer`, `billing_compliance_agent`). None of this demo's 4
  specialists is naturally "always last" — which one matters depends on the case (an
  acute call needs `clinical_summary_agent` last to confirm history; a refill needs
  `medication_review_agent` last) — so `care_coordinator` routes among all 4 via the
  same re-routing loop, then compiles the summary itself. One fewer graph node than
  `hospital_revenue_cycle`, not a missing piece.
- **A real bug caught during verification**: `clinical_summary_tools()`'s
  `get_vital_signs` call was bound to `task_type="care_coordination"`, but that task's
  `task_bindings.permitted_sources` in `clinical_operations.yaml` only lists
  `[ehr_summaries, care_plans, lab_results]` — `vital_signs` isn't in it, even though
  it's genuinely in `clinical_summary_agent_policy.allowed_sources`. The call was
  denied on every run regardless of model behavior, same failure shape
  `aml_compliance`'s own caught bug has (a task_type/task_bindings mismatch there and
  here). Fixed by rebinding the call to `task_type="chart_review"`, whose
  `task_bindings` already include `vital_signs`. If you add or rewire a tool here,
  cross-check its `(source, task_type)` pair against that task's
  `task_bindings.permitted_sources` directly — don't assume a source being in
  `allowed_sources` means every task binding covers it.
- `decision_node` is rule-based, grounded in real underlying signal data (actual
  vitals + cardiac history, registry overdue-days) — not any role's self-reported
  finding — same principle as every other demo's decision node. `proposed_action` is
  one of 4 small **fixed** labels, same convention as `hospital_revenue_cycle_demo.py`'s
  own fix for this (see that section above) — no dynamic strings baked in.
- Two attack-surface tools on `care_summary_tools()` mirror
  `sar_generator_tools()`/`revenue_summary_tools()`'s exactly: `get_case_agent_outputs`
  (session isolation — reaches `agent_outputs` through `clinical_summary_agent`'s
  session instead of its own) and `get_subject_medication_status` (role spoofing —
  `care_coordinator`'s real `agent_id` claiming `agent_role="medication_review_agent"`
  to reach `medication_history`). Both verified directly during development, same as
  the other demos' equivalents — see DESIGN.md §8.
- No hosted AutoPIL SaaS trial mode, unlike the 5 demos that have it — out of scope for
  this round, see DESIGN.md §7.
- **Has its own standalone `examples/care_coordination/frontend/`** — same Vite +
  React + TypeScript structure as `hospital_revenue_cycle/frontend/` (single
  disposition interrupt, no MCP/audit-source-choice second pause). Also copied into
  the shared multi-demo `frontend/src/demos/care_coordination/` (see the module
  immediately above this one for what "keep in sync by hand" means if either one
  changes later).
- The audit database `examples/care_coordination/care_coordination_audit.db` is
  disposable — safe to delete between runs.

## Working with the quality_control demo

- Follows `hospital_revenue_cycle`'s exact architecture (`orchestrator_review_node`
  re-routing loop, rule-based `decision_node` + human `interrupt()`) with one
  deliberate departure: `defect_detection_agent` always runs first via a fixed graph
  edge, not an LLM choice. Every quality case starts the same way — a defect gets
  flagged before anyone investigates why — so there's no real routing decision at
  that step; `quality_orchestrator_node` sets `route_plan =
  ["defect_detection_agent"]` directly instead of calling an LLM, the same reasoning
  `aml_compliance`'s fixed-sequence `intake_node` uses for its own deterministic
  first step. The LLM-driven re-routing only kicks in afterward, among the 3
  follow-up specialists (`spc_agent`/`supplier_quality_agent`/`calibration_agent`).
- **No fixed final specialist.** None of the 3 follow-up specialists is naturally
  "always last" — which one matters depends on the case (a calibration lapse needs
  `calibration_agent` last to confirm the overdue date; a supplier issue needs
  `supplier_quality_agent` last to confirm the open nonconformance) — so
  `quality_orchestrator` routes among all 3 via the re-routing loop, then compiles
  the finding itself.
- **A real bug caught during verification — in the fixture data, not the policy.**
  The first draft put the control-chart shift's lot-changeover correlation
  (`lot_changeover_aligned`) inside `spc_charts`, a source `defect_detection_agent`
  is legitimately authorized to read. Live-tested via the CLI path (Claude Opus),
  `defect_detection_agent` used that field to reason its way to the correct root
  cause on every case, including QC-003, **without ever attempting the
  `cost_data`/`supplier_contracts` over-scope tools** — across 6 consecutive live
  QC-003 runs it never once called them, because its own authorized read already
  ruled out a supplier/material cause. Nothing was ever denied that should have been
  allowed or vice versa — this didn't corrupt any AutoPIL decision — but it silently
  defeated the demo's own over-scope scenario: the "core over-scope" case never
  fired because the model had no reason to reach past its lane. Fixed by moving
  `lot_changeover_aligned`/`nearest_lot_changeover_days_prior` to `measurement_data`
  (a source only `spc_agent`/`calibration_agent` can read) and adding a one-line
  case-specific hint to QC-003's background naming a concrete reason to suspect a
  material substitution. Re-verified live afterward: the over-scope attempt now
  fires reliably (3/3 follow-up runs). If you add or move a data field between
  sources in this demo, check not just whether AutoPIL denies/allows it correctly,
  but whether the change removes a role's actual *reason* to reach for an
  over-scope tool at all — see DESIGN.md §7 for the fuller writeup.
- **Every `(source, task_type)` pair and every role's `max_sensitivity` were
  cross-checked against `quality_control.yaml`'s `task_bindings`/real source ratings
  *before* the first live run**, specifically to avoid the task_type/task_bindings
  mismatch `aml_compliance` caught and the sensitivity-ceiling mismatch
  `hospital_revenue_cycle` caught. No such bug was found here — all 5 roles' real,
  allowed sources are rated `low`/`medium` (matching the original stub's
  `max_sensitivity: medium` for the 4 specialists) or `high` (matching
  `quality_orchestrator`'s `agent_outputs`, ceiling set to `high` from the start) —
  see DESIGN.md §6 for the full cross-check.
- `decision_node` is rule-based, grounded in real underlying signal data
  (`quality_control_data.CALIBRATION_RECORDS`/`NONCONFORMANCE_REPORTS`/
  `MEASUREMENT_DATA`) — not any role's self-reported finding — same principle as
  every other demo's decision node. `proposed_action` is one of 5 small **fixed**
  labels (`PROPOSED_ACTIONS`), same convention as `hospital_revenue_cycle_demo.py`'s/
  `aml_compliance_demo.py`'s own fix for this.
- **A written note is required on both approve and override, not just override** —
  the one demo in this repo where `decision_node` enforces this itself rather than
  leaving it to the (not-yet-built) frontend: it loops on `interrupt()` until a
  non-empty `notes` field comes back on the resume payload. This is a deliberate,
  confirmed-effective UX choice, enforced server-side independent of whatever the
  frontend does. The CLI's `run_case()` supplies
  `"Auto-approved via CLI unattended run."` on every resume so it stays unattended.
- Two attack-surface tools on `quality_finding_tools()` mirror
  `sar_generator_tools()`/`revenue_summary_tools()`'s exactly:
  `get_case_agent_outputs` (session isolation — reaches `agent_outputs` through
  `calibration_agent`'s session instead of its own) and
  `get_subject_nonconformance_status` (role spoofing — `quality_orchestrator`'s real
  `agent_id` claiming `agent_role="supplier_quality_agent"` to reach
  `nonconformance_reports`). Both verified directly during development, same as the
  other demos' equivalents — see DESIGN.md §9.
- No hosted AutoPIL SaaS trial mode and no `saas_guard.py` — out of scope for this
  round, see DESIGN.md §8.
- **Has its own standalone `examples/quality_control/frontend/`** — same
  Vite + React + TypeScript structure as `hospital_revenue_cycle/frontend/`, minus
  the MCP/audit-source-choice second interrupt (this demo has only the one
  disposition interrupt, same as `fraud_investigation`/`aml_compliance`/
  `hospital_revenue_cycle`). Two things this demo's Execution tab handles
  differently from that template, since the backend itself behaves differently:
  the review form requires a non-empty note before Approve *or* Override can be
  submitted (`decision_node` enforces the same thing server-side, looping on
  `interrupt()` until it gets one), and the first routing event in the live feed is
  rendered as a fixed step, not a live routing decision, since
  `defect_detection_agent` running first is a plain graph edge rather than an LLM
  choice. Also copied into the shared multi-demo
  `frontend/src/demos/quality_control/` (see the module immediately above this one
  for what "keep in sync by hand" means if either one changes later).
- The audit database `examples/quality_control/quality_control_audit.db` is
  disposable — safe to delete between runs.

## Working with the trading_desk_ops demo

- Follows `fraud_investigation`'s architecture (LLM-driven orchestrator routing,
  `orchestrator_review_node` re-routing loop, rule-based `decision_node` + human
  `interrupt()`) — moved into Financial Services' trading-operations surface, two of a
  planned 5-sub-domain build (see `/TRADING_OPS_ROADMAP.md`). Equities was built
  first; Fixed Income was added second, extending the same graph/policy rather than
  duplicating it — see the Fixed Income-specific bullets below. FX/Commodities/
  International remain unbuilt.
- **`trading_ops_orchestrator`'s classification step is genuinely dynamic, not a
  fixed first step** — a deliberate departure from `quality_control`'s
  `defect_detection_agent`-always-first design. It classifies the incoming trigger
  (new order / amendment / cancellation / PM rebalance / corporate-action trade) via
  a real LLM call, and that classification decides which specialist runs FIRST: a
  new-order/amendment trigger routes through `order_intake_agent`; a PM-rebalance
  trigger (EQ-004) skips it entirely and routes straight to `allocation_agent`, since
  the PM's system already produced structured data with nothing to parse. Verified
  live that EQ-004's actual graph path differs from EQ-001's, not just that both
  complete — see its DESIGN.md §10.
- **Extensible domain registry, not a new example per sub-domain — confirmed to
  actually work, not just declared, once a second domain landed.** `TRADING_DOMAINS`
  mirrors `institutional_portfolio_review`'s `REVIEW_TYPES` shape — one dict keyed by
  sub-domain (`specialist_roles` / `first_step_by_trigger` / `skip_by_trigger` /
  `review_guidance`), now with `"equities"` AND `"fixed_income"` populated. Adding
  Fixed Income required generalizing 3 spots that were hardcoded to Equities:
  `orchestrator_review_node`'s `remaining` candidate list (was
  `EQUITIES_SPECIALIST_ROLES`, now `TRADING_DOMAINS[state["domain"]]["specialist_roles"]`),
  its re-routing prompt's "normal order" guidance (pulled into each domain's own
  `review_guidance` string), and `_reset_sessions()` (was a hardcoded equities-only
  list, now iterates `AGENT_IDS` — every registered role, across every domain).
  `build_graph()` itself needed no edge restructuring — it wires
  `ALL_SPECIALIST_ROLES` (the union of every populated domain's `specialist_roles`) as
  static nodes, and `trading_ops_orchestrator_node`'s classification call needed zero
  changes, since `domain` was already an LLM-reasoned field reading off
  `list(TRADING_DOMAINS.keys())`, not a fixed harness-level selection. A future PR
  adds `"fx"` / `"commodities"` / `"international"` as sibling entries and their own
  specialist node functions the same way. See DESIGN.md §4.
- **Two-tier human review — new mechanism when Equities shipped it, extended (not
  restructured) for Fixed Income.** `decision_node` classifies severity from real
  underlying fixture data — never any role's self-reported finding, never a
  `case_id -> tier` lookup — and routes the `interrupt()` to one of two reviewer
  tiers: Tier 1 (ops-analyst, routine corrections and proactive escalations —
  EQ-002/EQ-003/FI-003/FI-004) or Tier 2 (compliance-officer, escalated
  settlement-risk events — EQ-005 invoking Reg SHO locate-requirement logic, FI-005
  invoking FICC's named Fails Charge Trading Practice penalty instead, same tier,
  different named mechanism). Fixed Income added two more `elif` branches to the same
  function — a `pool_notification_data.deadline_at_risk` check (FI-004, fires before
  any fail) and a `fails_charge_data.fails_charge_applicable` check (FI-005, picks the
  Fails-Charge-flavored proposed-action text on the same `inventory_shortfall > 0`
  branch EQ-005 established) — without changing the function's shape. The interrupt
  payload carries `tier`/`tier_label` explicitly so a future frontend can render a
  different reviewer form per tier. A written note is required on BOTH approve and
  override, on BOTH tiers — same confirmed-effective UX choice `quality_control`'s
  `decision_node` established for one tier, applied here across two.
- **Fixed Income's three new mechanisms** (see `/TRADING_OPS_ROADMAP.md`'s
  "Sub-domain 2" section for the design source of truth): (1) **two distinct break
  types** — `affirmation_matching_agent`'s existing quantity/SSI break (equities) and
  a new day-count/accrued-interest CASH break (`AFFIRMATION_RESULTS.break_type ==
  "cash_break"`, FI-003), grounded in a real `DAY_COUNT_REFERENCE` lookup table
  (Actual/Actual for Treasuries, 30/360 for corporate/municipal/agency MBS), a
  genuinely different fixture field from `"ssi_error"`/`"timing_lag"`, not a
  relabeling; (2) **a proactive deadline escalation** — `POOL_NOTIFICATION_DATA`'s
  48-hour Pass-Thru Notification cutoff tracker (FI-004), checked in `decision_node`
  BEFORE any break-type check, so it fires on a deadline at risk before a fail
  happens, not as a reactive investigation; (3) **the FICC Fails Charge Trading
  Practice regime** — `FAILS_CHARGE_DATA` (FI-005), this domain's own named penalty
  mechanism in place of Reg SHO (which doesn't apply to Treasury/Agency MBS
  settlement at all — every FI-### case's `REG_SHO_LOCATE_DATA` entry carries an
  explicit "not applicable" stub rather than silently allowing the equities-only
  mechanism to leak in).
- **The one new role, `instrument_classification_agent`** (Fixed Income only) —
  resolves instrument type (Treasury / corporate / municipal / agency MBS-TBA) from
  CUSIP/security-master reference data into the settlement cycle and day-count
  convention. FI-002 is what happens when this goes wrong: an FNMA ticket the desk
  describes as "a Fannie Mae note, standard T+1 settlement" resolves via CUSIP lookup
  as an Agency MBS TBA pool instead — a different clearing corp (FICC MBSD, not DTCC)
  and settlement calendar (a fixed monthly SIFMA date, not T+1). Same denial shape as
  `order_intake_agent`'s over-scope tools (client account/position/pricing data), and
  its own `max_sensitivity: low` — its only real source, `security_master`, is rated
  `low`, so the ceiling was set to match it exactly rather than inherited from a
  sibling role, per the task_bindings/sensitivity-ceiling discipline below.
  `SECURITY_MASTER` itself is EXTENDED with CUSIP-keyed bond entries alongside its
  existing ticker-keyed equity entries — same dict, same getter, no new source; the
  5 genuinely new sources (`day_count_reference`, `ficc_gsd_data`, `ficc_mbsd_data`,
  `pool_notification_data`, `fails_charge_data`) were added only because no existing
  schema fit, per the same "extend, don't invent" discipline.
- **No existing autopil policy stub matched this domain** — designed from scratch
  (unlike `hospital_revenue_cycle`/`care_coordination`/`quality_control`, each
  adapted from a real stub in the sibling `autopil` repo).
  `policies/financial_services/clearing_settlement.yaml` was checked first and
  doesn't match (interbank wire/Fedwire/CHIPS clearing, not securities trade
  settlement), but its top-level `regulations:` metadata-block convention
  (`id`/`name`/`applicable_rules`/`how_enforced`) was borrowed for
  `trading_desk_ops.yaml`, populated from `TRADING_OPS_ROADMAP.md`'s own
  compliance-framework table instead (SEC Rule 15c6-1/15c6-2/15c3-3/17a-4, DTCC/NSCC
  CNS, Reg SHO, FINRA CAT, FINRA Rule 5310, information barriers/MNPI).
- **Every `(source, task_type)` pair and every role's `max_sensitivity` were
  cross-checked against `trading_desk_ops.yaml`'s `task_bindings`/real source
  ratings *before* the first live run**, same discipline `quality_control`'s
  DESIGN.md §6 established after this exact bug class recurred in
  `aml_compliance`/`hospital_revenue_cycle`/`care_coordination`. No task_bindings/
  sensitivity-ceiling bug was found here — see DESIGN.md §11 for the full cross-check.
  **Re-run for Fixed Income's additions before its first live run too** — every new
  `(source, task_type)` pair (`day_count_reference`/`ficc_gsd_data`/`ficc_mbsd_data`/
  `pool_notification_data`/`fails_charge_data` against `trade_matching`/
  `settlement_verification`/`break_triage`/`instrument_classification`) checked
  against `trading_desk_ops.yaml`'s expanded `task_bindings`, and
  `instrument_classification_agent`'s `max_sensitivity: low` checked against its one
  real source (`security_master`, rated `low`) — no mismatch found here either, see
  DESIGN.md §11a.
- **A real bug caught during verification — in the prompt design, not the policy.**
  The first live run showed `affirmation_matching_agent` checking only
  quantity/price (`trade_capture` vs `counterparty_records`) and self-reporting a
  clean match for EQ-002 **without ever calling `get_ssi_data`** — meaning the
  SSI-staleness signal never surfaced through its own reasoning, and
  `orchestrator_review_node` never routed to `exception_investigation_agent` at all.
  `decision_node`'s final disposition was still correct (it's grounded directly in
  `data.AFFIRMATION_RESULTS`/`data.SSI_DATA`, never any role's self-report), but the
  scenario's own investigative narrative didn't fire — same shape of bug
  `quality_control`'s DESIGN.md §7 documents (a fixture/prompt-design issue that let
  a role bypass its own investigative reasoning, not a policy misconfiguration).
  Fixed with a one-line `ROLE_FOCUS_HINTS` steer (mirroring
  `institutional_portfolio_review`'s convention) telling
  `affirmation_matching_agent` that same-day affirmation has two independent
  angles — quantity/price AND per-sub-account SSI currency — not just one.
  Re-verified live afterward: the role now reliably calls `get_ssi_data` and the
  EQ-002 reroute to `exception_investigation_agent` fires as designed. See
  DESIGN.md §10 for the full writeup.
- Two attack-surface tools on `compliance_report_tools()` mirror every sibling
  demo's final-role equivalent: session isolation (`get_case_agent_outputs`, reaching
  `agent_outputs` through `exception_investigation_agent`'s session instead of
  `compliance_reporting_agent`'s own) and role spoofing
  (`get_subject_settlement_status`, `compliance_reporting_agent`'s real `agent_id`
  claiming `agent_role="settlement_reconciliation_agent"` to reach `dtcc_cns_data`).
  **The session-isolation tool has a precondition worth knowing**: it only denies
  once `exception_investigation_agent`'s session has already been established by a
  real call under that role earlier in the same case (true for EQ-002/EQ-003/EQ-005,
  where it runs) — this is `guard.protect()`'s documented session-lifecycle behavior
  (a session is only "stolen" once it has an existing owner), not a bug in this demo.
  Both verified directly (bypassing the LLM) during development — see DESIGN.md §10.
- **Optional hosted AutoPIL SaaS trial mode**, added after the initial round, same
  auto-detect/`RemoteContextGuard` design as the other 5 demos — see
  `trading_desk_ops_saas_guard.py` and DESIGN.md's "Appendix: hosted trial mode". None
  of this demo's role names matched any pre-seeded policy on the shared trial
  tenant (confirmed live via `GET /v1/policies`, 112 policies checked, zero matches),
  same situation `institutional_portfolio_review`/`splunk_secops` hit — so
  `trading_desk_ops_demo.py` calls `ensure_policy()` to create dedicated
  `demo_tdo_<role>_policy` policies (one per role, including
  `instrument_classification_agent`), translated field-for-field from
  `trading_desk_ops.yaml` (including folding each regulation's `applicable_rules` into
  whichever policy its own `how_enforced` text names — `CreatePolicyRequest` now has
  a `regulations` field, confirmed live against the OpenAPI schema, a genuine schema
  change from what `institutional_portfolio_review`'s/`splunk_secops`'s own
  `ensure_policy()` found). `owner_tag="Trading-Desk-Ops-team"` /
  `owner_team="Meridian Bank"`. Confirmed live: EQ-001 (clean straight-through) and
  EQ-003 (information-barrier scenario) both ran end-to-end in hosted mode with
  legitimate calls allowed and over-scope/role-spoofing/session-isolation attempts
  denied remotely; `GET /v1/audit/sessions/{id}` with the Admin key read both audit
  trails back correctly. **Known gap, front and center because it's an active local
  mechanism, not a hypothetical one**: this demo's `trading_desk_ops.yaml` sets
  `session_ttl_minutes: 1440` (24-hour cap) on every role — confirmed live against
  the real OpenAPI schema and an actual returned policy object that
  `CreatePolicyRequest`/the hosted policy object has no `session_ttl_minutes` (or
  `permitted_agent_ids`/`sensitivity_decay`) field at all, so that 24-hour cap is
  **not enforceable the same way remotely** — hosted mode is additive, not a
  replacement for local enforcement. **A separate, pre-existing environment issue
  found while adding Fixed Income, unrelated to this sub-domain's own build**: in this
  repo's current environment, `bootstrap_agents()` fails with `409 Conflict` on
  `POST /v1/agents` even for the original, unmodified Equities-only code (confirmed by
  re-running the exact pre-Fixed-Income file with the same env) — the shared trial
  tenant's agent-role registration has drifted from a clean state independent of
  anything in this round's change. Local mode (unset `AUTOPIL_ADMIN_KEY`/
  `AUTOPIL_EVALUATE_KEY`) is unaffected and is what this round's own verification
  used — see DESIGN.md §11a.
- **Has its own standalone `examples/trading_desk_ops/frontend/`** — same
  Vite + React + TypeScript structure as `quality_control/frontend/`, minus the
  MCP/audit-source-choice second interrupt (this demo has only the one disposition
  interrupt, same as `fraud_investigation`/`aml_compliance`/`quality_control`). Two
  things this demo's Execution tab handles differently from that template, since the
  backend itself behaves differently: the orchestrator's classification event renders
  as a live "ROUTE" decision (never a "FIXED STEP" badge — that badge is specific to
  `quality_control`'s fixed first step, not applicable here since this classification
  is genuinely dynamic), with any role the classification determined is not
  applicable to the trigger (e.g. `order_intake_agent` on EQ-004's PM-rebalance path)
  rendered as a distinct "skipped" row so EQ-001 and EQ-004 visibly take different
  paths; and the review panel renders a visibly different tier — a Tier 1
  (ops-analyst) review gets an accent badge/border, a Tier 2 (compliance-officer)
  review (the Reg SHO escalation path, EQ-005) gets a red badge/border — with the same
  non-empty-note-required-on-both-approve-and-override enforcement `quality_control`'s
  reviewer form established, applied here at both tiers. Also copied into the shared
  multi-demo `frontend/src/demos/trading_desk_ops/` (see the module immediately above
  this one for what "keep in sync by hand" means if either one changes later).
- The audit database `examples/trading_desk_ops/trading_desk_ops_audit.db` is
  disposable — safe to delete between runs.
