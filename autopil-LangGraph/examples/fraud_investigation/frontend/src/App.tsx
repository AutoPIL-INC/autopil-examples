import { useEffect, useRef, useState } from "react";
import { useStream } from "@langchain/langgraph-sdk/react";
import { LogoMark } from "./LogoMark";
import {
  CASE_IDS,
  CASE_INFO,
  OVERRIDE_ACTIONS,
  PROVIDERS,
  initialInput,
  type FeedEvent,
  type InterruptPayload,
  type InvestigationState,
} from "./types";
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

const THEME_KEY = "autopil_fraud_demo_theme";

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

function ToolCallRow({ event }: { event: FeedEvent & { type: "tool_call" } }) {
  const denied = event.status === "denied";
  return (
    <div className={`feed-row ${denied ? "denied" : "allowed"}`}>
      <span className="feed-badge">{denied ? "DENIED" : "ALLOWED"}</span>
      <span className="feed-role">{event.role}</span>
      <span className="feed-body">
        {event.tool}
        {event.key ? `(${event.key})` : "()"}
      </span>
      {denied && <div className="feed-reason">{event.reason}</div>}
    </div>
  );
}

function RoutingRow({ event }: { event: FeedEvent & { type: "routing" } }) {
  return (
    <div className="feed-row routing">
      <span className="feed-badge">ROUTE</span>
      <span className="feed-body">
        {event.stage === "initial"
          ? `orchestrator → ${event.route?.join(", ")}`
          : `orchestrator review → ${event.next}`}
      </span>
      {event.reason && <div className="feed-reason">{event.reason}</div>}
    </div>
  );
}

function FindingRow({ event }: { event: FeedEvent & { type: "finding" } }) {
  return (
    <div className="feed-row finding">
      <span className="feed-badge">FINDING</span>
      <span className="feed-role">{event.role}</span>
      <span className="feed-body">{event.finding.recommendation}</span>
      {event.finding.summary && <div className="feed-reason">{event.finding.summary}</div>}
    </div>
  );
}

function DispositionBanner({ event }: { event: FeedEvent & { type: "disposition" } }) {
  return (
    <div className="disposition-banner">
      <div className="disposition-action">{event.action}</div>
      <div className="disposition-review">
        {event.human_approved
          ? "✓ Approved by reviewer"
          : `⚠ Overridden by reviewer (proposed: ${event.proposed_action})`}
        {event.human_notes && ` — ${event.human_notes}`}
      </div>
      <div className="disposition-meta">
        {event.case_id} · specialists run: {event.specialists_run.join(", ")} · denials: {event.denial_count}
        {" · "}
        audit trail: {event.audit_summary.allowed} allowed / {event.audit_summary.denied} denied
        {" ("}
        {event.audit_summary.total} events)
      </div>
    </div>
  );
}

function ReviewPanel({
  payload,
  onApprove,
  onOverride,
}: {
  payload: InterruptPayload;
  onApprove: () => void;
  onOverride: (action: string, notes: string) => void;
}) {
  const [overriding, setOverriding] = useState(false);
  const [overrideAction, setOverrideAction] = useState<string>(OVERRIDE_ACTIONS[0]);
  const [notes, setNotes] = useState("");

  return (
    <div className="review-panel">
      <div className="review-header">Awaiting compliance review — {payload.case_id}</div>
      <div className="review-proposed">Proposed: {payload.proposed_action}</div>
      <div className="review-meta">
        specialists run: {payload.specialists_run.join(", ")} · denials: {payload.denial_log.length}
      </div>

      {!overriding ? (
        <div className="review-actions">
          <button className="approve" onClick={onApprove}>Approve</button>
          <button className="override" onClick={() => setOverriding(true)}>Override…</button>
        </div>
      ) : (
        <div className="review-override-form">
          <select value={overrideAction} onChange={(e) => setOverrideAction(e.target.value)}>
            {OVERRIDE_ACTIONS.map((action) => (
              <option key={action} value={action}>{action}</option>
            ))}
          </select>
          <textarea
            placeholder="Notes (optional)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
          <div className="review-actions">
            <button className="override" onClick={() => onOverride(overrideAction, notes)}>
              Submit override
            </button>
            <button onClick={() => setOverriding(false)}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}

function CaseCard({
  caseId,
  active,
  disabled,
  onRun,
}: {
  caseId: (typeof CASE_IDS)[number];
  active: boolean;
  disabled: boolean;
  onRun: () => void;
}) {
  const info = CASE_INFO[caseId];
  return (
    <button
      className={`case-card ${active ? "active" : ""}`}
      onClick={onRun}
      disabled={disabled}
    >
      <div className="case-card-top">
        <span className="case-card-id">{caseId}</span>
        <span className="case-card-time">{info.estimatedTime}</span>
      </div>
      <div className="case-card-title">{info.title}</div>
      <div className="case-card-description">{info.description}</div>
      <div className="case-card-cta">{active ? "Running…" : "Run this case"}</div>
    </button>
  );
}

function FeedItem({ event }: { event: FeedEvent }) {
  switch (event.type) {
    case "tool_call":
      return <ToolCallRow event={event} />;
    case "routing":
      return <RoutingRow event={event} />;
    case "finding":
      return <FindingRow event={event} />;
    case "disposition":
      return null; // rendered separately as the banner
  }
}

export default function App() {
  const [feed, setFeed] = useState<FeedEvent[]>([]);
  const [disposition, setDisposition] = useState<(FeedEvent & { type: "disposition" }) | null>(null);
  const [provider, setProvider] = useState<string>(PROVIDERS[0].value);
  const [activeCase, setActiveCase] = useState<string | null>(null);
  const feedEndRef = useRef<HTMLDivElement>(null);
  const serverConnected = useServerStatus();
  const [theme, toggleTheme] = useTheme();

  const stream = useStream<InvestigationState>({
    apiUrl: API_URL,
    assistantId: "fraud_investigation",
    onCustomEvent: (data) => {
      const event = data as FeedEvent;
      setFeed((prev) => [...prev, event]);
      if (event.type === "disposition") setDisposition(event);
    },
  });
  const interruptPayload = stream.interrupt?.value as InterruptPayload | undefined;

  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [feed]);

  const runCase = (caseId: string) => {
    setFeed([]);
    setDisposition(null);
    setActiveCase(caseId);
    stream.submit(initialInput(caseId, provider), { streamMode: ["custom"] });
  };

  const approve = () => {
    stream.submit(undefined, { command: { resume: { approved: true } }, streamMode: ["custom"] });
  };

  const override = (overrideAction: string, notes: string) => {
    stream.submit(undefined, {
      command: { resume: { approved: false, override_action: overrideAction, notes } },
      streamMode: ["custom"],
    });
  };

  return (
    <div className="app-shell">
      <header className="header">
        <div className="logo">
          <div className="logo-mark"><LogoMark id="fraud-demo" /></div>
          <div>
            <div className="logo-name">Auto<span className="accent">PIL</span></div>
            <div className="logo-sub">Fraud Investigation — Live Feed</div>
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

      <main className="main">
        <div className="section-title">Model</div>
        <div className="provider-bar">
          <select
            id="provider-select"
            className="provider-select"
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            disabled={stream.isLoading || !!interruptPayload}
          >
            {PROVIDERS.map((p) => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
          {stream.isLoading && <span className="running-indicator">running…</span>}
        </div>

        <div className="section-title">Cases</div>
        <div className="case-grid">
          {CASE_IDS.map((caseId) => (
            <CaseCard
              key={caseId}
              caseId={caseId}
              active={activeCase === caseId && stream.isLoading}
              disabled={stream.isLoading || !!interruptPayload}
              onRun={() => runCase(caseId)}
            />
          ))}
        </div>

        {stream.error != null && (
          <div className="run-error">
            Run failed: {String((stream.error as { message?: string })?.message ?? stream.error)}
          </div>
        )}

        {interruptPayload && (
          <ReviewPanel payload={interruptPayload} onApprove={approve} onOverride={override} />
        )}

        {disposition && <DispositionBanner event={disposition} />}

        <div className="section-title">Live audit trail</div>
        <div className="feed table-card">
          {feed.length === 0 && !stream.isLoading && (
            <p className="feed-empty">Pick a case above to start a live run.</p>
          )}
          {feed.map((event, i) => <FeedItem key={i} event={event} />)}
          <div ref={feedEndRef} />
        </div>
      </main>

      <footer className="footer">
        <span>AutoPIL × LangGraph — reasoning-driven fraud investigation demo</span>
        <span>autopil.ai</span>
      </footer>
    </div>
  );
}
