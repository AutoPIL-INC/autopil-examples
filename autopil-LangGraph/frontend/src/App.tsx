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
import { INDUSTRIES } from "./industries";
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
    () => (localStorage.getItem(THEME_KEY) as "dark" | "light") ?? "dark",
  );

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  return [theme, () => setTheme((t) => (t === "dark" ? "light" : "dark"))] as const;
}

type Demo = "fraud" | "client_analysis" | "institutional_portfolio_review" | "aml_compliance" | "splunk_secops";
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
};

export default function App() {
  const serverConnected = useServerStatus();
  const [theme, toggleTheme] = useTheme();
  const [demo, setDemo] = useState<Demo>("fraud");
  const [tab, setTab] = useState<Tab>("description");
  // Industry context only — see industries.ts. Doesn't drive which demo tabs show
  // below; only "financial_services" has demos behind it today, so it's the only
  // enabled option. Not persisted: nothing downstream reads it yet.
  const [industry, setIndustry] = useState<string>("financial_services");

  const active = DEMOS[demo];
  const { Description } = active;

  const selectDemo = (next: Demo) => {
    setDemo(next);
    setTab("description");
  };

  return (
    <div className="app-shell">
      <header className="header">
        <div className="logo">
          <div className="logo-mark"><LogoMark id="autopil-demos" /></div>
          <div>
            <div className="logo-name">Auto<span className="accent">PIL</span></div>
            <select
              className="industry-select"
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              title="Industry (context only — doesn't change which demo tabs show below)"
            >
              {INDUSTRIES.map((ind) => (
                <option key={ind.value} value={ind.value} disabled={!ind.enabled}>
                  {ind.label} — {ind.company} Demo{!ind.enabled ? " (coming soon)" : ""}
                </option>
              ))}
            </select>
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
          {(Object.keys(DEMOS) as Demo[]).map((key) => (
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
