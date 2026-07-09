# AML & Compliance Investigation Demo — Design Doc

Status: implemented — see `aml_compliance_demo.py`, `README.md`
Depends on: real `autopil` package (`autopil[langgraph]>=0.10.0` from PyPI)

## 1. Why this demo, and why now

Split out of `institutional_portfolio_review`, where this financial-crime-governance
workflow (`aml_case`: `aml_investigator` → `kyc_agent` → `compliance_officer`) sat
awkwardly split across that demo's two policy files — `kyc_agent_policy` lived in the
*wealth* file despite 100% of its allowed sources being risk-catalog data, and the
three roles' policies never got a single coherent home. AML/sanctions/KYC governance
is also thematically distinct from portfolio/wealth advisory work — closer in spirit
to `fraud_investigation`'s financial-crime narrative than to quarterly rebalancing —
so it gets `fraud_investigation`'s structure: case-driven, a fixed investigation
chain, human-in-the-loop sign-off, one dedicated policy file.

Splitting this out also shrinks `institutional_portfolio_review` from 11 roles to 8,
independently helping the long-role-chain convergence issues already documented in
this repo's root `CLAUDE.md`.

## 2. Design approach: fixed sequence, not dynamic routing

| | This demo |
|---|---|
| Role sequence | Fixed: every case runs `aml_investigator` → `kyc_agent` → `compliance_officer`, always in that order. No LLM-driven routing decision — unlike `fraud_investigation`'s dynamically-routed specialists, there's no real reason the order would vary case to case for a linear KYC/AML investigation workflow. |
| Tool access per role | Each role is handed a toolbelt *wider* than its policy authorization — a curated, per-role list of real + a couple of deliberate over-scope tools, same pattern as `fraud_investigation`'s `*_tools()` functions (not the "identical full toolbelt for every role" pattern `client_analysis`/`institutional_portfolio_review` use). |
| "Violation attempts" | Emergent — the model decides for itself, given an ambiguous case brief, whether it needs a tool outside its role's scope. |
| Governance enforcement | `guard.protect()` on every tool call, one consolidated policy file for all 3 roles. |
| Final disposition | Deterministic, rule-based on the real underlying signal data (§7.4) — not LLM-improvised, and not trusting any role's self-reported finding. |

Because the sequence is fixed and known in advance, there's no `_bind_forced()`/
forced-`tool_choice` machinery anywhere in this file — that mechanism exists in the
other demos specifically to force a single classification/routing decision call, and
this demo has no such call. `intake_node` is a plain dict lookup, matching
`client_analysis_demo.py`'s own `intake_node` (added when that demo dropped its
LLM-driven orchestrator for the same reason).

## 3. Non-goals

- Not adding new AutoPIL features — exercises what exists today (`ContextGuard.protect`,
  `task_bindings`, `sensitivity_decay`, `session_ttl_minutes`, audit trail).
- Not wiring hosted AutoPIL SaaS trial mode in this round. `fraud_investigation` and
  `client_analysis` both have this (see their own `saas_guard.py`/DESIGN.md appendices);
  the same pattern would apply here, but it's a deliberate follow-up, not part of this
  split — consistent with how those two demos sequenced it (local mode proven first).
- Not reusing `institutional_portfolio_review`'s existing `aml_case` fixture data
  verbatim — that data was "clean" (no real watchlist hits, no delinquency, all KYC
  verified) since it was never designed as a suspicious-pattern case the way
  `fraud_investigation`'s 5 cases are. New fixture data was written instead (§9).

## 4. Folder structure

```
examples/aml_compliance/
├── DESIGN.md                                      # this file
├── README.md                                      # setup + run instructions
├── aml_case_data.py                               # 5-case queue + fixture tables
├── policies/financial_services/aml_compliance.yaml  # the consolidated 3-role policy
├── aml_compliance_demo.py                         # the LangGraph graph
└── frontend/                                      # live audit-trail viewer (same scaffold as fraud_investigation/frontend)
```

`aml_case_data.py` is deliberately not named `simulated_data.py` — that name is
already used by `fraud_investigation`, and `langgraph dev` loads every demo's graph
into one Python process; a same-named module in two demo directories would collide
via `sys.modules` caching (documented in root `CLAUDE.md`). Checked against every
other demo's module names before finalizing.

## 5. Environment

- Additional dependency: `autopil[langgraph]>=0.10.0`, published to PyPI — already
  listed in the shared `requirements.txt`, no new dependency needed.
- Same `_make_llm()` 4-provider chain as `fraud_investigation_demo.py` (Anthropic →
  Gemini → Groq → Ollama) — no Bedrock, matching fraud_investigation rather than
  client_analysis/institutional_portfolio_review (which are Bedrock-first).

## 6. State shape

```python
class AMLCaseState(TypedDict):
    case_id: str
    provider: str
    account_id: str
    reason_for_review: str
    roles_completed: list[str]
    findings: dict[str, Finding]
    denial_log: list[DenialEvent]
    final_decision: str
```

`account_id`/`reason_for_review` are populated by `intake_node` from
`aml_case_data.AML_CASES[case_id]` — the same "looked up server-side from an ID"
pattern every demo in this repo uses, so the live viewer's client never needs to send
more than a case ID.

## 7. Node design

### 7.1 Intake (deterministic, not LLM-driven)

Looks up the case, seeds `account_id`/`reason_for_review`, resets sessions. No model
call — see §2 on why this demo has no routing decision to make.

### 7.2 Role agents (aml_investigator, kyc_agent, compliance_officer)

- Each is a real tool-calling loop (`run_tool_loop()`, same shared helper every other
  demo in this repo uses) with its own curated toolbelt (`aml_investigator_tools()`,
  `kyc_agent_tools()`, `compliance_officer_tools()`) — real authorized sources plus 1-2
  deliberate over-scope tools per role, mirroring `fraud_investigation`'s per-role
  `*_tools()` functions rather than institutional_portfolio_review/client_analysis's
  "identical full toolbelt for everyone" pattern.
- `task_type` is baked into each tool definition (not assigned dynamically), matching
  `fraud_investigation`'s convention — e.g. `get_transaction_history` is always called
  under `task_type="pattern_detection"` for `aml_investigator`.
- **A real bug caught during verification**: `compliance_officer`'s
  `get_regulatory_filings` tool was initially bound to `task_type="sar_filing"`, but
  `sar_filing`'s `task_bindings.permitted_sources` doesn't include
  `regulatory_filings` (only `policy_validation`/`compliance_review`/`sox_review` do)
  — meaning that tool was denied on every single call regardless of model behavior,
  contradicting the "denials aren't scripted" design. Fixed to `task_type=
  "compliance_review"`, whose `permitted_sources` does include `regulatory_filings`;
  re-verified live afterward (§10).
- `compliance_officer` is the broadest role and reaches into `client_profile`/
  `portfolio_holdings` (not just risk-catalog sources) for cross-client audit — the
  one role in this demo authorized across both data domains, same nuance the source
  `institutional_portfolio_review` policy modeled for this role.

### 7.3 Decision node — rule-based, grounded in real signal data

`decision_node` computes `proposed_action` from the real underlying data
(`aml_case_data.WATCHLIST`/`IDENTITY_RECORDS`/`TRANSACTION_HISTORY`), not from any
role's self-reported finding — same "the disposition is rule-based, not
LLM-improvised" principle as `fraud_investigation_demo.py`'s `decision_node`. A
human reviewer still gets the last word via `interrupt()`: approve the proposed
action, or override it with one of `OVERRIDE_ACTIONS`. The CLI auto-approves; the live
viewer's reviewer decides for real.

## 8. Governance surface being demonstrated

| AutoPIL mechanism | What this demo exercises |
|---|---|
| `guard.protect()` role/source matrix | Every tool call, in-scope or not, across all 3 roles |
| `task_bindings` (purpose limitation) | e.g. `aml_investigator` reaching for `identity_records` under `pattern_detection` — not in that task's permitted sources, denied regardless of `identity_records` never being in `allowed_sources` at all either |
| Sensitivity ceiling + `sensitivity_decay` | `kyc_agent_policy` has the longest `session_ttl_minutes` (240) and deepest decay (medium at 60 min, low at 120 min) of the three — a real KYC refresh workflow runs longer than a single investigation step |
| Cross-catalog reach | `compliance_officer_policy` is the only one of the three authorized for `client_profile`/`portfolio_holdings`, not just risk-catalog sources |
| Audit trail | `guard.get_audit_trail()` per session, same mechanism as every other demo |

## 9. Scenarios

Five cases, mixed severity — same "not every case should look the same" disclosure as
`fraud_investigation`'s 5 cases. See `aml_case_data.py`'s module docstring for the
exact fixture data; `get_expected_outcome()` there is the ground truth `decision_node`
is checked against, not something `decision_node` reads directly:

- **AML-001** — a genuine structuring pattern: 4 wire transfers just under the
  $10,000 CTR threshold within a 4-day window. Expected: SAR required.
- **AML-002** — a watchlist false positive: a fuzzy OFAC/SDN name match that resolves
  to a different legal entity on verification. Expected: cleared.
- **AML-003** — a stale KYC refresh: beneficial ownership verification lapsed past the
  policy renewal window, no transaction signal involved at all. Expected: hold
  pending refresh.
- **AML-004** — a routine cross-client audit (`compliance_officer`'s flagship case,
  mirroring the source `aml_case`'s "confirm handled consistently across our
  institutional book" framing). Expected: cleared.
- **AML-005** — a clean case with no prior flags, clearing at every step. Expected: no
  further action.

No case is scripted to fail or succeed at the tool-call level — whether a given role
reaches for an over-scope tool is the model's own call each run; `decision_node`'s
proposed action, however, is always deterministic given the fixture data (verified
live in §10, matched ground truth in 5/5 cases across two full runs).

## 10. Verified live during implementation

1. **Full 5-case CLI run via Ollama, twice** (once before and once after the
   `get_regulatory_filings` task_type fix in §7.2) — all 5 cases' proposed actions
   matched `get_expected_outcome()` ground truth exactly, no tracebacks, real
   `task_bindings`/plain-`denied_sources` denials fired for the deliberate over-scope
   tools (`aml_investigator` reaching for `identity_records`, `kyc_agent` reaching for
   `risk_models`/`transaction_history`).
2. **`langgraph dev` loads all 4 graphs cleanly** (`fraud_investigation`,
   `client_analysis`, `institutional_portfolio_review`, `aml_compliance`) after adding
   this demo's entry to the shared `langgraph.json` — required a full server restart,
   not just a hot-reload, since adding a new `graph_id` (not just editing an existing
   file) isn't picked up by the file-watcher alone.
3. Module name collision check (§4) — confirmed `aml_case_data.py` doesn't collide
   with any other demo's module names before wiring it in.

## 11. Out of scope for this round

- Hosted AutoPIL SaaS trial mode (see §3).
- Any escalation/re-routing path — the 3-role sequence is fixed and linear; there's no
  equivalent of `fraud_investigation`'s orchestrator re-route-after-denial or
  `client_analysis`'s tiered human-in-the-loop escalation here, since a 3-role KYC/AML
  chain doesn't have a natural "escalate to a broader-access role" step the way those
  two demos' designs call for.
