# Trading Desk Ops — Planning Doc

**Status: pre-implementation.** Nothing here is built yet — no example directory,
no policy YAML, no code. This captures the design discussion so it doesn't need to be
re-derived when the build starts. Once Equities is actually built, this doc's Equities
section should be superseded by that example's own `DESIGN.md`, and this file kept for
the remaining four sub-domains until they're built too.

## Decisions

1. **Placement** — one example, `examples/trading_desk_ops/`, under the existing
   Financial Services vertical (sibling to `aml_compliance`/
   `institutional_portfolio_review`). All 5 sub-domains (Equities, FX, Commodities,
   Fixed Income, International) live *underneath* this one example rather than as 5
   separate example directories — same relationship `institutional_portfolio_review`
   has to its multiple `REVIEW_TYPES` (`quarterly_review`, `trade_settlement_check`):
   one shared orchestrator pattern, a domain-classification step as the entry point,
   then each sub-domain's own specialist chain. Equities is the first sub-domain
   built; the other four get added as their own workflow entries later, not as new
   top-level examples.
2. **Two-tier human review** — confirmed for the first build (not deferred). A routine
   ops correction and an escalated compliance-officer review are both in scope from
   day one; see EQ-002 vs. EQ-005 below.
3. **Entity naming** — **Meridian Bank's Trading Unit** (not a distinct entity) —
   consistent with every other Financial Services demo in this repo using Meridian
   Bank, scoped to its trading desk specifically.

## Why AutoPIL fits Trading Ops specifically

T+1 settlement removes the traditional control window. Every existing compliance
control in trading ops (four-eyes review, EOD reconciliation, exception queues)
assumed a day or two of slack — T+1 collapses that, since settlement instructions have
to go out same-day. That's exactly the condition where "the model gets a real
tool-calling loop wider than its authorization, and a runtime policy decides what it
can touch" matters most. It's also a domain regulators already demand a defensible
answer for (SEC Rule 15c6-2's same-day-affirmation mandate, FINRA CAT reporting) — "who
saw what, under what authority, and who signed off on the override" is a compliance
requirement here, not just a nice-to-have audit log.

## Design principle: dynamic reasoning, grounded action

Every demo already in this repo follows one rule: **routing/investigation is
reasoning-driven, but the final action is grounded and human-gated.**
`quality_control`'s `decision_node` docstring states it outright — "an LLM can draft
the narrative; it shouldn't decide the corrective action." This split is what makes
the demo compelling rather than a liability: the agent reasons freely and can even
overreach (denials happen because it tried something plausible, not because a script
forced it), but AutoPIL governs what it can see and a human decides what actually
moves money or shares.

Trading ops earns *more* dynamism at the classification/routing layer than
`quality_control` did, because the trigger genuinely varies (unlike `quality_control`,
where every case started identically and a fixed graph edge was the right call):

| Decision point | Why it's genuinely dynamic |
|---|---|
| Trigger classification | New order vs. amendment vs. cancellation vs. PM rebalance vs. corporate-action trade — each routes to a different downstream path entirely. |
| Break/exception triage | Timing lag vs. data-capture error vs. genuine fails-to-deliver risk vs. manipulation-flavored anomaly — requires synthesizing multiple data sources, the same investigative shape that made `fraud_investigation` land. |
| Allocation logic | Splitting a block order across sub-accounts involves tax lots, wash-sale exposure, client-specific restrictions, and best-execution obligations — real trade-offs, not a pro-rata formula. |

The actual settlement release, allocation finalization, or break resolution stays
rule-based/grounded plus human `interrupt()` sign-off, same as every existing demo.

## Sub-domain 1 (first build): Equities

`examples/trading_desk_ops/`, Meridian Bank's Trading Unit. Trigger: an external
client places a 10,000-share MSFT order. Internally this fans out into allocation
across sub-accounts, same-day affirmation, DTCC settlement verification, and (when
something breaks) exception handling — inside a T+1 window.

`trading_ops_orchestrator`'s classification step doubles as the future sub-domain
router: for this first build it only ever resolves to Equities, but the same
classification call is where FX/Commodities/Fixed Income/International plug in later
as additional branches, each with their own specialist chain below the fold.

### Roles

| Role | Reads | Denied | Notable mechanism |
|---|---|---|---|
| `trading_ops_orchestrator` | `case_metadata`, `agent_outputs` | every raw trade/position/settlement source | Genuinely LLM-driven classification of the trigger (new order / amendment / cancellation / PM rebalance / corporate-action trade) — not a fixed first step. Re-routes among specialists based on findings. |
| `order_intake_agent` | raw instruction (email/FIX text), security master reference data | client account data, position data, pricing/commission data | Parses into a structured trade ticket; flags potential short-sale status for Reg SHO relevance. Runs only on the new-order/amendment path — a rebalance trigger skips it since the PM's system already produced structured data. |
| `allocation_agent` | client account/position data *for accounts in this block only*, investment-restriction/mandate data | pricing, commission, other blocks' allocations, other clients' positions | Splits the order across sub-accounts respecting concentration limits and client restrictions. Boundary grounded in SEC Rule 15c3-3 — one client's allocation must never be visible to another, even internally. |
| `affirmation_matching_agent` | trade capture, custodian/counterparty records, standing settlement instructions (SSI) | client PII beyond account/SSI reference, pricing, commission | Matches internal capture vs. counterparty record same-day, per SEC Rule 15c6-2. A mismatch is a flag, never a unilateral fix. |
| `settlement_reconciliation_agent` | DTCC/NSCC CNS net settlement data, internal position ledger | desk P&L, commissions, unrelated client orders | Verifies the firm's net settlement obligation against internal books. A break here is a potential fails-to-deliver risk, not cosmetic. |
| `exception_investigation_agent` | whatever's relevant to the specific flagged break (widest reasoning scope, scoped per-break not blanket) | — | Triages: timing lag, data/SSI error, genuine fails-to-deliver risk, or manipulation-flavored anomaly. Proposes a resolution; cannot execute one. |
| `compliance_reporting_agent` | `agent_outputs` only | every raw source | Compiles the FINRA CAT-style audit record — same "never touches a raw source, compiles from outputs" pattern every orchestrator/compiler role in this repo uses. |

### Compliance framework grounding each boundary

| Regulation / mechanism | What it requires | Which agent/boundary it grounds |
|---|---|---|
| SEC Rule 15c6-1 | T+1 settlement cycle (effective May 2024) | The whole pipeline's time pressure — no scenario has slack for manual exception handling |
| SEC Rule 15c6-2 | Same-day affirmation (SDA) mandate for institutional trades | `affirmation_matching_agent` must complete same trade-date |
| DTCC/NSCC CNS (Continuous Net Settlement) | Firm's netted settlement obligation vs. internal books | `settlement_reconciliation_agent`'s core check; a mismatch is EQ-005's fails-to-deliver scenario |
| SEC Rule 15c3-3 (Customer Protection Rule) | Client assets/positions must stay segregated | `allocation_agent`'s hard boundary — one client's allocation invisible to any agent not handling that client |
| Reg SHO | Locate requirement before executing a short sale | `order_intake_agent`'s short-sale flag; escalation trigger in EQ-005 if inventory can't cover the obligation |
| FINRA CAT (Consolidated Audit Trail) | Every order event (receipt, route, modify, cancel, execute) reported with timestamps | `compliance_reporting_agent`'s final compile — maps directly onto AutoPIL's own tamper-evident audit log |
| SEC Rule 17a-4 | WORM recordkeeping for broker-dealers | The audit trail itself |
| Information barriers / MNPI policy | Trading-side agents must not access research/banking-side or other-desk data | Grounds the EQ-003 over-scope denial — a real regulatory reason, not an arbitrary rule |
| FINRA Rule 5310 (Best Execution) | Obligation to seek best execution for client orders | Contextual reasoning input for `allocation_agent`, not a hard denial |

### Scenarios

- **EQ-001 — Clean straight-through.** New 10,000-share MSFT order via FIX message.
  Intake parses it, flags long (not short). Allocation splits across 3 client
  sub-accounts, all within concentration limits. Affirmation matches cleanly same-day.
  Settlement confirms DTCC/internal ledger agree. No exceptions.
- **EQ-002 — SSI data error.** One sub-account's standing settlement instruction is
  stale (wrong custodian account). Affirmation flags a mismatch; investigation triages
  it as a data error (not a settlement-risk event); proposes correcting the SSI and
  reprocessing. Requires human sign-off before the correction goes live.
- **EQ-003 — Governance beat (information barrier).** Exception investigation is
  handed a plausible-but-denied tool — checking desk P&L/commission data "to see if
  this trade was being deprioritized" — crossing an information-barrier boundary it
  has no authorization for. Denied. Orchestrator reroutes to a narrower investigation
  using only settlement/affirmation data it's actually entitled to.
- **EQ-004 — PM rebalance trigger (the dynamic-routing showcase).** A portfolio
  manager requests trimming MSFT across several accounts to fund a rebalance
  elsewhere. The orchestrator classifies this trigger differently from EQ-001 — it's
  already structured, so it routes straight to `allocation_agent`, skipping
  `order_intake_agent` entirely. Concrete proof that classification is genuinely
  dynamic, not a fixed edge.
- **EQ-005 — Genuine fails-to-deliver risk (highest severity).** Settlement
  reconciliation finds the firm doesn't hold enough MSFT shares in inventory to
  deliver — a real settlement-risk event. Pulls in Reg SHO's locate-requirement logic
  and escalates to a senior compliance officer, not a routine ops sign-off —
  demonstrating the human-in-the-loop step itself can route to a different reviewer
  based on severity.

### Human-in-the-loop

Two-tier from day one, both requiring a written note: a routine ops-analyst correction
(EQ-002) vs. an escalated compliance-officer review (EQ-005) — a step beyond every
existing demo's single-tier interrupt. The severity classification (which tier a given
exception routes to) is itself a reasoning decision, not a hardcoded mapping from
scenario ID to reviewer — worth verifying live that the routing is actually driven by
the investigation's own findings (e.g. "is this a data error or a real settlement-risk
event") rather than which EQ-### case happened to be running.

## Pain-scenario menu: the other four sub-domains

Equities is the cleanest starting point specifically because T+1 is uniform and
DTCC/CNS is one clearing path. The other four each break that simplicity in a
different way — useful for sequencing which to build next.

**FX** — still T+2 spot (didn't move with equities' 2024 T+1 shift), settled through
CLS (Continuous Linked Settlement) for payment-vs-payment risk elimination, or
bilaterally via correspondent nostro/vostro chains when CLS-ineligible. Pain scenario:
an FX settlement agent has to make a real branching decision — is this pair
CLS-eligible, or does it fall back to bilateral settlement with real principal risk —
and that branch has its own distinct data-access needs (correspondent bank account
data vs. CLS membership data) that shouldn't leak into each other.

**Commodities** — physically-settled contracts (a WTI future settling into an actual
delivery, warehouse receipts, quality certificates) vs. financially-settled swaps are
handled by agents that should never share a toolbelt — one needs logistics/storage
data, the other needs cash-settlement data only. Pain scenario: misrouting a
physical-delivery obligation to a cash-settlement agent (or vice versa) is a good
denial/governance-boundary story, plus clearinghouse (CME/ICE) variation-margin call
verification is a time-pressured check analogous to the DTCC step in equities.

**Fixed Income** — corporate/muni bonds moved to T+1 alongside equities in 2024, but
Treasuries and repo can settle same-day (T+0). Pain scenario: an agent misclassifying
instrument type (bond vs. Treasury vs. repo) picks the wrong settlement cycle
entirely — a good "grounded in real reference data, not LLM-improvised" decision-node
story. Accrued-interest calculation correctness feeding the settlement amount is
another concrete, checkable data point.

**International** — really a composition problem, not a new primitive: a non-US
equity or bond settlement needs the equities/fixed-income pipeline *plus* an FX
conversion step *plus* a local sub-custodian (global custodian → local market
custodian chain) *plus* market-specific settlement cycles (some emerging markets
still T+2/T+3) *plus* cross-border withholding tax logic. Best built last, as the
capstone that composes agents from the other four sub-domains — same relationship
`institutional_portfolio_review` already has to `aml_compliance` (a workflow that
spans policy surfaces other demos own individually).

## Suggested build sequence

All 5 land inside `examples/trading_desk_ops/` over time, added the same way
`institutional_portfolio_review`'s `REVIEW_TYPES` grew — one new domain branch at a
time, not a new example each round. Equities first (closest to a clean single-domain
build, and the one already fully sketched above). Fixed Income second (same T+1
cycle, different instrument-classification risk — the fastest follow-on). FX and
Commodities third and fourth (each needs a real branching decision Equities/Fixed
Income don't). International last, as the cross-cutting domain that composes the
other four's agents rather than introducing its own from scratch.
