# Trading Desk Ops — Planning Doc

**Status: Equities and Fixed Income built** (`examples/trading_desk_ops/`). Equities:
backend, frontend, and hosted SaaS trial mode all live (PR #5). Fixed Income: backend
only so far (extending the same graph/policy, not a new example) — frontend and
hosted-mode coverage for it are a separate follow-up task. Both sub-domains' full
design detail now lives in that example's own `DESIGN.md`, not here — see the short
pointer below instead of a duplicate; the "Sub-domain 2 (next build)" section below is
kept as the original build sketch, superseded by `DESIGN.md` now that it's built. FX,
Commodities, and International remain at the pain-scenario-menu level until it's
their turn.

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

## Sub-domain 1 (built): Equities

`examples/trading_desk_ops/` — see that example's own `DESIGN.md` for full detail
(roles, compliance table, EQ-001..005 scenarios, two-tier human review, hosted SaaS
trial mode). Summary: an external client's 10,000-share block order fans out into
allocation across sub-accounts, same-day affirmation, DTCC settlement verification,
and (when something breaks) exception handling, inside a T+1 window.
`trading_ops_orchestrator`'s classification step doubles as the sub-domain router —
for Equities it only ever resolves to `"equities"`, but the same call is where Fixed
Income and the rest plug in as additional branches in `TRADING_DOMAINS`.

## Sub-domain 2 (next build): Fixed Income

Unlike Equities, this sub-domain adds a second axis of complexity: **instrument
classification determines the settlement cycle itself**, not just the workflow path.
A Treasury, a corporate bond, and an agency MBS traded TBA (To-Be-Announced) settle on
three different calendars (T+1, T+1, and a fixed monthly SIFMA date respectively),
cleared through different clearing corporations (FICC's GSD for Treasuries, DTCC for
corporates, FICC's MBSD for agency MBS). Misclassifying the instrument doesn't just
risk a wrong workflow — it computes an actually wrong settlement date.

Three mechanisms this sub-domain introduces that Equities didn't need:

- **Two distinct break types, not one.** Equities only had quantity/SSI mismatches.
  Fixed income adds **cash breaks** — the settlement amount itself (principal +
  accrued interest) can be wrong because the day-count convention was misapplied
  (Treasuries use Actual/Actual, corporates typically use 30/360) even when quantity
  and counterparty match perfectly.
- **A deadline that hasn't happened yet, not just a break that already has.** TBA
  agency MBS has a hard 48-hour pool-notification cutoff before the SIFMA settlement
  date, via FICC's Pass-Thru Notification (PTN) system. This is a proactive
  time-window escalation, not a reactive break investigation — genuinely different
  from every scenario in Equities.
- **A named, real financial penalty regime for the worst case.** Treasury settlement
  fails trigger FICC's actual **Fails Charge Trading Practice** (a specific
  formula-based penalty on failed Treasury/Agency MBS settlements) — sharper
  regulatory grounding than Equities' EQ-005 had.

### Roles (Equities' 7, plus one genuinely new one)

Same shape as Equities — orchestrator + specialists, dynamic classification, two-tier
review — plus:

| Role | Reads | Denied | Notable mechanism |
|---|---|---|---|
| `instrument_classification_agent` *(new)* | security master / CUSIP reference data | client account/position data, pricing, commission | Resolves instrument type (Treasury / corporate / municipal / agency MBS-TBA) into the correct settlement cycle and day-count convention. Everything downstream depends on this being right — FI-002 is what happens when it isn't. |

The other 6 roles (`fixed_income_ops_orchestrator`, and Fixed-Income-flavored versions
of `affirmation_matching_agent`, `settlement_reconciliation_agent`,
`exception_investigation_agent`, `compliance_reporting_agent`, plus a settlement-amount
calculation role) carry over Equities' shape — full allowed/denied source detail to be
finalized at build time, same as Equities' worked example was before its own build.

### Compliance framework (lighter pass — full table at build time)

| Regulation / mechanism | Grounds |
|---|---|
| SEC Rule 15c6-1 | T+1 now covers corporate/municipal bonds (May 2024); Treasuries were already T+1 |
| FICC GSD (Government Securities Division) | Treasury clearing/netting — FI-005's core check |
| FICC MBSD + Pass-Thru Notification (PTN) | TBA MBS pool notification deadline — FI-004 |
| FICC Fails Charge Trading Practice | The named penalty regime — FI-005's escalation |
| FINRA TRACE / MSRB Rule G-14 (RTRS) | 15-minute post-trade reporting for corporate/municipal bonds — a much tighter compliance-reporting clock than equities' CAT |
| Day-count convention standards (Actual/Actual vs. 30/360) | FI-003's grounding reference table |

### Scenarios

- **FI-001 — Clean straight-through (corporate bond).** Correctly classified via
  CUSIP/security-master lookup, correct 30/360 accrued-interest calculation, clean
  affirmation, clean FICC/DTCC settlement match. Baseline.
- **FI-002 — Instrument misclassification risk.** A trade ticket is ambiguous about
  whether it's a Treasury note or a similarly-named agency/corporate bond. The
  classification agent must resolve this from real reference data, not guess — a
  wrong classification computes the wrong settlement cycle entirely (and if
  misclassified as TBA MBS, an entirely wrong monthly settlement date).
- **FI-003 — Accrued-interest / day-count convention break (a cash break, not a
  quantity break).** The settlement amount is computed with the wrong day-count
  convention for this instrument type, producing a real cash mismatch at affirmation
  even though quantity and counterparty details are correct. Grounded in a real
  reference table, not an LLM's own arithmetic.
- **FI-004 — TBA MBS pool-notification deadline at risk (proactive escalation).** An
  agency MBS trade approaching its 48-hour pool-notification cutoff before the SIFMA
  settlement date. The investigation agent must recognize the deadline risk *before*
  a fail happens and escalate proactively — a genuinely different reasoning shape
  than every reactive-investigation scenario in this repo so far.
- **FI-005 — Treasury settlement fail, Fails Charge regime (Tier 2, highest
  severity).** A Treasury trade fails to settle — a real inventory/counterparty
  shortfall — triggering FICC's actual Fails Charge Trading Practice. Escalates to
  Tier 2 compliance-officer review, same severity tier as Equities' EQ-005 but
  grounded in fixed income's own named penalty mechanism.

**Optional stretch scenario (not core to this round):** a repo/collateral-substitution
case — genuinely different governance shape again (daily mark-to-market, margin
calls, collateral eligibility/haircut schedules) rather than a settlement-chain
problem at all. Worth a future FI-006 if repo-desk coverage is wanted later, kept
separate from the initial 5 rather than diluting this round.

## Pain-scenario menu: the remaining sub-domains

FX, Commodities, and International stay at this lighter menu level until their turn.

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
time, not a new example each round. **Equities — done.** Fixed Income next (sketched
in full above, not yet built). FX and Commodities after that (each needs a real
branching decision Equities/Fixed Income don't). International last, as the
cross-cutting domain that composes the other four's agents rather than introducing
its own from scratch.
