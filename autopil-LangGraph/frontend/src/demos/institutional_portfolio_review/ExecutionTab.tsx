import { useEffect, useRef, useState } from "react";
import { useStream } from "@langchain/langgraph-sdk/react";
import {
  REQUEST_IDS,
  REQUEST_INFO,
  PROVIDERS,
  OVERRIDE_ACTIONS,
  initialInput,
  type FeedEvent,
  type InterruptPayload,
  type ReviewState,
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
          ? `orchestrator → ${event.review_type}  (plan: ${event.plan?.join(" → ")})`
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
      <div className={`disposition-review ${event.human_approved ? "approved" : "overridden"}`}>
        <strong>{event.human_approved ? "✓ Approved by reviewer" : "⚠ Overridden by reviewer"}</strong>
        {!event.human_approved && (
          <div className="disposition-proposed">Originally proposed: {event.proposed_outcome}</div>
        )}
        {event.human_notes && <div className="disposition-reason">Reviewer's reason: "{event.human_notes}"</div>}
      </div>
      <div className="disposition-meta">
        {event.request_id} · review_type: {event.review_type} · roles run: {event.roles_completed.join(" → ")}
        {event.escalated && " (escalated)"}
        {" · "}
        denials: {event.denial_count}
        {" ("}
        {event.audit_summary.allowed} allowed / {event.audit_summary.denied} denied
        {" of "}
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
  onApprove: (notes: string) => void;
  onOverride: (action: string, notes: string) => void;
}) {
  const [overriding, setOverriding] = useState(false);
  const [overrideAction, setOverrideAction] = useState<string>(OVERRIDE_ACTIONS[0]);
  const [notes, setNotes] = useState("");

  return (
    <div className="review-panel">
      <div className="review-header">Awaiting supervisor review — {payload.request_id}</div>
      <div className="review-proposed">Proposed: {payload.proposed_outcome}</div>
      <div className="review-meta">
        roles run: {payload.roles_completed.join(", ")} · denials: {payload.denial_log.length}
        {payload.escalated && " · escalated"}
      </div>

      <textarea
        className="review-notes"
        placeholder="Notes (optional) — recorded either way, in the final outcome"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
      />

      {!overriding ? (
        <div className="review-actions">
          <button className="approve" onClick={() => onApprove(notes)}>Approve</button>
          <button className="override" onClick={() => setOverriding(true)}>Override…</button>
        </div>
      ) : (
        <div className="review-override-form">
          <select value={overrideAction} onChange={(e) => setOverrideAction(e.target.value)}>
            {OVERRIDE_ACTIONS.map((action) => (
              <option key={action} value={action}>{action}</option>
            ))}
          </select>
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
      <div className="case-card-cta">{active ? "Running…" : "Run this review"}</div>
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
  // stream.interrupt is derived from a background-refreshed thread-state snapshot in
  // the SDK, not the resume call itself — there's a real timing gap where it can stay
  // stale for a beat (or longer) after Approve/Override. Track resolution ourselves so
  // the dialog disappears the instant the user clicks, instead of waiting on that.
  const [reviewResolved, setReviewResolved] = useState(false);
  // What the reviewer actually decided, shown immediately in the feed on click — the
  // disposition event (with the same info) only arrives after decision_node re-runs
  // past the interrupt, which can take a moment.
  const [reviewDecision, setReviewDecision] = useState<{ approved: boolean; action?: string; notes?: string } | null>(null);
  const feedEndRef = useRef<HTMLDivElement>(null);

  const stream = useStream<ReviewState>({
    apiUrl: API_URL,
    assistantId: "institutional_portfolio_review",
    onCustomEvent: (data) => {
      const event = data as FeedEvent;
      setFeed((prev) => [...prev, event]);
      if (event.type === "disposition") setDisposition(event);
    },
  });
  // stream.interrupt/stream.interrupts fall back to a background-refreshed thread-state
  // snapshot when "values" stream mode was never requested/read — read the
  // __interrupt__ key directly off stream.values instead, same fix as
  // fraud_investigation's ExecutionTab.tsx. Requires "values" in streamMode below.
  const graphValues = stream.values as (ReviewState & { __interrupt__?: Array<{ value: InterruptPayload }> }) | undefined;
  const interruptPayload = graphValues?.__interrupt__?.[0]?.value;
  const awaitingReview = interruptPayload != null && !reviewResolved;

  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [feed, interruptPayload]);

  const runRequest = (requestId: string) => {
    setFeed([]);
    setDisposition(null);
    setActiveRequest(requestId);
    setReviewResolved(false);
    setReviewDecision(null);
    stream.submit(initialInput(requestId, provider), { streamMode: ["custom", "values"] });
  };

  const approve = (notes: string) => {
    setReviewResolved(true);
    setReviewDecision({ approved: true, notes: notes || undefined });
    stream.submit(undefined, {
      command: { resume: { approved: true, notes } },
      streamMode: ["custom", "values"],
    });
  };

  const override = (overrideAction: string, notes: string) => {
    setReviewResolved(true);
    setReviewDecision({ approved: false, action: overrideAction, notes: notes || undefined });
    stream.submit(undefined, {
      command: { resume: { approved: false, override_outcome: overrideAction, notes } },
      streamMode: ["custom", "values"],
    });
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
          disabled={stream.isLoading || awaitingReview}
        >
          {PROVIDERS.map((p) => (
            <option key={p.value} value={p.value}>{p.label}</option>
          ))}
        </select>
        {stream.isLoading && <span className="running-indicator">running…</span>}
      </div>

      <div className="section-title">Reviews</div>
      <div className="case-grid">
        {REQUEST_IDS.map((requestId) => (
          <RequestCard
            key={requestId}
            requestId={requestId}
            active={activeRequest === requestId && stream.isLoading}
            disabled={stream.isLoading || awaitingReview}
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
          <p className="feed-empty">Pick a review above to start a live run.</p>
        )}
        {feed.map((event, i) => <FeedItem key={i} event={event} />)}
        {awaitingReview && (
          <>
            <div className="feed-row paused">
              <span className="feed-badge">PAUSED</span>
              <span className="feed-body">graph execution paused — awaiting supervisor review</span>
            </div>
            <ReviewPanel payload={interruptPayload} onApprove={approve} onOverride={override} />
          </>
        )}
        {reviewDecision && (
          <div className={`feed-row ${reviewDecision.approved ? "resolved-approve" : "resolved-override"}`}>
            <span className="feed-badge">{reviewDecision.approved ? "APPROVED" : "OVERRIDDEN"}</span>
            <span className="feed-body">
              {reviewDecision.approved
                ? "reviewer approved the proposed outcome"
                : `reviewer overrode to: ${reviewDecision.action}`}
            </span>
            {reviewDecision.notes && <div className="feed-reason">Reason: {reviewDecision.notes}</div>}
          </div>
        )}
        <div ref={feedEndRef} />
      </div>
    </div>
  );
}
