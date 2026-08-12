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
import { INDUSTRIES } from "./industries";
import { INDUSTRY_ICONS } from "./industryIcons";
import "./App.css";

const API_URL = "http://localhost:2024";

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

type Demo = "fraud" | "client_analysis" | "institutional_portfolio_review" | "aml_compliance" | "splunk_secops" | "hospital_revenue_cycle";
type Tab = "description" | "execution";

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
};

export default function App() {
  const serverConnected = useServerStatus();
  const [theme, toggleTheme] = useTheme();
  const [demo, setDemo] = useState<Demo>("fraud");
  const [tab, setTab] = useState<Tab>("description");
  // Drives which demos the sidebar shows — see industries.ts's `demos` field per
  // industry. Not persisted: nothing outside this component reads it.
  const [industry, setIndustry] = useState<string>("financial_services");

  const active = DEMOS[demo];
  const { Description } = active;

  const visibleDemoKeys = (INDUSTRIES.find((i) => i.value === industry)?.demos ?? []) as Demo[];

  const selectDemo = (next: Demo) => {
    setDemo(next);
    setTab("description");
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
          {visibleDemoKeys.map((key) => (
            <button
              key={key}
              className={`sidebar-item ${demo === key ? "active" : ""}`}
              onClick={() => selectDemo(key)}
            >
              {DEMOS[key].label}
            </button>
          ))}
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
