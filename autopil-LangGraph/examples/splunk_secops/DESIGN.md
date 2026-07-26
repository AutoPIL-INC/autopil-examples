# SOC / Splunk SecOps Multi-Agent Demo — Design Doc

## 1. Why this demo

Every other demo in this repo governs financial-services data domains (fraud,
wealth/portfolio review, AML/KYC, tiered client review). This one moves the same
governance pattern into security operations: IBM mainframe tooling forwards `z/OS` SMF
(System Management Facility) log types into Splunk, and 5 SOC agent roles investigate
security cases over that data — RACF access-violation review, live-incident triage,
compliance reporting, and a final threat-report synthesis. Same story, different
industry: per-role data boundaries, a reasoning-driven orchestrator, and a synthesizer
that reads compiled outputs only.

## 2. Design approach: reasoning-driven agents, not scripted logic

Same principle as `fraud_investigation` (the canonical reference this repo's
`USECASE_GUIDE.md` points to): every specialist is a real Claude tool-calling loop,
handed a toolbelt **wider** than its AutoPIL policy authorizes. A denial happens only
when the model itself reaches for an out-of-scope source — never a scripted branch.
This means the exact denial pattern varies run to run; see `README.md`'s "What to
expect."

## 3. Folder structure

```
examples/splunk_secops/
├── DESIGN.md                          # this file
├── README.md                          # setup + run instructions
├── splunk_secops_data.py              # fixture data — no live Splunk anywhere
├── splunk_secops_demo.py              # the demo itself
├── policies/SecOps/
│   └── soc_mainframe_logs.yaml        # the 5-role AutoPIL policy matrix
└── frontend/                          # Vite + React + TypeScript live viewer
```

No `saas_guard.py`/hosted-SaaS-trial mode, unlike the other 4 demos — out of scope for
this round (see §7).

## 4. Governance surface being demonstrated

| Role | Reads | Denied | Sensitivity ceiling | Notable mechanism |
|---|---|---|---|---|
| `soc_orchestrator` | `security_alerts`, `case_metadata`, `agent_outputs` | every raw SMF source, `splunk_index_summery`, `regulatory_templates` | medium | orchestration only — never touches raw logs |
| `security_auditor` | `smf_security` | everything else | high | `permitted_agent_ids` locks the daily scheduled sweep to a named service agent, mirroring `transaction_analyst_policy` |
| `incident_triage` | all 4 SMF sources + `security_alerts` + `case_metadata` | `splunk_index_summery`, `agent_outputs`, `regulatory_templates` | critical | broadest allowed set of any specialist, deliberately time-boxed (`session_ttl_minutes: 30` + a 2-step `sensitivity_decay`) |
| `compliance_reporter` | `splunk_index_summery` only | every raw SMF source + everything else | medium | narrowest specialist — index-level rollups only, never a raw field |
| `splunk_threat_synthesizer` | `agent_outputs`, `case_metadata`, `regulatory_templates` | every raw SMF source, `splunk_index_summery` | critical | same role `sar_generator` plays in `fraud_investigation` — reads compiled findings only |

## 5. Scenarios (`splunk_secops_data.py`)

- **SEC-001** — routine daily RACF sweep on `MVSP01` (`security_auditor`'s scheduled
  job): a below-incident-threshold access-violation pattern. `orchestrator_review_node`
  is expected to route straight to `compliance_reporter` next rather than escalating —
  this is the concrete mechanism behind "the orchestrator reads security_auditor's
  reasoning and decides to call compliance_reporter."
- **SEC-002** — active incident on `MVSP02` (card authorization): an unauthorized RACF
  privilege grant correlated with a CPU spike and abending high-value transactions.
  Exercises `incident_triage`'s broad, time-boxed cross-source access.
- **SEC-003** — compliance spot-check on the clean `MVSP03` system. `compliance_reporter`
  is handed `get_smf_security_events`/`get_smf_transactions` as plausible-but-denied
  over-scope tools — the demo's explicit "compliance_reporter tries to read raw SMF
  fields directly" scenario.
- **SEC-004** — multi-source correlation incident on `MVSP04` (general ledger, SOX
  scope): unauthorized batch postings outside the change window plus an unscheduled
  subsystem restart. Exercises the full pipeline plus `splunk_threat_synthesizer`'s
  session-isolation and role-spoofing over-scope tools (see below).

`splunk_threat_synthesizer_tools()` includes the same two attack-surface tools
`sar_generator_tools()` demonstrates in `fraud_investigation`:
1. **Session isolation** — `get_case_agent_outputs` reaches `agent_outputs` (a source
   the synthesizer legitimately reads) through `incident_triage`'s session_id instead of
   its own — denied independent of the source policy check.
2. **Role spoofing** — `get_subject_racf_status` uses the synthesizer's own real,
   registered `agent_id` but claims `agent_role="security_auditor"` to reach
   `smf_security` — denied as `role_not_permitted` because the registry validates the
   claimed role against that `agent_id`'s canonical value, not the caller's claim.

Both were verified directly (bypassing the LLM, calling the guarded getters with the
exact same arguments the tools use) during development — see the commit history for the
verification transcript.

## 6. Correcting the source spec

The original 5-role source list, taken literally, had a few self-contradictions (the
same source appearing in both a role's allowed and denied list — almost certainly
copy-paste artifacts from listing "everything except what's allowed" by hand). Resolved
by treating each role's **allowed list as authoritative** and computing
`denied_sources` as the complement over the full 9-source set — this reproduces every
non-contradictory entry the original spec listed and drops only the conflicting ones.
Two duplicate source names in the original list (`agent_outputs` / `agent_output`) were
collapsed into the single canonical `agent_outputs`, matching every other demo's naming.

## 7. Out of scope for this round

- **Hosted AutoPIL SaaS trial mode** — every other demo in this repo supports this
  (`AUTOPIL_ADMIN_KEY`/`AUTOPIL_EVALUATE_KEY`); this demo intentionally stays local-only
  to keep the addition scoped to the governance pattern itself.
- **OpenAI Agents SDK variant** and a **pytest suite** — `USECASE_GUIDE.md` (from the
  core `autopil` SDK repo) calls for both as part of a complete use case; this repo's
  existing demos (fraud/client_analysis/institutional_portfolio_review/aml_compliance)
  don't carry either one, so this addition follows the *established convention of this
  repo* rather than the guide's full 6-artifact checklist.
- **Literal scheduling** — "security_auditor's daily scheduled operation" is modeled as
  a design fact (its policy assumes a named, approved service agent via
  `permitted_agent_ids`, mirroring a real cron-triggered service identity), not as
  actual cron/timer code — no demo in this repo runs anything on an actual schedule.
