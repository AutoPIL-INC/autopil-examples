// AutoPIL.ai's industry coverage (see autopil.ai/industries), each paired with a
// fictional example company for display — none of these are real AutoPIL customers.
// `demos` lists which of App.tsx's DEMOS keys belong to that industry — the sidebar
// filters to just that list when an industry is selected (see App.tsx's `visibleDemos`).
// Every entry below `enabled: false` has an empty `demos` list and is shown
// "(coming soon)" in the dropdown — there's nothing to filter to yet.
export type Industry = {
  value: string;
  label: string;
  company: string;
  enabled: boolean;
  demos: string[];
};

export const INDUSTRIES: Industry[] = [
  {
    value: "financial_services", label: "Financial Services", company: "Meridian Bank", enabled: true,
    // splunk_secops's mainframe scenarios are core-banking/card-auth/general-ledger
    // workloads, not a distinct vertical, despite living in a security-ops-flavored demo.
    demos: ["fraud", "client_analysis", "institutional_portfolio_review", "aml_compliance", "splunk_secops"],
  },
  {
    value: "healthcare", label: "Healthcare", company: "Alden Health Partners", enabled: true,
    demos: ["hospital_revenue_cycle"],
  },
  { value: "telecom", label: "Telecom", company: "Northbridge Telecom", enabled: false, demos: [] },
  { value: "logistics", label: "Logistics", company: "Vantage Freight Systems", enabled: false, demos: [] },
  { value: "insurance", label: "Insurance", company: "Harborstone Insurance", enabled: false, demos: [] },
  { value: "retail", label: "Retail", company: "Cobalt Retail Group", enabled: false, demos: [] },
  { value: "energy", label: "Energy", company: "Solace Energy", enabled: false, demos: [] },
  { value: "manufacturing", label: "Manufacturing", company: "Ironview Manufacturing", enabled: false, demos: [] },
  { value: "real_estate", label: "Real Estate", company: "Willowmark Realty", enabled: false, demos: [] },
  { value: "pharmacy", label: "Pharmacy", company: "Cascade Pharmacy Network", enabled: false, demos: [] },
  { value: "public_sector", label: "Public Sector", company: "Civic Digital Services", enabled: false, demos: [] },
  { value: "technology", label: "Technology", company: "Fernwood Technologies", enabled: false, demos: [] },
];
