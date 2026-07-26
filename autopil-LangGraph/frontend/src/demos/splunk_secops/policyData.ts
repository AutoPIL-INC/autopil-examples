// Mirrors policies/SecOps/soc_mainframe_logs.yaml — kept in sync by hand. This is
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
    role: "soc_orchestrator",
    displayName: "SOC Orchestrator",
    description: "Routes security alerts to specialist agents; orchestration only, no raw Splunk index access.",
    allowedSources: ["security_alerts", "case_metadata", "agent_outputs"],
    deniedSources: ["smf_security", "smf_performance", "smf_transactions", "smf_systems", "splunk_index_summery", "regulatory_templates"],
    maxSensitivity: "medium",
    sessionTtlMinutes: 480,
  },
  {
    role: "security_auditor",
    displayName: "Security Auditor",
    description: "Reviews RACF access-violation events from the daily scheduled SMF security sweep; no access to any other Splunk source.",
    allowedSources: ["smf_security"],
    deniedSources: ["smf_performance", "smf_transactions", "smf_systems", "splunk_index_summery", "agent_outputs", "regulatory_templates", "security_alerts", "case_metadata"],
    maxSensitivity: "high",
    sessionTtlMinutes: 60,
  },
  {
    role: "incident_triage",
    displayName: "Incident Triage",
    description: "Cross-source investigation across all 4 SMF log types during an active incident; broader index set than any other specialist, deliberately time-boxed.",
    allowedSources: ["smf_security", "smf_performance", "smf_transactions", "smf_systems", "security_alerts", "case_metadata"],
    deniedSources: ["splunk_index_summery", "agent_outputs", "regulatory_templates"],
    maxSensitivity: "critical",
    sessionTtlMinutes: 30,
  },
  {
    role: "compliance_reporter",
    displayName: "Compliance Reporter",
    description: "Reports index-level retention/health summaries across all Splunk indices; no raw SMF record access on any source.",
    allowedSources: ["splunk_index_summery"],
    deniedSources: ["smf_security", "smf_performance", "smf_transactions", "smf_systems", "agent_outputs", "regulatory_templates", "security_alerts", "case_metadata"],
    maxSensitivity: "medium",
    sessionTtlMinutes: 120,
  },
  {
    role: "splunk_threat_synthesizer",
    displayName: "Splunk Threat Synthesizer",
    description: "Synthesizes the final threat/incident report from compiled specialist findings only; no raw Splunk index access.",
    allowedSources: ["agent_outputs", "regulatory_templates", "case_metadata"],
    deniedSources: ["smf_security", "smf_performance", "smf_transactions", "smf_systems", "splunk_index_summery", "security_alerts"],
    maxSensitivity: "critical",
    sessionTtlMinutes: 60,
  },
];

export const REGULATIONS = [
  { id: "PCI-DSS-v4", name: "PCI-DSS v4.0 — Payment Card Industry Data Security Standard" },
  { id: "SOX-ITGC", name: "SOX ITGC — Sarbanes-Oxley IT General Controls" },
  { id: "INTERNAL-SEC-POLICY", name: "Internal Security Policy — Crown Jewels / Enterprise-Wide Systems" },
];
