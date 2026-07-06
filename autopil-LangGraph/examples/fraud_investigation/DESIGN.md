# Fraud Investigation Multi-Agent Demo — Design Doc

Status: implemented — see `fraud_investigation_demo.py`, `README.md`
Depends on: real `autopil` package (editable install from `../autopil/packages/core`)

## 1. Why this demo, and why now

Agentic case investigation is moving from pilot to production in 2026. NICE Actimize's
InvestigateAI is described as having "the agency to determine what data, data sources,
and risk signals to leverage" for a case. Verafin's Agentic AML/Fraud Analysts and FIS's
Anthropic-built Financial Crimes Agent both target 2H 2026 GA. The common thread: the
newest generation of these tools gives the *agent* reasoning and discretion over which
data source to reach for — not a developer-scripted pipeline.

Regulators are permissive on adoption but strict on two things: FinCEN's 2026 framework
says a SAR built on non-auditable, non-explainable agent reasoning "may not survive
regulatory scrutiny," and emerging agentic-security guidance is converging on
per-agent least privilege ("dedicated service identities, narrow tool allowlists,
time-bounded credentials") as the required mitigation for agents with real autonomy.

The point of this demo is to show that mitigation working — not against a scripted
"agent tries to do the bad thing," but against a real model that has genuine discretion
over which tools it calls, and can genuinely reason its way toward crossing a boundary.

## 2. What's different from the existing `autopil/examples/fraud_investigation` demo

| | Original demo | This demo |
|---|---|---|
| Specialist reasoning | Hardcoded `if/elif` on data flags | Real `ChatAnthropic` tool-calling loop per agent |
| Tool access per agent | Only the functions the role is authorized for exist in scope | Each agent is handed a toolbelt *wider* than its authorization — including tools it should never successfully call |
| "Violation attempts" | Scripted: a designated function forces a specific denied call at a fixed point in the script | Emergent: the model decides for itself, given an ambiguous case brief, whether it needs a tool outside its scope |
| Orchestrator routing | Fixed edge list (`orchestrator → transaction_analyst → account_profiler → kyc_specialist → sar_generator`) | LLM-driven: orchestrator reads the alert and decides which specialists to invoke, and can re-route after a denial |
| Governance enforcement | `guard.protect()` — unchanged | `guard.protect()` — unchanged. This is the point: the enforcement layer doesn't need to change when the agent gets smarter/more autonomous. |
| Final disposition | Deterministic flag logic | Stays deterministic flag logic (unchanged — see §6) |

The enforcement code is intentionally the *same* AutoPIL mechanism as the original demo.
What changes is that we stop asserting a violation will happen and instead give a model
room to decide, which is a more credible demonstration that the boundary holds
regardless of what the agent wants to do.

## 3. Non-goals

- Not adding new AutoPIL features. This demo exercises what exists today
  (`ContextGuard.protect`, session isolation, audit trail, sensitivity decay).
- Not simulating full real-world investigation scale (case aging, external data
  requests, human QA sign-off). See the "what's stylized" discussion from the design
  conversation — this demo is illustrating the *governance* problem, not the full
  operational workflow.
- Not moving data to Databricks. Local Python fixtures are sufficient; Databricks would
  add infra cost with no payoff for a LangGraph-pattern demo.

## 4. Folder structure

```
examples/fraud_investigation/
├── DESIGN.md                                        # this file
├── README.md                                        # setup + run instructions
├── simulated_data.py                                # reused as-is from autopil/examples/fraud_investigation
├── policies/financial_services/fraud_investigation.yaml   # reused as-is
└── fraud_investigation_demo.py                      # new — reasoning-driven orchestration
```

`simulated_data.py` and the policy YAML are copied verbatim from the existing autopil
demo — 5 accounts, 50 transactions, 3 fraud alerts (structuring / account takeover /
synthetic identity), KYC records, and the 5-role policy matrix with BSA/OFAC/FinCEN
mapping. No reason to re-derive fixture data that's already correct and matches the
policy exactly.

## 5. Environment

- Additional dependency: `pip install -e "<path-to-autopil>/packages/core[langgraph]"`
  — editable install of the sibling repo. Documented in README, not silently added to
  `requirements.txt` (a local sibling path isn't portable).
- `ANTHROPIC_API_KEY` already required by `01_basics.py` via `.env` — reused.

## 6. State shape

```python
class InvestigationState(TypedDict):
    case_id: str
    account_id: str
    alert: dict
    case_metadata: dict

    # per-specialist scratch: each specialist's own tool-calling transcript
    # (messages list) plus its final structured finding once it stops calling tools
    transaction_analyst: AgentTurn
    account_profiler: AgentTurn
    kyc_specialist: AgentTurn

    sar_draft: dict
    denial_log: list[dict]       # every DENY the guard raised, across all agents, with reason
    routing_history: list[str]   # which specialists the orchestrator invoked, in order
    final_decision: dict         # deterministic flag-based outcome (§8)
```

`AgentTurn` = `{"messages": list[BaseMessage], "finding": dict | None}` — an agent is
"done" when it emits a structured finding instead of another tool call.

## 7. Node design

### 7.1 Orchestrator (reasoning-driven routing)

- Input: `alert` + `case_metadata` (its only two authorized sources, via `guard.protect`
  exactly as today).
- Prompts the model with the alert description and asks which specialists are relevant
  and in what order, returned as structured output (`{"route": ["transaction_analyst",
  "kyc_specialist", ...]}`), not a scripted edge list.
- After each specialist returns, the orchestrator sees that specialist's finding and the
  current `denial_log`, and decides: invoke another specialist, re-route (e.g. a denial
  on `account_pii` should make it realize identity verification needs to go through
  `kyc_specialist`), or hand off to `sar_generator`.
- This is a `while` loop inside one LangGraph node (or a `Send`-based conditional edge
  back to itself) with a hard iteration cap — model-driven routing needs a circuit
  breaker so a confused model can't loop forever.

### 7.2 Specialist agents (transaction_analyst, account_profiler, kyc_specialist)

- Each is a small tool-calling loop: `llm.bind_tools([...])` → model responds with
  either a tool call or a final finding → if tool call, execute it (every tool wrapped
  in `guard.protect(agent_role=..., source_id=..., session_id=...)`) → feed the
  ALLOW/DENY result back as a `ToolMessage` → repeat, capped at ~5 turns.
- **The toolbelt is intentionally over-scoped.** `transaction_analyst`'s tools include
  its 5 authorized sources *and* `identity_data` / `account_pii` — sources its policy
  denies. The model is never told which tools are off-limits; it finds out from the
  `PermissionError` that comes back as a tool result, same as the original demo's
  runtime behavior, except now the *decision to try* is the model's own, not a scripted
  branch.
- A denial doesn't crash the node — the caught `PermissionError` becomes a `ToolMessage`
  with the reason, and the model reasons over it on its next turn (accept the boundary
  and produce a finding without that data, or ask the orchestrator to route the request
  elsewhere via its structured output).

### 7.3 SAR generator

- Same tool-calling pattern, over-scoped toolbelt including `transaction_history`
  (denied) and a tool that reuses another agent's `session_id` (to exercise session
  isolation, not just source-policy denial) — again, offered as an available tool, not
  forced.
- Composes the SAR narrative only from whatever `agent_outputs`/findings it actually
  obtained through authorized channels.

### 7.4 Decision node — stays deterministic

Per the earlier design conversation: the final disposition (SAR warranted, freeze,
escalate, monitor) stays rule-based on the extracted findings, not LLM-improvised. This
mirrors the real regulatory expectation — FinCEN's guidance expects a human-reviewable,
explainable path to the filing decision, not a black-box model call at the last step.
An LLM can draft the narrative; it shouldn't decide the compliance action.

## 8. Governance surface being demonstrated

| AutoPIL mechanism | What this demo exercises |
|---|---|
| `guard.protect()` role/source matrix | Every tool call, in-scope or not, regardless of which agent or how many turns of reasoning led to it |
| Session isolation | `sar_generator` offered a tool that reads via `transaction_analyst`'s `session_id` |
| Audit trail (hash-chained) | Printed per-session after each scenario, same as the original demo |
| `LineageStoreBase.get_actions_for_session()` | New: reconstruct each agent's full tool-call sequence in order, so a denial can be shown in context ("tried X, got denied, then correctly asked for Y") — addresses the "standard logs don't show the full action chain" gap from the NHI article |
| `denial_type` classification | Shown per denial (policy vs. session isolation) |
| `sensitivity_decay` / `session_ttl_minutes` | Not the focus of this demo, but present in the reused policy YAML — could be called out as a stretch scenario later (a long-running investigation session losing access to `critical` sources mid-case) |

## 9. Scenarios

Same three underlying cases as the original demo (CASE-001 structuring, CASE-002 account
takeover, CASE-003 synthetic identity), run through the reasoning-driven graph instead of
the scripted one. Because the model decides for itself whether to reach for an
out-of-scope tool, a boundary-crossing *attempt* is a probable outcome given the
over-scoped toolbelt and an ambiguous case brief — but not a guaranteed one per run. That
non-determinism is disclosed as a property of the demo, not hidden:

- If the model stays in-bounds: the demo shows clean investigation + full audit lineage
  (same value as the original happy path).
- If the model reaches out of bounds: the demo shows the denial, the model's recovery
  (or failure to recover), and the completed investigation despite the attempt — the
  more compelling case, and the one the industry research points at as the actual risk.

No scenario is scripted to fail or succeed. The prompts should be written to make a
boundary-crossing attempt *plausible* (e.g., CASE-002's brief mentions "verify identity"
without saying which agent owns that) without instructing the model to attempt it.

**Later addition:** two more cases were added on top of the original three — CASE-004
(elder financial exploitation: a brand-new authorized signer diverts funds from a
25-year account) and CASE-005 (money mule / check kiting: third-party checks withdrawn
before hold periods release). Both reuse the exact same mechanism as CASE-001/002 —
a new flag in `SOURCES["velocity_signals"]` and a new `elif` branch in `decision_node`
— no new AutoPIL source types or tool plumbing were needed. See `simulated_data.py`'s
module docstring for the full account/transaction/KYC data.

## 10. Open questions before implementation

1. **Cost/latency** — each specialist is now a multi-turn tool-calling loop instead of
   one `llm.invoke()`. Three specialists + orchestrator + sar_generator, each up to ~5
   turns, is a meaningfully larger number of API calls per scenario run than the
   original demo. Acceptable for a demo script; worth knowing going in.
2. **Non-determinism in a demo** — do we want a "seed" case brief that's been tested to
   reliably surface a boundary attempt at least once for the recorded/shared version of
   this demo, while still being honest that it's model-driven rather than scripted?
3. **Iteration caps** — need hard turn limits on both the orchestrator loop and each
   specialist's tool-calling loop to bound worst-case runtime.
4. **Structured output format** — orchestrator routing decisions and specialist findings
   need a schema (tool-call-forced structured output, matching how `01_basics.py` keeps
   things simple) so `decision_node` can reliably extract flags from free-text findings.

## 11. Out of scope for this round

- Explicit declared delegation/trust graph between agents (flagged as a partial gap in
  the AutoPIL-vs-NHI-article comparison — real feature work, not a demo concern).
- Full chain-level pre-execution validation (same — roadmap item, not something to fake
  in a demo).

```
DENIED | source='agent_outputs' | agent='sar_generator' |
Agent 'kyc-specialist-001' is not permitted to act as 'sar_generator' — permitted: ['kyc_specialist']
```

Denied outright (`policy_name="role_not_permitted"`), not silently evaluated under
either role. The front door flagged as unlocked earlier is now locked on the
SDK/embedded path this demo exercises.

**Also checked the REST API path** (`app.py`, `EvaluateRequest.agent_role`) — a separate
code path from the SDK, since the earlier concern was specifically that `agent_role` had
no cryptographic binding *anywhere* in the system, not just in `guard.py`. Live-tested
against the actual FastAPI app (not just read), two scenarios:

1. Claimed role not in the agent's `permitted_roles` at all → denied outright
   (`role_not_permitted`), same as the SDK path.
2. Sharper test — claimed role *is* technically in a multi-role agent's `permitted_roles`,
   but isn't that agent's canonical registered role → the server silently evaluates under
   the canonical role's policy anyway, not the claim. Proved with a sensitivity-ceiling
   difference between the two roles' policies: the claimed role would have allowed a
   `high`-sensitivity read; the audit trail confirms it was evaluated under the canonical
   (tighter) role's policy instead.

Confirmed the lock isn't narrowed to bound keys or strong-identity methods (mTLS/SPIFFE/
Conjur) — it fires uniformly for any registered, approved agent, including a plain
`X-API-Key` with `agent_id` supplied only in the request body, which was the specific
narrower-fix risk worth ruling out. Both gaps — SDK and REST — are closed.

**Promoted this into a live over-scope tool, not just a manual verification script** —
`sar_generator_tools()` now includes `get_subject_identity_check` (over-scope 3): the
underlying guarded call uses `sar_generator`'s own real registered `agent_id`, but
*claims* `agent_role="kyc_specialist"` — a privilege-escalation attempt via role claim
(not identity theft, unlike over-scope 2's session-stealing tool). `identity_data` is a
source `kyc_specialist_policy` genuinely allows, so this is denied purely on the role
claim (`role_not_permitted`), before source-based policy checks even run — same ordering
property that makes over-scope 2 a clean isolation test rather than a relabeled policy
denial.

This tool triggers far more reliably than the session-isolation one: 6/6 across two live
runs (all three cases, twice), vs. zero spontaneous triggers for `get_case_agent_outputs`
across 12+ runs — "verify subject identity while drafting a SAR" is a far more natural
thing for the model to reach for than "alternate lookup keyed by case session." Worth
knowing if you want a reliably-observable boundary-crossing attempt without depending on
model luck.

Verified behaviors, live:

- Ran all three cases end to end. In every run, at least one specialist reasoned its way
  into a denied tool call on its own (no scripted branch involved), and the orchestrator
  correctly re-routed based on reading the denial reason, not a hardcoded scenario flag.
- The deterministic `decision_node` outcome matched `simulated_data.get_expected_outcome()`
  ground truth in all three cases regardless of which denials occurred.
- The session-isolation tool (`get_case_agent_outputs`) was not spontaneously triggered
  in any of three live runs — expected, per §9's disclosed non-determinism. Verified
  directly instead (bypassing the LLM): claiming `transaction_analyst`'s session first,
  then calling the tool, produces `cross_agent_isolation` deny on `agent_outputs` — a
  source `sar_generator` **is** authorized for — confirming isolation is enforced
  independently of the source policy check, not a relabeled policy denial.

## Appendix: hosted trial mode (deferred, not this round)

Considered running this demo against the hosted AutoPIL trial (real tenant, real admin
key) instead of local embedded `ContextGuard`. Decided against it for now — local mode
keeps iteration fast and isolates "does the reasoning-driven design work" from "does the
trial onboarding flow work." Revisit once the demo itself is proven.

If/when this is revisited, note what's actually required — confirmed against the live
code, not assumed:

1. **Provision a tenant** — `POST /v1/admin/tenants` (or `POST /v1/admin/trial/provision`,
   which also mints a separate `evaluate`-scoped agent key in the same call — the more
   realistic "new trial tenant" path).
2. **Create the 5 policies via REST** — `POST /v1/policies` once per role. This is real
   JSON `CreatePolicyRequest`, not a YAML upload — the existing `fraud_investigation.yaml`
   would need to be translated into 5 request bodies.
3. **Register the 5 agents** — `POST /v1/agents`, each bound via `policy_name`.
4. **Every guarded retrieval becomes a raw HTTP call** — `ContextGuard.protect()` is
   embedded-only in Python (always talks to a local SQLite/Postgres file directly; no
   `base_url`/remote mode — Go/TypeScript/Java have hosted SDKs, Python doesn't). Hosted
   mode means replacing every `@guard.protect(...)` call site with
   `POST /v1/context/evaluate` + `X-API-Key: <agent_key>`, which would need a small
   wrapper to avoid repetitive HTTP boilerplate at every tool call.

Two product findings surfaced while checking this, worth tracking independent of the demo:

- The **saas app doesn't enforce the "policy_name must resolve" 422 check** that the
  single-tenant core app does (`packages/core/autopil/api/app.py` vs.
  `packages/saas/autopil_saas/api/app.py`) — registering an agent with a typo'd
  `policy_name` on the hosted trial silently stores `policy_id=None` and falls back to
  role-scan instead of erroring.
- **No first-party Python HTTP client** exists for the hosted API — only Go/TS/Java SDKs
  do. If Python/LangGraph shops are a target trial segment, that's a gap independent of
  this demo.
