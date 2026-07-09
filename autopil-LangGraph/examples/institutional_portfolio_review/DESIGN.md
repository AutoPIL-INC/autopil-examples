# Institutional Portfolio Review Multi-Agent Demo — Design Doc

Status: implemented — see `institutional_portfolio_review_demo.py`, `README.md`
Depends on: real `autopil` package (`autopil[langgraph]>=0.10.0` from PyPI)

## 1. Why this demo, and why now

The fraud investigation and client analysis demos in this repo each enforce one
policy file per demo. Real institutional wealth operations rarely work that way — a
single client review touches roles that report up through different functions
(advisory, risk, compliance, operations), each governed by policy someone else owns.
This demo shows AutoPIL holding a governance boundary across **two independently
authored policy files at once**, where which file governs a given call depends on
*who's asking*, not what they're asking for — the same underlying data
(`credit_scores`, `loan_history`, `identity_records`, `risk_models`) is reachable by
roles from both files, each evaluated under its own file's rules, completely
independently.

## 2. Source review — what's real, what's aspirational

Ported from the private `autopil` monorepo's
`examples/institutional_portfolio_review/`, which itself depends on two real product
policy files (`policies/financial_services/wealth.yaml` and `risk_compliance.yaml` —
not demo-scoped copies). Several things needed correcting, not just translating:

- **The source is fully scripted** — no LLM calls at all. "Violation attempts" are
  direct Python function calls with hardcoded session/source combinations. This demo
  replaces that with real tool-calling loops, same as the other two demos in this repo.
- **The README's "11 agents" claim is aspirational relative to the actual code.** The
  source's wired LangGraph graph only has 9 specialist nodes — `kyc_agent` and
  `settlement_agent` are never wired into `g.add_node`/`g.add_edge`, despite both
  having tool functions. `settlement_agent` has **no matching policy entry at all** in
  the real `wealth.yaml` — every call it made would have been denied by default. Both
  are wired into this demo's graph; `settlement_agent` gets a new policy (§4).
- **Two roles in the real policy files aren't part of this demo's cast**:
  `intake_agent_policy` (in `wealth.yaml`) and `compliance_agent_policy` (in
  `risk_compliance.yaml`) belong to a different onboarding-workflow demo that happens
  to share these production files. Neither is named in the source's own docstring role
  list. Excluded here, along with the two sources only `intake_agent` referenced
  (`application_forms`, `medical_records`).
- **`require_principal_entitlements`** appears throughout both real policy files (e.g.
  `wealth_advisor_policy` requiring `group:licensed-advisors` for its core sources).
  Verified directly against the installed SDK's `policy_engine.py`
  (`_check_principal_entitlements`): it evaluates against `request.principal_claims`,
  which is only ever set by the hosted REST API layer (`app.py`) before evaluation —
  `guard.protect()`'s embedded decorator, used by every demo in this repo, never sets
  it. Any rule with `require_any`/`require_all` therefore denies unconditionally via
  the SDK path — carrying these over as written would make `wealth_advisor` (and
  others) unable to ever succeed, breaking the happy-path review. **Not ported.**
  Documented here rather than silently dropped, since it's a real capability gap
  between the embedded SDK and the hosted API worth knowing about independent of this
  demo.
- Several risk-side sources have **no real fixture data in the source at all** —
  `audit_logs`, `transaction_history`, `delinquency_records`, `trade_confirmations`,
  `counterparty_data` are wired as empty `{}` placeholders in the source's `SOURCES`
  dict. Real (if thin) fixture rows were invented for all of them here.

## 3. Design approach: same toolbelt across two catalogs, policy decides what succeeds

| | This demo |
|---|---|
| Tool access per role | Identical across all 11 roles — every source across both `catalog.wealth.*` and `catalog.risk.*` catalogs, every time |
| Which policy governs a call | A property of the **calling role**, not the source — `ROLE_GUARD` maps each role to `wealth_guard` or `risk_guard` |
| Role reasoning | Real tool-calling loop per role (`run_tool_loop()`, same shared pattern as the other two demos) |
| Orchestration | LLM classifies the request into a `review_type`, which maps to a real ordered role/task sequence — models an actual workflow, not a scripted violation |
| Escalation | One modeled path: `fiduciary_benchmark` → `wealth_advisor` denied → `investment_analyst` (the correctly-authorized role) |
| Outcome classification | Per-role, grounded in the real audit trail — a self-reported `COMPLETED` is only trusted if that role's own session shows a real `ALLOW` |

The "same tools for everyone, across both catalogs" design is the same principle
`client_analysis` established, extended to two policy files: giving every role the
full cross-catalog surface removes any ambiguity about whether a denial came from the
tool layer or from AutoPIL — it's always AutoPIL.

## 4. The two policy files

`policies/financial_services/portfolio_review_wealth.yaml` (7 roles: `portfolio_orchestrator`,
`wealth_advisor`, `investment_analyst`, `kyc_agent`, `macro_analyst`,
`rebalancing_agent`, `report_generator`) and `portfolio_review_risk.yaml` (4 roles:
`compliance_officer`, `credit_risk_analyst`, `aml_investigator`, `settlement_agent`) —
direct translations of the real production files, keeping every
`allowed_sources`/`denied_sources`/`allowed_tasks`/`denied_tasks`/`task_bindings`/
`max_sensitivity`/`require_task_for_sensitivity`/`session_ttl_minutes`/
`sensitivity_decay` value as-is, dropping only `require_principal_entitlements` (§2)
and the two excluded roles.

**`settlement_agent_policy` is new** — the source demo's `settlement_agent` had tool
functions but no policy anywhere. Added to the risk file (operational risk domain fits
better than wealth advisory): `allowed_sources: [trade_confirmations,
counterparty_data]`, `denied_sources: [portfolio_holdings, client_profile]`,
`task_bindings` for `trade_settlement`/`counterparty_verification`.

**`investment_analyst_policy.max_sensitivity` was raised from `medium` to `critical`**
relative to what a literal translation would produce. This demo deliberately grants
`investment_analyst` access to `other_client_portfolios` (critical sensitivity, for
peer benchmarking) — a grant the source demo never needed, since it never gave this
role that source at all. Live-tested and caught directly: leaving the ceiling at
`medium` silently blocked the very source the role's `allowed_sources`/`task_bindings`
say it's authorized for, contradicting the policy's own grant. This is the kind of
policy-authoring mistake AutoPIL is *supposed* to catch — worth naming, not glossing
over.

## 5. Data model: two simulated Unity Catalog schemas

`portfolio_review_uc_data.py`, same technique as `client_analysis`'s — Python fixtures with
`sensitivity_level`/`data_classification` tags, `catalog.schema.table` source IDs.

- **`catalog.wealth.*`** — `client_profile`, `portfolio_holdings`,
  `other_client_portfolios`, `rebalancing_instructions`, `market_data`,
  `product_catalog`, `research_reports`, `internal_pricing_models`,
  `executive_communications`, `macro_indicators`, `economic_indicators`,
  `sec_filings`, `geopolitical_signals`, `regulatory_templates`, `agent_outputs`,
  `portfolio_metrics`. 12 of these carry the source demo's actual fixture data (3
  institutional clients — Harrington University Endowment, Meridian Family
  Foundation, Cascade Industrial Pension Trust); the rest are small, newly invented.
- **`catalog.risk.*`** — `account_summaries`, `audit_logs`, `regulatory_filings`,
  `transaction_history`, `delinquency_records`, `board_materials`, `watchlist`,
  `counterparty_data`, `personal_hr_records`, `marketing_data`,
  `internal_risk_models`, `trade_confirmations`, plus `credit_scores`,
  `loan_history`, `identity_records`, `risk_models` — the four sources shared across
  both policy files. Most non-`watchlist`/`account_summaries` tables here are thin,
  invented decoys: several are never in *any* kept role's `allowed_sources`, so a tool
  for them is always offered but never expected to succeed for anyone.

## 6. Graph design

`orchestrator_node` looks up the request brief from `request_id`
(`ucdata.PORTFOLIO_REVIEW_REQUESTS`), classifies it into a `review_type` (forced
structured output, same `_bind_forced()` helper as `client_analysis`), and expands
that into `roles_plan` — an ordered list of `[role, task_type]` pairs:

```python
REVIEW_TYPES = {
    "quarterly_review": [["investment_analyst", "market_analysis"], ["wealth_advisor", "portfolio_review"],
                          ["rebalancing_agent", "rebalancing_recommendation"], ["report_generator", "quarterly_review"]],
    "fiduciary_benchmark": [["wealth_advisor", "portfolio_review"]],
    "aml_case": [["aml_investigator", "sar_generation"], ["kyc_agent", "kyc_check"], ["compliance_officer", "cross_client_audit"]],
    "credit_limit_review": [["credit_risk_analyst", "limit_review"]],
    "trade_settlement_check": [["macro_analyst", "macro_analysis"], ["settlement_agent", "trade_settlement"]],
}
```

Originally `quarterly_review` was a single 6-role chain (also including `macro_analyst`
and `settlement_agent`). Live-tested and found to converge poorly — every extra role in
a chain is another chance for one step to stall, and 6 compounded that risk badly
enough that most runs ended up only partially complete, reading as broken rather than
as a governance story. Split into a 4-role `quarterly_review` plus a new
`trade_settlement_check` (2 roles) — same 11-role coverage across 5 shorter chains
instead of 4 longer ones, and each chain now converges far more reliably (see §6.1).

Each role in the plan runs as its own graph node (`_make_role_node` generates a thin
wrapper per role — LangGraph's conditional edges need statically known node names, and
there are only 11 to enumerate), routes to `orchestrator_review` on completion, which
either continues to the next step in the plan, escalates once (only
`fiduciary_benchmark` has an escalation target — `ESCALATION` maps it to
`investment_analyst`/`benchmarking`, mirroring the source's Scenario 2 exactly), or
moves to `decision` once the plan is exhausted.

`task_type` is constant across every tool call within one role's step — assigned once
by the plan, not hardcoded per tool — so `task_bindings` purpose limitation can
actually fire: the same source can succeed under one task and fail under another, for
the identical role.

### Toolbelt-size finding (verified live)

With 32 tools available, Ollama's `qwen2.5:7b` calls most/all of them in one big batch
per turn and doesn't reliably include `submit_finding` in that batch — it repeats the
*same* batch turn after turn instead of concluding, which the fraud/client_analysis
demos' smaller toolbelts never triggered. `run_tool_loop()` here appends an explicit
message after every turn without a finding — a soft nudge on early turns ("call
submit_finding instead of repeating tools you've already called"), an explicit
prohibition on the last turn ("do not call any more data tools"). This measurably
worked: an early test run without this fix logged 93 denials on the happy-path
scenario alone (repeated identical batches); with it, that dropped to single digits
per scenario, matching individually-legitimate policy enforcement rather than
runaway repetition.

`ROLE_FOCUS_HINTS` adds one more line to each step's brief — a steer toward the
*category* of data that step is about (e.g. `report_generator`: "you compile this
report from what OTHER agents have already found — check compiled agent outputs
before reaching for anything else"), not which tool to call. The fraud and
client_analysis demos never needed this — their toolbelts are small enough that a
generic "gather what you need" brief was already enough to converge. Combined with the
shorter role chains (above), this took the demo from mostly `PARTIALLY BLOCKED` runs to
mostly clean completions in live testing.

## 7. Human-in-the-loop review

Before the outcome is finalized, `decision_node` pauses via LangGraph's `interrupt()`
and waits for a supervisor to Approve or Override it, with optional notes — the same
mechanism and the same before/after-`interrupt()` side-effect split as
`fraud_investigation_demo.py`'s `decision_node` (everything computing
`proposed_outcome` must be pure/cheap, since `interrupt()` re-executes the node from
the top on resume; everything after only runs once). The CLI (`run_request()`) stays
fully unattended — it builds its own checkpointed graph instance
(`build_graph(checkpointer=InMemorySaver())`) and auto-approves via
`Command(resume={"approved": True})` if it hits an interrupt; the module-level `graph`
exposed to `langgraph dev` stays checkpointer-free, since the platform manages
persistence itself and refuses to load a graph pre-compiled with one.

Verified live against the real streaming API (not just the CLI path): created a thread
explicitly via `POST /threads`, ran a request against it, confirmed the interrupt
payload matches the frontend's `InterruptPayload` type field-for-field, then resumed
with `Command(resume={"approved": false, "override_outcome": ..., "notes": ...})`
against the same thread and confirmed the `disposition` event reflects the override
exactly.

## 8. Decision node — grounded in the audit trail, not self-report

Same principle as `client_analysis`'s fix, applied per-role across a whole review:
for each completed step, check whether that role's own audit-trail session shows at
least one real `ALLOW` before trusting a self-reported `COMPLETED`. A role can
legitimately end a step self-reporting `BLOCKED` even after getting real data back
(live-observed) — a conservative model judgment that it didn't have *enough*, not a
bug; `decision_node` doesn't try to second-guess that call, only the reverse case
(claiming success with zero real data).

Denial reasons are classified by matching AutoPIL's actual returned reason strings
(same `_classify_denial()` logic as `client_analysis`, extended with two patterns this
demo's roles can hit that the other demo's roles don't: `"isolation"`/`"owned by"` for
session-isolation denials, and `"not permitted to act as"` for role-claim denials).

## 9. Appendix: what a real Unity Catalog / hosted deployment would require

Same shape as `client_analysis`'s appendix — not attempted or tested here, described
for completeness:

1. Create the tables in real Unity Catalog schemas (`wealth`/`risk`) tagged with
   `sensitivity_level`/`data_classification` matching `TABLE_PROPERTIES`.
2. Read tags back via `SHOW TBLPROPERTIES` rather than hardcoding them.
3. Swap `SOURCES`'s dict lookups for real Spark SQL reads, keeping the same
   `guard.protect()` wrapper per call.
4. For a hosted-API deployment (not the embedded SDK this demo uses),
   `require_principal_entitlements` becomes usable — the REST layer would need to
   populate `principal_claims` from whatever identity/entitlement system authenticates
   the human behind the request, which the embedded SDK path has no hook for.

## 10. Appendix: hosted trial mode

Implemented — see `ipr_saas_guard.py` and the `_SAAS_MODE` block in
`institutional_portfolio_review_demo.py`. Same `RemoteContextGuard`/
`bootstrap_agents()` design as the other 3 demos' hosted mode, but this demo needed a
genuinely new capability none of the others did: `ensure_policy()`, which creates
policies via `POST /v1/policies` rather than only reusing pre-seeded ones. See
README.md's own "Hosted AutoPIL SaaS trial mode" section for how to get a trial
account and Admin/Evaluate keys — this appendix covers what was verified, not setup
steps.

Verified live against the same real trial tenant used for the other 3 demos
(`https://autopil-api.onrender.com`, 2026-07-10):

1. **None of this demo's 8 pre-seeded role policies on the shared trial tenant
   actually match** — checked directly, not assumed. Every one of them uses *plain*
   source names (`client_profile`, `portfolio_holdings`); this demo's local YAML uses
   `catalog.wealth.*`/`catalog.risk.*` prefixed names (a real Unity-Catalog-style
   convention this demo specifically models, unlike the flatter naming the other 3
   demos use). Binding to any pre-seeded policy as-is would deny every call for a
   naming mismatch, not real enforcement.
2. **`ensure_policy()` creates 8 new policies instead**, named `demo_ipr_<role>_policy`
   — translated field-for-field from `portfolio_review_wealth.yaml`/
   `portfolio_review_risk.yaml` via `POST /v1/policies`, so this demo's own source
   naming never had to change. `session_ttl_minutes`/`sensitivity_decay` are omitted
   from every created policy — no such field exists on `CreatePolicyRequest`, confirmed
   against the real OpenAPI schema, same disclosed gap the other 3 demos already carry
   for different local mechanisms.
3. **A real cross-demo collision, caught live**: a first attempt used the generic
   `owner_tag="autopil-langgraph-demos"` and `demo_<role>_policy` naming (matching
   `client_analysis`'s own convention) for this demo's agent bootstrap. Because this
   demo's `wealth_advisor` role name is the same as `client_analysis`'s, and
   `bootstrap_agents()` only de-dupes agents by `(agent_role, owner_tag)` — not by
   which demo is asking — the attempt silently reused `client_analysis`'s existing
   `wealth_advisor` agent, and would have skipped creating this demo's own
   `demo_wealth_advisor_policy` too, since `ensure_policy()` only checks for a name
   match (that name already existed, bound to `client_analysis`'s
   `catalog.finance.*` sources, not this demo's `catalog.wealth.*` ones). Fixed with a
   demo-specific `owner_tag` (`Investments-team`) and policy prefix
   (`demo_ipr_<role>_policy`) — confirmed via a second bootstrap run producing 8 fresh,
   distinct `agent_id`s, and confirmed the `wealth_advisor` agent's `policy_name` came
   back as `demo_ipr_wealth_advisor_policy`, not the shared one.
4. **Module name collision, caught live**: this demo's `saas_guard.py` was originally
   named identically to the other 3 demos' copies (a per-demo-module-name rule this
   repo's root `CLAUDE.md` already documents for data-fixture modules, but hadn't yet
   been applied to `saas_guard.py`). The moment this demo's copy grew an
   `ensure_policy()` function the others lacked, `langgraph dev` crashed on startup —
   whichever demo's graph loaded first "won" the `sys.modules['saas_guard']` slot for
   every demo, and `fraud_investigation`'s copy (loaded first, no `ensure_policy()`)
   got silently imported everywhere instead. Renamed every demo's copy to a
   demo-specific module name (`fraud_saas_guard.py`, `client_analysis_saas_guard.py`,
   `ipr_saas_guard.py`, `aml_saas_guard.py`).
5. **`wealth_guard`/`risk_guard` collapse into the same `RemoteContextGuard` instance
   in SaaS mode** — the hosted API is one tenant with one evaluate endpoint regardless
   of which local YAML file a policy conceptually belongs to, so there's no need for
   two remote guard instances the way local mode needs two `ContextGuard`s.
6. **A live full-case run** (PORT-001, quarterly_review, 4 roles, via Ollama) against
   the hosted API produced real `task_bindings` denials (`wealth_advisor` reaching for
   `catalog.wealth.macro_indicators`/`catalog.wealth.market_data` outside its
   `portfolio_review` task binding) and the same disposition shape as local mode
   (`COMPLETED WITH GOVERNANCE INTERVENTION`).
