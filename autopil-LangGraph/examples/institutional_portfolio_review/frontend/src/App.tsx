import { useEffect, useState } from "react";
import { LogoMark } from "./LogoMark";
import DescriptionTab from "./DescriptionTab";
import ExecutionTab from "./ExecutionTab";
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

const THEME_KEY = "autopil_portfolio_review_demo_theme";

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

type Tab = "description" | "execution";

export default function App() {
  const serverConnected = useServerStatus();
  const [theme, toggleTheme] = useTheme();
  const [tab, setTab] = useState<Tab>("description");

  return (
    <div className="app-shell">
      <header className="header">
        <div className="logo">
          <div className="logo-mark"><LogoMark id="portfolio-review-demo" /></div>
          <div>
            <div className="logo-name">Auto<span className="accent">PIL</span></div>
            <div className="logo-sub">Institutional Portfolio Review</div>
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

      <nav className="tab-nav">
        <button className={`tab ${tab === "description" ? "active" : ""}`} onClick={() => setTab("description")}>
          Description
        </button>
        <button className={`tab ${tab === "execution" ? "active" : ""}`} onClick={() => setTab("execution")}>
          Execution
        </button>
      </nav>

      <main className="main">
        {tab === "description" ? <DescriptionTab /> : <ExecutionTab />}
      </main>

      <footer className="footer">
        <span>AutoPIL × LangGraph — 11-role institutional portfolio review demo (Databricks Unity Catalog)</span>
        <span>autopil.ai</span>
      </footer>
    </div>
  );
}
