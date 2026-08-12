// Mirrors policies/healthcare/revenue_cycle.yaml — kept in sync by hand. This is
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
    role: "revenue_orchestrator",
    displayName: "Revenue Orchestrator",
    description: "Routes revenue-cycle cases to specialist agents and aggregates the final revenue summary; orchestration only, no raw source access.",
    allowedSources: ["case_metadata", "agent_outputs"],
    deniedSources: ["ehr_summaries", "clinical_notes", "vital_signs", "lab_results", "diagnosis_codes", "procedure_codes", "coding_guidelines", "charge_master", "billing_records", "insurance_eligibility"],
    maxSensitivity: "high",
    sessionTtlMinutes: 480,
  },
  {
    role: "clinical_documentation_agent",
    displayName: "Clinical Documentation Agent",
    description: "Reads EHR summaries and clinical notes; extracts coded findings for downstream agents; no coding, charge, or billing source access.",
    allowedSources: ["ehr_summaries", "clinical_notes", "vital_signs", "lab_results"],
    deniedSources: ["case_metadata", "diagnosis_codes", "procedure_codes", "coding_guidelines", "charge_master", "billing_records", "insurance_eligibility", "agent_outputs"],
    maxSensitivity: "critical",
    sessionTtlMinutes: 60,
  },
  {
    role: "cdi_specialist_agent",
    displayName: "CDI Specialist Agent",
    description: "Reviews clinical documentation for coding gaps and undercoding; no billing or charge source access.",
    allowedSources: ["clinical_notes", "diagnosis_codes", "coding_guidelines"],
    deniedSources: ["case_metadata", "ehr_summaries", "vital_signs", "lab_results", "procedure_codes", "charge_master", "billing_records", "insurance_eligibility", "agent_outputs"],
    maxSensitivity: "critical",
    sessionTtlMinutes: 480,
  },
  {
    role: "medical_coding_agent",
    displayName: "Medical Coding Agent",
    description: "Assigns ICD-10 and CPT codes from procedure/diagnosis codes and coding guidelines; no raw clinical or billing source access.",
    allowedSources: ["procedure_codes", "diagnosis_codes", "coding_guidelines"],
    deniedSources: ["case_metadata", "ehr_summaries", "clinical_notes", "vital_signs", "lab_results", "charge_master", "billing_records", "insurance_eligibility", "agent_outputs"],
    maxSensitivity: "high",
    sessionTtlMinutes: 480,
  },
  {
    role: "charge_reconciliation_agent",
    displayName: "Charge Reconciliation Agent",
    description: "Matches rendered services to billed charges via charge master and billing records; no clinical or coding-reference source access.",
    allowedSources: ["charge_master", "billing_records", "agent_outputs"],
    deniedSources: ["case_metadata", "ehr_summaries", "clinical_notes", "vital_signs", "lab_results", "diagnosis_codes", "procedure_codes", "coding_guidelines", "insurance_eligibility"],
    maxSensitivity: "high",
    sessionTtlMinutes: 480,
  },
  {
    role: "billing_compliance_agent",
    displayName: "Billing Compliance Agent",
    description: "Validates final claims against payer rules and eligibility; no clinical or charge-master source access.",
    allowedSources: ["billing_records", "insurance_eligibility", "agent_outputs"],
    deniedSources: ["case_metadata", "ehr_summaries", "clinical_notes", "vital_signs", "lab_results", "diagnosis_codes", "procedure_codes", "coding_guidelines", "charge_master"],
    maxSensitivity: "high",
    sessionTtlMinutes: 480,
  },
];

export const REGULATIONS = [
  { id: "HIPAA-PRIVACY", name: "HIPAA Privacy Rule — Minimum Necessary Standard (45 CFR 164.502(b))" },
  { id: "HIPAA-SECURITY", name: "HIPAA Security Rule — Access Control & Audit Controls (45 CFR 164.312)" },
  { id: "CMS-CODING-COMPLIANCE", name: "CMS Coding & Billing Compliance — Correct Coding Initiative" },
];
