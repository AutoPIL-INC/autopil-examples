"""
Simulated data for the AutoPIL + LangGraph Hospital Revenue Cycle demo.

Adapted from the core AutoPIL SDK repo's `examples/hospital_revenue_cycle/` (a scripted
REST-only demo) into this repo's fixture-table shape — see DESIGN.md's "Adapting from
the original scripted demo" section for what changed and why. No live EHR/Splunk/etc.
anywhere; every guarded getter in hospital_revenue_cycle_demo.py reads from the tables
below, exactly like every other demo in this repo.

4 patient encounters, each a distinct revenue-cycle story:
  - ENC-001 (PT-8821): CDI gap — clinical notes support acute respiratory failure with
    hypoxia, but the discharge code filed is unspecified. DRG shift, +$1,800.
  - ENC-002 (PT-4455): Missed charge — wound debridement performed and documented, but
    the CPT codes were never added to the claim. +$650.
  - ENC-003 (PT-7730): Policy-violation + reroute — charge_reconciliation_agent reaches
    for raw clinical sources it isn't authorized for (2 DENYs); the coded findings it
    actually needs are already recoverable through agent_outputs. +$1,750.
  - ENC-004 (PT-6613): Clean baseline — coding and billing already correct, nothing to
    recover. Used the same way every other demo in this repo keeps a clean case
    alongside the ones with a real finding.
"""

# ── patient encounters — the primary entity every domain table is keyed by ─────────

PATIENT_ENCOUNTERS = {
    "ENC-001": {
        "encounter_id": "ENC-001", "patient_id": "PT-8821", "patient_name": "Robert Nguyen",
        "mrn": "MRN-448821", "admission_date": "2026-03-28", "discharge_date": "2026-04-04",
        "los_days": 7, "unit": "ICU", "attending_physician": "Dr. Sarah Chen",
        "primary_dx_on_file": "J96.00", "drg_on_file": "189", "payer": "Medicare",
        "revenue_issue": "cdi_gap",
    },
    "ENC-002": {
        "encounter_id": "ENC-002", "patient_id": "PT-4455", "patient_name": "Gloria Martinez",
        "mrn": "MRN-114455", "admission_date": "2026-04-01", "discharge_date": "2026-04-05",
        "los_days": 4, "unit": "Med/Surg", "attending_physician": "Dr. James Okafor",
        "primary_dx_on_file": "L97.429", "drg_on_file": "573", "payer": "Blue Cross Blue Shield",
        "revenue_issue": "missed_charge",
    },
    "ENC-003": {
        "encounter_id": "ENC-003", "patient_id": "PT-7730", "patient_name": "Thomas Whitfield",
        "mrn": "MRN-227730", "admission_date": "2026-04-03", "discharge_date": "2026-04-08",
        "los_days": 5, "unit": "Oncology", "attending_physician": "Dr. Priya Nair",
        "primary_dx_on_file": "C34.11", "drg_on_file": "582", "payer": "Aetna",
        "revenue_issue": "missed_charge_with_overscope_attempt",
    },
    "ENC-004": {
        "encounter_id": "ENC-004", "patient_id": "PT-6613", "patient_name": "Linda Osei",
        "mrn": "MRN-336613", "admission_date": "2026-04-05", "discharge_date": "2026-04-07",
        "los_days": 2, "unit": "Surgical", "attending_physician": "Dr. Marcus Webb",
        "primary_dx_on_file": "K35.80", "drg_on_file": "339", "payer": "UnitedHealthcare",
        "revenue_issue": "none",
    },
}

CASE_METADATA = {eid: {"encounter_id": eid, "status": "open", "assigned_to": None} for eid in PATIENT_ENCOUNTERS}

# ── ehr_summaries / clinical_notes / vital_signs / lab_results — raw clinical/PHI ───

EHR_SUMMARIES = {
    "ENC-001": {
        "summary": "72-year-old male admitted via ED with acute hypoxic respiratory failure. "
                   "SpO2 82% on room air. History of COPD. Intubated within 2 hours of admission. "
                   "ICU stay 7 days. Extubated day 6. Discharged to skilled nursing facility.",
        "discharge_note": "Discharge diagnosis: respiratory failure.",  # <-- filed as 'unspecified', not 'acute with hypoxia'
    },
    "ENC-002": {
        "summary": "57-year-old female admitted for infected chronic lower-extremity ulcer. "
                   "Wound care hospital day 2 — selective debridement of necrotic tissue, "
                   "approximately 22 sq cm wound surface. IV antibiotics initiated.",
        "discharge_note": "Non-pressure chronic ulcer, lower left leg with superimposed infection. "
                          "Selective debridement performed 2026-04-02. Wound closure improving.",
    },
    "ENC-003": {
        "summary": "54-year-old male with right upper lobe lung carcinoma. Admitted for Cycle 2 "
                   "carboplatin/paclitaxel chemotherapy infusion. Pre-hydration IV 1 hour, "
                   "carboplatin 400mg over 30 min, paclitaxel 200mg over 3 hours, post-hydration IV 1 hour.",
        "discharge_note": "Chemotherapy Cycle 2 completed without complication. Tolerated well.",
    },
    "ENC-004": {
        "summary": "61-year-old female admitted for acute appendicitis. Laparoscopic appendectomy "
                   "performed hospital day 1, uncomplicated. Discharged post-op day 2, tolerating diet.",
        "discharge_note": "Acute appendicitis without perforation. Laparoscopic appendectomy, no complications.",
    },
}

CLINICAL_NOTES = {
    "ENC-001": {
        "notes": [
            {"date": "2026-03-28", "author": "Dr. Sarah Chen", "type": "ED_physician",
             "text": "SpO2 82% on room air, RR 32/min. ABG: pH 7.31, PaO2 58, PaCO2 52. "
                     "PaO2/FiO2 ratio 148. Diagnosis: ACUTE respiratory failure with hypoxia. "
                     "Placed on mechanical ventilation (AC/VC, FiO2 0.60)."},
            {"date": "2026-04-03", "author": "Dr. Sarah Chen", "type": "ICU_progress",
             "text": "Day 6 ICU. Spontaneous breathing trial successful. Extubated at 1400."},
        ],
        "cdi_flag": "Discharge summary states 'respiratory failure' without specificity. Clinical notes "
                    "consistently document ACUTE respiratory failure with hypoxia (PaO2/FiO2 148, "
                    "mechanical ventilation). Code should be J96.01, not J96.00.",
    },
    "ENC-002": {
        "notes": [
            {"date": "2026-04-02", "author": "RN Maria Santos", "type": "nursing_procedure",
             "text": "Selective debridement of necrotic tissue, left lower leg ulcer. Wound size "
                     "measured 5.5cm x 4.0cm (22 sq cm). Procedure time 35 minutes."},
            {"date": "2026-04-02", "author": "Dr. James Okafor", "type": "physician_order",
             "text": "Order: wound debridement, selective, lower left leg. Wound size >20 sq cm."},
        ],
        "charge_capture_flag": "Wound debridement documented (22 sq cm) but CPT 97597 not found in current "
                               "claim; CPT 97598 applicable for additional surface.",
    },
    "ENC-003": {
        "notes": [
            {"date": "2026-04-03", "author": "RN David Park", "type": "nursing_infusion",
             "text": "Pre-hydration IV infusion started 0800, normal saline 500mL over 60 min. "
                     "Carboplatin 400mg IV 0900. Paclitaxel 200mg IV 0935 over 3h. "
                     "Post-hydration IV infusion 1400, normal saline 500mL over 60 min."},
        ],
        "charge_capture_flag": "Pre- and post-hydration IV infusions (each 1 hour) documented but not "
                               "billed. CPT 96360 applies to pre-hydration, 96361 to post-hydration.",
    },
    "ENC-004": {
        "notes": [
            {"date": "2026-04-05", "author": "Dr. Marcus Webb", "type": "op_note",
             "text": "Laparoscopic appendectomy performed without complication. Estimated blood loss "
                     "minimal. Appendix grossly inflamed, sent to pathology."},
        ],
        "charge_capture_flag": None,
    },
}

VITAL_SIGNS = {
    "ENC-001": [
        {"date": "2026-03-28", "time": "14:00", "spo2": 82, "rr": 32, "hr": 118},
        {"date": "2026-04-03", "time": "14:30", "spo2": 94, "rr": 18, "hr": 82, "note": "post-extubation"},
    ],
    "ENC-002": [
        {"date": "2026-04-01", "time": "10:00", "spo2": 98, "rr": 16, "hr": 84, "temp": 38.4, "note": "wound site warm, erythematous"},
        {"date": "2026-04-05", "time": "09:00", "spo2": 99, "rr": 14, "hr": 78, "temp": 37.0, "note": "discharge, afebrile"},
    ],
    "ENC-003": [
        {"date": "2026-04-03", "time": "08:00", "spo2": 97, "rr": 16, "hr": 76, "note": "pre-chemo baseline"},
    ],
    "ENC-004": [
        {"date": "2026-04-06", "time": "08:00", "spo2": 98, "rr": 16, "hr": 72, "note": "post-op day 1, stable"},
    ],
}

LAB_RESULTS = {
    "ENC-001": [
        {"date": "2026-03-28", "test": "ABG", "values": {"pH": 7.31, "PaO2": 58, "PaCO2": 52},
         "interpretation": "Hypoxic and hypercapnic respiratory failure. PaO2/FiO2 ratio: 148."},
    ],
    "ENC-002": [
        {"date": "2026-04-02", "test": "wound_culture", "values": {"organism": "S. aureus (MSSA)"},
         "interpretation": "MSSA wound infection. IV Vancomycin appropriate."},
    ],
    "ENC-003": [
        {"date": "2026-04-03", "test": "CBC_pre_chemo", "values": {"WBC": 6.2, "ANC": 3100},
         "interpretation": "Counts acceptable for chemotherapy administration."},
    ],
    "ENC-004": [
        {"date": "2026-04-05", "test": "CBC", "values": {"WBC": 11.8},
         "interpretation": "Mild leukocytosis, consistent with acute appendicitis."},
    ],
}

# ── diagnosis_codes / procedure_codes — coded PHI, on file vs. what's supported ────

DIAGNOSIS_CODES = {
    "ENC-001": {
        "filed": [{"icd10": "J96.00", "description": "Respiratory failure, unspecified", "type": "primary"}],
        "suggested": [{"icd10": "J96.01", "description": "Acute respiratory failure with hypoxia",
                        "rationale": "PaO2/FiO2 148 + mechanical ventilation meets criteria",
                        "drg_impact": "DRG 189 -> DRG 207 (+$1,800)"}],
    },
    "ENC-002": {
        "filed": [{"icd10": "L97.429", "description": "Non-pressure chronic ulcer, left ankle", "type": "primary"}],
        "suggested": [],  # diagnosis coding is correct; issue is a missing procedure charge
    },
    "ENC-003": {
        "filed": [{"icd10": "C34.11", "description": "Malignant neoplasm, upper lobe right bronchus/lung", "type": "primary"}],
        "suggested": [],  # diagnosis coding is correct; issue is missing infusion charges
    },
    "ENC-004": {
        "filed": [{"icd10": "K35.80", "description": "Unspecified acute appendicitis", "type": "primary"}],
        "suggested": [],
    },
}

PROCEDURE_CODES = {
    "ENC-001": {"filed": [{"cpt": "94002", "description": "Ventilation management, inpatient", "units": 5},
                           {"cpt": "31500", "description": "Emergency intubation", "units": 1}],
                "missing": []},
    "ENC-002": {"filed": [{"cpt": "99232", "description": "Subsequent hospital care, moderate complexity", "units": 3}],
                "missing": [{"cpt": "97597", "description": "Debridement, open wound, first 20 sq cm", "estimated_revenue": 420},
                            {"cpt": "97598", "description": "Debridement, open wound, each add'l 20 sq cm", "estimated_revenue": 230}]},
    "ENC-003": {"filed": [{"cpt": "96413", "description": "Chemo admin, IV infusion, up to 1 hour", "units": 1},
                           {"cpt": "96415", "description": "Chemo admin, IV infusion, each add'l hour", "units": 2}],
                "missing": [{"cpt": "96360", "description": "IV infusion, hydration, initial hour", "estimated_revenue": 980},
                            {"cpt": "96361", "description": "IV infusion, hydration, each add'l hour", "estimated_revenue": 770}]},
    "ENC-004": {"filed": [{"cpt": "44970", "description": "Laparoscopic appendectomy", "units": 1}],
                "missing": []},
}

# ── coding_guidelines — reference material, not PHI; the only low-sensitivity source
#    cdi_specialist_agent/medical_coding_agent are meant to lean on ────────────────

CODING_GUIDELINES = {
    "guideline": "ICD-10-CM Official Guidelines for Coding and Reporting",
    "relevant_excerpts": [
        "Respiratory failure: assign the most specific code supported by clinical documentation "
        "(acute vs. chronic, with/without hypoxia or hypercapnia) — do not default to 'unspecified' "
        "when supporting documentation (ABG values, ventilator requirement) exists.",
        "Wound debridement: code by depth and total surface area treated per encounter; each "
        "additional 20 sq cm beyond the first is a separately billable add-on code.",
        "IV hydration infusion is separately billable from chemotherapy administration when "
        "medically necessary and distinctly documented (pre-/post-hydration).",
    ],
}

# ── charge_master / billing_records / insurance_eligibility — financial/billing ────

CHARGE_MASTER = {
    "ENC-001": [{"cpt": "94002", "chargemaster_rate": 1840, "units_expected": 5},
                {"cpt": "31500", "chargemaster_rate": 980, "units_expected": 1}],
    "ENC-002": [{"cpt": "99232", "chargemaster_rate": 290, "units_expected": 3},
                {"cpt": "97597", "chargemaster_rate": 420, "units_expected": 1,
                 "note": "entry exists — procedure performed, charge never captured"},
                {"cpt": "97598", "chargemaster_rate": 230, "units_expected": 1,
                 "note": "entry exists — procedure performed, charge never captured"}],
    "ENC-003": [{"cpt": "96413", "chargemaster_rate": 1240, "units_expected": 1},
                {"cpt": "96415", "chargemaster_rate": 620, "units_expected": 2},
                {"cpt": "96360", "chargemaster_rate": 980, "units_expected": 1,
                 "note": "entry exists — pre-hydration documented, not billed"},
                {"cpt": "96361", "chargemaster_rate": 770, "units_expected": 1,
                 "note": "entry exists — post-hydration documented, not billed"}],
    "ENC-004": [{"cpt": "44970", "chargemaster_rate": 4200, "units_expected": 1}],
}

BILLING_RECORDS = {
    "ENC-001": {"claim_id": "CLM-8821-0412", "claim_status": "pending", "billed_amount": 38400,
                "expected_reimbursement": 11420, "line_items": [{"cpt": "94002", "billed": 9200}, {"cpt": "31500", "billed": 980}]},
    "ENC-002": {"claim_id": "CLM-4455-0408", "claim_status": "pending", "billed_amount": 12800,
                "expected_reimbursement": 8340, "line_items": [{"cpt": "99232", "billed": 870}]},
    "ENC-003": {"claim_id": "CLM-7730-0410", "claim_status": "draft", "billed_amount": 22400,
                "expected_reimbursement": 14200, "line_items": [{"cpt": "96413", "billed": 1240}, {"cpt": "96415", "billed": 1240}]},
    "ENC-004": {"claim_id": "CLM-6613-0407", "claim_status": "submitted", "billed_amount": 15600,
                "expected_reimbursement": 15600, "line_items": [{"cpt": "44970", "billed": 4200}]},
}

INSURANCE_ELIGIBILITY = {
    "ENC-001": {"payer": "Medicare", "coverage_active": True, "authorization_required": False},
    "ENC-002": {"payer": "Blue Cross Blue Shield", "coverage_active": True, "authorization_required": True,
                "authorization_on_file": "AUTH-2026-4455-RC"},
    "ENC-003": {"payer": "Aetna", "coverage_active": True, "chemo_authorization_on_file": "AUTH-2026-7730-CHEMO-C2"},
    "ENC-004": {"payer": "UnitedHealthcare", "coverage_active": True, "authorization_required": False},
}

# ── agent_outputs — pre-compiled coded findings, distinct from live per-run findings
#    gathered during the graph run itself; mirrors every other demo's AGENT_OUTPUTS ─

AGENT_OUTPUTS = {
    "ENC-001": {
        "clinical_documentation_agent": {
            "summary": "Discharge summary states 'respiratory failure' without specificity; clinical "
                       "notes and ABG (PaO2/FiO2 148) plus mechanical ventilation support acute "
                       "respiratory failure with hypoxia.",
            "recommendation": "CDI_QUERY_NEEDED",
        },
    },
    "ENC-002": {
        "clinical_documentation_agent": {
            "summary": "Selective wound debridement (22 sq cm) documented 2026-04-02 but not reflected "
                       "in current procedure codes.",
            "recommendation": "MISSING_CHARGE",
        },
        "charge_reconciliation_agent": {
            "summary": "Charge master has entries for CPT 97597/97598; neither appears on the current "
                       "claim. Total missed revenue $650.",
            "recommendation": "ADD_CHARGES",
        },
    },
    "ENC-003": {
        "clinical_documentation_agent": {
            "summary": "Pre- and post-hydration IV infusions (60 min each) documented 2026-04-03; "
                       "CPT 96360/96361 applicable, not currently coded.",
            "recommendation": "MISSING_CHARGE",
        },
        "charge_reconciliation_agent": {
            "summary": "Charge master has entries for CPT 96360/96361; neither appears on the draft "
                       "claim. Total missed revenue $1,750.",
            "recommendation": "ADD_CHARGES",
        },
    },
    "ENC-004": {
        "clinical_documentation_agent": {
            "summary": "Op note and diagnosis code are consistent; no undercoding or undocumented "
                       "procedure found.",
            "recommendation": "COMPLIANT",
        },
    },
}

# ── expected outcomes — ground truth the rule-based decision_node checks against ───

EXPECTED_OUTCOMES = {
    "ENC-001": {"revenue_recovery": 1800, "action_required": "CDI physician query -> code update (J96.00 -> J96.01) before claim submission",
                "policy_violation": False},
    "ENC-002": {"revenue_recovery": 650, "action_required": "Add CPT 97597 + 97598 to claim before submission",
                "policy_violation": False},
    "ENC-003": {"revenue_recovery": 1750, "action_required": "Add CPT 96360 + 96361 to claim draft before submission to Aetna",
                "policy_violation": True},
    "ENC-004": {"revenue_recovery": 0, "action_required": "None -- coding and billing complete and accurate",
                "policy_violation": False},
}


# ── convenience accessors ───────────────────────────────────────────────────────────

def get_encounter(encounter_id: str) -> dict:
    return PATIENT_ENCOUNTERS.get(encounter_id, {})


def get_agent_outputs(encounter_id: str) -> dict:
    return AGENT_OUTPUTS.get(encounter_id, {})


def get_expected_outcome(encounter_id: str) -> dict:
    return EXPECTED_OUTCOMES.get(encounter_id, {})
