import { useEffect, useRef, useState } from "react";
import { useStream } from "@langchain/langgraph-sdk/react";
import {
  CUSTOMER_IDS,
  CLIENT_REVIEWS,
  OVERRIDE_ACTIONS,
  TIER_LABELS,
  PROVIDERS,
  initialInput,
  type ClientReviewState,
  type FeedEvent,
  type HumanDecision,
  type InterruptPayload,
} from "./types";

const API_URL = "http://localhost:2024";

function formatOpenedDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function tierLabel(tier: string): string {
  return TIER_LABELS[tier] ?? tier;
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
          ? `intake → ${tierLabel(event.tier ?? "")}`
          : `${tierLabel(event.tier ?? "")} review → escalate to ${tierLabel(event.next ?? "")}`}
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
      <span className="feed-body">{event.finding.proposed_action}</span>
      {event.finding.summary && <div className="feed-reason">{event.finding.summary}</div>}
    </div>
  );
}

function DispositionBanner({ event }: { event: FeedEvent & { type: "disposition" } }) {
  const decisions = Object.entries(event.human_decisions) as Array<[string, HumanDecision]>;
  return (
    <div className="disposition-banner">
      <div className="disposition-action">{event.final_action}</div>
      <div className="disposition-review approved">
        <strong>Closed at {tierLabel(event.closed_at_tier)}</strong>
        <div className="disposition-proposed">Tiers visited: {event.tiers_visited.map(tierLabel).join(" → ")}</div>
        {decisions.map(([tier, d]) => (
          <div key={tier} className="disposition-reason">
            {tierLabel(tier)}: {d.decision}
            {d.override_action ? ` → ${d.override_action}` : ""}
            {d.notes ? ` — "${d.notes}"` : ""}
          </div>
        ))}
      </div>
      <div className="disposition-meta">
        {event.customer_id} · denials: {event.denial_count}
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
  onEscalate,
}: {
  payload: InterruptPayload;
  onApprove: (notes: string) => void;
  onOverride: (action: string, notes: string) => void;
  onEscalate: (notes: string) => void;
}) {
  const [overriding, setOverriding] = useState(false);
  const [overrideAction, setOverrideAction] = useState<string>(OVERRIDE_ACTIONS[0]);
  const [notes, setNotes] = useState("");

  return (
    <div className="review-panel">
      <div className="review-header">
        Awaiting {tierLabel(payload.tier)} review — {payload.customer_id}
      </div>
      <div className="review-proposed">Proposed: {payload.finding.proposed_action}</div>
      <div className="review-meta">
        {payload.finding.summary} · denials: {payload.denial_log.length}
      </div>

      <textarea
        className="review-notes"
        placeholder="Notes (optional) — recorded either way, in the final disposition"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
      />

      {!overriding ? (
        <div className="review-actions">
          <button className="approve" onClick={() => onApprove(notes)}>Approve</button>
          <button className="override" onClick={() => setOverriding(true)}>Override…</button>
          {payload.can_escalate && (
            <button className="escalate" onClick={() => onEscalate(notes)}>
              Escalate to {tierLabel(payload.next_tier ?? "")}…
            </button>
          )}
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

function CustomerCard({
  customerId,
  active,
  disabled,
  onRun,
}: {
  customerId: (typeof CUSTOMER_IDS)[number];
  active: boolean;
  disabled: boolean;
  onRun: () => void;
}) {
  const review = CLIENT_REVIEWS[customerId];
  return (
    <button
      className={`case-card ${active ? "active" : ""}`}
      onClick={onRun}
      disabled={disabled}
    >
      <div className="case-card-top">
        <span className="case-card-id">{customerId}</span>
        <span className="case-card-time">~1–3 min</span>
      </div>
      <div className="case-card-body">
        <div className="case-card-meta">
          Opened {formatOpenedDate(review.opened)} · Priority: {review.priority}
        </div>
        <div className="case-card-description">{review.reasonForReview}</div>
      </div>
      <div className="case-card-cta">{active ? "Reviewing…" : "Pull from queue"}</div>
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
  const [activeCustomer, setActiveCustomer] = useState<string | null>(null);
  // A case can pause up to 3 times (once per tier it reaches). Track which tiers'
  // reviews have already been resolved rather than a single boolean, so a *new*
  // interrupt at the next tier correctly shows as pending again — same reasoning as
  // the fraud demo's reviewResolved flag, extended to a set since there can be more
  // than one review per run here.
  const [resolvedTiers, setResolvedTiers] = useState<Set<string>>(new Set());
  const [resolutions, setResolutions] = useState<Array<{ tier: string; decision: string; action?: string; notes?: string }>>([]);
  const feedEndRef = useRef<HTMLDivElement>(null);

  const stream = useStream<ClientReviewState>({
    apiUrl: API_URL,
    assistantId: "client_analysis",
    onCustomEvent: (data) => {
      const event = data as FeedEvent;
      setFeed((prev) => [...prev, event]);
      if (event.type === "disposition") setDisposition(event);
    },
  });
  // Read __interrupt__ directly off stream.values rather than stream.interrupt(s) —
  // those getters fall back to a background-refreshed thread-state snapshot that can
  // lag a resume by a beat or more. Requires "values" in streamMode on every submit.
  const graphValues = stream.values as (ClientReviewState & { __interrupt__?: Array<{ value: InterruptPayload }> }) | undefined;
  const interruptPayload = graphValues?.__interrupt__?.[0]?.value;
  const awaitingReview = interruptPayload != null && !resolvedTiers.has(interruptPayload.tier);

  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [feed, interruptPayload]);

  const runCustomer = (customerId: string) => {
    setFeed([]);
    setDisposition(null);
    setActiveCustomer(customerId);
    setResolvedTiers(new Set());
    setResolutions([]);
    stream.submit(initialInput(customerId, provider), { streamMode: ["custom", "values"] });
  };

  const resolve = (tier: string, decision: string, action: string | undefined, notes: string, resume: Record<string, unknown>) => {
    setResolvedTiers((prev) => new Set(prev).add(tier));
    setResolutions((prev) => [...prev, { tier, decision, action, notes: notes || undefined }]);
    stream.submit(undefined, { command: { resume }, streamMode: ["custom", "values"] });
  };

  const approve = (notes: string) => {
    if (!interruptPayload) return;
    resolve(interruptPayload.tier, "approved", undefined, notes, { decision: "approve", notes });
  };

  const override = (overrideAction: string, notes: string) => {
    if (!interruptPayload) return;
    resolve(interruptPayload.tier, "overridden", overrideAction, notes, { decision: "override", override_action: overrideAction, notes });
  };

  const escalate = (notes: string) => {
    if (!interruptPayload) return;
    resolve(interruptPayload.tier, "escalated", undefined, notes, { decision: "escalate", notes });
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

      <div className="section-title">Client Review Queue</div>
      <div className="case-queue">
        {CUSTOMER_IDS.map((customerId) => (
          <CustomerCard
            key={customerId}
            customerId={customerId}
            active={activeCustomer === customerId && stream.isLoading}
            disabled={stream.isLoading || awaitingReview}
            onRun={() => runCustomer(customerId)}
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
          <p className="feed-empty">Pull a customer from the queue above to start the review.</p>
        )}
        {feed.map((event, i) => <FeedItem key={i} event={event} />)}
        {awaitingReview && interruptPayload && (
          <>
            <div className="feed-row paused">
              <span className="feed-badge">PAUSED</span>
              <span className="feed-body">graph execution paused — awaiting {tierLabel(interruptPayload.tier)} review</span>
            </div>
            <ReviewPanel payload={interruptPayload} onApprove={approve} onOverride={override} onEscalate={escalate} />
          </>
        )}
        {resolutions.map((r, i) => (
          <div key={i} className={`feed-row ${r.decision === "approved" ? "resolved-approve" : "resolved-override"}`}>
            <span className="feed-badge">{r.decision.toUpperCase()}</span>
            <span className="feed-body">
              {tierLabel(r.tier)}:{" "}
              {r.decision === "approved" && "reviewer approved the proposed action"}
              {r.decision === "overridden" && `reviewer overrode to: ${r.action}`}
              {r.decision === "escalated" && "reviewer escalated to the next tier"}
            </span>
            {r.notes && <div className="feed-reason">Reason: {r.notes}</div>}
          </div>
        ))}
        <div ref={feedEndRef} />
      </div>
    </div>
  );
}
