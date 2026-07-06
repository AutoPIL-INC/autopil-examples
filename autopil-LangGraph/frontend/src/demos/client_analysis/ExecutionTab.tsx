import { useEffect, useRef, useState } from "react";
import { useStream } from "@langchain/langgraph-sdk/react";
import {
  REQUEST_IDS,
  REQUEST_INFO,
  PROVIDERS,
  initialInput,
  type FeedEvent,
  type GovernanceState,
} from "./types";

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
          ? `orchestrator → ${event.role} (task_type=${event.task_type})`
          : `orchestrator review → ${event.next}`}
      </span>
      {(event.reasoning || event.reason) && <div className="feed-reason">{event.reasoning ?? event.reason}</div>}
    </div>
  );
}

function FindingRow({ event }: { event: FeedEvent & { type: "finding" } }) {
  return (
    <div className="feed-row finding">
      <span className="feed-badge">FINDING</span>
      <span className="feed-role">{event.role}</span>
      <span className="feed-body">{event.finding.outcome}</span>
      {event.finding.summary && <div className="feed-reason">{event.finding.summary}</div>}
    </div>
  );
}

function DispositionBanner({ event }: { event: FeedEvent & { type: "disposition" } }) {
  return (
    <div className="disposition-banner">
      <div className="disposition-action">{event.outcome}</div>
      <div className="disposition-meta">
        {event.request_id} · roles: {event.roles_attempted.join(" → ")} · task_type: {event.task_type}
        {" · "}
        expected role: {event.expected_role} · denials: {event.denial_count}
        {" ("}
        {event.audit_summary.allowed} allowed / {event.audit_summary.denied} denied
        {" of "}
        {event.audit_summary.total} events)
      </div>
    </div>
  );
}

function RequestCard({
  requestId,
  active,
  disabled,
  onRun,
}: {
  requestId: (typeof REQUEST_IDS)[number];
  active: boolean;
  disabled: boolean;
  onRun: () => void;
}) {
  const info = REQUEST_INFO[requestId];
  return (
    <button
      className={`case-card ${active ? "active" : ""}`}
      onClick={onRun}
      disabled={disabled}
    >
      <div className="case-card-top">
        <span className="case-card-id">{requestId}</span>
        <span className="case-card-time">{info.estimatedTime}</span>
      </div>
      <div className="case-card-title">{info.title}</div>
      <div className="case-card-description">{info.description}</div>
      <div className="case-card-cta">{active ? "Running…" : "Run this request"}</div>
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

export default function ExecutionTab() {
  const [feed, setFeed] = useState<FeedEvent[]>([]);
  const [disposition, setDisposition] = useState<(FeedEvent & { type: "disposition" }) | null>(null);
  const [provider, setProvider] = useState<string>(PROVIDERS[0].value);
  const [activeRequest, setActiveRequest] = useState<string | null>(null);
  const feedEndRef = useRef<HTMLDivElement>(null);

  const stream = useStream<GovernanceState>({
    apiUrl: API_URL,
    assistantId: "client_analysis",
    onCustomEvent: (data) => {
      const event = data as FeedEvent;
      setFeed((prev) => [...prev, event]);
      if (event.type === "disposition") setDisposition(event);
    },
  });

  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [feed]);

  const runRequest = (requestId: string) => {
    setFeed([]);
    setDisposition(null);
    setActiveRequest(requestId);
    stream.submit(initialInput(requestId, provider), { streamMode: ["custom", "values"] });
  };

  return (
    <div className="execution-tab">
      <div className="section-title">Model</div>
      <div className="provider-bar">
        <select
          id="provider-select"
          className="provider-select"
          value={provider}
          onChange={(e) => setProvider(e.target.value)}
          disabled={stream.isLoading}
        >
          {PROVIDERS.map((p) => (
            <option key={p.value} value={p.value}>{p.label}</option>
          ))}
        </select>
        {stream.isLoading && <span className="running-indicator">running…</span>}
      </div>

      <div className="section-title">Requests</div>
      <div className="case-grid">
        {REQUEST_IDS.map((requestId) => (
          <RequestCard
            key={requestId}
            requestId={requestId}
            active={activeRequest === requestId && stream.isLoading}
            disabled={stream.isLoading}
            onRun={() => runRequest(requestId)}
          />
        ))}
      </div>

      {stream.error != null && (
        <div className="run-error">
          Run failed: {String((stream.error as { message?: string })?.message ?? stream.error)}
        </div>
      )}

      {disposition && <DispositionBanner event={disposition} />}

      <div className="section-title">Live audit trail</div>
      <div className="feed table-card">
        {feed.length === 0 && !stream.isLoading && (
          <p className="feed-empty">Pick a request above to start a live run.</p>
        )}
        {feed.map((event, i) => <FeedItem key={i} event={event} />)}
        <div ref={feedEndRef} />
      </div>
    </div>
  );
}
