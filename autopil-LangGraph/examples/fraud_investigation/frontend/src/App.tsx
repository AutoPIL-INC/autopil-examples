import { useEffect, useRef, useState } from "react";
import { useStream } from "@langchain/langgraph-sdk/react";
import {
  CASE_IDS,
  OVERRIDE_ACTIONS,
  initialInput,
  type FeedEvent,
  type InterruptPayload,
  type InvestigationState,
} from "./types";
import "./App.css";

const API_URL = "http://localhost:2024";

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
  const feedEndRef = useRef<HTMLDivElement>(null);

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
    stream.submit(initialInput(caseId), { streamMode: ["custom"] });
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
    <div className="app">
      <header className="app-header">
        <h1>AutoPIL × LangGraph — Fraud Investigation Live Feed</h1>
        <p>Live AutoPIL audit trail as each specialist agent reasons and calls tools.</p>
      </header>

      <div className="case-picker">
        {CASE_IDS.map((caseId) => (
          <button key={caseId} onClick={() => runCase(caseId)} disabled={stream.isLoading || !!interruptPayload}>
            Run {caseId}
          </button>
        ))}
        {stream.isLoading && <span className="running-indicator">running…</span>}
      </div>

      {interruptPayload && (
        <ReviewPanel payload={interruptPayload} onApprove={approve} onOverride={override} />
      )}

      {disposition && <DispositionBanner event={disposition} />}

      <div className="feed">
        {feed.length === 0 && !stream.isLoading && (
          <p className="feed-empty">Pick a case above to start a live run.</p>
        )}
        {feed.map((event, i) => <FeedItem key={i} event={event} />)}
        <div ref={feedEndRef} />
      </div>
    </div>
  );
}
