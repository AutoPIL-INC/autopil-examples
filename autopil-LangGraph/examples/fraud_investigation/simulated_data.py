"""
Simulated data for the AutoPIL Fraud Investigation demo.

Five fraud cases with distinct patterns:
  - CASE-001: Structuring (currency transactions just under $10,000 reporting threshold)
  - CASE-002: Account takeover (velocity spike + new device + geo anomaly)
  - CASE-003: Synthetic identity (new account, thin file, rapid high-value activity)
  - CASE-004: Elder financial exploitation (new authorized signer + fund diversion)
  - CASE-005: Money mule / check kiting (third-party checks withdrawn before hold release)

Each case includes:
  - A fraud alert (trigger for the orchestrator)
  - Linked account record
  - Transaction history
  - Identity/KYC record
  - Expected investigation outcome
"""

from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Accounts (5 total — 3 under investigation, 2 clean baselines)
# ---------------------------------------------------------------------------

ACCOUNTS = {
    "ACC_8821": {
        "account_id": "ACC_8821",
        "holder_name": "Marcus T. Webb",
        "account_type": "checking",
        "opened_date": "2026-01-08",          # opened 11 weeks ago — new account
        "tenure_days": 77,
        "average_monthly_balance": 4200,
        "prior_sar_count": 0,
        "account_flags": ["new_account", "high_velocity"],
        "risk_score": 87,                      # elevated
        "product_holdings": ["checking"],
    },
    "ACC_3347": {
        "account_id": "ACC_3347",
        "holder_name": "Elena Vostrikova",
        "account_type": "checking",
        "opened_date": "2019-06-14",
        "tenure_days": 2480,
        "average_monthly_balance": 18500,
        "prior_sar_count": 0,
        "account_flags": ["geo_anomaly", "new_device_login"],
        "risk_score": 71,
        "product_holdings": ["checking", "savings", "credit_card"],
    },
    "ACC_5590": {
        "account_id": "ACC_5590",
        "holder_name": "Daniel R. Forsythe",
        "account_type": "checking",
        "opened_date": "2026-02-20",           # opened 5 weeks ago — very new
        "tenure_days": 38,
        "average_monthly_balance": 800,
        "prior_sar_count": 0,
        "account_flags": ["new_account", "thin_file", "rapid_escalation"],
        "risk_score": 92,                      # high risk
        "product_holdings": ["checking"],
    },
    "ACC_6634": {
        "account_id": "ACC_6634",
        "holder_name": "Eleanor J. Whitfield",
        "account_type": "checking",
        "opened_date": "2001-05-10",           # 25-year customer
        "tenure_days": 9089,
        "average_monthly_balance": 6200,
        "prior_sar_count": 0,
        "account_flags": ["elder_customer", "new_authorized_signer"],
        "risk_score": 68,
        "product_holdings": ["checking", "savings"],
    },
    "ACC_7743": {
        "account_id": "ACC_7743",
        "holder_name": "Jamal K. Reyes",
        "account_type": "checking",
        "opened_date": "2025-10-02",            # ~6 months — plausible recruited-mule profile
        "tenure_days": 178,
        "average_monthly_balance": 1100,
        "prior_sar_count": 0,
        "account_flags": ["short_tenure", "third_party_deposits"],
        "risk_score": 81,
        "product_holdings": ["checking"],
    },
    # Clean baseline accounts (no active alerts)
    "ACC_1102": {
        "account_id": "ACC_1102",
        "holder_name": "Patricia M. Huang",
        "account_type": "checking",
        "opened_date": "2015-03-22",
        "tenure_days": 4028,
        "average_monthly_balance": 32000,
        "prior_sar_count": 0,
        "account_flags": [],
        "risk_score": 12,
        "product_holdings": ["checking", "savings", "investment"],
    },
    "ACC_2288": {
        "account_id": "ACC_2288",
        "holder_name": "Robert J. Okafor",
        "account_type": "checking",
        "opened_date": "2021-09-05",
        "tenure_days": 1667,
        "average_monthly_balance": 9700,
        "prior_sar_count": 0,
        "account_flags": [],
        "risk_score": 18,
        "product_holdings": ["checking", "credit_card"],
    },
}

# ---------------------------------------------------------------------------
# Transaction history (50 records across all accounts)
# ---------------------------------------------------------------------------

TRANSACTIONS = [

    # ── CASE-001: ACC_8821 — Structuring pattern ──────────────────────────────
    # 12 cash deposits over 8 days, all between $9,100 and $9,800 (just under $10k CTR threshold)

    {"txn_id": "T001", "account_id": "ACC_8821", "date": "2026-03-22", "type": "cash_deposit",
     "amount": 9400, "merchant": None,         "channel": "branch",  "city": "Dallas",   "state": "TX"},
    {"txn_id": "T002", "account_id": "ACC_8821", "date": "2026-03-22", "type": "cash_deposit",
     "amount": 9200, "merchant": None,         "channel": "branch",  "city": "Fort Worth","state": "TX"},
    {"txn_id": "T003", "account_id": "ACC_8821", "date": "2026-03-23", "type": "cash_deposit",
     "amount": 9700, "merchant": None,         "channel": "branch",  "city": "Arlington", "state": "TX"},
    {"txn_id": "T004", "account_id": "ACC_8821", "date": "2026-03-23", "type": "cash_deposit",
     "amount": 9100, "merchant": None,         "channel": "atm",     "city": "Dallas",    "state": "TX"},
    {"txn_id": "T005", "account_id": "ACC_8821", "date": "2026-03-24", "type": "cash_deposit",
     "amount": 9500, "merchant": None,         "channel": "branch",  "city": "Plano",     "state": "TX"},
    {"txn_id": "T006", "account_id": "ACC_8821", "date": "2026-03-24", "type": "cash_deposit",
     "amount": 9300, "merchant": None,         "channel": "atm",     "city": "Irving",    "state": "TX"},
    {"txn_id": "T007", "account_id": "ACC_8821", "date": "2026-03-25", "type": "cash_deposit",
     "amount": 9800, "merchant": None,         "channel": "branch",  "city": "Garland",   "state": "TX"},
    {"txn_id": "T008", "account_id": "ACC_8821", "date": "2026-03-25", "type": "cash_deposit",
     "amount": 9150, "merchant": None,         "channel": "branch",  "city": "Mesquite",  "state": "TX"},
    {"txn_id": "T009", "account_id": "ACC_8821", "date": "2026-03-26", "type": "cash_deposit",
     "amount": 9600, "merchant": None,         "channel": "atm",     "city": "Dallas",    "state": "TX"},
    {"txn_id": "T010", "account_id": "ACC_8821", "date": "2026-03-27", "type": "cash_deposit",
     "amount": 9250, "merchant": None,         "channel": "branch",  "city": "Dallas",    "state": "TX"},
    {"txn_id": "T011", "account_id": "ACC_8821", "date": "2026-03-28", "type": "cash_deposit",
     "amount": 9450, "merchant": None,         "channel": "branch",  "city": "Fort Worth","state": "TX"},
    {"txn_id": "T012", "account_id": "ACC_8821", "date": "2026-03-29", "type": "cash_deposit",
     "amount": 9350, "merchant": None,         "channel": "atm",     "city": "Dallas",    "state": "TX"},
    # One outbound wire — funds leaving after structuring
    {"txn_id": "T013", "account_id": "ACC_8821", "date": "2026-03-29", "type": "wire_transfer",
     "amount": -87400, "merchant": None,       "channel": "online",  "city": "Dallas",    "state": "TX",
     "wire_destination": "offshore", "beneficiary_country": "BVI"},

    # ── CASE-002: ACC_3347 — Account takeover ────────────────────────────────
    # Normal baseline transactions, then a velocity spike from a new device in a new geo

    {"txn_id": "T014", "account_id": "ACC_3347", "date": "2026-03-15", "type": "purchase",
     "amount": -142, "merchant": "Whole Foods",    "channel": "card",   "city": "Austin",    "state": "TX"},
    {"txn_id": "T015", "account_id": "ACC_3347", "date": "2026-03-17", "type": "purchase",
     "amount": -380, "merchant": "Delta Airlines", "channel": "online", "city": "Austin",    "state": "TX"},
    {"txn_id": "T016", "account_id": "ACC_3347", "date": "2026-03-20", "type": "purchase",
     "amount": -67,  "merchant": "HEB",            "channel": "card",   "city": "Austin",    "state": "TX"},
    # Geo anomaly: Austin-based account suddenly active in Miami then NYC within 2 hours (impossible travel)
    {"txn_id": "T017", "account_id": "ACC_3347", "date": "2026-03-29", "type": "purchase",
     "amount": -1200, "merchant": "Apple Store",   "channel": "card",   "city": "Miami",     "state": "FL",
     "device_id": "DEV_NEW_9921", "geo_anomaly": True},
    {"txn_id": "T018", "account_id": "ACC_3347", "date": "2026-03-29", "type": "purchase",
     "amount": -3400, "merchant": "Saks Fifth Ave","channel": "card",   "city": "New York",  "state": "NY",
     "device_id": "DEV_NEW_9921", "geo_anomaly": True},
    {"txn_id": "T019", "account_id": "ACC_3347", "date": "2026-03-29", "type": "wire_transfer",
     "amount": -8900, "merchant": None,            "channel": "online", "city": "New York",  "state": "NY",
     "device_id": "DEV_NEW_9921", "geo_anomaly": True},
    {"txn_id": "T020", "account_id": "ACC_3347", "date": "2026-03-29", "type": "purchase",
     "amount": -2100, "merchant": "Jewelry Exchange","channel": "card", "city": "New York",  "state": "NY",
     "device_id": "DEV_NEW_9921", "geo_anomaly": True},
    {"txn_id": "T021", "account_id": "ACC_3347", "date": "2026-03-29", "type": "atm_withdrawal",
     "amount": -500,  "merchant": None,            "channel": "atm",    "city": "New York",  "state": "NY",
     "device_id": "DEV_NEW_9921", "geo_anomaly": True},

    # ── CASE-003: ACC_5590 — Synthetic identity ──────────────────────────────
    # New account (38 days), thin file, jumps immediately to high-value activity

    {"txn_id": "T022", "account_id": "ACC_5590", "date": "2026-02-22", "type": "cash_deposit",
     "amount": 500,  "merchant": None,             "channel": "branch", "city": "Dallas",    "state": "TX"},
    {"txn_id": "T023", "account_id": "ACC_5590", "date": "2026-02-28", "type": "cash_deposit",
     "amount": 500,  "merchant": None,             "channel": "atm",    "city": "Dallas",    "state": "TX"},
    # Account jumps to large activity after minimal history — classic synthetic identity escalation
    {"txn_id": "T024", "account_id": "ACC_5590", "date": "2026-03-10", "type": "purchase",
     "amount": -4200, "merchant": "Best Buy",      "channel": "card",   "city": "Dallas",    "state": "TX"},
    {"txn_id": "T025", "account_id": "ACC_5590", "date": "2026-03-15", "type": "purchase",
     "amount": -3800, "merchant": "Costco",        "channel": "card",   "city": "Dallas",    "state": "TX"},
    {"txn_id": "T026", "account_id": "ACC_5590", "date": "2026-03-18", "type": "cash_advance",
     "amount": -4900, "merchant": None,            "channel": "branch", "city": "Dallas",    "state": "TX"},
    {"txn_id": "T027", "account_id": "ACC_5590", "date": "2026-03-22", "type": "purchase",
     "amount": -3100, "merchant": "Walmart",       "channel": "card",   "city": "Dallas",    "state": "TX"},
    {"txn_id": "T028", "account_id": "ACC_5590", "date": "2026-03-25", "type": "purchase",
     "amount": -4700, "merchant": "Target",        "channel": "card",   "city": "Dallas",    "state": "TX"},
    {"txn_id": "T029", "account_id": "ACC_5590", "date": "2026-03-28", "type": "purchase",
     "amount": -4400, "merchant": "Sam's Club",    "channel": "card",   "city": "Dallas",    "state": "TX"},
    # Account stops making payments — bust-out pattern
    {"txn_id": "T030", "account_id": "ACC_5590", "date": "2026-03-30", "type": "nsf_return",
     "amount": 0,    "merchant": None,             "channel": "system", "city": None,        "state": None,
     "flag": "insufficient_funds"},

    # ── CASE-004: ACC_6634 — Elder financial exploitation ──────────────────────
    # 25-year low-activity retirement account. New authorized signer added 2026-03-17 —
    # escalating transfers to that signer's personal account follow within days.

    {"txn_id": "T051", "account_id": "ACC_6634", "date": "2026-02-02", "type": "ss_deposit",
     "amount": 2100,  "merchant": "SSA Direct Deposit", "channel": "ach",  "city": "Plano", "state": "TX"},
    {"txn_id": "T052", "account_id": "ACC_6634", "date": "2026-02-05", "type": "purchase",
     "amount": -85,   "merchant": "CVS",                "channel": "card", "city": "Plano", "state": "TX"},
    {"txn_id": "T053", "account_id": "ACC_6634", "date": "2026-02-10", "type": "bill_payment",
     "amount": -210,  "merchant": "Oncor Electric",     "channel": "ach",  "city": "Plano", "state": "TX"},
    {"txn_id": "T054", "account_id": "ACC_6634", "date": "2026-03-02", "type": "ss_deposit",
     "amount": 2100,  "merchant": "SSA Direct Deposit", "channel": "ach",  "city": "Plano", "state": "TX"},
    {"txn_id": "T055", "account_id": "ACC_6634", "date": "2026-03-08", "type": "purchase",
     "amount": -64,   "merchant": "Kroger",             "channel": "card", "city": "Plano", "state": "TX"},
    # New authorized signer added 2026-03-17 — transfers to their personal account begin days later
    {"txn_id": "T056", "account_id": "ACC_6634", "date": "2026-03-20", "type": "transfer",
     "amount": -4200, "merchant": "K. Whitfield Personal", "channel": "online", "city": "Plano", "state": "TX",
     "new_payee": True},
    {"txn_id": "T057", "account_id": "ACC_6634", "date": "2026-03-22", "type": "transfer",
     "amount": -6500, "merchant": "K. Whitfield Personal", "channel": "online", "city": "Plano", "state": "TX",
     "new_payee": True},
    {"txn_id": "T058", "account_id": "ACC_6634", "date": "2026-03-24", "type": "transfer",
     "amount": -7800, "merchant": "K. Whitfield Personal", "channel": "online", "city": "Plano", "state": "TX",
     "new_payee": True},
    {"txn_id": "T059", "account_id": "ACC_6634", "date": "2026-03-26", "type": "transfer",
     "amount": -8900, "merchant": "K. Whitfield Personal", "channel": "online", "city": "Plano", "state": "TX",
     "new_payee": True},
    {"txn_id": "T060", "account_id": "ACC_6634", "date": "2026-03-28", "type": "transfer",
     "amount": -7100, "merchant": "K. Whitfield Personal", "channel": "online", "city": "Plano", "state": "TX",
     "new_payee": True},

    # ── CASE-005: ACC_7743 — Money mule / check kiting ──────────────────────────
    # Recently opened account. Five third-party check deposits from unrelated remitters,
    # each withdrawn same-day — before standard hold periods would release the funds.

    {"txn_id": "T061", "account_id": "ACC_7743", "date": "2025-10-15", "type": "purchase",
     "amount": -45,   "merchant": "7-Eleven",           "channel": "card", "city": "San Antonio", "state": "TX"},
    {"txn_id": "T062", "account_id": "ACC_7743", "date": "2025-12-01", "type": "payroll_deposit",
     "amount": 1400,  "merchant": "Gig Economy Payroll","channel": "ach", "city": "San Antonio", "state": "TX"},
    {"txn_id": "T063", "account_id": "ACC_7743", "date": "2026-03-20", "type": "check_deposit",
     "amount": 8200,  "merchant": None, "channel": "mobile", "city": "San Antonio", "state": "TX",
     "remitter": "Unknown Payer 1"},
    {"txn_id": "T064", "account_id": "ACC_7743", "date": "2026-03-20", "type": "atm_withdrawal",
     "amount": -7500, "merchant": None, "channel": "atm",    "city": "San Antonio", "state": "TX",
     "before_hold_release": True},
    {"txn_id": "T065", "account_id": "ACC_7743", "date": "2026-03-22", "type": "check_deposit",
     "amount": 9100,  "merchant": None, "channel": "mobile", "city": "San Antonio", "state": "TX",
     "remitter": "Unknown Payer 2"},
    {"txn_id": "T066", "account_id": "ACC_7743", "date": "2026-03-22", "type": "wire_transfer",
     "amount": -8600, "merchant": None, "channel": "online", "city": "San Antonio", "state": "TX",
     "before_hold_release": True},
    {"txn_id": "T067", "account_id": "ACC_7743", "date": "2026-03-24", "type": "check_deposit",
     "amount": 7800,  "merchant": None, "channel": "mobile", "city": "San Antonio", "state": "TX",
     "remitter": "Unknown Payer 3"},
    {"txn_id": "T068", "account_id": "ACC_7743", "date": "2026-03-24", "type": "atm_withdrawal",
     "amount": -7200, "merchant": None, "channel": "atm",    "city": "San Antonio", "state": "TX",
     "before_hold_release": True},
    {"txn_id": "T069", "account_id": "ACC_7743", "date": "2026-03-26", "type": "check_deposit",
     "amount": 8900,  "merchant": None, "channel": "mobile", "city": "San Antonio", "state": "TX",
     "remitter": "Unknown Payer 4"},
    {"txn_id": "T070", "account_id": "ACC_7743", "date": "2026-03-26", "type": "wire_transfer",
     "amount": -8300, "merchant": None, "channel": "online", "city": "San Antonio", "state": "TX",
     "before_hold_release": True},
    {"txn_id": "T071", "account_id": "ACC_7743", "date": "2026-03-27", "type": "check_deposit",
     "amount": 8000,  "merchant": None, "channel": "mobile", "city": "San Antonio", "state": "TX",
     "remitter": "Unknown Payer 5"},
    {"txn_id": "T072", "account_id": "ACC_7743", "date": "2026-03-27", "type": "atm_withdrawal",
     "amount": -7400, "merchant": None, "channel": "atm",    "city": "San Antonio", "state": "TX",
     "before_hold_release": True},

    # ── Clean account baseline — ACC_1102 ─────────────────────────────────────
    {"txn_id": "T031", "account_id": "ACC_1102", "date": "2026-03-01", "type": "payroll_deposit",
     "amount": 8400,  "merchant": "Citibank Payroll","channel": "ach",  "city": "Dallas",    "state": "TX"},
    {"txn_id": "T032", "account_id": "ACC_1102", "date": "2026-03-05", "type": "purchase",
     "amount": -210,  "merchant": "HEB",            "channel": "card",  "city": "Dallas",    "state": "TX"},
    {"txn_id": "T033", "account_id": "ACC_1102", "date": "2026-03-10", "type": "bill_payment",
     "amount": -1850, "merchant": "Mortgage",       "channel": "ach",   "city": "Dallas",    "state": "TX"},
    {"txn_id": "T034", "account_id": "ACC_1102", "date": "2026-03-15", "type": "purchase",
     "amount": -420,  "merchant": "Whole Foods",    "channel": "card",  "city": "Dallas",    "state": "TX"},
    {"txn_id": "T035", "account_id": "ACC_1102", "date": "2026-03-20", "type": "transfer",
     "amount": -2000, "merchant": "Fidelity",       "channel": "online","city": "Dallas",    "state": "TX"},

    # ── Clean account baseline — ACC_2288 ─────────────────────────────────────
    {"txn_id": "T036", "account_id": "ACC_2288", "date": "2026-03-01", "type": "payroll_deposit",
     "amount": 4200,  "merchant": "Employer ACH",   "channel": "ach",   "city": "Houston",   "state": "TX"},
    {"txn_id": "T037", "account_id": "ACC_2288", "date": "2026-03-07", "type": "purchase",
     "amount": -145,  "merchant": "Amazon",         "channel": "online","city": "Houston",   "state": "TX"},
    {"txn_id": "T038", "account_id": "ACC_2288", "date": "2026-03-12", "type": "purchase",
     "amount": -380,  "merchant": "Shell",          "channel": "card",  "city": "Houston",   "state": "TX"},
    {"txn_id": "T039", "account_id": "ACC_2288", "date": "2026-03-18", "type": "bill_payment",
     "amount": -950,  "merchant": "Rent",           "channel": "ach",   "city": "Houston",   "state": "TX"},
    {"txn_id": "T040", "account_id": "ACC_2288", "date": "2026-03-25", "type": "purchase",
     "amount": -230,  "merchant": "HEB",            "channel": "card",  "city": "Houston",   "state": "TX"},

    # Additional ACC_8821 baseline (pre-structuring period — normal activity)
    {"txn_id": "T041", "account_id": "ACC_8821", "date": "2026-01-15", "type": "cash_deposit",
     "amount": 800,   "merchant": None,             "channel": "atm",   "city": "Dallas",    "state": "TX"},
    {"txn_id": "T042", "account_id": "ACC_8821", "date": "2026-02-01", "type": "purchase",
     "amount": -120,  "merchant": "CVS",            "channel": "card",  "city": "Dallas",    "state": "TX"},
    {"txn_id": "T043", "account_id": "ACC_8821", "date": "2026-02-14", "type": "cash_deposit",
     "amount": 500,   "merchant": None,             "channel": "branch","city": "Dallas",    "state": "TX"},
    {"txn_id": "T044", "account_id": "ACC_8821", "date": "2026-03-01", "type": "purchase",
     "amount": -85,   "merchant": "Walgreens",      "channel": "card",  "city": "Dallas",    "state": "TX"},
    {"txn_id": "T045", "account_id": "ACC_8821", "date": "2026-03-10", "type": "cash_deposit",
     "amount": 1200,  "merchant": None,             "channel": "atm",   "city": "Dallas",    "state": "TX"},

    # Additional ACC_3347 baseline (pre-takeover — normal activity)
    {"txn_id": "T046", "account_id": "ACC_3347", "date": "2026-03-01", "type": "payroll_deposit",
     "amount": 11200, "merchant": "Employer ACH",   "channel": "ach",   "city": "Austin",    "state": "TX"},
    {"txn_id": "T047", "account_id": "ACC_3347", "date": "2026-03-03", "type": "bill_payment",
     "amount": -2400, "merchant": "Rent",           "channel": "ach",   "city": "Austin",    "state": "TX"},
    {"txn_id": "T048", "account_id": "ACC_3347", "date": "2026-03-08", "type": "purchase",
     "amount": -290,  "merchant": "Trader Joes",    "channel": "card",  "city": "Austin",    "state": "TX"},
    {"txn_id": "T049", "account_id": "ACC_3347", "date": "2026-03-12", "type": "purchase",
     "amount": -175,  "merchant": "Netflix/Spotify","channel": "online","city": "Austin",    "state": "TX"},
    {"txn_id": "T050", "account_id": "ACC_3347", "date": "2026-03-19", "type": "transfer",
     "amount": -1500, "merchant": "Savings",        "channel": "online","city": "Austin",    "state": "TX"},
]

# ---------------------------------------------------------------------------
# Identity / KYC records
# ---------------------------------------------------------------------------

KYC_RECORDS = {
    "ACC_8821": {
        "account_id": "ACC_8821",
        "full_name": "Marcus T. Webb",
        "dob": "1988-04-12",
        "ssn_last4": "7734",
        "address": "2841 Commerce St, Dallas, TX 75226",
        "id_type": "drivers_license",
        "id_state": "TX",
        "id_verified": True,
        "kyc_status": "passed",
        "kyc_date": "2026-01-08",
        "ofac_screened": True,
        "ofac_match": False,
        "pep_match": False,
        "adverse_media": False,
        "notes": "Identity verified at branch opening. No prior relationship.",
    },
    "ACC_3347": {
        "account_id": "ACC_3347",
        "full_name": "Elena Vostrikova",
        "dob": "1979-11-30",
        "ssn_last4": "2209",
        "address": "512 W 6th St Apt 14B, Austin, TX 78701",
        "id_type": "passport",
        "id_state": None,
        "id_verified": True,
        "kyc_status": "passed",
        "kyc_date": "2019-06-14",
        "ofac_screened": True,
        "ofac_match": False,
        "pep_match": False,
        "adverse_media": False,
        "notes": "Long-tenured customer. Last KYC refresh 2023-01. Device ID DEV_NEW_9921 not in known device history.",
    },
    "ACC_5590": {
        "account_id": "ACC_5590",
        "full_name": "Daniel R. Forsythe",
        "dob": "1993-07-04",
        "ssn_last4": "4481",
        "address": "1099 Main St Apt 3, Dallas, TX 75201",
        "id_type": "drivers_license",
        "id_state": "TX",
        "id_verified": True,
        "kyc_status": "passed",
        "kyc_date": "2026-02-20",
        "ofac_screened": True,
        "ofac_match": False,
        "pep_match": False,
        "adverse_media": False,
        # Key finding: SSN was used in a prior fraudulent account application (different name)
        "notes": "SSN 4481 matches a prior declined application under name 'David R. Forsyth' (2025-11-03). "
                 "Prior application denied — thin file, inconsistent employment. Possible synthetic identity.",
        "prior_application_flag": True,
        "prior_application_date": "2025-11-03",
        "prior_application_name": "David R. Forsyth",
    },
    "ACC_6634": {
        "account_id": "ACC_6634",
        "full_name": "Eleanor J. Whitfield",
        "dob": "1948-09-02",
        "ssn_last4": "5512",
        "address": "77 Heritage Oaks Dr, Plano, TX 75024",
        "id_type": "drivers_license",
        "id_state": "TX",
        "id_verified": True,
        "kyc_status": "passed",
        "kyc_date": "2001-05-10",
        "ofac_screened": True,
        "ofac_match": False,
        "pep_match": False,
        "adverse_media": False,
        # Key finding: brand-new authorized signer, zero precedent in 25 years on file
        "notes": "25-year customer, historically low-activity retirement account. New authorized "
                 "signer 'Kevin Whitfield' (listed as grandson) added 2026-03-17 — no prior "
                 "authorized signers on file in the account's 25-year history.",
        "authorized_signer_added": "2026-03-17",
        "authorized_signer_name": "Kevin Whitfield",
    },
    "ACC_7743": {
        "account_id": "ACC_7743",
        "full_name": "Jamal K. Reyes",
        "dob": "1999-02-18",
        "ssn_last4": "6690",
        "address": "440 Alamo Plaza Apt 9, San Antonio, TX 78205",
        "id_type": "drivers_license",
        "id_state": "TX",
        "id_verified": True,
        "kyc_status": "passed",
        "kyc_date": "2025-10-02",
        "ofac_screened": True,
        "ofac_match": False,
        "pep_match": False,
        "adverse_media": False,
        # Key finding: the holder's own identity isn't in question — the concern is whose
        # money is moving through the account, not who the account belongs to
        "notes": "Account holder's own identity is not in question. Five check deposits over 7 "
                 "days from five different, unrelated remitters, each followed same-day by "
                 "withdrawal before standard hold periods would release — consistent with a "
                 "recruited money mule (e.g. a 'payment processing job' scam) rather than the "
                 "holder's own funds.",
    },
}

# ---------------------------------------------------------------------------
# Fraud alerts (5 — one per case, these trigger the orchestrator)
# ---------------------------------------------------------------------------

FRAUD_ALERTS = [
    {
        "alert_id": "ALERT-001",
        "account_id": "ACC_8821",
        "alert_type": "structuring",
        "triggered_at": "2026-03-29T14:22:00Z",
        "triggered_by": "aml_rule_engine",
        "rule_name": "CTR_AVOIDANCE_PATTERN",
        "description": "12 cash deposits in 8 days, all between $9,100-$9,800. "
                       "Cumulative total $112,500. Single outbound wire $87,400 to BVI entity "
                       "immediately follows deposit pattern.",
        "priority": "HIGH",
        "assigned_to": None,
        "status": "open",
        "case_id": "CASE-001",
    },
    {
        "alert_id": "ALERT-002",
        "account_id": "ACC_3347",
        "alert_type": "account_takeover",
        "triggered_at": "2026-03-29T16:47:00Z",
        "triggered_by": "fraud_detection_model",
        "rule_name": "GEO_VELOCITY_ANOMALY",
        "description": "Austin TX → Miami FL → New York NY in 97 minutes. "
                       "All three transactions from unrecognized device DEV_NEW_9921. "
                       "$16,100 total debits in 4-hour window vs. $380 prior daily average.",
        "priority": "CRITICAL",
        "assigned_to": None,
        "status": "open",
        "case_id": "CASE-002",
    },
    {
        "alert_id": "ALERT-003",
        "account_id": "ACC_5590",
        "alert_type": "synthetic_identity",
        "triggered_at": "2026-03-30T09:15:00Z",
        "triggered_by": "credit_risk_model",
        "rule_name": "BUST_OUT_PATTERN",
        "description": "Account opened 38 days ago. Minimal opening activity, then $25,100 in "
                       "purchases over 20 days across mass retailers. NSF returned today. "
                       "SSN matches prior declined application under different name.",
        "priority": "HIGH",
        "assigned_to": None,
        "status": "open",
        "case_id": "CASE-003",
    },
    {
        "alert_id": "ALERT-004",
        "account_id": "ACC_6634",
        "alert_type": "elder_financial_exploitation",
        "triggered_at": "2026-03-28T11:05:00Z",
        "triggered_by": "aml_rule_engine",
        "rule_name": "AUTHORIZED_SIGNER_FUND_DIVERSION",
        "description": "New authorized signer added 2026-03-17 to a 25-year, historically "
                       "low-activity retirement account. $34,500 in transfers to that signer's "
                       "personal account over the following 11 days — no comparable activity "
                       "anywhere in the account's prior history.",
        "priority": "HIGH",
        "assigned_to": None,
        "status": "open",
        "case_id": "CASE-004",
    },
    {
        "alert_id": "ALERT-005",
        "account_id": "ACC_7743",
        "alert_type": "money_mule_check_kiting",
        "triggered_at": "2026-03-27T15:30:00Z",
        "triggered_by": "check_fraud_detection_model",
        "rule_name": "RAPID_CHECK_DEPOSIT_WITHDRAWAL",
        "description": "Five third-party check deposits totaling $42,000 over 7 days, each from a "
                       "different, unrelated remitter, followed same-day by withdrawal before "
                       "standard hold periods release. Classic money-mule / check-kiting signature.",
        "priority": "HIGH",
        "assigned_to": None,
        "status": "open",
        "case_id": "CASE-005",
    },
]

# ---------------------------------------------------------------------------
# Processed agent outputs (what sub-agents surface — only this is available to sar_generator)
# ---------------------------------------------------------------------------

AGENT_OUTPUTS = {
    "CASE-001": {
        "transaction_analyst": {
            "agent_role": "transaction_analyst",
            "case_id": "CASE-001",
            "findings": {
                "pattern": "structuring",
                "transaction_count": 12,
                "amount_range": [9100, 9800],
                "total_deposited": 112500,
                "outbound_wire": 87400,
                "wire_destination": "BVI",
                "structuring_confidence": 0.96,
                "days_active": 8,
            },
            "recommendation": "ESCALATE — classic structuring pattern with immediate wire-out to high-risk jurisdiction",
        },
        "account_profiler": {
            "agent_role": "account_profiler",
            "case_id": "CASE-001",
            "findings": {
                "account_tenure_days": 77,
                "risk_score": 87,
                "flags": ["new_account", "high_velocity"],
                "prior_sar_count": 0,
                "average_monthly_balance": 4200,
                "activity_inconsistent_with_profile": True,
            },
            "recommendation": "ESCALATE — activity vastly inconsistent with account history and tenure",
        },
        "kyc_specialist": {
            "agent_role": "kyc_specialist",
            "case_id": "CASE-001",
            "findings": {
                "kyc_status": "passed",
                "ofac_match": False,
                "pep_match": False,
                "adverse_media": False,
                "kyc_age_days": 77,
            },
            "recommendation": "MONITOR — KYC clear but account is new; wire destination (BVI) warrants enhanced due diligence",
        },
    },
    "CASE-002": {
        "transaction_analyst": {
            "agent_role": "transaction_analyst",
            "case_id": "CASE-002",
            "findings": {
                "pattern": "account_takeover_velocity",
                "total_debits_4h": 16100,
                "prior_daily_avg": 380,
                "velocity_multiplier": 42.4,
                "geo_sequence": ["Austin TX", "Miami FL", "New York NY"],
                "travel_time_minutes": 97,
                "device_id": "DEV_NEW_9921",
                "device_known": False,
            },
            "recommendation": "FREEZE — impossible travel + velocity anomaly + unknown device = high-confidence ATO",
        },
        "account_profiler": {
            "agent_role": "account_profiler",
            "case_id": "CASE-002",
            "findings": {
                "account_tenure_days": 2480,
                "risk_score": 71,
                "flags": ["geo_anomaly", "new_device_login"],
                "prior_sar_count": 0,
                "average_monthly_balance": 18500,
                "activity_inconsistent_with_profile": True,
            },
            "recommendation": "ESCALATE — long-tenured account, behavior completely inconsistent with 7-year history",
        },
        "kyc_specialist": {
            "agent_role": "kyc_specialist",
            "case_id": "CASE-002",
            "findings": {
                "kyc_status": "passed",
                "ofac_match": False,
                "pep_match": False,
                "adverse_media": False,
                "last_kyc_refresh_days": 1186,
            },
            "recommendation": "KYC clear. Recommend contacting account holder to verify whether activity is authorized.",
        },
    },
    "CASE-003": {
        "transaction_analyst": {
            "agent_role": "transaction_analyst",
            "case_id": "CASE-003",
            "findings": {
                "pattern": "bust_out",
                "account_age_days_at_escalation": 38,
                "total_purchases_30d": 25100,
                "nsf_returned": True,
                "merchant_concentration": ["Best Buy", "Costco", "Walmart", "Target", "Sam's Club"],
                "bust_out_confidence": 0.91,
            },
            "recommendation": "ESCALATE — bust-out pattern consistent with synthetic identity fraud",
        },
        "account_profiler": {
            "agent_role": "account_profiler",
            "case_id": "CASE-003",
            "findings": {
                "account_tenure_days": 38,
                "risk_score": 92,
                "flags": ["new_account", "thin_file", "rapid_escalation"],
                "prior_sar_count": 0,
                "average_monthly_balance": 800,
                "activity_inconsistent_with_profile": True,
            },
            "recommendation": "ESCALATE — high risk score, rapid escalation from thin file to high spend",
        },
        "kyc_specialist": {
            "agent_role": "kyc_specialist",
            "case_id": "CASE-003",
            "findings": {
                "kyc_status": "passed",
                "ofac_match": False,
                "pep_match": False,
                "adverse_media": False,
                "ssn_collision": True,
                "ssn_collision_date": "2025-11-03",
                "ssn_collision_name": "David R. Forsyth",
                "synthetic_identity_flag": True,
            },
            "recommendation": "ESCALATE — SSN collision with prior declined application under different name. "
                              "High confidence synthetic identity.",
        },
    },
    "CASE-004": {
        "transaction_analyst": {
            "agent_role": "transaction_analyst",
            "case_id": "CASE-004",
            "findings": {
                "pattern": "elder_fund_diversion",
                "transfer_count": 5,
                "cumulative_transfers": 34500,
                "new_payee": "K. Whitfield Personal",
                "days_since_signer_added": 11,
                "prior_comparable_activity": False,
            },
            "recommendation": "ESCALATE — sustained transfers to a newly added payee, zero precedent in 25-year history",
        },
        "account_profiler": {
            "agent_role": "account_profiler",
            "case_id": "CASE-004",
            "findings": {
                "account_tenure_days": 9089,
                "risk_score": 68,
                "flags": ["elder_customer", "new_authorized_signer"],
                "prior_sar_count": 0,
                "average_monthly_balance": 6200,
                "activity_inconsistent_with_profile": True,
            },
            "recommendation": "ESCALATE — new authorized signer plus fund diversion on an elder customer's account",
        },
        "kyc_specialist": {
            "agent_role": "kyc_specialist",
            "case_id": "CASE-004",
            "findings": {
                "kyc_status": "passed",
                "ofac_match": False,
                "pep_match": False,
                "adverse_media": False,
                "authorized_signer_added": "2026-03-17",
                "authorized_signer_name": "Kevin Whitfield",
            },
            "recommendation": "ESCALATE — account holder's own identity is not in question; concern is "
                              "exploitation by the newly authorized signer, warranting an APS referral",
        },
    },
    "CASE-005": {
        "transaction_analyst": {
            "agent_role": "transaction_analyst",
            "case_id": "CASE-005",
            "findings": {
                "pattern": "money_mule_check_kiting",
                "check_deposit_count": 5,
                "total_checks_7d": 42000,
                "distinct_remitters": 5,
                "withdrawn_before_hold_release": True,
            },
            "recommendation": "ESCALATE — check-kiting signature: deposit then withdraw before hold release, repeated 5x",
        },
        "account_profiler": {
            "agent_role": "account_profiler",
            "case_id": "CASE-005",
            "findings": {
                "account_tenure_days": 178,
                "risk_score": 81,
                "flags": ["short_tenure", "third_party_deposits"],
                "prior_sar_count": 0,
                "average_monthly_balance": 1100,
                "activity_inconsistent_with_profile": True,
            },
            "recommendation": "ESCALATE — short-tenure, low-balance account suddenly moving $40K+ in a week",
        },
        "kyc_specialist": {
            "agent_role": "kyc_specialist",
            "case_id": "CASE-005",
            "findings": {
                "kyc_status": "passed",
                "ofac_match": False,
                "pep_match": False,
                "adverse_media": False,
                "remitters_related_to_holder": False,
            },
            "recommendation": "ESCALATE — account holder's identity is clean; five unrelated remitters "
                              "with no apparent relationship to the holder is the mule signature, not an ID issue",
        },
    },
}

# ---------------------------------------------------------------------------
# Watchlist / sanctions data (partial — only what's relevant to these cases)
# ---------------------------------------------------------------------------

WATCHLIST_ENTRIES = [
    {
        "list": "OFAC_SDN",
        "name": "Marcus T. Webb",
        "match_score": 0.0,    # No match for ACC_8821
        "notes": "No SDN match found.",
    },
    {
        "list": "OFAC_SDN",
        "name": "Elena Vostrikova",
        "match_score": 0.0,    # No match for ACC_3347
        "notes": "No SDN match found.",
    },
    {
        "list": "OFAC_SDN",
        "name": "Daniel R. Forsythe",
        "match_score": 0.0,    # No match for ACC_5590
        "notes": "No SDN match. However, name variant 'David R. Forsyth' not in SDN.",
    },
    {
        "list": "OFAC_SDN",
        "name": "Eleanor J. Whitfield",
        "match_score": 0.0,    # No match for ACC_6634
        "notes": "No SDN match found.",
    },
    {
        "list": "OFAC_SDN",
        "name": "Jamal K. Reyes",
        "match_score": 0.0,    # No match for ACC_7743
        "notes": "No SDN match found.",
    },
]

# ---------------------------------------------------------------------------
# Expected outcomes (ground truth for testing)
# ---------------------------------------------------------------------------

EXPECTED_OUTCOMES = {
    "CASE-001": {
        "case_id": "CASE-001",
        "account_id": "ACC_8821",
        "fraud_type": "structuring / money laundering",
        "expected_sar": True,
        "expected_account_action": "freeze_and_report",
        "regulatory_obligation": "BSA / FinCEN SAR within 30 days of detection",
        "key_evidence": [
            "12 cash deposits under $10,000 CTR threshold over 8 days",
            "Cumulative deposits of $112,500 followed immediately by BVI wire",
            "Account only 77 days old — activity vastly inconsistent with profile",
        ],
    },
    "CASE-002": {
        "case_id": "CASE-002",
        "account_id": "ACC_3347",
        "fraud_type": "account takeover",
        "expected_sar": False,      # ATO — contact customer first, SAR if confirmed unauthorized
        "expected_account_action": "freeze_pending_customer_contact",
        "regulatory_obligation": "Reg E dispute investigation within 10 business days if customer confirms",
        "key_evidence": [
            "Impossible travel: Austin TX → Miami FL → New York NY in 97 minutes",
            "All activity from unrecognized device DEV_NEW_9921",
            "$16,100 debits in 4 hours vs. $380 daily average",
        ],
    },
    "CASE-003": {
        "case_id": "CASE-003",
        "account_id": "ACC_5590",
        "fraud_type": "synthetic identity / bust-out",
        "expected_sar": True,
        "expected_account_action": "close_and_report",
        "regulatory_obligation": "BSA / FinCEN SAR; potential referral to law enforcement",
        "key_evidence": [
            "SSN collision with prior declined application under different name",
            "$25,100 purchases in 38 days from thin-file account ending in NSF",
            "Merchant concentration in liquidable goods (electronics, bulk retail)",
        ],
    },
    "CASE-004": {
        "case_id": "CASE-004",
        "account_id": "ACC_6634",
        "fraud_type": "elder financial exploitation",
        "expected_sar": True,
        "expected_account_action": "freeze_and_adult_protective_services_referral",
        "regulatory_obligation": "BSA / FinCEN SAR (see FinCEN FIN-2022-A002 elder exploitation "
                                 "advisory); state Adult Protective Services referral",
        "key_evidence": [
            "New authorized signer added 2026-03-17 with zero prior history on the account",
            "$34,500 transferred to that signer's personal account within 11 days",
            "25-year account with no comparable activity anywhere in its history",
        ],
    },
    "CASE-005": {
        "case_id": "CASE-005",
        "account_id": "ACC_7743",
        "fraud_type": "money mule / check kiting",
        "expected_sar": True,
        "expected_account_action": "freeze_pending_investigation",
        "regulatory_obligation": "BSA / FinCEN SAR; potential referral if account holder was "
                                 "recruited via a job or romance scam",
        "key_evidence": [
            "5 third-party check deposits from unrelated remitters totaling $42,000 in 7 days",
            "Each deposit withdrawn same-day, before standard hold periods release",
            "Recently opened, low-balance account inconsistent with this volume of activity",
        ],
    },
}


# ---------------------------------------------------------------------------
# Convenience accessors for the demo
# ---------------------------------------------------------------------------

def get_fraud_alert(case_id: str) -> dict:
    """Return the fraud alert for a given case."""
    return next((a for a in FRAUD_ALERTS if a["case_id"] == case_id), {})


def get_transactions(account_id: str) -> list[dict]:
    """Return all transactions for an account, sorted by date."""
    return sorted(
        [t for t in TRANSACTIONS if t["account_id"] == account_id],
        key=lambda t: t["date"],
    )


def get_account(account_id: str) -> dict:
    """Return account record."""
    return ACCOUNTS.get(account_id, {})


def get_kyc(account_id: str) -> dict:
    """Return KYC record for an account."""
    return KYC_RECORDS.get(account_id, {})


def get_agent_outputs(case_id: str) -> dict:
    """Return processed agent outputs for a case (what sar_generator can access)."""
    return AGENT_OUTPUTS.get(case_id, {})


def get_expected_outcome(case_id: str) -> dict:
    """Return ground truth for test assertions."""
    return EXPECTED_OUTCOMES.get(case_id, {})


def summarize_transactions(account_id: str) -> dict:
    """
    Return a structured summary of transaction activity — what transaction_analyst surfaces.
    Does NOT include identity fields — safe for transaction_analyst role.
    """
    txns = get_transactions(account_id)
    deposits = [t for t in txns if t["amount"] > 0]
    debits   = [t for t in txns if t["amount"] < 0]
    return {
        "account_id":      account_id,
        "total_txns":      len(txns),
        "total_deposits":  sum(t["amount"] for t in deposits),
        "total_debits":    sum(t["amount"] for t in debits),
        "largest_deposit": max((t["amount"] for t in deposits), default=0),
        "largest_debit":   min((t["amount"] for t in debits), default=0),
        "transactions":    txns,
    }
