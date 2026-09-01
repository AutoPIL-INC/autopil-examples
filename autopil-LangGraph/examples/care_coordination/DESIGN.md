# Care Coordination Multi-Agent Demo — Design Doc

## 1. Why this demo

`hospital_revenue_cycle` covers the back-office half of healthcare AI governance —
coding, charges, claims. This one covers the point-of-care half: a care team with
triage, chart review, medication management, and chronic-care outreach, each with a
narrow legitimate job over patient data. Together they give the Healthcare vertical the
same kind of functional split Financial Services has across its 5 demos, rather than
two demos telling the same billing-flavored story.

## 2. Adapting from the original policy file

This demo's roles and data are adapted from the core AutoPIL SDK repo's
`policies/healthcare/clinical_operations.yaml` — 4 flat specialist policies with **no
orchestrator role at all** and **no `task_bindings`/`require_task_for_sensitivity`
anywhere in the file**. Porting it required more than a straight copy:

- **A 5th role added for real routing.** Unlike `hospital_revenue_cycle`'s
  `revenue_orchestrator` (which already had a real `revenue_summary` task in the
  original), none of the 4 original roles here naturally fits an orchestrator identity
  without semantic stretching — `triage_agent` is about symptom urgency, not case
  routing. Added `care_coordinator`, a genuinely new role, matching the majority
  convention (`fraud_investigation`/`institutional_portfolio_review`/`splunk_secops`
  all use a dedicated orchestrator, not a repurposed specialist).
- **`task_bindings`/`require_task_for_sensitivity` added to all 5 roles.** The original
  file has neither anywhere — every demo in this repo needs them, since `task_type` is
  passed on every guarded call. Added consistently, disclosed here rather than silently
  assumed.
- **`care_plans` sensitivity set to `medium`, not `high`.** It's shared between
  `clinical_summary_agent` (a `high`-ceiling role) and `care_gap_agent` (a
  `medium`-ceiling role) in the original. Rating a shared source above the lower of the
  two roles' ceilings reproduces the exact bug caught in `hospital_revenue_cycle`
  (see §6) — picked the lower tier from the start this time.
- **No fixed final specialist, unlike every other orchestrated demo here.**
  `fraud_investigation`/`splunk_secops`/`hospital_revenue_cycle` all have one role that
  always runs last before the synthesizer step (`sar_generator`,
  `splunk_threat_synthesizer`, `billing_compliance_agent`). None of this demo's 4
  specialists is naturally "always last" — which one matters depends entirely on the
  case (an acute call needs `clinical_summary_agent` last to confirm history; a refill
  needs `medication_review_agent` last). So `care_coordinator` routes among all 4 via
  the same re-routing loop, then compiles the summary itself — one fewer graph node
  than `hospital_revenue_cycle`, not a missing piece.

## 3. Folder structure

```
examples/care_coordination/
├── DESIGN.md                          # this file
├── README.md                          # setup + run instructions
├── care_coordination_data.py          # fixture data — no live EHR/pharmacy system anywhere
├── care_coordination_demo.py          # the demo itself
├── policies/healthcare/
│   └── clinical_operations.yaml       # the 5-role AutoPIL policy matrix
└── frontend/                          # Vite + React + TypeScript live viewer
```

No `saas_guard.py` — hosted SaaS trial mode is out of scope for this round (see §7),
same starting point `hospital_revenue_cycle` had.

## 4. Governance surface being demonstrated

| Role | Reads | Denied | Sensitivity ceiling | Notable mechanism |
|---|---|---|---|---|
| `care_coordinator` | `case_metadata`, `agent_outputs` | every clinical/medication/registry source | high | Routes to specialists, compiles the final care note — never touches a raw clinical source. Ceiling set to `high` from the start (see §6). |
| `triage_agent` | symptom intake, vitals, demographics | chart, medications, registry | medium | Narrowest role — intake only, no chart access |
| `clinical_summary_agent` | EHR summaries, labs, vitals, care plans | medications, registry | high, decaying to medium (60min) then low (120min) | Only role with full-chart access; ceiling narrows as the session ages |
| `medication_review_agent` | medication history, allergies, pharmacy data, drug-interaction reference | chart, registry | high, same decay schedule | `permitted_agent_ids`-locked (the original policy's own comment calls for this); the demo's core over-scope scenario lives here |
| `care_gap_agent` | chronic-condition registry, preventive-care schedule, demographics, care plans | chart, medications | medium | Population/outreach angle, lowest ceiling of the four specialists |

## 5. Scenarios (`care_coordination_data.py`)

- **CC-001** (Marcus Whitfield) — acute symptom call: chest tightness, SpO2 91%, prior
  MI, on chronic warfarin. `orchestrator_review_node` is expected to route toward
  `clinical_summary_agent` after `triage_agent` flags the escalation concern, then
  `medication_review_agent` to check anticoagulation status before the disposition.
- **CC-002** (Dolores Kim) — care-gap outreach: diabetic patient overdue for an A1C
  recheck (195 days against a 180-day guideline interval). Exercises
  `care_gap_agent`'s registry-driven gap identification.
- **CC-003** (Andre Boucher) — routine medication refill: clean interaction/allergy
  check. `medication_review_agent` is handed plausible-but-denied tools
  (`get_ehr_summary`/`get_lab_results`) alongside its real ones — the demo's core
  "reaches for the raw chart instead of trusting its own lane" over-scope story.
- **CC-004** (Priya Anand) — clean well-visit: no chronic conditions, no medications,
  nothing concerning. Clean baseline case, same convention every demo here keeps.

`care_summary_tools()` includes the same two attack-surface tools every other demo's
final-role equivalent (`sar_generator_tools()`, `splunk_threat_synthesizer_tools()`,
`revenue_summary_tools()`) demonstrates:
1. **Session isolation** — `get_case_agent_outputs` reaches `agent_outputs` (a source
   `care_coordinator` legitimately reads) through `clinical_summary_agent`'s
   session_id instead of its own — denied independent of the source policy check.
2. **Role spoofing** — `get_subject_medication_status` uses `care_coordinator`'s own
   real, registered `agent_id` but claims `agent_role="medication_review_agent"` to
   reach `medication_history` — denied as `role_not_permitted` because the registry
   validates the claimed role against that `agent_id`'s canonical value, not the
   caller's claim.

Both verified directly during development — see §8.

## 6. A real bug caught during verification

`clinical_summary_tools()`'s `get_vital_signs` call was bound to `task_type=
"care_coordination"`, but that task's `task_bindings.permitted_sources` in the policy
YAML only lists `[ehr_summaries, care_plans, lab_results]` — `vital_signs` isn't in it,
even though it's genuinely in `clinical_summary_agent_policy.allowed_sources`. The call
was denied on every run regardless of model behavior, same shape bug
`aml_compliance`'s and `hospital_revenue_cycle`'s own DESIGN.md documents catching
(a task_type/task_bindings mismatch there and here; a sensitivity-ceiling mismatch in
`hospital_revenue_cycle`'s other caught bug) — fails silently as an always-deny rather
than an error, so it won't surface unless you check the live audit trail. Fixed by
rebinding the call to `task_type="chart_review"`, whose `task_bindings` already include
`vital_signs`. If you add or rewire a tool here, cross-check its `(source, task_type)`
pair against that task's `task_bindings.permitted_sources` in `clinical_operations.yaml`
directly — don't assume a source being in `allowed_sources` means every task binding
covers it.

## 7. Out of scope for this round

- **Hosted AutoPIL SaaS trial mode** — same starting point `hospital_revenue_cycle` had
  before any future hosted-mode addition.
- **OpenAI Agents SDK variant** and a **pytest suite** — same convention every existing
  demo in this repo follows.
- **A second, MCP-transport audit-trail interrupt** — single interrupt (approve/
  override), same shape as `fraud_investigation`/`aml_compliance`/
  `hospital_revenue_cycle`, not `splunk_secops`'s later addition.

## 8. Verification notes

Live-tested via the CLI path across all 4 cases. CC-001 confirmed the full
escalation story: `triage_agent` denied on `ehr_summaries`, `orchestrator_review_node`
routed to `clinical_summary_agent` next citing the escalation concern, then to
`medication_review_agent` to resolve the anticoagulation-status gap — all reasoning,
not scripted branches. `medication_review_agent` reached for both of its over-scope
tools (`get_ehr_summary`, `get_lab_results`) and both denied correctly. Session-isolation
(`get_case_agent_outputs`) and role-spoofing (`get_subject_medication_status`) both
denied with the expected reasons (`cross_agent_isolation`-equivalent context-ownership
message, `role_not_permitted`) during the same run. `decision_node` computed
`ESCALATE — refer for urgent care` correctly from real vitals + cardiac-history data,
independent of any specialist's self-reported finding.
