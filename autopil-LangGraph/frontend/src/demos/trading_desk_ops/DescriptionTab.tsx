import { AGENT_POLICIES, REGULATIONS, type AgentPolicy } from "./policyData";
import { CASE_IDS, CASE_INFO, CASE_META } from "./types";

function PolicyCard({ policy }: { policy: AgentPolicy }) {
  return (
    <div className="policy-card">
      <div className="policy-card-name">{policy.displayName}</div>
      <div className="policy-card-desc">{policy.description}</div>
      <div className="policy-card-row">
        <span className="policy-label">Allowed</span>
        <div className="chip-list">
          {policy.allowedSources.map((s) => (
            <span key={s} className="chip chip-allowed">{s}</span>
          ))}
        </div>
      </div>
      <div className="policy-card-row">
        <span className="policy-label">Denied</span>
        <div className="chip-list">
          {policy.deniedSources.map((s) => (
            <span key={s} className="chip chip-denied">{s}</span>
          ))}
        </div>
      </div>
      <div className="policy-card-meta">
        max sensitivity: <strong>{policy.maxSensitivity}</strong> · session TTL:{" "}
        <strong>{policy.sessionTtlMinutes} min</strong>
      </div>
    </div>
  );
}

export default function DescriptionTab() {
  const orchestrator = AGENT_POLICIES[0];
  const orderIntake = AGENT_POLICIES[1];
  const followUpSpecialists = AGENT_POLICIES.slice(2, 5);
  const compiler = AGENT_POLICIES[6];

  return (
    <div className="description-tab">
      <section className="desc-section">
        <h2>What this demo shows</h2>
        <p>
          Seven AI agents handle a block equity order — a different name each scenario
          (MSFT, NVDA, AAPL, AMZN, GOOG) — the way a real
          trading-operations desk at Meridian Bank would — an orchestrator, an order
          intake parser, an allocation specialist, a same-day affirmation matcher, a
          DTCC/NSCC settlement reconciler, an exception investigator, and a compliance
          reporting compiler — each given access to more trade, position, and
          settlement data than it's actually allowed to use, all inside a T+1
          settlement window with no slack for manual exception handling.
        </p>
        <p>
          AutoPIL is the policy layer that decides, in real time, what each agent can
          see. When an agent reaches for data outside its lane — desk P&amp;L,
          commission, another client's position, raw client PII — AutoPIL blocks it
          and logs why, the same way it would in production, not because the demo told
          it not to look there. And no settlement disposition happens on an AI's
          say-so: a human reviewer signs off or overrides every recommendation before
          it's final — at one of two review tiers, depending on real severity signals.
        </p>
        <details className="desc-technical">
          <summary>How this actually works, technically</summary>
          <p>
            Each specialist runs a real tool-calling loop — not a scripted branch — on
            whichever model you pick (Claude, Gemini, Groq, or Ollama), and each is
            handed a toolbelt <strong>wider</strong> than what its policy actually
            authorizes. Nothing in the code tells a specialist which of its tools are
            off-limits; it finds out the same way a production agent would: it calls a
            tool, and AutoPIL's <code>guard.protect()</code> either returns data or a
            denial reason.
          </p>
          <p>
            Unlike <code>quality_control</code>'s fixed first step, the orchestrator's
            classification here is <strong>genuinely dynamic</strong>: it classifies
            the incoming trigger (new order / amendment / cancellation / PM rebalance /
            corporate-action trade) via a real LLM call, and that classification
            decides which specialist runs <strong>first</strong>. A new-order trigger
            routes through <code>order_intake_agent</code> to parse the raw
            instruction; a PM-rebalance trigger arrives already structured from the
            PM's own system, so <code>order_intake_agent</code> is skipped
            entirely — not run as a no-op, genuinely excluded from the routing
            candidate list. Compare the EQ-001 and EQ-004 cases below to watch this
            live. No live OMS/EMS, custodian, or DTCC/NSCC feed is involved anywhere —
            every guarded getter reads from simulated fixture data.
          </p>
        </details>
      </section>

      <section className="desc-section">
        <h2>The 7 agents</h2>
        <div className="flow-diagram">
          <div className="flow-box flow-orchestrator">
            <div className="flow-box-title">{orchestrator.displayName}</div>
            <div className="flow-box-sub">{orchestrator.description}</div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-branch-label">
            classifies the trigger via a real LLM call — this decides which specialist runs
            first: a new order routes through order_intake_agent; a PM-rebalance trigger
            skips straight to allocation_agent, since order_intake_agent's own trigger is
            genuinely not applicable
          </div>
          <div className="flow-box flow-specialist">
            <div className="flow-box-title">{orderIntake.displayName}</div>
            <div className="flow-box-sub">{orderIntake.description}</div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-branch-label">
            orchestrator re-routes among these + order_intake_agent (if not skipped), based on
            findings and denials so far — also genuinely LLM-driven
          </div>
          <div className="flow-row">
            {followUpSpecialists.map((p) => (
              <div key={p.role} className="flow-box flow-specialist">
                <div className="flow-box-title">{p.displayName}</div>
                <div className="flow-box-sub">{p.description}</div>
              </div>
            ))}
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-box flow-specialist">
            <div className="flow-box-title">{compiler.displayName}</div>
            <div className="flow-box-sub">
              {compiler.description} Runs once every relevant specialist has finished —
              which one matters last depends on the case.
            </div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-box flow-review">
            <div className="flow-box-title">Two-Tier Human Review</div>
            <div className="flow-box-sub">
              Tier 1 (ops-analyst) for routine corrections, Tier 2 (compliance-officer)
              for escalated settlement-risk events — computed from real fixture data,
              never the case ID. Approve or override, a written note is required
              either way, at either tier. See DESIGN.md.
            </div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-box flow-decision">
            <div className="flow-box-title">Final Disposition</div>
            <div className="flow-box-sub">Rule-based, not LLM-improvised — an LLM can draft the narrative, it shouldn't decide the settlement action.</div>
          </div>
        </div>
      </section>

      <section className="desc-section">
        <h2>Each agent's AutoPIL policy</h2>
        <p>
          This is the actual enforcement boundary — mirrored from{" "}
          <code>policies/financial_services/trading_desk_ops.yaml</code>, not invented
          for display. Every allowed/denied source below is checked by AutoPIL at
          retrieval time, regardless of what the agent's own toolbelt makes available.
        </p>
        <div className="policy-grid">
          {AGENT_POLICIES.map((p) => (
            <PolicyCard key={p.role} policy={p} />
          ))}
        </div>
      </section>

      <section className="desc-section">
        <h2>Compliance framework this maps to</h2>
        <p>
          No existing AutoPIL policy stub matched this domain — designed from scratch,
          with the <code>regulations:</code> metadata-block convention borrowed from{" "}
          <code>policies/financial_services/clearing_settlement.yaml</code>. Each row
          below is a real regulatory requirement mapped directly onto the policy
          mechanism that enforces it, not a bare compliance-sounding label.
        </p>
        <div className="regulation-table">
          {REGULATIONS.map((r) => (
            <div key={r.id} className="regulation-card">
              <div className="regulation-card-head">
                <span className="regulation-id">{r.id}</span>
                <span className="regulation-card-name">{r.name}</span>
              </div>
              {r.applicableRules.map((rule, i) => (
                <div key={i} className="regulation-rule">
                  <div className="regulation-rule-text">{rule.rule}</div>
                  <div className="regulation-rule-enforced">{rule.howEnforced}</div>
                </div>
              ))}
            </div>
          ))}
        </div>
      </section>

      <section className="desc-section">
        <h2>The 5 cases</h2>
        <div className="case-grid">
          {CASE_IDS.map((caseId) => {
            const info = CASE_INFO[caseId];
            const meta = CASE_META[caseId];
            return (
              <div key={caseId} className="case-card case-card-static">
                <div className="case-card-top">
                  <span className="case-card-id">{caseId}</span>
                  <span className="case-card-time">{info.estimatedTime}</span>
                </div>
                <div className="case-card-title">{info.title}</div>
                <div className="case-card-meta">
                  {meta.symbol} · {meta.side} {meta.totalQuantity.toLocaleString()} shares
                </div>
                <div className="case-card-description">{info.description}</div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
