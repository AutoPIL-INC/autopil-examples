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
| Task assignment | LLM-driven: an orchestrator reads a natural-language business request and decides both the role *and* the `task_type` (purpose) it falls under |
| "Violation attempts" | Emergent — the model decides for itself, given an ambiguous business request, whether it needs a source outside its role's authorization or outside the assigned task's purpose |
| Escalation | One optional re-route to `senior_analyst` (the broadest role) if the assigned role is fully blocked — mirrors the fraud demo's re-route-after-denial, capped to a single attempt |
| Governance enforcement | `guard.protect()` on every tool call, with `task_type` threaded through so `task_bindings` purpose limitation can actually fire |
| Outcome classification | Grounded in the real audit trail (did the role get any `ALLOW`), not the model's self-reported outcome alone — see §7.4 |

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
- Not guaranteeing the sensitivity-ceiling path fires from the 3 shipped request
  briefs. Verified against the real policy evaluation order (`policy_engine.py`):
  `task_bindings` is checked *before* the sensitivity ceiling, and every
  `senior_analyst_policy` task binding that exists (`credit_analysis`,
  `risk_assessment`) already excludes `stress_test_models` from its permitted
  sources — so a request assigned to either of those tasks hits `task_bindings`
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
- No human-in-the-loop review step. That was specific to the fraud demo's compliance
  sign-off narrative; this demo's payoff is the governance boundary itself.

## 4. Folder structure

```
examples/client_analysis/
├── DESIGN.md                                        # this file
├── README.md                                        # setup + run instructions
├── simulated_uc_data.py                             # 8 simulated UC tables + 3 request briefs
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
class GovernanceState(TypedDict):
    request_id: str
    provider: str
    brief: str                    # looked up server-side from request_id, not client-supplied
    assigned_role: str
    task_type: str
    roles_attempted: list[str]     # >1 entry only if escalation happened
    escalated: bool
    finding: dict                  # {"summary": str, "outcome": "COMPLETED"|"BLOCKED", "sources_used": [...]}
    denial_log: list[dict]
    final_decision: str
```

`brief` is populated by `orchestrator_node` from `simulated_uc_data.GOVERNANCE_REQUESTS`
using only `request_id` — the same pattern the fraud demo uses for `alert`/
`case_metadata` (looked up server-side from `case_id`), so the live viewer's client
never needs to send more than an ID.

## 7. Node design

### 7.1 Orchestrator (role + task assignment)

- Looks up the request brief from `request_id`, then asks the model to decide which of
  the 3 roles should handle it and what `task_type` it falls under, as structured
  output (`assign_request` tool, forced via `tool_choice` where the provider supports
  it).
- Not every model honors an enum constraint strictly — live-tested with Ollama's
  `qwen2.5:7b`, which once returned a *list* of candidate task types instead of a
  single string. `orchestrator_node` coerces this defensively (picks the first valid
  value from a list, falls back to a default if nothing valid is present) rather than
  passing a malformed `task_type` into every guarded call downstream, which would deny
  everything for the wrong reason.

### 7.2 Role agents (junior_analyst, senior_analyst, wealth_advisor)

- Each is the exact same tool-calling loop (`run_tool_loop()`, reused unmodified from
  the fraud demo) with the exact same 8-tool toolbelt (`role_tools()`) — only
  `agent_role`/`agent_id`/`task_type` differ per role/request.
- `task_type` is constant across every tool call within one role's run — it's the
  business purpose assigned once by the orchestrator, not hardcoded per tool the way
  the fraud demo's specialists do it. That's what makes `task_bindings` purpose
  limitation meaningful here: the same source (e.g. `customer_pii`) can succeed under
  one `task_type` and fail under another, for the identical role.

### 7.3 Orchestrator review (single optional escalation)

- If the assigned role's finding reports `BLOCKED` and it actually hit denials, and
  the role isn't already `senior_analyst`, and no escalation has happened yet, the
  orchestrator gets one more structured decision: escalate to `senior_analyst` or
  accept the outcome as final. `escalated: True` on the state prevents a second
  escalation — self-limiting by construction, no step counter needed.
- Escalating doesn't guarantee success — verified live: a `wealth_advisor` request
  escalated to `senior_analyst` under `task_type="wealth_planning"` was *also* denied
  there, because `senior_analyst_policy.allowed_tasks` doesn't include
  `wealth_planning` at all. Broader source access doesn't mean broader task
  authorization.

### 7.4 Decision node — grounded in the audit trail, not the model's self-report

`decision_node` does not trust a role's self-reported `outcome` field at face value.
Live-tested with Ollama's `qwen2.5:7b`: it once returned `outcome: "COMPLETED"` on a
run where every single tool call had been denied. Before classifying a run as
completed, `decision_node` checks the real audit trail for the last role that ran —
did it get at least one `ALLOW` — and only trusts a `COMPLETED` self-report if that's
true. This is the same spirit as the fraud demo's decision being rule-based rather
than LLM-improvised (its own §7.4), applied to a self-report-classification problem
instead of a disposition-generation problem.

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

## 9. Scenarios

Three business requests, one flagship per role, run through the reasoning-driven
graph. Non-determinism is disclosed as a property of the demo, not hidden — see
`simulated_uc_data.GOVERNANCE_REQUESTS` for the exact brief text:

- **GOV-001** — a market outlook memo request, nudging toward `customer_pii`/
  `transaction_history` instead of `market_data`/`public_reports`.
- **GOV-002** — a credit exposure review, nudging toward `customer_pii` under a
  `credit_analysis` task_type that `task_bindings` restricts to `credit_scores`/
  `risk_models` only.
- **GOV-003** — a retirement plan update, nudging toward `customer_pii` instead of
  `client_portfolios`.

No scenario is scripted to fail or succeed; the briefs are written to make reaching
for an out-of-scope source plausible without instructing the model to attempt it.

## 10. Open questions / verified live during implementation

1. **Bedrock's `tool_choice` failure mode differs from Ollama's.** Verified directly
   against the installed `langchain-aws` source (not assumed): forcing a named tool
   via `tool_choice=<name>` works for Anthropic-on-Bedrock models, but **raises
   `ValueError` at `bind_tools()` time** for models whose `supports_tool_choice_values`
   doesn't include `"tool"` (tested against a Llama-family Bedrock model ID). Ollama,
   by contrast, silently ignores an unsupported `tool_choice`. `_bind_forced()`
   catches both cases uniformly.
2. **Cost/latency** — same shape as the fraud demo: each role is a multi-turn
   tool-calling loop, not one `llm.invoke()`. Acceptable for a demo script.
3. **Iteration caps** — `MAX_TOOL_TURNS` bounds each role's loop; the single-escalation
   design (rather than a step counter) bounds the orchestrator review loop.

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
