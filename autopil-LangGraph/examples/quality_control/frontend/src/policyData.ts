// Mirrors policies/manufacturing/quality_control.yaml — kept in sync by hand. This is
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
    role: "quality_orchestrator",
    displayName: "Quality Orchestrator",
    description: "Routes quality-investigation cases to specialist agents and compiles the final root-cause finding; orchestration only, no raw source access.",
    allowedSources: ["case_metadata", "agent_outputs"],
    deniedSources: ["sensor_data", "vision_system_outputs", "spc_charts", "product_specs", "inspection_records", "measurement_data", "process_parameters", "calibration_records", "supplier_scorecards", "nonconformance_reports", "audit_records", "equipment_registry", "maintenance_schedules"],
    maxSensitivity: "high",
    sessionTtlMinutes: 480,
  },
  {
    role: "defect_detection_agent",
    displayName: "Defect Detection Agent",
    description: "Sensor and vision data for quality inspection; no supplier contracts or financial data access.",
    allowedSources: ["sensor_data", "vision_system_outputs", "spc_charts", "product_specs", "inspection_records"],
    deniedSources: ["supplier_contracts", "financial_ledgers", "customer_data", "hr_records", "cost_data"],
    maxSensitivity: "medium",
    sessionTtlMinutes: 480,
  },
  {
    role: "spc_agent",
    displayName: "SPC Agent",
    description: "Statistical process control analysis; no supplier contracts or financial ledgers access.",
    allowedSources: ["spc_charts", "measurement_data", "process_parameters", "product_specs", "calibration_records"],
    deniedSources: ["supplier_contracts", "financial_ledgers", "hr_records", "customer_data"],
    maxSensitivity: "medium",
    sessionTtlMinutes: 480,
  },
  {
    role: "supplier_quality_agent",
    displayName: "Supplier Quality Agent",
    description: "Supplier scorecards and nonconformance reporting; no customer data or financials.",
    allowedSources: ["supplier_scorecards", "inspection_records", "nonconformance_reports", "product_specs", "audit_records"],
    deniedSources: ["customer_data", "financial_ledgers", "hr_records", "internal_pricing_models"],
    maxSensitivity: "medium",
    sessionTtlMinutes: 480,
  },
  {
    role: "calibration_agent",
    displayName: "Calibration Agent",
    description: "Calibration and measurement tracking; no financial or customer data access.",
    allowedSources: ["calibration_records", "equipment_registry", "measurement_data", "maintenance_schedules", "product_specs"],
    deniedSources: ["financial_ledgers", "customer_data", "supplier_contracts", "hr_records"],
    maxSensitivity: "medium",
    sessionTtlMinutes: 480,
  },
];

export const REGULATIONS = [
  { id: "IATF-16949-CORRECTIVE-ACTION", name: "IATF 16949 Clause 10.2 — Nonconformity and Corrective Action" },
  { id: "IATF-16949-SUPPLIER-CONTROL", name: "IATF 16949 Clause 8.4 — Control of Externally Provided Processes, Products, and Services" },
  { id: "ISO-9001-MEASURING-RESOURCES", name: "ISO 9001 Clause 7.1.5 — Monitoring and Measuring Resources" },
];
