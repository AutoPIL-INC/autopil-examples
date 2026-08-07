import { useEffect, useRef, useState } from "react";
import { useStream } from "@langchain/langgraph-sdk/react";
import {
  CASE_IDS,
  CASE_INFO,
  CASE_ALERTS,
  OVERRIDE_ACTIONS,
  PROVIDERS,
  initialInput,
  isAuditSourceAsk,
  type AuditSummary,
  type FeedEvent,
  type InterruptPayload,
  type InvestigationState,
  type LocalAuditRoleSummary,
  type McpAuditRoleSummary,
  type ReviewInterruptPayload,
} from "./types";

const API_URL = "http://localhost:2024";

function formatOpenedDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
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

function isMcpRoleSummary(r: LocalAuditRoleSummary | McpAuditRoleSummary): r is McpAuditRoleSummary {
  return "sources_accessed" in r;
}

function AuditSummaryTable({ summary }: { summary: AuditSummary }) {
  return (
    <div className="audit-summary-table">
      {Object.entries(summary.roles).map(([role, r]) => (
        <div key={role} className="audit-summary-row">
          <span className="audit-summary-role">{role}</span>
          <span className="audit-summary-counts">{r.allowed} allowed / {r.denied} denied</span>
          {isMcpRoleSummary(r) ? (
            <span className="audit-summary-detail">
              sources: {r.sources_accessed.join(", ") || "(none)"}
            </span>
          ) : (
            <span className="audit-summary-detail">
              {r.events.filter((e) => e.decision === "DENY").map((e) => e.reason).join("; ") || "no denials"}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

function DispositionBanner({ event }: { event: FeedEvent & { type: "disposition" } }) {
  return (
    <div className="disposition-banner">
      <div className="disposition-action">{event.action}</div>
      <div className={`disposition-review ${event.human_approved ? "approved" : "overridden"}`}>
        <strong>{event.human_approved ? "✓ Approved by reviewer" : "⚠ Overridden by reviewer"}</strong>
        {!event.human_approved && (
          <div className="disposition-proposed">Originally proposed: {event.proposed_action}</div>
        )}
        {event.human_notes && <div className="disposition-reason">Reviewer's reason: "{event.human_notes}"</div>}
      </div>
      <div className="disposition-meta">
        {event.case_id} · specialists run: {event.specialists_run.join(", ")} · denials: {event.denial_count}
        {" · "}
        audit trail ({event.audit_source}): {event.audit_summary.allowed} allowed / {event.audit_summary.denied} denied
        {" ("}
        {event.audit_summary.total} events)
      </div>
      <AuditSummaryTable summary={event.audit_summary} />
    </div>
  );
}

function ReviewPanel({
  payload,
  onApprove,
  onOverride,
}: {
  payload: ReviewInterruptPayload;
  onApprove: (notes: string) => void;
  onOverride: (action: string, notes: string) => void;
}) {
  const [overriding, setOverriding] = useState(false);
  const [overrideAction, setOverrideAction] = useState<string>(OVERRIDE_ACTIONS[0]);
  const [notes, setNotes] = useState("");

  return (
    <div className="review-panel">
      <div className="review-header">Awaiting SOC compliance review — {payload.case_id}</div>
      <div className="review-proposed">Proposed: {payload.proposed_action}</div>
      <div className="review-meta">
        specialists run: {payload.specialists_run.join(", ")} · denials: {payload.denial_log.length}
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

function AuditSourcePanel({ onChoose }: { onChoose: (source: "mcp" | "local") => void }) {
  return (
    <div className="review-panel">
      <div className="review-header">Awaiting audit-trail source choice</div>
      <div className="review-proposed">
        How should this case's AutoPIL audit trail be gathered — via AutoPIL's MCP server
        (get_session_status, one call per role, aggregate counts + sources touched) or
        directly from the local audit log (guard.get_audit_trail(), per-decision detail
        including denial reasons)?
      </div>
      <div className="review-actions">
        <button className="approve" onClick={() => onChoose("mcp")}>Via MCP</button>
        <button className="override" onClick={() => onChoose("local")}>Via local audit trail</button>
      </div>
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
  const alert = CASE_ALERTS[caseId];
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
      <div className="case-card-body">
        <div className="case-card-meta">
          Opened {formatOpenedDate(alert.triggeredAt)} · Priority: {alert.priority} · Flagged by: {alert.ruleName}
        </div>
        <div className="case-card-description">{alert.description}</div>
      </div>
      <div className="case-card-cta">{active ? "Investigating…" : "Pull from queue"}</div>
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
  const [activeCase, setActiveCase] = useState<string | null>(null);
  // stream.interrupt is derived from a background-refreshed thread-state snapshot in
  // the SDK, not the resume call itself — there's a real timing gap where it can stay
  // stale for a beat (or longer) after Approve/Override. Track resolution ourselves so
  // the dialog disappears the instant the user clicks, instead of waiting on that.
  const [reviewResolved, setReviewResolved] = useState(false);
  // What the reviewer actually decided, shown immediately in the feed on click — the
  // disposition event (with the same info) only arrives after decision_node re-runs
  // past the interrupt, which can take a moment.
  const [reviewDecision, setReviewDecision] = useState<{ approved: boolean; action?: string; notes?: string } | null>(null);
  // Same resolved-tracking problem as reviewResolved above, for the second
  // interrupt() (audit-source choice) that now follows the review one.
  const [auditChoiceResolved, setAuditChoiceResolved] = useState(false);
  const [auditChoiceDecision, setAuditChoiceDecision] = useState<"mcp" | "local" | null>(null);
  const feedEndRef = useRef<HTMLDivElement>(null);

  const stream = useStream<InvestigationState>({
    apiUrl: API_URL,
    assistantId: "splunk_secops",
    onCustomEvent: (data) => {
      const event = data as FeedEvent;
      setFeed((prev) => [...prev, event]);
      if (event.type === "disposition") setDisposition(event);
    },
  });
  // stream.interrupt/stream.interrupts fall back to a background-refreshed thread-state
  // snapshot when "values" stream mode was never requested/read — which is flaky both
  // ways (can show stale-true after resume, or never populate at all). Read the
  // __interrupt__ key directly off stream.values instead — the exact same shape
  // decision_node's interrupt() produces. Requires "values" in streamMode below on
  // every submit.
  const graphValues = stream.values as (InvestigationState & { __interrupt__?: Array<{ value: InterruptPayload }> }) | undefined;
  const interruptPayload = graphValues?.__interrupt__?.[0]?.value;
  // decision_node pauses twice now — the review interrupt first, then the
  // audit-source-choice interrupt right after it resolves — so which panel to show
  // depends on the payload's own shape, not just "an interrupt exists."
  const isAuditAsk = interruptPayload != null && isAuditSourceAsk(interruptPayload);
  const awaitingReview = interruptPayload != null && !isAuditAsk && !reviewResolved;
  const awaitingAuditChoice = interruptPayload != null && isAuditAsk && !auditChoiceResolved;

  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [feed, interruptPayload]);

  const runCase = (caseId: string) => {
    setFeed([]);
    setDisposition(null);
    setActiveCase(caseId);
    setReviewResolved(false);
    setReviewDecision(null);
    setAuditChoiceResolved(false);
    setAuditChoiceDecision(null);
    stream.submit(initialInput(caseId, provider), { streamMode: ["custom", "values"] });
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
      command: { resume: { approved: false, override_action: overrideAction, notes } },
      streamMode: ["custom", "values"],
    });
  };

  const chooseAuditSource = (source: "mcp" | "local") => {
    setAuditChoiceResolved(true);
    setAuditChoiceDecision(source);
    stream.submit(undefined, {
      command: { resume: { source } },
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
          disabled={stream.isLoading || awaitingReview || awaitingAuditChoice}
        >
          {PROVIDERS.map((p) => (
            <option key={p.value} value={p.value}>{p.label}</option>
          ))}
        </select>
        {stream.isLoading && <span className="running-indicator">running…</span>}
      </div>

      <div className="section-title">Case Queue</div>
      <div className="case-queue">
        {CASE_IDS.map((caseId) => (
          <CaseCard
            key={caseId}
            caseId={caseId}
            active={activeCase === caseId && stream.isLoading}
            disabled={stream.isLoading || awaitingReview || awaitingAuditChoice}
            onRun={() => runCase(caseId)}
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
          <p className="feed-empty">Pull a case from the queue above to start the investigation.</p>
        )}
        {feed.map((event, i) => <FeedItem key={i} event={event} />)}
        {awaitingReview && interruptPayload != null && !isAuditSourceAsk(interruptPayload) && (
          <>
            <div className="feed-row paused">
              <span className="feed-badge">PAUSED</span>
              <span className="feed-body">graph execution paused — awaiting SOC compliance review</span>
            </div>
            <ReviewPanel payload={interruptPayload} onApprove={approve} onOverride={override} />
          </>
        )}
        {reviewDecision && (
          <div className={`feed-row ${reviewDecision.approved ? "resolved-approve" : "resolved-override"}`}>
            <span className="feed-badge">{reviewDecision.approved ? "APPROVED" : "OVERRIDDEN"}</span>
            <span className="feed-body">
              {reviewDecision.approved
                ? "reviewer approved the proposed disposition"
                : `reviewer overrode to: ${reviewDecision.action}`}
            </span>
            {reviewDecision.notes && <div className="feed-reason">Reason: {reviewDecision.notes}</div>}
          </div>
        )}
        {awaitingAuditChoice && (
          <>
            <div className="feed-row paused">
              <span className="feed-badge">PAUSED</span>
              <span className="feed-body">graph execution paused — awaiting audit-trail source choice</span>
            </div>
            <AuditSourcePanel onChoose={chooseAuditSource} />
          </>
        )}
        {auditChoiceDecision && (
          <div className="feed-row resolved-approve">
            <span className="feed-badge">SOURCE</span>
            <span className="feed-body">
              audit trail will be shown via {auditChoiceDecision === "mcp" ? "AutoPIL's MCP server" : "the local audit log"}
            </span>
          </div>
        )}
        <div ref={feedEndRef} />
      </div>
    </div>
  );
}
