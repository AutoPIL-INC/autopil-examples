"""
Simulated data for the AutoPIL + LangGraph AML & Compliance demo.

5 accounts, 5 AML cases, mixed severity — same "not every case should look the same"
disclosure as the fraud investigation demo's 5 cases: a genuine SAR-worthy pattern, a
watchlist false positive, a compliance-process case (no transaction signal at all), a
routine cross-client audit, and a clean case that clears at every step.

`AML_CASES` carries the real, spoiler-bearing signal data (what actually happened).
The frontend's `CASE_ALERTS` (types.ts) mirrors only the factual, non-conclusory
subset of this — case ID, opened date, priority, triggering reason — never the
underlying signal flags below, same spoiler-free framing as the fraud demo's
`CASE_ALERTS` vs. `CASE_INFO` split.
"""

# ---------------------------------------------------------------------------
# client_profile — keyed by account_id
# ---------------------------------------------------------------------------

CLIENT_PROFILE = {
    "ACCT-AML-001": {"account_id": "ACCT-AML-001", "name": "Kestrel Import-Export LLC", "entity_type": "corporate", "relationship_since": "2019-03-11", "relationship_manager": "Dana Ruiz"},
    "ACCT-AML-002": {"account_id": "ACCT-AML-002", "name": "Silverton Analytics Group", "entity_type": "corporate", "relationship_since": "2021-07-22", "relationship_manager": "Priya Nair"},
    "ACCT-AML-003": {"account_id": "ACCT-AML-003", "name": "Bellweather Municipal Advisors", "entity_type": "institutional", "relationship_since": "2015-01-09", "relationship_manager": "Tom Ellery"},
    "ACCT-AML-004": {"account_id": "ACCT-AML-004", "name": "Cascade Regional Holdings", "entity_type": "institutional", "relationship_since": "2012-11-30", "relationship_manager": "Dana Ruiz"},
    "ACCT-AML-005": {"account_id": "ACCT-AML-005", "name": "Fenwick Trust Services", "entity_type": "institutional", "relationship_since": "2017-05-18", "relationship_manager": "Priya Nair"},
}

# ---------------------------------------------------------------------------
# account_summaries
# ---------------------------------------------------------------------------

ACCOUNT_SUMMARIES = {
    "ACCT-AML-001": {"account_id": "ACCT-AML-001", "type": "business_checking", "aum_usd": 3_400_000, "status": "active", "flags": ["transaction_monitoring_alert"]},
    "ACCT-AML-002": {"account_id": "ACCT-AML-002", "type": "business_checking", "aum_usd": 6_100_000, "status": "active", "flags": ["watchlist_review_pending"]},
    "ACCT-AML-003": {"account_id": "ACCT-AML-003", "type": "institutional", "aum_usd": 41_000_000, "status": "active", "flags": ["kyc_refresh_overdue"]},
    "ACCT-AML-004": {"account_id": "ACCT-AML-004", "type": "institutional", "aum_usd": 58_000_000, "status": "active", "flags": []},
    "ACCT-AML-005": {"account_id": "ACCT-AML-005", "type": "institutional", "aum_usd": 22_500_000, "status": "active", "flags": []},
}

# ---------------------------------------------------------------------------
# transaction_history — the real signal for the structuring case (ACCT-AML-001)
# ---------------------------------------------------------------------------

TRANSACTION_HISTORY = {
    "ACCT-AML-001": [
        {"txn_id": "T-AML-101", "type": "wire_out", "amount_usd": 9_400, "counterparty": "Havenport Trading Co", "date": "2026-06-02"},
        {"txn_id": "T-AML-102", "type": "wire_out", "amount_usd": 9_650, "counterparty": "Havenport Trading Co", "date": "2026-06-03"},
        {"txn_id": "T-AML-103", "type": "wire_out", "amount_usd": 9_200, "counterparty": "Marlow Freight Ltd", "date": "2026-06-04"},
        {"txn_id": "T-AML-104", "type": "wire_out", "amount_usd": 9_800, "counterparty": "Havenport Trading Co", "date": "2026-06-05"},
    ],
    "ACCT-AML-002": [
        {"txn_id": "T-AML-201", "type": "wire_in", "amount_usd": 240_000, "counterparty": "Silverton Client Escrow", "date": "2026-06-10"},
    ],
    "ACCT-AML-003": [
        {"txn_id": "T-AML-301", "type": "ach_out", "amount_usd": 18_000, "counterparty": "Municipal Payroll Services", "date": "2026-06-08"},
    ],
    "ACCT-AML-004": [
        {"txn_id": "T-AML-401", "type": "wire_out", "amount_usd": 1_200_000, "counterparty": "Cascade Bond Trustee", "date": "2026-06-01"},
    ],
    "ACCT-AML-005": [
        {"txn_id": "T-AML-501", "type": "wire_out", "amount_usd": 340_000, "counterparty": "Fenwick Custodial Acct", "date": "2026-06-09"},
    ],
}

# ---------------------------------------------------------------------------
# watchlist — the real signal for the false-positive case (ACCT-AML-002)
# ---------------------------------------------------------------------------

WATCHLIST = {
    "ACCT-AML-001": {"account_id": "ACCT-AML-001", "list": "OFAC_SDN", "ofac_match": False, "match_score": 0.02, "notes": "No SDN match."},
    "ACCT-AML-002": {"account_id": "ACCT-AML-002", "list": "OFAC_SDN", "ofac_match": False, "match_score": 0.71, "notes": "Fuzzy name match to 'Silverton Analytics Group Ltd' (SDN, different jurisdiction, different tax ID). Confirmed different legal entity — no SDN match."},
    "ACCT-AML-003": {"account_id": "ACCT-AML-003", "list": "OFAC_SDN", "ofac_match": False, "match_score": 0.0, "notes": "No SDN match."},
    "ACCT-AML-004": {"account_id": "ACCT-AML-004", "list": "OFAC_SDN", "ofac_match": False, "match_score": 0.0, "notes": "No SDN match."},
    "ACCT-AML-005": {"account_id": "ACCT-AML-005", "list": "OFAC_SDN", "ofac_match": False, "match_score": 0.0, "notes": "No SDN match."},
}

# ---------------------------------------------------------------------------
# counterparty_data
# ---------------------------------------------------------------------------

COUNTERPARTY_DATA = {
    "HAVENPORT_TRADING": {"counterparty": "Havenport Trading Co", "type": "trading_company", "jurisdiction": "US-DE", "risk_rating": "medium"},
    "MARLOW_FREIGHT": {"counterparty": "Marlow Freight Ltd", "type": "logistics", "jurisdiction": "US-NJ", "risk_rating": "low"},
    "SILVERTON_ESCROW": {"counterparty": "Silverton Client Escrow", "type": "escrow_agent", "jurisdiction": "US-NY", "risk_rating": "low"},
}

# ---------------------------------------------------------------------------
# delinquency_records
# ---------------------------------------------------------------------------

DELINQUENCY_RECORDS = {
    "ACCT-AML-001": {"account_id": "ACCT-AML-001", "status": "current", "delinquent_facilities": 0},
    "ACCT-AML-002": {"account_id": "ACCT-AML-002", "status": "current", "delinquent_facilities": 0},
    "ACCT-AML-003": {"account_id": "ACCT-AML-003", "status": "current", "delinquent_facilities": 0},
    "ACCT-AML-004": {"account_id": "ACCT-AML-004", "status": "current", "delinquent_facilities": 0},
    "ACCT-AML-005": {"account_id": "ACCT-AML-005", "status": "current", "delinquent_facilities": 0},
}

# ---------------------------------------------------------------------------
# identity_records — the real signal for the stale-KYC case (ACCT-AML-003)
# ---------------------------------------------------------------------------

IDENTITY_RECORDS = {
    "ACCT-AML-001": {"account_id": "ACCT-AML-001", "kyc_status": "verified", "beneficial_owners_verified": True, "last_kyc_refresh": "2025-11-02"},
    "ACCT-AML-002": {"account_id": "ACCT-AML-002", "kyc_status": "verified", "beneficial_owners_verified": True, "last_kyc_refresh": "2025-09-15"},
    "ACCT-AML-003": {"account_id": "ACCT-AML-003", "kyc_status": "expired", "beneficial_owners_verified": False, "last_kyc_refresh": "2023-02-10", "notes": "Beneficial ownership refresh overdue — 3+ years since last verification, exceeds 2-year policy window."},
    "ACCT-AML-004": {"account_id": "ACCT-AML-004", "kyc_status": "verified", "beneficial_owners_verified": True, "last_kyc_refresh": "2026-01-20"},
    "ACCT-AML-005": {"account_id": "ACCT-AML-005", "kyc_status": "verified", "beneficial_owners_verified": True, "last_kyc_refresh": "2025-12-05"},
}

# ---------------------------------------------------------------------------
# loan_history / credit_scores — shared by kyc_agent (kyc_check) and
# compliance_officer (cross_client_audit)
# ---------------------------------------------------------------------------

LOAN_HISTORY = {
    "ACCT-AML-001": {"account_id": "ACCT-AML-001", "credit_facilities": [{"type": "line_of_credit", "limit_usd": 1_000_000, "drawn_usd": 150_000}]},
    "ACCT-AML-002": {"account_id": "ACCT-AML-002", "credit_facilities": []},
    "ACCT-AML-003": {"account_id": "ACCT-AML-003", "credit_facilities": [{"type": "term_loan", "limit_usd": 5_000_000, "drawn_usd": 5_000_000}]},
    "ACCT-AML-004": {"account_id": "ACCT-AML-004", "credit_facilities": []},
    "ACCT-AML-005": {"account_id": "ACCT-AML-005", "credit_facilities": []},
}

CREDIT_SCORES = {
    "ACCT-AML-001": {"account_id": "ACCT-AML-001", "institutional_rating": "BBB", "rating_agency": "S&P", "rated_date": "2025-08-01"},
    "ACCT-AML-002": {"account_id": "ACCT-AML-002", "institutional_rating": "A-", "rating_agency": "S&P", "rated_date": "2025-08-01"},
    "ACCT-AML-003": {"account_id": "ACCT-AML-003", "institutional_rating": "A", "rating_agency": "Moody's", "rated_date": "2025-06-15"},
    "ACCT-AML-004": {"account_id": "ACCT-AML-004", "institutional_rating": "AA-", "rating_agency": "Moody's", "rated_date": "2025-06-15"},
    "ACCT-AML-005": {"account_id": "ACCT-AML-005", "institutional_rating": "AA", "rating_agency": "S&P", "rated_date": "2025-08-01"},
}

# ---------------------------------------------------------------------------
# audit_logs / regulatory_filings — compliance_officer's real sources
# ---------------------------------------------------------------------------

AUDIT_LOGS = {
    "AL-2026-Q2-004": {"log_id": "AL-2026-Q2-004", "scope": "aml_case_review", "status": "clean", "reviewed_by": "internal_audit"},
}

REGULATORY_FILINGS = {
    "ACCT-AML-004": {"account_id": "ACCT-AML-004", "filing_type": "SAR filing history", "status": "none_on_file", "last_checked": "2026-06-01"},
}

# ---------------------------------------------------------------------------
# portfolio_holdings — compliance_officer's cross-client-audit source, the one
# place this demo reaches outside the strictly risk-catalog data
# ---------------------------------------------------------------------------

PORTFOLIO_HOLDINGS = {
    "ACCT-AML-004": {"account_id": "ACCT-AML-004", "as_of_date": "2026-06-01", "total_aum_usd": 58_000_000, "asset_mix": {"fixed_income": 0.55, "equities": 0.30, "cash": 0.15}},
}

# ---------------------------------------------------------------------------
# denied-only decoys — never in any role's allowed_sources
# ---------------------------------------------------------------------------

RISK_MODELS = {
    "AML_TYPOLOGY_MODEL_V4": {"model": "AML_TYPOLOGY_MODEL_V4", "owner": "model_risk", "status": "proprietary"},
}

EXECUTIVE_COMMUNICATIONS = {
    "EXEC-2026-06": {"title": "Q2 Compliance Committee Briefing", "classification": "executive_confidential"},
}

# ---------------------------------------------------------------------------
# AML case queue — 5 accounts up for review, mixed severity. `reason_for_review`/
# `priority`/`opened` are the only fields ever shown before a case is opened (queue
# card) — never the signal flags below, which would give away the outcome before the
# investigation "discovers" it. See get_expected_outcome() for the rule-based ground
# truth decision_node's ungoverned logic is checked against.
# ---------------------------------------------------------------------------

AML_CASES = {
    "AML-001": {
        "case_id": "AML-001", "account_id": "ACCT-AML-001", "priority": "HIGH",
        "opened": "2026-06-06T09:00:00Z",
        "reason_for_review": "Transaction monitoring alert: repeated wire transfers just under the $10,000 CTR reporting threshold within a 4-day window.",
    },
    "AML-002": {
        "case_id": "AML-002", "account_id": "ACCT-AML-002", "priority": "MEDIUM",
        "opened": "2026-06-10T14:00:00Z",
        "reason_for_review": "OFAC/SDN watchlist screening returned a fuzzy name match requiring manual clearance before the account can be marked clean.",
    },
    "AML-003": {
        "case_id": "AML-003", "account_id": "ACCT-AML-003", "priority": "MEDIUM",
        "opened": "2026-06-08T11:30:00Z",
        "reason_for_review": "Periodic KYC refresh review — beneficial ownership verification due for renewal per policy cycle.",
    },
    "AML-004": {
        "case_id": "AML-004", "account_id": "ACCT-AML-004", "priority": "LOW",
        "opened": "2026-06-01T08:00:00Z",
        "reason_for_review": "Quarterly cross-client consistency audit requested by internal audit — confirm AML handling is applied uniformly across the institutional book.",
    },
    "AML-005": {
        "case_id": "AML-005", "account_id": "ACCT-AML-005", "priority": "LOW",
        "opened": "2026-06-09T10:15:00Z",
        "reason_for_review": "Routine annual AML case review — no prior flags on this account.",
    },
}


def get_expected_outcome(case_id: str) -> dict:
    """Ground truth for verification prints only — decision_node computes its
    proposed_action from the same underlying signal data, not from this function.
    Mirrors fraud_investigation's simulated_data.get_expected_outcome()."""
    return {
        "AML-001": {"proposed_action": "SAR REQUIRED — structuring pattern confirmed"},
        "AML-002": {"proposed_action": "CLEARED — watchlist match resolved as false positive"},
        "AML-003": {"proposed_action": "HOLD PENDING KYC REFRESH — beneficial ownership verification lapsed"},
        "AML-004": {"proposed_action": "CLEARED — cross-client audit confirms consistent handling"},
        "AML-005": {"proposed_action": "CLEAR — NO FURTHER ACTION REQUIRED"},
    }[case_id]
