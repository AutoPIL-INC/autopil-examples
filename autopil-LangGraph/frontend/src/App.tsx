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

type Demo = "fraud" | "client_analysis" | "institutional_portfolio_review" | "aml_compliance";
type Tab = "description" | "execution";

const DEMOS: Record<Demo, { label: string; sub: string; Description: ComponentType; Execution: ComponentType }> = {
  fraud: {
    label: "Fraud Investigation",
    sub: "Fraud Investigation",
    Description: FraudDescriptionTab,
    Execution: FraudExecutionTab,
  },
  client_analysis: {
    label: "Client Analysis",
    sub: "Client Analysis",
    Description: ClientAnalysisDescriptionTab,
    Execution: ClientAnalysisExecutionTab,
  },
  institutional_portfolio_review: {
    label: "Institutional Portfolio Review",
    sub: "Institutional Portfolio Review",
    Description: PortfolioReviewDescriptionTab,
    Execution: PortfolioReviewExecutionTab,
  },
  aml_compliance: {
    label: "AML & Compliance",
    sub: "AML & Compliance",
    Description: AmlComplianceDescriptionTab,
    Execution: AmlComplianceExecutionTab,
  },
};

export default function App() {
  const serverConnected = useServerStatus();
  const [theme, toggleTheme] = useTheme();
  const [demo, setDemo] = useState<Demo>("fraud");
  const [tab, setTab] = useState<Tab>("description");

  const active = DEMOS[demo];
  const { Description, Execution } = active;

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
            <div className="logo-sub">{active.sub}</div>
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

      <nav className="tab-nav tab-nav-demos">
        {(Object.keys(DEMOS) as Demo[]).map((key) => (
          <button
            key={key}
            className={`tab ${demo === key ? "active" : ""}`}
            onClick={() => selectDemo(key)}
          >
            {DEMOS[key].label}
          </button>
        ))}
      </nav>

      <nav className="tab-nav">
        <button className={`tab ${tab === "description" ? "active" : ""}`} onClick={() => setTab("description")}>
          Description
        </button>
        <button className={`tab ${tab === "execution" ? "active" : ""}`} onClick={() => setTab("execution")}>
          Execution
        </button>
      </nav>

      <main className="main">
        {tab === "description" ? <Description /> : <Execution />}
      </main>

      <footer className="footer">
        <span>AutoPIL × LangGraph — reasoning-driven governance demos</span>
        <span>autopil.ai</span>
      </footer>
    </div>
  );
}
