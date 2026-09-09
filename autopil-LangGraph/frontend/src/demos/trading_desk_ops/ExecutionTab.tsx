import { useEffect, useRef, useState } from "react";
import { useStream } from "@langchain/langgraph-sdk/react";
import { REGULATIONS, regulationForDenial } from "./policyData";
import {
  CASE_IDS,
  CASE_INFO,
  CASE_META,
  DOMAIN_LABELS,
  OVERRIDE_ACTIONS,
  PROVIDERS,
  TIER_LABELS,
  classifyProposedAction,
  initialInput,
  type AuditSummary,
  type BreakKind,
  type CaseMeta,
  type FeedEvent,
  type ReviewInterruptPayload,
  type TradingOpsState,
} from "./types";

const API_URL = "http://localhost:2024";

// Which regulation a given break KIND is actually grounded in, per REGULATIONS in
// policyData.ts — not invented here, just a display-side lookup keyed off
// classifyProposedAction()'s own kind. "clean"/"ssi_error"/"timing_lag" have no single
// regulation-grounded banner line in the original Equities build (SSI/timing-lag are
// data-quality findings, not a named regulatory mechanism), so they're intentionally
// absent from this map, same as before Fixed Income was added.
const GROUNDING_REGULATION_ID_BY_KIND: Partial<Record<BreakKind, string>> = {
  fails_to_deliver_eq: "REG-SHO",
  fails_to_deliver_fi: "FICC-FAILS-CHARGE",
  cash_break: "DAY-COUNT-CONVENTION",
  pool_notification_risk: "FICC-MBSD-PTN",
};

function groundingRegulationForAction(proposedAction: string) {
  const info = classifyProposedAction(proposedAction);
  const regulationId = info ? GROUNDING_REGULATION_ID_BY_KIND[info.kind] : undefined;
  return regulationId ? REGULATIONS.find((r) => r.id === regulationId) : undefined;
}

function ToolCallRow({ event }: { event: FeedEvent & { type: "tool_call" } }) {
  const denied = event.status === "denied";
  const regulation = denied ? regulationForDenial(event.tool, event.role) : undefined;
  // action-level governance pilot (autopil>=0.12.0) — omitted on every read (which is
  // every tool_call except decision_node's post-approval settlement-correction write
  // on a Fixed Income cash break), so this only ever adds a badge to the one row
  // where the action gate is doing something beyond the default, same "don't clutter
  // the common case" convention the AutoPIL dashboard's own action badge follows.
  const action = event.action;
  return (
    <div className={`feed-row ${denied ? "denied" : "allowed"}`}>
      <span className="feed-badge">{denied ? "DENIED" : "ALLOWED"}</span>
      {action && <span className={`feed-action-badge feed-action-${action}`}>{action.toUpperCase()}</span>}
      <span className="feed-role">{event.role}</span>
      <span className="feed-body">
        {event.tool}
        {event.key ? `(${event.key})` : "()"}
      </span>
      {denied && <div className="feed-reason">{event.reason}</div>}
      {regulation && (
        <div className="feed-regulation">
          Grounds: <span className="regulation-id">{regulation.id}</span> — {regulation.name}
        </div>
      )}
    </div>
  );
}

// Both stages here are genuinely LLM-driven — trading_ops_orchestrator_node's
// classification call decides which specialist runs FIRST (not a fixed graph edge the
// way quality_control's initial step is), so this always renders as a live "ROUTE"
// decision, never a "FIXED STEP" badge. The "initial" stage additionally carries
// `skipped` — roles the classification determined are genuinely not applicable to
// this trigger (e.g. order_intake_agent on a pm_rebalance trigger) — rendered as a
// distinct SKIP row directly beneath the route decision so EQ-004's path visibly
// diverges from EQ-001's without reading raw JSON. `domain` is now "equities" or
// "fixed_income" — this row already rendered it generically before Fixed Income
// existed, so no change was needed here beyond this comment.
function RoutingRow({ event }: { event: FeedEvent & { type: "routing" } }) {
  const isInitial = event.stage === "initial";
  return (
    <>
      <div className="feed-row routing">
        <span className="feed-badge">ROUTE</span>
        <span className="feed-body">
          {isInitial
            ? `orchestrator classified domain=${event.domain} trigger_type=${event.trigger_type} → routes first to ${event.route?.join(", ")}`
            : `orchestrator review → ${event.next}`}
        </span>
        {(event.reasoning || event.reason) && (
          <div className="feed-reason">{event.reasoning ?? event.reason}</div>
        )}
      </div>
      {isInitial && event.skipped != null && event.skipped.length > 0 && (
        <div className="feed-row skipped">
          <span className="feed-badge">SKIP</span>
          <span className="feed-body">
            skipped: {event.skipped.join(", ")} (already-structured trigger — nothing to parse)
          </span>
        </div>
      )}
    </>
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

function AuditSummaryTable({ summary }: { summary: AuditSummary }) {
  return (
    <div className="audit-summary-table">
      {Object.entries(summary.roles).map(([role, r]) => (
        <div key={role} className="audit-summary-row">
          <span className="audit-summary-role">{role}</span>
          <span className="audit-summary-counts">{r.allowed} allowed / {r.denied} denied</span>
          <span className="audit-summary-detail">
            {r.events.filter((e) => e.decision === "DENY").map((e) => e.reason).join("; ") || "no denials"}
          </span>
        </div>
      ))}
    </div>
  );
}

// A break-kind badge/note rendered alongside the tier badge — both in the pending
// ReviewPanel and the final DispositionBanner — so a cash break (FI-003), a proactive
// pool-notification deadline escalation (FI-004), and a genuine fails-to-deliver
// (EQ-005/FI-005, two different named penalty regimes) never render identically to
// each other or to a routine SSI/timing-lag correction. Keyed off classifyProposedAction()
// — the only backend-emitted signal that reliably distinguishes break TYPE (see its
// own doc comment in types.ts for why free-text findings can't be parsed reliably instead).
function BreakKindNote({ proposedAction }: { proposedAction: string }) {
  const info = classifyProposedAction(proposedAction);
  if (!info || info.kind === "clean") return null;
  const grounding = groundingRegulationForAction(proposedAction);
  return (
    <div className={`break-kind-note break-kind-${info.kind}`}>
      <span className={`break-kind-badge break-kind-${info.kind}`}>{info.label}</span>
      {info.proactive && (
        <div className="break-kind-proactive">
          Proactive escalation — fires before any settlement fail, not a reactive break investigation.
        </div>
      )}
      {grounding && (
        <div className="feed-regulation">
          Grounds: <span className="regulation-id">{grounding.id}</span> — {grounding.name}
        </div>
      )}
    </div>
  );
}

function DispositionBanner({ event }: { event: FeedEvent & { type: "disposition" } }) {
  const isTier2 = event.tier === "tier2_compliance_officer";
  return (
    <div className="disposition-banner">
      <div className="disposition-action">{event.action}</div>
      <div className={`tier-badge ${isTier2 ? "tier2" : "tier1"}`}>{event.tier_label}</div>
      <BreakKindNote proposedAction={event.proposed_action} />
      <div className={`disposition-review ${event.human_approved ? "approved" : "overridden"}`}>
        <strong>{event.human_approved ? "✓ Approved by reviewer" : "⚠ Overridden by reviewer"}</strong>
        {!event.human_approved && (
          <div className="disposition-proposed">Originally proposed: {event.proposed_action}</div>
        )}
        {event.human_notes && <div className="disposition-reason">Reviewer's note: "{event.human_notes}"</div>}
      </div>
      <div className="disposition-meta">
        {event.case_id} · specialists run: {event.specialists_run.join(", ") || "none"}
        {event.skipped_roles.length > 0 && ` · skipped: ${event.skipped_roles.join(", ")}`}
        {" · "}
        denials: {event.denial_count}
        {" · "}
        audit trail: {event.audit_summary.allowed} allowed / {event.audit_summary.denied} denied
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
  const isTier2 = payload.tier === "tier2_compliance_officer";
  // decision_node loops on interrupt() until a non-empty notes field comes back on the
  // resume payload, on BOTH approve and override, at BOTH tiers. Enforce the same
  // requirement here at the form layer instead of relying on the backend's own retry
  // loop, which would otherwise silently re-pause with no visible feedback.
  const notesEmpty = notes.trim().length === 0;

  return (
    <div className={`review-panel ${isTier2 ? "tier2" : "tier1"}`}>
      <div className={`tier-badge ${isTier2 ? "tier2" : "tier1"}`}>
        {payload.tier_label ?? TIER_LABELS[payload.tier]}
      </div>
      <div className="review-header">
        Awaiting {isTier2 ? "compliance-officer" : "ops-analyst"} review — {payload.case_id}
      </div>
      <div className="review-proposed">Proposed: {payload.proposed_action}</div>
      <BreakKindNote proposedAction={payload.proposed_action} />
      <div className="review-meta">
        specialists run: {payload.specialists_run.join(", ") || "none"}
        {payload.skipped_roles.length > 0 && ` · skipped: ${payload.skipped_roles.join(", ")}`}
        {" · "}denials: {payload.denial_log.length}
      </div>

      <textarea
        className="review-notes"
        placeholder="Note (required to approve or override) — recorded in the final disposition"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
      />
      {notesEmpty && <div className="review-notes-hint">A note is required before you can approve or override.</div>}

      {!overriding ? (
        <div className="review-actions">
          <button className="approve" disabled={notesEmpty} onClick={() => onApprove(notes)}>Approve</button>
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
            <button className="override" disabled={notesEmpty} onClick={() => onOverride(overrideAction, notes)}>
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
  const meta = CASE_META[caseId];
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
        <span className={`domain-badge domain-badge-${meta.domain}`}>{DOMAIN_LABELS[meta.domain]}</span>
        <div className="case-card-meta">
          {meta.symbol} · {meta.side} {meta.totalQuantity.toLocaleString()} {meta.quantityUnit}
        </div>
        <div className="case-card-description">{info.description}</div>
      </div>
      <div className="case-card-cta">{active ? "Processing…" : "Pull from queue"}</div>
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

export default function ExecutionTab({ domain }: { domain: CaseMeta["domain"] }) {
  // Equities and Fixed Income are separate sidebar entries now — each Execution tab
  // only ever queues its own domain's cases, not all 10 mixed together. Same shared
  // graph/assistantId underneath (trading_desk_ops classifies domain dynamically per
  // case regardless), this is purely a display-side filter.
  const caseIds = CASE_IDS.filter((id) => CASE_META[id].domain === domain);
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
  const feedEndRef = useRef<HTMLDivElement>(null);

  const stream = useStream<TradingOpsState>({
    apiUrl: API_URL,
    assistantId: "trading_desk_ops",
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
  const graphValues = stream.values as (TradingOpsState & { __interrupt__?: Array<{ value: ReviewInterruptPayload }> }) | undefined;
  const interruptPayload = graphValues?.__interrupt__?.[0]?.value;
  const awaitingReview = interruptPayload != null && !reviewResolved;

  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [feed, interruptPayload]);

  const runCase = (caseId: string) => {
    setFeed([]);
    setDisposition(null);
    setActiveCase(caseId);
    setReviewResolved(false);
    setReviewDecision(null);
    stream.submit(initialInput(caseId, provider), { streamMode: ["custom", "values"] });
  };

  const approve = (notes: string) => {
    setReviewResolved(true);
    setReviewDecision({ approved: true, notes });
    stream.submit(undefined, {
      command: { resume: { approved: true, notes } },
      streamMode: ["custom", "values"],
    });
  };

  const override = (overrideAction: string, notes: string) => {
    setReviewResolved(true);
    setReviewDecision({ approved: false, action: overrideAction, notes });
    stream.submit(undefined, {
      command: { resume: { approved: false, override_action: overrideAction, notes } },
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

      <div className="section-title">Case Queue — {DOMAIN_LABELS[domain]}</div>
      <div className="case-queue">
        {caseIds.map((caseId) => (
          <CaseCard
            key={caseId}
            caseId={caseId}
            active={activeCase === caseId && stream.isLoading}
            disabled={stream.isLoading || awaitingReview}
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
          <p className="feed-empty">Pull a case from the queue above to start processing.</p>
        )}
        {feed.map((event, i) => <FeedItem key={i} event={event} />)}
        {awaitingReview && interruptPayload != null && (
          <>
            <div className="feed-row paused">
              <span className="feed-badge">PAUSED</span>
              <span className="feed-body">
                graph execution paused — awaiting {interruptPayload.tier === "tier2_compliance_officer" ? "compliance-officer" : "ops-analyst"} review
              </span>
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
            {reviewDecision.notes && <div className="feed-reason">Note: {reviewDecision.notes}</div>}
          </div>
        )}
        <div ref={feedEndRef} />
      </div>
    </div>
  );
}
