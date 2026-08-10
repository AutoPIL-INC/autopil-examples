// AutoPIL.ai's industry coverage (see autopil.ai/industries), each paired with a
// fictional example company for display — none of these are real AutoPIL customers.
// Only Financial Services has demos behind it in this repo (fraud_investigation,
// client_analysis, institutional_portfolio_review, aml_compliance, and splunk_secops
// — the latter's mainframe scenarios are core-banking/card-auth/general-ledger
// workloads, not a distinct vertical, despite living in a security-ops-flavored demo).
// Every other entry is disabled until a demo exists for it — picking one here doesn't
// change which demo tabs are shown (see the demo tab row below the header for that);
// this is industry context only, not a filter.
export type Industry = {
  value: string;
  label: string;
  company: string;
  enabled: boolean;
};

export const INDUSTRIES: Industry[] = [
  { value: "financial_services", label: "Financial Services", company: "Meridian Bank", enabled: true },
  { value: "healthcare", label: "Healthcare", company: "Alden Health Partners", enabled: false },
  { value: "telecom", label: "Telecom", company: "Northbridge Telecom", enabled: false },
  { value: "logistics", label: "Logistics", company: "Vantage Freight Systems", enabled: false },
  { value: "insurance", label: "Insurance", company: "Harborstone Insurance", enabled: false },
  { value: "retail", label: "Retail", company: "Cobalt Retail Group", enabled: false },
  { value: "energy", label: "Energy", company: "Solace Energy", enabled: false },
  { value: "manufacturing", label: "Manufacturing", company: "Ironview Manufacturing", enabled: false },
  { value: "real_estate", label: "Real Estate", company: "Willowmark Realty", enabled: false },
  { value: "pharmacy", label: "Pharmacy", company: "Cascade Pharmacy Network", enabled: false },
  { value: "public_sector", label: "Public Sector", company: "Civic Digital Services", enabled: false },
  { value: "technology", label: "Technology", company: "Fernwood Technologies", enabled: false },
];
