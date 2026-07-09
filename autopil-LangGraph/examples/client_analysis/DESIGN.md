# Client Analysis Multi-Agent Demo — Design Doc

Status: implemented — see `client_analysis_demo.py`, `README.md`
Depends on: real `autopil` package (`autopil[langgraph]>=0.10.0` from PyPI)

## 1. Why this demo, and why now

Unity Catalog gives Databricks shops a real, queryable classification layer —
`sensitivity_level`/`data_classification` table properties — but classification isn't
enforcement. Knowing a table is `critical` doesn't stop an agent from reading it; it's
just metadata unless something actually checks it at retrieval time, per call, for the
specific role and purpose making the request.

This demo shows that check happening against the same governance problem the fraud
investigation demo demonstrates, but through a different lens: instead of one
investigation with multiple specialist roles collaborating, this is one shared toolbelt
handed to three roles with very different authorization levels, and the enforcement
question is "does policy hold regardless of which role reaches for what, and why."
Two enforcement paths get specific attention here that the fraud demo's policies don't
exercise as cleanly: `task_bindings` purpose limitation (a source can be allowed for a
role in general, but not for the specific task/purpose it's being requested under) and
the sensitivity ceiling (`max_sensitivity` blocking a source regardless of source-level
authorization).

## 2. Design approach: same toolbelt, policy decides what succeeds

| | This demo |
|---|---|
| Tool access per role | **Identical across all three roles** — all 8 Unity Catalog tables, every time. Policy, not the tool layer, decides what succeeds. |
| Role reasoning | Real tool-calling loop per role (same `run_tool_loop()` the fraud demo uses, reused unmodified) |
| Task assignment | Deterministic per case: `simulated_uc_data.CLIENT_REVIEWS[customer_id]["tier_tasks"]` says what task a tier works on *if* it reaches that tier — a lookup, not a model decision |
| "Violation attempts" | Emergent — the model decides for itself, given its assigned task, whether it needs a source outside its role's authorization or outside that task's purpose |
| Escalation | Human-in-the-loop, at **every** tier: a case starts at `junior_analyst` and can progressively escalate through `senior_analyst` to `wealth_advisor`, with a human approving, overriding, or escalating the proposed action at each tier it reaches — up to 3 review points per case |
| Governance enforcement | `guard.protect()` on every tool call, with `task_type` threaded through so `task_bindings` purpose limitation can actually fire |
| Outcome classification | Grounded in the real audit trail (did the role get any `ALLOW`), not any tier's self-reported finding alone — see §7.4 |

The "same tools for everyone" design is deliberate, not incidental: it's the cleanest
way to show that authorization lives in the policy layer. If each role had a
different, pre-filtered toolbelt, a denial firing would be ambiguous — did the tool
layer already prevent the attempt, or did AutoPIL? Giving every role the full 8-table
surface removes that ambiguity entirely.

## 3. Non-goals

- Not adding new AutoPIL features. This demo exercises what exists today
  (`ContextGuard.protect`, `task_type`/`task_bindings`, sensitivity ceiling, audit
  trail).
- Not connecting to a real Databricks Unity Catalog workspace or writing to a real
  Delta audit table. Local Python fixtures are sufficient to demonstrate the
  governance mechanism; a live workspace would add setup cost with no payoff for this
  repo's audience (see the appendix for what that would actually require).
- Not guaranteeing the sensitivity-ceiling path fires from the 5 shipped customer
  cases. Verified against the real policy evaluation order (`policy_engine.py`):
  `task_bindings` is checked *before* the sensitivity ceiling, and every
  `senior_analyst_policy` task binding that exists (`credit_analysis`,
  `risk_assessment`) already excludes `stress_test_models` from its permitted
  sources — so a case assigned to either of those tasks hits `task_bindings`
  first, never reaching the ceiling check. The ceiling is only reachable if
  `senior_analyst` is assigned a task with *no* binding entry (`market_research`,
  `portfolio_review`, `client_reporting`) and still reaches for `stress_test_models`
  under that task — plausible, but not engineered to happen, consistent with this
  demo's own "not scripted" philosophy (§9). The mechanism is real and present in the
  policy; it's disclosed here rather than silently claimed as guaranteed-observable.
- Not computing a PIL score or chain-verification digest. Mentioned in the original
  Databricks demo's README this was adapted from, but never actually implemented in
  the fraud investigation demo either — not inventing new AutoPIL API usage without
  verifying it exists in the installed SDK version first. The audit trail reuses
  exactly what the fraud demo proved out: `guard.get_audit_trail(session_id)`.

## 4. Folder structure

```
examples/client_analysis/
├── DESIGN.md                                        # this file
├── README.md                                        # setup + run instructions
├── simulated_uc_data.py                             # 8 simulated UC tables + 5-customer review queue
├── policies/financial_services/client_analysis.yaml   # the 3-role policy matrix
├── client_analysis_demo.py                    # the LangGraph graph
└── frontend/                                         # live audit-trail viewer (same scaffold as fraud_investigation/frontend)
```

## 5. Environment

- Additional dependency: `autopil[langgraph]>=0.10.0`, published to PyPI — listed
  directly in `requirements.txt`, shared with the fraud investigation demo.
- `langchain-aws` for `ChatBedrockConverse` — also shared, added to `requirements.txt`.
- Bedrock needs `AWS_BEDROCK_MODEL_ID` set (explicit opt-in) plus AWS credentials
  configured the normal way (env vars, `~/.aws/credentials`, or `AWS_PROFILE`) and
  model access enabled for that model ID in the Bedrock console.

## 6. State shape

```python
class ClientReviewState(TypedDict):
    customer_id: str
    provider: str
    reason_for_review: str        # looked up server-side from customer_id, not client-supplied
    current_tier: str             # the tier whose review node is (about to be) running
    tiers_visited: list[str]      # >1 entry only if escalation happened
    findings: dict                 # {tier: {"summary": str, "proposed_action": str, "recommend_escalation": bool, "sources_used": [...]}}
    human_decisions: dict          # {tier: {"decision": "approve"|"override"|"escalate", "override_action": str|None, "notes": str|None}}
    denial_log: list[dict]
    final_action: str
    closed_at_tier: str
```

`reason_for_review` is populated by `intake_node` from
`simulated_uc_data.CLIENT_REVIEWS` using only `customer_id` — the same pattern the
fraud demo uses for `alert`/`case_metadata` (looked up server-side from `case_id`), so
the live viewer's client never needs to send more than an ID.

## 7. Node design

### 7.1 Intake (deterministic, not LLM-driven)

- Looks up `simulated_uc_data.CLIENT_REVIEWS[customer_id]`, seeds `reason_for_review`
  and `current_tier: "junior_analyst"` — every case starts at the same tier. No model
  call: which task a tier works on is pre-designed per case (`tier_tasks`), so there's
  nothing to classify, unlike the old single-role orchestrator this replaced.

### 7.2 Role agents (junior_analyst, senior_analyst, wealth_advisor)

- Each is the exact same tool-calling loop (`run_tool_loop()`, reused unmodified from
  the fraud demo) with the exact same 8-tool toolbelt (`role_tools()`) — only
  `agent_role`/`agent_id`/`task_type` differ per role/case, built by the
  `_make_role_node(role)` factory.
- `task_type` comes from `CLIENT_REVIEWS[customer_id]["tier_tasks"][role]`, falling
  back to `DEFAULT_TIER_TASK[role]` if a human escalates a case past what it was
  designed to reach — deterministic, not assigned by a model. That's what makes
  `task_bindings` purpose limitation meaningful here: the same source (e.g.
  `customer_pii`) can succeed under one `task_type` and fail under another, for the
  identical role.
- Each tier submits a `proposed_action` (one of `CLIENT_ACTIONS` — a concrete
  next-best-action for the client, not a governance label) and a
  `recommend_escalation` boolean, via the shared `submit_finding` schema.
- Not every model honors a required schema field strictly — live-tested with Ollama's
  `qwen2.5:7b`: `proposed_action` came back missing/`None` on some turns despite being
  required. `_run_role` coerces it to a safe default (`FLAG FOR COMPLIANCE / RISK
  REVIEW`, forcing `recommend_escalation: True`) rather than letting an invalid action
  reach the review panel — same defensive-coercion pattern as the old orchestrator's
  `task_type` handling this replaced.

### 7.3 Review nodes (human-in-the-loop, once per tier)

- `_make_review_node(role, next_role)` builds one review node per tier.
  `interrupt()`s with `{customer_id, tier, finding, denial_log, can_escalate,
  next_tier}` — `can_escalate` is `False` only for `wealth_advisor` (top of the chain).
- On resume, the human's `{"decision": ...}` is one of:
  - `"approve"` — finalizes with the tier's own `proposed_action`
  - `"override"` — finalizes with the human's chosen action from `CLIENT_ACTIONS`
  - `"escalate"` — routes to `next_role`'s node (only offered when one exists)
- A case can pause up to 3 times (once per tier it reaches) before it closes. The CLI's
  `run_request()` loops over `"__interrupt__" in result` rather than the single `if` the
  fraud/portfolio-review demos use, since a single run here can interrupt more than
  once. Auto-decision mirrors what the tier itself recommended: `"escalate"` if
  `recommend_escalation` and `can_escalate`, else `"approve"`.
- Escalating doesn't guarantee a clean outcome at the next tier — the same
  `task_bindings`/sensitivity-ceiling denials can fire there too; escalation changes
  who's asking, not what they're authorized for.

### 7.4 `_finalize` — grounded in the audit trail, not any tier's self-report

`_finalize` (called from whichever review node closes the case) doesn't just take a
tier's `proposed_action` at face value once a human has approved or overridden it — the
disposition it emits carries the real audit trail (`_collect_audit_summary()`), not a
model's summary of it, same spirit as the fraud demo's decision being grounded in real
data rather than LLM-improvised (its own §7.4).

Denial reasons are classified into one of four mechanisms by matching against
AutoPIL's actual returned reason strings (verified against the installed
`policy_engine.py`, not guessed): `denied_sources`, `denied_tasks`, `task_bindings`
(purpose limitation), and `sensitivity ceiling`.

## 8. Governance surface being demonstrated

| AutoPIL mechanism | What this demo exercises |
|---|---|
| `guard.protect()` role/source matrix | Every tool call, regardless of role or how many turns of reasoning led to it |
| `task_type` / `task_bindings` | Purpose limitation — a source allowed for a role in general can still be denied for the wrong task |
| Sensitivity ceiling (`max_sensitivity`) | `senior_analyst_policy` sets `max_sensitivity: high`, not `critical` — `stress_test_models` is blocked by the ceiling when reachable (see §3's non-goal note on when `task_bindings` preempts this) |
| Audit trail | `guard.get_audit_trail()` per session, same mechanism as the fraud demo |
| Agent registry / `agent_id` | All 4 roles registered via `SQLiteAgentRegistryStore`, required on every guarded call as of autopil `0.10.0` |
| Human-in-the-loop review | `interrupt()`/`Command(resume=...)` per tier, same mechanism as the fraud/portfolio-review demos, but up to 3 times in a single run instead of once |

## 9. Scenarios

Five customers, mixed complexity, run through the tiered-escalation graph.
Non-determinism is disclosed as a property of the demo, not hidden — see
`simulated_uc_data.CLIENT_REVIEWS` for the exact `tier_tasks` per case:

- **C001** — designed to close at `junior_analyst` (`portfolio_review` only).
- **C002** — designed to reach `senior_analyst` (`market_research` →
  `credit_analysis`), nudging toward a `credit_analysis` task_type that
  `task_bindings` restricts to `credit_scores`/`risk_models` only.
- **C003** — designed to reach `wealth_advisor` (`portfolio_review` →
  `credit_analysis` → `wealth_planning`) — the one case that exercises the full
  3-tier chain, since `wealth_planning` is exclusively a `wealth_advisor` task.
- **C004** — designed to reach `senior_analyst` (`portfolio_review` →
  `risk_assessment`), a different senior-tier task than C002.
- **C005** — designed to close at `junior_analyst` (`client_reporting` only).

Whether a case actually reaches the tier it's designed for depends on what each tier's
own finding recommends and what the human reviewer decides — not guaranteed on every
run, same "not scripted" philosophy as every other demo in this repo. `tier_tasks` is
never shown on the live viewer's queue card (only `reason_for_review`/`priority`/
`opened` are) — showing it would give away how far a case is designed to escalate
before the investigation gets there.

## 10. Open questions / verified live during implementation

1. **`_bind_forced()`/forced `tool_choice` no longer applies to this demo.** The prior
   design used a forced single-tool call for the orchestrator's role/task assignment
   and its escalation decision — both LLM-driven decisions. Neither exists anymore:
   `intake_node` looks up the tier chain deterministically, and escalation is a human
   decision via `interrupt()`. Every remaining `bind_tools()` call in this file
   (inside `run_tool_loop()`) is already unforced, since a role choosing which data
   tool to call next is exactly the open-ended decision this demo wants to observe.
   Removed the now-dead `_bind_forced()`/`_ALWAYS_SUPPORTS_FORCED_CHOICE` rather than
   leave unused code behind — the Bedrock/Ollama `tool_choice` divergence this handled
   is still real (see the fraud/portfolio-review demos, which still force a tool for
   their own single-decision nodes), just no longer exercised here.
2. **Cost/latency** — same shape as the fraud demo: each role is a multi-turn
   tool-calling loop, not one `llm.invoke()`. Acceptable for a demo script.
3. **Iteration caps** — `MAX_TOOL_TURNS` bounds each role's loop; the fixed 3-tier
   chain (`junior_analyst → senior_analyst → wealth_advisor`, no cycles) bounds the
   escalation path — a case can never revisit a tier it already left.
4. **The CLI's auto-approve loop has to be a `while`, not an `if`.** Every other
   human-in-the-loop demo in this repo (fraud, portfolio-review) pauses at most once
   per run, so `if "__interrupt__" in result: ...` suffices. Here a single case can
   pause up to 3 times — live-tested across all 5 customers via Ollama, confirming the
   `while "__interrupt__" in result: result = graph.invoke(Command(resume=...), ...)`
   loop correctly drives 1-tier, 2-tier, and 3-tier runs to completion without hanging.
5. **Full 3-tier escalation verified against the real streaming API**, not just the
   CLI path — created a thread via `POST /threads`, ran C003, resumed at
   `junior_analyst` with `{"decision": "escalate"}`, confirmed the `senior_analyst`
   interrupt appeared with `next_tier: "wealth_advisor"`, resumed again with
   `{"decision": "escalate"}`, confirmed the `wealth_advisor` interrupt appeared with
   `can_escalate: false`, resumed with `{"decision": "approve"}`, and confirmed the
   final disposition showed `closed_at_tier: "wealth_advisor"`, all 3 tiers in
   `tiers_visited`, and all 3 human decisions recorded correctly.

## 11. Appendix: running against a real Databricks Unity Catalog workspace (not this round)

This demo runs entirely on local Python fixtures — `simulated_uc_data.py` — so it
works with `pip install -r requirements.txt` and nothing else. If/when pointing this
at a real workspace is worth doing, here's what's actually required, based on how
Unity Catalog table properties flow into AutoPIL's source registry:

1. **Create the 8 tables in a real Unity Catalog schema**, each tagged with
   `sensitivity_level`/`data_classification` table properties matching
   `simulated_uc_data.TABLE_PROPERTIES` — via `ALTER TABLE ... SET TBLPROPERTIES`.
2. **Read the tags back via `SHOW TBLPROPERTIES`** to build the AutoPIL source
   registry from what Unity Catalog actually says about each table, rather than the
   hardcoded `TABLE_PROPERTIES` dict — the classification should flow from UC, never
   the reverse.
3. **Swap `SOURCES`'s dict lookups for real Spark SQL reads** — `role_tools()`'s
   guarded getters would query `catalog.schema.table` via `spark.sql(...)` instead of
   indexing into a Python dict, keeping the same `guard.protect()` wrapper.
4. **Audit trail**: AutoPIL ships a `DeltaAuditLog` for writing the tamper-evident
   audit trail to a governed Delta table instead of local SQLite — same
   hash-chained event model, different storage backend. Not needed for the SDK/local
   mode this demo runs in.

Not attempted or tested as part of this round — this is a description of what the
path would involve, not a verified integration.

## 12. Appendix: hosted trial mode

Implemented — see `saas_guard.py` and the "Hosted AutoPIL SaaS trial mode" section in
`client_analysis_demo.py`. Same `RemoteContextGuard`/`bootstrap_agents()` design as
fraud_investigation's own hosted mode (see its DESIGN.md for the fuller writeup); this
section covers what's specific to this demo. See README.md's own "Hosted AutoPIL SaaS
trial mode" section for how to get a trial account and Admin/Evaluate keys — this
appendix covers what was verified, not setup steps.

**Verified live against the same real trial tenant** used for fraud_investigation
(`https://autopil-api.onrender.com`, 2026-07-09):

1. **`junior_analyst_policy` and `senior_analyst_policy` matched the local YAML
   byte-for-byte**, same as fraud_investigation's roles did — no translation needed.
2. **`wealth_advisor` has a real naming collision on this tenant**: two policies
   declare `agent_role="wealth_advisor"` — `demo_wealth_advisor_policy` (matches
   `policies/financial_services/client_analysis.yaml`'s `wealth_advisor_policy`
   exactly — same `catalog.finance.*` source names, same task_bindings) and
   `wealth_advisor_policy` (an unrelated, pre-existing generic wealth-demo policy
   using entirely different source names like `portfolio_holdings` instead of
   `catalog.finance.client_portfolios`). The evaluate endpoint's role-scan fallback
   (used when an agent has no explicit `policy_name`) would risk binding to whichever
   of the two it resolves first — confirmed by registering a test agent and checking
   its bound `policy_name` came back correctly only because `bootstrap_agents()` pins
   it explicitly (`_SAAS_POLICY_NAMES["wealth_advisor"] = "demo_wealth_advisor_policy"`
   in `client_analysis_demo.py`), not because the fallback happened to pick right.
3. **`GET /v1/audit/sessions/{id}` requires the Admin key**, not the Evaluate key — an
   Evaluate-scoped key gets `403 Forbidden` calling it, discovered live when a full
   3-tier run's `_finalize()` crashed trying to read the audit trail with only the
   evaluate key wired through. `RemoteContextGuard` takes both keys for exactly this
   split: `evaluate_key` for `.protect()`'s decision calls, `admin_key` for
   `.get_audit_trail()`. This is a real API constraint, not demo-specific — the same
   fix was applied to fraud_investigation's `saas_guard.py` copy.
4. **A live multi-tier run** (C001, junior_analyst → senior_analyst, via Ollama)
   produced the same shape of outcome as local mode: real per-tier `ALLOW`/`DENY`
   decisions matching the policy (`task_bindings` and plain `denied_sources`/
   `allowed_sources` denials both fired correctly), the human-in-the-loop
   `interrupt()`/resume flow worked unchanged (it's a LangGraph mechanism,
   independent of which guard backs it), and the audit trail read back correctly for
   both tiers' sessions after the fix in point 3.
5. **The vestigial `governance_orchestrator` entry was removed from `AGENT_IDS`**
   while wiring this — a leftover from the pre-tiered design (§7.1's old
   LLM-classifying orchestrator), never referenced by any guarded call since
   `intake_node` replaced it with a plain lookup. No SaaS agent needed for it either.
6. **Known gap, inherited from the hosted API itself, not this demo**: no
   `permitted_agent_ids`/`sensitivity_decay` fields exist in the hosted policy schema
   (`GET`/`POST /v1/policies`) — doesn't affect this demo directly since none of its 3
   roles use either feature locally, but flagged here for completeness alongside
   fraud_investigation's disclosure of the same gap.
7. **`owner_team` (business-accountable team, e.g. "Wealth Team") doesn't persist via
   `PUT /v1/agents/{id}`** — confirmed live: the request returns `200` and
   `updated_at` changes, but `owner_team` reads back `null` immediately after.
   `bootstrap_agents()` still sends `owner_team` on agent *creation* (untested,
   since this demo's 3 agents already existed when this was added) and attempts to
   sync it via `PUT` on every call for existing ones — harmless no-op against this
   gap today, forward-compatible if the hosted API's update path is fixed later.
   Not something fixable from this repo's side.
