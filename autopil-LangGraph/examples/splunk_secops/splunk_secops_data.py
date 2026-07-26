"""
Simulated data for the AutoPIL + LangGraph SOC / Splunk SecOps demo.

IBM mainframe tools forward 4 SMF (System Management Facility) log types into Splunk;
this module is the fixture data every guarded getter in splunk_secops_demo.py reads
from instead of hitting a real Splunk instance. Mirrors fraud_investigation's
simulated_data.py shape exactly: primary entities, per-domain record tables, case
alerts, pre-compiled agent outputs, expected outcomes, and thin getter functions.

5 mainframe systems (LPARs), 4 SOC cases:
  - SEC-001: MVSP01 — routine daily RACF review (security_auditor's scheduled sweep),
    a below-incident-threshold access-violation pattern -> compliance_reporter closes it
  - SEC-002: MVSP02 — active incident: RACF privilege escalation correlated with a CPU
    spike and an off-hours batch job -> incident_triage's broad, time-boxed access
  - SEC-003: MVSP03 — compliance spot-check: clean system, compliance_reporter asked to
    certify index retention/health; over-scope raw SMF pull is denied
  - SEC-004: MVSP04 — multi-source correlation incident touching general-ledger postings
    (SOX ITGC angle): unauthorized batch job + unscheduled subsystem restart

MVSP05 is a clean baseline system tied to no case, used the same way fraud_investigation
keeps clean accounts alongside the ones under investigation.
"""

# ── mainframe systems (LPARs) — the primary entity every domain table is keyed by ──

SYSTEMS = {
    "MVSP01": {
        "system_id": "MVSP01", "lpar_name": "MVSPROD1", "region": "us-east-primary",
        "workload_type": "core_banking_batch", "criticality": "high",
        "commissioned_date": "2011-04-02", "tenure_days": 5570,
        "risk_score": 0.22, "system_flags": ["scheduled_racf_review"],
    },
    "MVSP02": {
        "system_id": "MVSP02", "lpar_name": "MVSPROD2", "region": "us-east-primary",
        "workload_type": "card_authorization", "criticality": "critical",
        "commissioned_date": "2009-11-18", "tenure_days": 6100,
        "risk_score": 0.91, "system_flags": ["active_incident", "privilege_escalation_suspected"],
    },
    "MVSP03": {
        "system_id": "MVSP03", "lpar_name": "MVSPROD3", "region": "us-west-secondary",
        "workload_type": "payroll_hr_batch", "criticality": "medium",
        "commissioned_date": "2014-02-27", "tenure_days": 4350,
        "risk_score": 0.08, "system_flags": ["compliance_spot_check"],
    },
    "MVSP04": {
        "system_id": "MVSP04", "lpar_name": "MVSPROD4", "region": "us-east-primary",
        "workload_type": "general_ledger_financial_reporting", "criticality": "critical",
        "commissioned_date": "2007-06-05", "tenure_days": 6900,
        "risk_score": 0.87, "system_flags": ["active_incident", "sox_scope"],
    },
    "MVSP05": {
        "system_id": "MVSP05", "lpar_name": "MVSPROD5", "region": "us-west-secondary",
        "workload_type": "reporting_analytics_batch", "criticality": "low",
        "commissioned_date": "2016-09-14", "tenure_days": 3600,
        "risk_score": 0.04, "system_flags": [],
    },
}

# ── smf_security: RACF access-violation + clean baseline events, per system ────────

SMF_SECURITY = {
    "MVSP01": [
        {"event_id": "SMF80-0001", "timestamp": "2026-07-24T02:11:03Z", "userid": "BATCHOPS1",
         "racf_class": "DATASET", "resource": "PROD.BATCH.PAYFILE", "violation_type": "INSUFFICIENT_AUTHORITY",
         "return_code": 8, "reason_code": "04"},
        {"event_id": "SMF80-0002", "timestamp": "2026-07-24T02:11:07Z", "userid": "BATCHOPS1",
         "racf_class": "DATASET", "resource": "PROD.BATCH.PAYFILE", "violation_type": "INSUFFICIENT_AUTHORITY",
         "return_code": 8, "reason_code": "04"},
        {"event_id": "SMF80-0003", "timestamp": "2026-07-24T02:11:12Z", "userid": "BATCHOPS1",
         "racf_class": "DATASET", "resource": "PROD.BATCH.PAYFILE", "violation_type": "INSUFFICIENT_AUTHORITY",
         "return_code": 8, "reason_code": "04"},
        {"event_id": "SMF80-0004", "timestamp": "2026-07-24T06:00:00Z", "userid": "SYSOPER1",
         "racf_class": "DATASET", "resource": "PROD.BATCH.LOGFILE", "violation_type": "CLEAN_ACCESS",
         "return_code": 0, "reason_code": "00"},
    ],
    "MVSP02": [
        {"event_id": "SMF80-0101", "timestamp": "2026-07-24T23:47:02Z", "userid": "CARDSVC3",
         "racf_class": "USER", "resource": "SPECIAL_ATTRIBUTE", "violation_type": "UNAUTHORIZED_PRIVILEGE_GRANT",
         "return_code": 8, "reason_code": "14"},
        {"event_id": "SMF80-0102", "timestamp": "2026-07-24T23:52:19Z", "userid": "CARDSVC3",
         "racf_class": "DATASET", "resource": "PROD.CARD.AUTHKEYS", "violation_type": "UNAUTHORIZED_DATASET_ACCESS",
         "return_code": 8, "reason_code": "04"},
        {"event_id": "SMF80-0103", "timestamp": "2026-07-25T00:03:44Z", "userid": "CARDSVC3",
         "racf_class": "DATASET", "resource": "PROD.CARD.AUTHKEYS", "violation_type": "UNAUTHORIZED_DATASET_ACCESS",
         "return_code": 8, "reason_code": "04"},
    ],
    "MVSP03": [
        {"event_id": "SMF80-0201", "timestamp": "2026-07-24T09:15:00Z", "userid": "HRBATCH2",
         "racf_class": "DATASET", "resource": "PROD.HR.PAYROLL", "violation_type": "CLEAN_ACCESS",
         "return_code": 0, "reason_code": "00"},
    ],
    "MVSP04": [
        {"event_id": "SMF80-0301", "timestamp": "2026-07-24T21:30:05Z", "userid": "GLBATCH9",
         "racf_class": "DATASET", "resource": "PROD.GL.POSTINGS", "violation_type": "UNAUTHORIZED_DATASET_ACCESS",
         "return_code": 8, "reason_code": "04"},
        {"event_id": "SMF80-0302", "timestamp": "2026-07-24T21:31:40Z", "userid": "GLBATCH9",
         "racf_class": "DATASET", "resource": "PROD.GL.POSTINGS", "violation_type": "UNAUTHORIZED_DATASET_ACCESS",
         "return_code": 8, "reason_code": "04"},
        {"event_id": "SMF80-0303", "timestamp": "2026-07-24T21:45:12Z", "userid": "GLBATCH9",
         "racf_class": "USER", "resource": "SPECIAL_ATTRIBUTE", "violation_type": "UNAUTHORIZED_PRIVILEGE_GRANT",
         "return_code": 8, "reason_code": "14"},
    ],
    "MVSP05": [
        {"event_id": "SMF80-0401", "timestamp": "2026-07-24T10:00:00Z", "userid": "RPTBATCH1",
         "racf_class": "DATASET", "resource": "PROD.RPT.EXTRACT", "violation_type": "CLEAN_ACCESS",
         "return_code": 0, "reason_code": "00"},
    ],
}

# ── smf_performance: workload/CPU/response-time snapshot per system ────────────────

SMF_PERFORMANCE = {
    "MVSP01": {"system_id": "MVSP01", "cpu_pct_avg_24h": 41.2, "cpu_pct_peak_24h": 58.0,
               "avg_response_ms": 120, "workload_anomaly_score": 0.11, "batch_jobs_run_24h": 340},
    "MVSP02": {"system_id": "MVSP02", "cpu_pct_avg_24h": 88.7, "cpu_pct_peak_24h": 99.4,
               "avg_response_ms": 910, "workload_anomaly_score": 0.94, "batch_jobs_run_24h": 512,
               "cpu_spike_flag": True, "spike_window": "2026-07-24T23:40Z-2026-07-25T00:10Z"},
    "MVSP03": {"system_id": "MVSP03", "cpu_pct_avg_24h": 33.5, "cpu_pct_peak_24h": 47.1,
               "avg_response_ms": 95, "workload_anomaly_score": 0.05, "batch_jobs_run_24h": 210},
    "MVSP04": {"system_id": "MVSP04", "cpu_pct_avg_24h": 76.9, "cpu_pct_peak_24h": 93.2,
               "avg_response_ms": 640, "workload_anomaly_score": 0.88, "batch_jobs_run_24h": 447,
               "cpu_spike_flag": True, "spike_window": "2026-07-24T21:25Z-2026-07-24T21:50Z"},
    "MVSP05": {"system_id": "MVSP05", "cpu_pct_avg_24h": 29.0, "cpu_pct_peak_24h": 40.3,
               "avg_response_ms": 88, "workload_anomaly_score": 0.03, "batch_jobs_run_24h": 180},
}

# ── smf_transactions: CICS/IMS transaction records per system ──────────────────────

SMF_TRANSACTIONS = {
    "MVSP01": [
        {"txn_id": "TXN-9001", "program": "PAYRUN01", "response_time_ms": 210, "abend_code": None, "amount_usd": None},
        {"txn_id": "TXN-9002", "program": "PAYRUN01", "response_time_ms": 198, "abend_code": None, "amount_usd": None},
    ],
    "MVSP02": [
        {"txn_id": "TXN-9101", "program": "CARDAUTH", "response_time_ms": 1840, "abend_code": "S0C7", "amount_usd": 4820.00},
        {"txn_id": "TXN-9102", "program": "CARDAUTH", "response_time_ms": 2210, "abend_code": "S0C7", "amount_usd": 9975.50},
        {"txn_id": "TXN-9103", "program": "CARDAUTH", "response_time_ms": 190, "abend_code": None, "amount_usd": 42.10},
    ],
    "MVSP03": [
        {"txn_id": "TXN-9201", "program": "HRPAYCALC", "response_time_ms": 140, "abend_code": None, "amount_usd": None},
    ],
    "MVSP04": [
        {"txn_id": "TXN-9301", "program": "GLPOST", "response_time_ms": 780, "abend_code": None,
         "amount_usd": 2_450_000.00, "posting_window_violation": True},
        {"txn_id": "TXN-9302", "program": "GLPOST", "response_time_ms": 812, "abend_code": None,
         "amount_usd": 1_190_000.00, "posting_window_violation": True},
        {"txn_id": "TXN-9303", "program": "GLPOST", "response_time_ms": 155, "abend_code": None,
         "amount_usd": 8_400.00, "posting_window_violation": False},
    ],
    "MVSP05": [
        {"txn_id": "TXN-9401", "program": "RPTEXTRACT", "response_time_ms": 110, "abend_code": None, "amount_usd": None},
    ],
}

# ── smf_systems: OS-level events (IPL, subsystem restarts, storage) per system ──────

SMF_SYSTEMS = {
    "MVSP01": {"system_id": "MVSP01", "last_ipl": "2026-06-30T04:00:00Z", "unscheduled_restarts_24h": 0,
               "storage_util_pct": 61.0, "dataset_alloc_failures_24h": 0},
    "MVSP02": {"system_id": "MVSP02", "last_ipl": "2026-05-12T04:00:00Z", "unscheduled_restarts_24h": 0,
               "storage_util_pct": 74.0, "dataset_alloc_failures_24h": 2},
    "MVSP03": {"system_id": "MVSP03", "last_ipl": "2026-07-01T04:00:00Z", "unscheduled_restarts_24h": 0,
               "storage_util_pct": 48.0, "dataset_alloc_failures_24h": 0},
    "MVSP04": {"system_id": "MVSP04", "last_ipl": "2026-03-20T04:00:00Z", "unscheduled_restarts_24h": 1,
               "storage_util_pct": 82.0, "dataset_alloc_failures_24h": 3,
               "restart_window": "2026-07-24T21:40Z", "restart_reason_logged": "OPERATOR_INITIATED"},
    "MVSP05": {"system_id": "MVSP05", "last_ipl": "2026-07-10T04:00:00Z", "unscheduled_restarts_24h": 0,
               "storage_util_pct": 39.0, "dataset_alloc_failures_24h": 0},
}

# ── splunk_index_summery: retention/health rollup per Splunk index — this, not raw
#    SMF records, is all compliance_reporter is authorized to read ─────────────────

SPLUNK_INDEX_SUMMARY = {
    "smf_security":    {"index": "smf_security", "event_count_24h": 11, "retention_days": 2555,
                         "queryable_days": 90, "storage_gb": 412.0, "last_ingest_lag_sec": 4, "integrity_check": "PASS"},
    "smf_performance":  {"index": "smf_performance", "event_count_24h": 5, "retention_days": 90,
                         "queryable_days": 90, "storage_gb": 88.0, "last_ingest_lag_sec": 2, "integrity_check": "PASS"},
    "smf_transactions": {"index": "smf_transactions", "event_count_24h": 9, "retention_days": 365,
                         "queryable_days": 90, "storage_gb": 640.0, "last_ingest_lag_sec": 6, "integrity_check": "PASS"},
    "smf_systems":      {"index": "smf_systems", "event_count_24h": 5, "retention_days": 365,
                         "queryable_days": 90, "storage_gb": 210.0, "last_ingest_lag_sec": 3, "integrity_check": "PASS"},
}

# ── security_alerts: triggers for the orchestrator, one per SOC case ───────────────

SECURITY_ALERTS = [
    {"case_id": "SEC-001", "system_id": "MVSP01", "alert_type": "racf_daily_sweep_finding",
     "priority": "LOW", "summary": "Daily scheduled RACF sweep flagged repeated INSUFFICIENT_AUTHORITY "
                                    "events from a batch service userid against a payroll dataset."},
    {"case_id": "SEC-002", "system_id": "MVSP02", "alert_type": "active_incident",
     "priority": "CRITICAL", "summary": "Card-authorization LPAR showing an unauthorized RACF privilege "
                                         "grant correlated with a CPU spike and abending high-value transactions."},
    {"case_id": "SEC-003", "system_id": "MVSP03", "alert_type": "compliance_spot_check",
     "priority": "LOW", "summary": "Scheduled quarterly compliance spot-check — certify index retention "
                                    "and integrity health for the payroll/HR LPAR."},
    {"case_id": "SEC-004", "system_id": "MVSP04", "alert_type": "active_incident",
     "priority": "CRITICAL", "summary": "General-ledger LPAR showing unauthorized batch postings outside "
                                         "the change window plus an unscheduled subsystem restart — "
                                         "SOX-scoped financial-reporting system."},
]

CASE_METADATA = {a["case_id"]: {"case_id": a["case_id"], "status": "open", "assigned_to": None} for a in SECURITY_ALERTS}

# ── regulatory_templates: the SOC incident-report filing template ──────────────────

REGULATORY_TEMPLATES = {
    "soc_incident_template_v1": {
        "form": "SOC Incident / Threat Report", "version": "1.0",
        "required_fields": ["system_id", "case_id", "incident_description", "affected_indices",
                            "severity", "recommended_action"],
    },
}

# ── pre-compiled agent outputs — what splunk_threat_synthesizer's get_agent_outputs
#    tool returns (distinct from the live per-run findings gathered during the graph
#    run itself; mirrors fraud_investigation's AGENT_OUTPUTS exactly) ───────────────

AGENT_OUTPUTS = {
    "SEC-001": {
        "security_auditor": {"summary": "Repeated INSUFFICIENT_AUTHORITY events from BATCHOPS1 against "
                                          "PROD.BATCH.PAYFILE during the scheduled daily sweep — below "
                                          "incident threshold, recommend routine access review.",
                              "recommendation": "MONITOR"},
    },
    "SEC-002": {
        "incident_triage": {"summary": "CARDSVC3 granted an unauthorized SPECIAL attribute and immediately "
                                         "accessed PROD.CARD.AUTHKEYS twice, correlated with a CPU spike and "
                                         "two abending high-value card-authorization transactions.",
                              "recommendation": "FREEZE"},
        "security_auditor": {"summary": "RACF class USER violation confirms an unauthorized privilege grant "
                                          "for CARDSVC3, not a transient authorization glitch.",
                              "recommendation": "ESCALATE"},
    },
    "SEC-003": {
        "compliance_reporter": {"summary": "All 4 Splunk indices pass integrity checks with retention windows "
                                             "within policy (smf_security 2555d, others 90-365d); no raw-record "
                                             "review performed or required for this spot-check.",
                                  "recommendation": "COMPLIANT"},
    },
    "SEC-004": {
        "incident_triage": {"summary": "GLBATCH9 posted two unauthorized general-ledger entries (~$3.64M "
                                         "combined) outside the change window, followed by an unscheduled "
                                         "subsystem restart logged as operator-initiated with no matching "
                                         "change ticket.",
                              "recommendation": "FREEZE"},
        "security_auditor": {"summary": "GLBATCH9 subsequently granted an unauthorized SPECIAL attribute — "
                                          "consistent with covering the unauthorized postings, not a scheduled "
                                          "batch credential refresh.",
                              "recommendation": "ESCALATE"},
    },
}

# ── expected outcomes — ground truth the rule-based decision_node checks against ───

EXPECTED_OUTCOMES = {
    "SEC-001": {"action": "MONITOR", "incident_report_warranted": False},
    "SEC-002": {"action": "FREEZE_AND_ESCALATE", "incident_report_warranted": True},
    "SEC-003": {"action": "COMPLIANT_NO_ACTION", "incident_report_warranted": False},
    "SEC-004": {"action": "FREEZE_AND_ESCALATE", "incident_report_warranted": True},
}


# ── convenience accessors ───────────────────────────────────────────────────────────

def get_security_alert(case_id: str) -> dict:
    return next((a for a in SECURITY_ALERTS if a["case_id"] == case_id), {})


def get_smf_security(system_id: str) -> list:
    return SMF_SECURITY.get(system_id, [])


def get_smf_performance(system_id: str) -> dict:
    return SMF_PERFORMANCE.get(system_id, {})


def get_smf_transactions(system_id: str) -> list:
    return SMF_TRANSACTIONS.get(system_id, [])


def get_smf_systems(system_id: str) -> dict:
    return SMF_SYSTEMS.get(system_id, {})


def get_splunk_index_summary(index_name: str = "") -> dict:
    return SPLUNK_INDEX_SUMMARY.get(index_name, SPLUNK_INDEX_SUMMARY) if index_name else SPLUNK_INDEX_SUMMARY


def get_agent_outputs(case_id: str) -> dict:
    return AGENT_OUTPUTS.get(case_id, {})


def get_expected_outcome(case_id: str) -> dict:
    return EXPECTED_OUTCOMES.get(case_id, {})


def summarize_smf_security(system_id: str) -> dict:
    events = get_smf_security(system_id)
    violations = [e for e in events if e["violation_type"] != "CLEAN_ACCESS"]
    return {
        "system_id": system_id, "event_count": len(events), "violation_count": len(violations),
        "distinct_userids": sorted({e["userid"] for e in violations}),
        "violation_types": sorted({e["violation_type"] for e in violations}),
    }
