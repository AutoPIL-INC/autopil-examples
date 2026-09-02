"""
Simulated data for the AutoPIL + LangGraph Care Coordination demo.

Adapted from the core AutoPIL SDK repo's `policies/healthcare/clinical_operations.yaml`
(4 flat specialist policies, no orchestrator) into this repo's fixture-table shape —
see DESIGN.md's "Adapting from the original policy file" section for what changed and
why. No live EHR/pharmacy system anywhere; every guarded getter in
care_coordination_demo.py reads from the tables below, exactly like every other demo
in this repo.

4 cases, each a distinct care-coordination story:
  - CC-001 (Marcus Whitfield): acute symptom call — chest tightness + low SpO2 on a
    patient with a cardiac history, on an anticoagulant. Escalation case.
  - CC-002 (Dolores Kim): care-gap outreach — a diabetic patient overdue for an A1C
    and retinal exam per the chronic-condition registry.
  - CC-003 (Andre Boucher): medication refill — a routine ACE-inhibitor refill with a
    clean interaction/allergy check. The demo's over-scope story: medication review
    reaching for the raw chart directly instead of trusting its own lane.
  - CC-004 (Priya Anand): clean well-visit — nothing acute, no gap, no refill needed.
"""

# ── cases — the primary entity every domain table is keyed by ──────────────────────

CASES = {
    "CC-001": {
        "case_id": "CC-001", "patient_name": "Marcus Whitfield", "age": 58, "sex": "M",
        "case_type": "acute_symptom", "cardiac_history": True,
    },
    "CC-002": {
        "case_id": "CC-002", "patient_name": "Dolores Kim", "age": 64, "sex": "F",
        "case_type": "care_gap", "cardiac_history": False,
    },
    "CC-003": {
        "case_id": "CC-003", "patient_name": "Andre Boucher", "age": 45, "sex": "M",
        "case_type": "refill_request", "cardiac_history": False,
    },
    "CC-004": {
        "case_id": "CC-004", "patient_name": "Priya Anand", "age": 34, "sex": "F",
        "case_type": "well_visit", "cardiac_history": False,
    },
}

CASE_METADATA = {cid: {"case_id": cid, "status": "open", "assigned_to": None} for cid in CASES}

# ── symptom_intake / vital_signs — triage_agent's own lane ──────────────────────────

SYMPTOM_INTAKE = {
    "CC-001": {"chief_complaint": "Chest tightness and shortness of breath", "onset": "2 hours ago",
               "self_reported_severity": "moderate-severe"},
    "CC-002": {"chief_complaint": "Routine chronic-care check-in call", "onset": "n/a", "self_reported_severity": "none"},
    "CC-003": {"chief_complaint": "Requesting prescription refill", "onset": "n/a", "self_reported_severity": "none"},
    "CC-004": {"chief_complaint": "Annual well-visit, no complaints", "onset": "n/a", "self_reported_severity": "none"},
}

VITAL_SIGNS = {
    "CC-001": {"hr": 112, "bp": "158/95", "spo2": 91, "temp": 37.4},
    "CC-002": {"hr": 76, "bp": "132/82", "spo2": 98, "temp": 36.8},
    "CC-003": {"hr": 70, "bp": "128/80", "spo2": 99, "temp": 36.7},
    "CC-004": {"hr": 68, "bp": "118/76", "spo2": 99, "temp": 36.6},
}

PATIENT_DEMOGRAPHICS = {cid: {"name": c["patient_name"], "age": c["age"], "sex": c["sex"]} for cid, c in CASES.items()}

# ── ehr_summaries / lab_results / care_plans — clinical_summary_agent's lane ────────

EHR_SUMMARIES = {
    "CC-001": {
        "summary": "58M with prior MI 3 years ago, on chronic anticoagulation (warfarin). "
                   "Presents with acute chest tightness and dyspnea, SpO2 91% at intake.",
        "relevant_history": ["MI (3 years ago)", "Hypertension", "On warfarin since MI"],
    },
    "CC-002": {
        "summary": "64F with Type 2 diabetes, managed with metformin. No acute complaints; "
                   "calling in for a routine chronic-care check-in.",
        "relevant_history": ["Type 2 diabetes (8 years)", "No prior retinopathy on record"],
    },
    "CC-003": {
        "summary": "45M with hypertension, well-controlled on lisinopril 10mg daily for 2 years. "
                   "Requesting routine refill, no new complaints.",
        "relevant_history": ["Hypertension (2 years)", "No known drug allergies on file"],
    },
    "CC-004": {
        "summary": "34F, healthy, presenting for annual well-visit. No chronic conditions, "
                   "no current medications, no complaints.",
        "relevant_history": [],
    },
}

LAB_RESULTS = {
    "CC-001": [{"test": "Troponin", "value": "0.02 ng/mL", "flag": "within normal limits, but drawn at intake — "
                                                                     "trend pending"}],
    "CC-002": [{"test": "A1C", "value": "8.1%", "date": "14 months ago", "flag": "elevated, overdue for recheck"}],
    "CC-003": [{"test": "Basic metabolic panel", "value": "potassium 4.2 mEq/L", "date": "3 months ago", "flag": "normal"}],
    "CC-004": [{"test": "CBC", "value": "within normal limits", "date": "this visit", "flag": "normal"}],
}

CARE_PLANS = {
    "CC-002": {"active_goals": ["A1C < 7.5%", "Annual retinal exam", "Quarterly foot exam"],
               "last_updated": "5 months ago"},
    "CC-004": {"active_goals": ["Maintain healthy weight", "Annual well-visit"], "last_updated": "this visit"},
}

# ── medication_history / allergy_records / pharmacy_data / drug_interaction_db —
#    medication_review_agent's lane ─────────────────────────────────────────────────

MEDICATION_HISTORY = {
    "CC-001": [{"drug": "Warfarin", "dose": "5mg daily", "started": "3 years ago", "indication": "post-MI anticoagulation"}],
    "CC-002": [{"drug": "Metformin", "dose": "1000mg twice daily", "started": "8 years ago", "indication": "Type 2 diabetes"}],
    "CC-003": [{"drug": "Lisinopril", "dose": "10mg daily", "started": "2 years ago", "indication": "hypertension"}],
    "CC-004": [],
}

ALLERGY_RECORDS = {
    "CC-001": [], "CC-002": [], "CC-003": ["No known drug allergies"], "CC-004": [],
}

PHARMACY_DATA = {
    "CC-001": {"last_fill": "28 days ago", "adherence": "on schedule"},
    "CC-002": {"last_fill": "25 days ago", "adherence": "on schedule"},
    "CC-003": {"last_fill": "30 days ago", "adherence": "on schedule", "refill_requested": "Lisinopril 10mg"},
    "CC-004": {"last_fill": None, "adherence": "n/a"},
}

# Reference material, not PHI — low sensitivity, mirrors coding_guidelines in
# hospital_revenue_cycle_data.py.
DRUG_INTERACTION_DB = {
    "guideline": "Common clinically significant interaction pairs (reference excerpt)",
    "relevant_pairs": [
        "Warfarin + NSAIDs: increased bleeding risk — avoid co-administration or monitor INR closely.",
        "ACE inhibitors (e.g. lisinopril) + potassium-sparing diuretics/supplements: hyperkalemia risk.",
        "Metformin + iodinated contrast: transient renal impairment risk — hold metformin around imaging.",
    ],
}

# ── chronic_condition_registry / preventive_care_schedule — care_gap_agent's lane ──

CHRONIC_CONDITION_REGISTRY = {
    "CC-002": {"condition": "Type 2 diabetes", "last_a1c_date": "14 months ago", "a1c_overdue_days": 195,
               "guideline_interval_days": 180},
}

PREVENTIVE_CARE_SCHEDULE = {
    "CC-002": {"screening": "Diabetic retinal exam", "last_completed": "22 months ago", "overdue_days": 305,
               "guideline_interval_days": 365},
}

# ── agent_outputs — pre-compiled compiled findings, distinct from live per-run
#    findings gathered during the graph run itself; mirrors every other demo's
#    AGENT_OUTPUTS ──────────────────────────────────────────────────────────────────

AGENT_OUTPUTS = {
    "CC-001": {
        "clinical_summary_agent": {
            "summary": "Cardiac history (prior MI, on warfarin) plus acute chest tightness and SpO2 91% "
                       "warrants urgent evaluation rather than outpatient management.",
            "recommendation": "ESCALATE",
        },
        "medication_review_agent": {
            "summary": "Patient is on chronic warfarin; no NSAID or other interacting agent currently "
                       "active, but any new analgesic order should avoid NSAIDs given bleeding risk.",
            "recommendation": "FLAG_INTERACTION_RISK",
        },
    },
    "CC-002": {
        "care_gap_agent": {
            "summary": "A1C last checked 14 months ago (195 days overdue per guideline interval) and "
                       "retinal exam overdue by 305 days.",
            "recommendation": "OUTREACH_NEEDED",
        },
        "clinical_summary_agent": {
            "summary": "No chart note in the last 6 months addressing either overdue screening — gap is "
                       "real, not already resolved.",
            "recommendation": "CONFIRMED_GAP",
        },
    },
    "CC-003": {
        "medication_review_agent": {
            "summary": "No known allergies, no interacting medications on file, refill request matches "
                       "existing dose and indication.",
            "recommendation": "APPROVE",
        },
    },
    "CC-004": {
        "clinical_summary_agent": {
            "summary": "No chronic conditions, no current medications, no concerning findings at this visit.",
            "recommendation": "COMPLIANT",
        },
    },
}

# ── expected outcomes — ground truth the rule-based decision_node checks against ───

EXPECTED_OUTCOMES = {
    "CC-001": {"disposition": "ESCALATE — refer for urgent care",
               "reason": "SpO2 91% (<92% threshold) with a positive cardiac history"},
    "CC-002": {"disposition": "OUTREACH REQUIRED — care gap identified",
               "reason": "A1C 195 days overdue against a 180-day guideline interval"},
    "CC-003": {"disposition": "REFILL APPROVED — no interaction or contraindication found",
               "reason": "No allergy or interaction flags; refill matches existing dose and indication"},
    "CC-004": {"disposition": "COMPLIANT — no action required",
               "reason": "No acute findings, no overdue screenings, no medications on file"},
}


# ── convenience accessors ───────────────────────────────────────────────────────────

def get_case(case_id: str) -> dict:
    return CASES.get(case_id, {})


def get_agent_outputs(case_id: str) -> dict:
    return AGENT_OUTPUTS.get(case_id, {})


def get_expected_outcome(case_id: str) -> dict:
    return EXPECTED_OUTCOMES.get(case_id, {})
