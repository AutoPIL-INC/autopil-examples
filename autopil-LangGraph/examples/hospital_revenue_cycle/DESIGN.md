# Hospital Revenue Cycle Multi-Agent Demo — Design Doc

## 1. Why this demo

Every other demo in this repo (except `splunk_secops`) governs financial-services data
domains. This one moves the same governance pattern into healthcare revenue-cycle
operations: a hospital's clinical, coding, and billing teams each have a legitimate but
narrow job — a CDI specialist needs clinical notes, a charge reconciliation agent does
not — and AutoPIL enforces that boundary at runtime while a 6-agent pipeline finds real
revenue leakage (undercoded diagnoses, missed charges) across 4 patient encounters.

## 2. Adapting from the original scripted demo

This demo's scenario, roles, and data are adapted from the core AutoPIL SDK repo's
`examples/hospital_revenue_cycle/` — a REST-only, fully **scripted** demo (every
`POST /v1/context/evaluate` call, including the deliberate policy-violation attempt, is
hardcoded in `scenario.py`; no LLM decides anything). That's a direct contradiction of
this repo's core design principle (see `USECASE_GUIDE.md` and every other demo's own
DESIGN.md): a denial should happen because a real reasoning loop decided to reach for
something out of scope, not because a scripted branch forced it to. Porting it required
more than a file copy:

- **Reasoning-driven, not scripted.** Every role here is a real Claude tool-calling
  loop with a toolbelt wider than its policy authorization — same as
  `fraud_investigation`/`splunk_secops`. The original's hardcoded "charge_reconciliation
  attempts raw EHR access" moment is now something the model decides to try, framed as
  a plausible tool ("if you need to verify a charge directly").
- **Local-first, not REST-only.** The original required a live AutoPIL server
  (`AUTOPIL_URL`/`AUTOPIL_API_KEY`) to run at all. This demo defaults to the embedded,
  local `ContextGuard` like every other demo in this repo — no server required. (Hosted
  SaaS trial mode is out of scope for this round — see §7.)
- **A real intake source for the orchestrator.** The original `revenue_orchestrator`'s
  policy only allowed `agent_outputs` — workable for a purely sequential scripted
  pipeline with no real routing decision, but this orchestrator has to decide which
  specialists to invoke and in what order, so it needs a legitimate intake source. Added
  `case_metadata` (low-sensitivity encounter status) to `revenue_orchestrator_policy`,
  mirroring every other demo's orchestrator (`case_metadata`/`security_alerts` in
  `fraud_investigation`/`splunk_secops`).
- **One dedicated policy file, not four unrelated ones mixed in.** The original
  `policies/healthcare/revenue_cycle.yaml` also carried 4 policies
  (`prior_auth_agent`, `claims_coding_agent`, `denial_management_agent`,
  `patient_billing_agent`) for a different, unrelated workflow that this demo's 6 roles
  never use. This demo's `policies/healthcare/revenue_cycle.yaml` carries only the 6
  policies its own roles actually reference.
- **A clean baseline encounter added.** The original had 3 scenarios, all with a real
  finding. Added ENC-004 — no revenue leakage, no violation attempt — the same way
  every other demo in this repo keeps a clean case alongside the ones with something to
  find (e.g. `splunk_secops`'s MVSP05, `fraud_investigation`'s clean accounts).
- **`coding_guidelines` added as a reference source.** The original's `cdi_specialist`/
  `medical_coding_agent` policies referenced a `coding_guidelines` source with no
  backing data. Added a small ICD-10-CM guideline excerpt table — the low-sensitivity
  reference material every demo in this repo gives its coding/compliance-adjacent
  roles (mirrors `regulatory_templates` in `fraud_investigation`/`splunk_secops`).

## 3. Folder structure

```
examples/hospital_revenue_cycle/
├── DESIGN.md                          # this file
├── README.md                          # setup + run instructions
├── hospital_revenue_cycle_data.py     # fixture data — no live EHR/billing system anywhere
├── hospital_revenue_cycle_demo.py     # the demo itself
├── policies/healthcare/
│   └── revenue_cycle.yaml             # the 6-role AutoPIL policy matrix
└── frontend/                          # Vite + React + TypeScript live viewer
```

No `saas_guard.py` — hosted SaaS trial mode is out of scope for this round (see §7),
same starting point `splunk_secops` had before its own hosted-mode addition.

## 4. Governance surface being demonstrated

| Role | Reads | Denied | Sensitivity ceiling | Notable mechanism |
|---|---|---|---|---|
| `revenue_orchestrator` | `case_metadata`, `agent_outputs` | every clinical/coding/billing source | high | orchestration + final revenue aggregation only — never touches a raw source |
| `clinical_documentation_agent` | `ehr_summaries`, `clinical_notes`, `vital_signs`, `lab_results` | everything else | critical | `permitted_agent_ids` locks this role to a named service agent, mirroring `security_auditor_policy` in `soc_mainframe_logs.yaml`; the only role with raw PHI access |
| `cdi_specialist_agent` | `clinical_notes`, `diagnosis_codes`, `coding_guidelines` | billing/charge sources + everything clinical it doesn't need | critical | reviews documentation gaps without touching billing at all |
| `medical_coding_agent` | `procedure_codes`, `diagnosis_codes`, `coding_guidelines` | raw clinical sources + billing | high | assigns codes from coded reference data only, never the raw chart |
| `charge_reconciliation_agent` | `charge_master`, `billing_records`, `agent_outputs` | every clinical/coding source | high | the demo's core over-scope scenario — reaches for raw clinical sources to "verify a charge directly" |
| `billing_compliance_agent` | `billing_records`, `insurance_eligibility`, `agent_outputs` | every clinical/coding source | high | final claim validation from compiled outputs, not the chart |

## 5. Scenarios (`hospital_revenue_cycle_data.py`)

- **ENC-001** — CDI gap on a respiratory-failure ICU stay: clinical notes support acute
  respiratory failure with hypoxia (ABG, mechanical ventilation), but the discharge code
  filed is unspecified. `orchestrator_review_node` is expected to route toward
  `cdi_specialist_agent`/`medical_coding_agent` after `clinical_documentation_agent`
  surfaces the discrepancy — the concrete mechanism behind "the coding gap gets a CDI
  query and a code recommendation, not just a clinical note."
- **ENC-002** — missed charge: a wound debridement is documented but never billed.
  Exercises `charge_reconciliation_agent`'s legitimate charge-master/billing-record
  reconciliation path.
- **ENC-003** — missed charge *with* an over-scope attempt: `charge_reconciliation_agent`
  is handed `get_ehr_summary`/`get_clinical_notes` as plausible-but-denied tools ("if you
  need to verify a charge directly"). Exercises the reroute-to-`clinical_documentation_agent`
  reasoning this demo's closest sibling (`splunk_secops`) also demonstrates.
- **ENC-004** — clean baseline: coding and billing are already correct. No revenue
  leakage, no violation attempt — used the same way every other demo in this repo keeps
  a clean case alongside the ones under investigation.

`revenue_summary_tools()` includes the same two attack-surface tools every other
demo's final-role equivalent (`sar_generator_tools()`, `splunk_threat_synthesizer_tools()`)
demonstrates:
1. **Session isolation** — `get_case_agent_outputs` reaches `agent_outputs` (a source
   `revenue_orchestrator` legitimately reads) through `billing_compliance_agent`'s
   session_id instead of its own — denied independent of the source policy check.
2. **Role spoofing** — `get_subject_billing_status` uses `revenue_orchestrator`'s own
   real, registered `agent_id` but claims `agent_role="billing_compliance_agent"` to
   reach `billing_records` — denied as `role_not_permitted` because the registry
   validates the claimed role against that `agent_id`'s canonical value, not the
   caller's claim.

Both verified directly during development — see §8.

## 6. A real bug caught during verification

`revenue_orchestrator_policy` and `billing_compliance_agent_policy` were both initially
written with `max_sensitivity: medium`, but their own real, allowed sources
(`agent_outputs`, `billing_records`) are rated `high` — meaning every legitimate call
either role made was denied on a sensitivity-ceiling mismatch before the source check
ever mattered, regardless of model behavior. Same shape bug `aml_compliance`'s own
DESIGN.md documents catching (a task_type/task_bindings mismatch there; a sensitivity
ceiling mismatch here) — both fail silently as an always-deny rather than an error, so
neither surfaces unless you check the live audit trail. `cdi_specialist_agent_policy`
had the same issue: it's genuinely allowed to read `clinical_notes` (`critical`-rated),
but its ceiling was `high`. Fixed by raising all three roles' `max_sensitivity` to match
their own highest-rated real source (`high`, `high`, and `critical` respectively) —
verified live afterward: every real allowed source cleanly ALLOWs, every over-scope/
attack-surface tool still correctly DENIES (raising a ceiling doesn't weaken a
source-based, session-isolation, or role-spoofing denial, since those checks don't
depend on the sensitivity ceiling at all).

## 7. Out of scope for this round

- **Hosted AutoPIL SaaS trial mode** — same starting point `splunk_secops` had before
  its own hosted-mode addition; not carried over from the original demo's REST-only
  design either, since that used the hosted API unconditionally rather than as an
  opt-in alongside a local default.
- **OpenAI Agents SDK variant** and a **pytest suite** — same convention every existing
  demo in this repo follows (see `splunk_secops`'s DESIGN.md §7 for the same call).
- **A second, MCP-transport audit-trail interrupt** — `splunk_secops` added this after
  its initial round; this demo starts at the same single-interrupt (approve/override)
  shape `fraud_investigation`/`aml_compliance`/`institutional_portfolio_review` use.

## 8. Verification notes

Live-tested via the CLI path across all 4 encounters. ENC-003 confirmed the full
reroute story: `charge_reconciliation_agent` denied on `clinical_notes` while its real
tools (`charge_master`/`billing_records`/`agent_outputs`) still succeeded,
`orchestrator_review_node` routed to `clinical_documentation_agent` next citing the
denial, and `decision_node` computed the correct $1,750 recovery with
`policy_violation: True` reflected in the proposed action. Session-isolation
(`get_case_agent_outputs`) and role-spoofing (`get_subject_billing_status`) both denied
with the expected reasons (`cross_agent_isolation`, `role_not_permitted`) during the
same run.
