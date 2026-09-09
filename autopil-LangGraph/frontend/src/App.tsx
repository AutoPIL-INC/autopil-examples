import { useEffect, useState, type ComponentType } from "react";
import { LogoMark } from "./LogoMark";
import FraudDescriptionTab from "./demos/fraud/DescriptionTab";
import FraudExecutionTab from "./demos/fraud/ExecutionTab";
import ClientAnalysisDescriptionTab from "./demos/client_analysis/DescriptionTab";
import ClientAnalysisExecutionTab from "./demos/client_analysis/ExecutionTab";
import PortfolioReviewDescriptionTab from "./demos/institutional_portfolio_review/DescriptionTab";
import PortfolioReviewExecutionTab from "./demos/institutional_portfolio_review/ExecutionTab";
import AmlComplianceDescriptionTab from "./demos/aml_compliance/DescriptionTab";
import AmlComplianceExecutionTab from "./demos/aml_compliance/ExecutionTab";
import SplunkSecopsDescriptionTab from "./demos/splunk_secops/DescriptionTab";
import SplunkSecopsExecutionTab from "./demos/splunk_secops/ExecutionTab";
import HospitalRevenueCycleDescriptionTab from "./demos/hospital_revenue_cycle/DescriptionTab";
import HospitalRevenueCycleExecutionTab from "./demos/hospital_revenue_cycle/ExecutionTab";
import CareCoordinationDescriptionTab from "./demos/care_coordination/DescriptionTab";
import CareCoordinationExecutionTab from "./demos/care_coordination/ExecutionTab";
import QualityControlDescriptionTab from "./demos/quality_control/DescriptionTab";
import QualityControlExecutionTab from "./demos/quality_control/ExecutionTab";
import TradingDeskOpsDescriptionTab from "./demos/trading_desk_ops/DescriptionTab";
import TradingDeskOpsExecutionTab from "./demos/trading_desk_ops/ExecutionTab";
import { INDUSTRIES } from "./industries";
import { INDUSTRY_ICONS } from "./industryIcons";
import "./App.css";

const API_URL = "http://localhost:2024";

// Equities and Fixed Income are one shared graph/policy on the backend (see
// trading_desk_ops's own CLAUDE.md section) but two distinct sidebar use cases here —
// same Description/Execution components, just parameterized by domain, so the case
// queue and copy for one domain never mixes with the other's.
const TradingDeskOpsEquitiesDescriptionTab = () => <TradingDeskOpsDescriptionTab domain="equities" />;
const TradingDeskOpsEquitiesExecutionTab = () => <TradingDeskOpsExecutionTab domain="equities" />;
const TradingDeskOpsFixedIncomeDescriptionTab = () => <TradingDeskOpsDescriptionTab domain="fixed_income" />;
const TradingDeskOpsFixedIncomeExecutionTab = () => <TradingDeskOpsExecutionTab domain="fixed_income" />;

function useServerStatus() {
  const [connected, setConnected] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    const check = () => {
      fetch(`${API_URL}/ok`)
        .then((r) => { if (!cancelled) setConnected(r.ok); })
        .catch(() => { if (!cancelled) setConnected(false); });
    };
    check();
    const id = setInterval(check, 5000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  return connected;
}

const THEME_KEY = "autopil_demos_theme";

function useTheme() {
  const [theme, setTheme] = useState<"dark" | "light">(
    () => (localStorage.getItem(THEME_KEY) as "dark" | "light") ?? "light",
  );

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  return [theme, () => setTheme((t) => (t === "dark" ? "light" : "dark"))] as const;
}

type Demo = "fraud" | "client_analysis" | "institutional_portfolio_review" | "aml_compliance" | "splunk_secops" | "hospital_revenue_cycle" | "care_coordination" | "quality_control" | "trading_desk_ops_equities" | "trading_desk_ops_fixed_income";
type Tab = "description" | "execution";

// Sidebar grouping: every key listed together here renders as indented sub-items
// under one collapsible parent header instead of its own flat top-level entry. Every
// other demo is unaffected — this is additive, not a sidebar redesign.
const SIDEBAR_GROUPS: Array<{ label: string; keys: Demo[] }> = [
  { label: "Trading Desk Ops", keys: ["trading_desk_ops_equities", "trading_desk_ops_fixed_income"] },
];

const DEMOS: Record<Demo, { label: string; Description: ComponentType; Execution: ComponentType }> = {
  fraud: {
    label: "Fraud Investigation",
    Description: FraudDescriptionTab,
    Execution: FraudExecutionTab,
  },
  client_analysis: {
    label: "Client Analysis",
    Description: ClientAnalysisDescriptionTab,
    Execution: ClientAnalysisExecutionTab,
  },
  institutional_portfolio_review: {
    label: "Institutional Portfolio Review",
    Description: PortfolioReviewDescriptionTab,
    Execution: PortfolioReviewExecutionTab,
  },
  aml_compliance: {
    label: "AML & Compliance",
    Description: AmlComplianceDescriptionTab,
    Execution: AmlComplianceExecutionTab,
  },
  splunk_secops: {
    label: "SOC / Splunk SecOps",
    Description: SplunkSecopsDescriptionTab,
    Execution: SplunkSecopsExecutionTab,
  },
  hospital_revenue_cycle: {
    label: "Hospital Revenue Cycle",
    Description: HospitalRevenueCycleDescriptionTab,
    Execution: HospitalRevenueCycleExecutionTab,
  },
  care_coordination: {
    label: "Care Coordination",
    Description: CareCoordinationDescriptionTab,
    Execution: CareCoordinationExecutionTab,
  },
  quality_control: {
    label: "Quality Control",
    Description: QualityControlDescriptionTab,
    Execution: QualityControlExecutionTab,
  },
  trading_desk_ops_equities: {
    label: "Equities",
    Description: TradingDeskOpsEquitiesDescriptionTab,
    Execution: TradingDeskOpsEquitiesExecutionTab,
  },
  trading_desk_ops_fixed_income: {
    label: "Fixed Income",
    Description: TradingDeskOpsFixedIncomeDescriptionTab,
    Execution: TradingDeskOpsFixedIncomeExecutionTab,
  },
};

export default function App() {
  const serverConnected = useServerStatus();
  const [theme, toggleTheme] = useTheme();
  const [demo, setDemo] = useState<Demo>("fraud");
  const [tab, setTab] = useState<Tab>("description");
  // Drives which demos the sidebar shows — see industries.ts's `demos` field per
  // industry. Not persisted: nothing outside this component reads it.
  const [industry, setIndustry] = useState<string>("financial_services");
  // Which SIDEBAR_GROUPS are expanded. selectDemo() below auto-expands a group when
  // one of its own sub-items becomes active, so picking a demo directly (e.g. from a
  // future deep link) never leaves its group collapsed around it.
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  const active = DEMOS[demo];
  const { Description } = active;

  const visibleDemoKeys = (INDUSTRIES.find((i) => i.value === industry)?.demos ?? []) as Demo[];

  const selectDemo = (next: Demo) => {
    setDemo(next);
    setTab("description");
    const group = SIDEBAR_GROUPS.find((g) => g.keys.includes(next));
    if (group) setExpandedGroups((prev) => new Set(prev).add(group.label));
  };

  const toggleGroup = (label: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
  };

  const selectIndustry = (next: string) => {
    setIndustry(next);
    const demosForIndustry = INDUSTRIES.find((i) => i.value === next)?.demos ?? [];
    // Switch to that industry's first demo if the currently-selected one isn't in it
    // — otherwise the sidebar would filter down while still showing a demo that's no
    // longer in the visible list.
    if (!demosForIndustry.includes(demo) && demosForIndustry.length > 0) {
      selectDemo(demosForIndustry[0] as Demo);
    }
  };

  return (
    <div className="app-shell">
      <header className="header">
        <div className="logo">
          <div className="logo-mark"><LogoMark id="autopil-demos" /></div>
          <div>
            <div className="logo-name">Auto<span className="accent">PIL</span></div>
            <div className="industry-row">
              <span className="industry-icon">{INDUSTRY_ICONS[industry]}</span>
              <select
                className="industry-select"
                value={industry}
                onChange={(e) => selectIndustry(e.target.value)}
                title="Industry — filters which use cases show in the sidebar"
              >
                {INDUSTRIES.map((ind) => (
                  <option key={ind.value} value={ind.value} disabled={!ind.enabled}>
                    {ind.label} — {ind.company} Demo{!ind.enabled ? " (coming soon)" : ""}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
        <div className="header-right">
          <span className="server-label">langgraph dev :2024</span>
          <div
            className={`status-dot${serverConnected === false ? " err" : ""}`}
            title={serverConnected === false ? "Server unreachable" : "Server connected"}
          />
          <button className="theme-toggle" onClick={toggleTheme} title="Toggle theme">
            {theme === "dark" ? "◑ Light" : "◐ Dark"}
          </button>
        </div>
      </header>

      <div className="body-layout">
        <aside className="sidebar">
          <div className="sidebar-title">Use Cases</div>
          {(() => {
            const renderedGroups = new Set<string>();
            return visibleDemoKeys.map((key) => {
              const group = SIDEBAR_GROUPS.find((g) => g.keys.includes(key));
              if (group == null) {
                return (
                  <button
                    key={key}
                    className={`sidebar-item ${demo === key ? "active" : ""}`}
                    onClick={() => selectDemo(key)}
                  >
                    {DEMOS[key].label}
                  </button>
                );
              }
              // A group can list keys the current industry doesn't show — render it
              // once, using only its members that are actually visible right now.
              if (renderedGroups.has(group.label)) return null;
              renderedGroups.add(group.label);
              const groupKeys = group.keys.filter((k) => visibleDemoKeys.includes(k));
              const expanded = expandedGroups.has(group.label) || groupKeys.includes(demo);
              return (
                <div key={group.label} className="sidebar-group">
                  <button
                    className="sidebar-item sidebar-group-header"
                    onClick={() => toggleGroup(group.label)}
                  >
                    <span className={`sidebar-group-caret ${expanded ? "expanded" : ""}`}>▸</span>
                    {group.label}
                  </button>
                  {expanded &&
                    groupKeys.map((k) => (
                      <button
                        key={k}
                        className={`sidebar-item sidebar-subitem ${demo === k ? "active" : ""}`}
                        onClick={() => selectDemo(k)}
                      >
                        {DEMOS[k].label}
                      </button>
                    ))}
                </div>
              );
            });
          })()}
        </aside>

        <div className="content-area">
          <nav className="tab-nav">
            <button className={`tab ${tab === "description" ? "active" : ""}`} onClick={() => setTab("description")}>
              Description
            </button>
            <button className={`tab ${tab === "execution" ? "active" : ""}`} onClick={() => setTab("execution")}>
              Execution
            </button>
          </nav>

          <main className="main">
            {tab === "description" && <Description />}
            {(Object.keys(DEMOS) as Demo[]).map((key) => {
              const { Execution } = DEMOS[key];
              return (
                <div key={key} style={{ display: tab === "execution" && demo === key ? "block" : "none" }}>
                  <Execution />
                </div>
              );
            })}
          </main>
        </div>
      </div>

      <footer className="footer">
        <span>AutoPIL × LangGraph — reasoning-driven governance demos</span>
        <span>autopil.ai</span>
      </footer>
    </div>
  );
}
