// Mirrors policies/healthcare/clinical_operations.yaml — kept in sync by hand. This is
// reference/display data only; the real enforcement happens server-side via AutoPIL's
// ContextGuard, not anything in this file.

export interface AgentPolicy {
  role: string;
  displayName: string;
  description: string;
  allowedSources: string[];
  deniedSources: string[];
  maxSensitivity: string;
  sessionTtlMinutes: number;
}

export const AGENT_POLICIES: AgentPolicy[] = [
  {
    role: "care_coordinator",
    displayName: "Care Coordinator",
    description: "Routes care-coordination cases to specialist agents and compiles the final care note; orchestration only, no raw source access.",
    allowedSources: ["case_metadata", "agent_outputs"],
    deniedSources: ["symptom_intake", "vital_signs", "patient_demographics", "ehr_summaries", "lab_results", "care_plans", "medication_history", "allergy_records", "pharmacy_data", "drug_interaction_db", "chronic_condition_registry", "preventive_care_schedule"],
    maxSensitivity: "high",
    sessionTtlMinutes: 480,
  },
  {
    role: "triage_agent",
    displayName: "Triage Agent",
    description: "Symptom intake and vital signs only; no chart, medication, or registry source access.",
    allowedSources: ["symptom_intake", "vital_signs", "patient_demographics"],
    deniedSources: ["case_metadata", "ehr_summaries", "lab_results", "care_plans", "medication_history", "allergy_records", "pharmacy_data", "drug_interaction_db", "chronic_condition_registry", "preventive_care_schedule", "agent_outputs"],
    maxSensitivity: "medium",
    sessionTtlMinutes: 480,
  },
  {
    role: "clinical_summary_agent",
    displayName: "Clinical Summary Agent",
    description: "EHR summaries, lab results, and care plans for chart review and care coordination; no medication, registry, or billing source access.",
    allowedSources: ["ehr_summaries", "lab_results", "vital_signs", "care_plans"],
    deniedSources: ["case_metadata", "symptom_intake", "patient_demographics", "medication_history", "allergy_records", "pharmacy_data", "drug_interaction_db", "chronic_condition_registry", "preventive_care_schedule", "agent_outputs"],
    maxSensitivity: "high",
    sessionTtlMinutes: 240,
  },
  {
    role: "medication_review_agent",
    displayName: "Medication Review Agent",
    description: "Medication history, allergy records, and pharmacy data for reconciliation and interaction checks; no chart or registry source access.",
    allowedSources: ["medication_history", "allergy_records", "pharmacy_data", "drug_interaction_db"],
    deniedSources: ["case_metadata", "symptom_intake", "vital_signs", "patient_demographics", "ehr_summaries", "lab_results", "care_plans", "chronic_condition_registry", "preventive_care_schedule", "agent_outputs"],
    maxSensitivity: "high",
    sessionTtlMinutes: 240,
  },
  {
    role: "care_gap_agent",
    displayName: "Care Gap Agent",
    description: "Chronic-condition registry and preventive-care schedule for gap identification and outreach; no chart or medication source access.",
    allowedSources: ["chronic_condition_registry", "preventive_care_schedule", "patient_demographics", "care_plans"],
    deniedSources: ["case_metadata", "symptom_intake", "vital_signs", "ehr_summaries", "lab_results", "medication_history", "allergy_records", "pharmacy_data", "drug_interaction_db", "agent_outputs"],
    maxSensitivity: "medium",
    sessionTtlMinutes: 480,
  },
];

export const REGULATIONS = [
  { id: "HIPAA-PRIVACY", name: "HIPAA Privacy Rule — Minimum Necessary Standard (45 CFR 164.502(b))" },
  { id: "HIPAA-SECURITY", name: "HIPAA Security Rule — Access Control & Audit Controls (45 CFR 164.312)" },
  { id: "CMS-CARE-COORDINATION", name: "CMS Care Coordination & Chronic Care Management Requirements" },
];
