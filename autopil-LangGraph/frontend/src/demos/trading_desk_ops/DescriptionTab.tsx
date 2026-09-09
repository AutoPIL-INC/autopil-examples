import { AGENT_POLICIES, REGULATIONS, type AgentPolicy } from "./policyData";
import { CASE_IDS, CASE_INFO, CASE_META, DOMAIN_LABELS, type CaseMeta } from "./types";

// Equities and Fixed Income now each get their own Description tab (separate sidebar
// entries) instead of one page narrating both sub-domains at once — this is the copy
// that actually differs per domain. Everything else on the page (agent policies,
// compliance framework) is shared, real data, not duplicated here.
const DOMAIN_COPY: Record<
  CaseMeta["domain"],
  { intro: string; technical: string; orchestratorBranch: string; specialistBranch: string }
> = {
  equities: {
    intro:
      "Seven AI agents handle a block equity order at Meridian Bank's Trading Unit — a different ticker each scenario (MSFT, NVDA, AAPL, AMZN, GOOG) — the way a real trading-operations desk would: an orchestrator, an order intake parser, an allocation specialist, a same-day affirmation matcher, a settlement reconciler, an exception investigator, and a compliance reporting compiler — each given access to more trade, position, and settlement data than it's actually allowed to use, all inside a T+1 settlement window with no slack for manual exception handling.",
    technical:
      "The orchestrator's classification here is genuinely dynamic: it classifies the incoming trigger (new order / amendment / cancellation / PM rebalance / corporate-action trade) via a real LLM call, and that classification decides which specialist runs first. A new-order trigger routes through order_intake_agent to parse the raw instruction; a PM-rebalance trigger (EQ-004) arrives already structured from the PM's own system, so order_intake_agent is skipped entirely — not run as a no-op, genuinely excluded from the routing candidate list. Compare the EQ-001 and EQ-004 cases below to watch this live. No live OMS/EMS, custodian, or DTCC/NSCC feed is involved anywhere — every guarded getter reads from simulated fixture data.",
    orchestratorBranch:
      "classifies the trigger via a real LLM call — this decides which specialist runs first: a new order routes through order_intake_agent; a PM-rebalance trigger (EQ-004) skips straight to allocation_agent, since order_intake_agent's own trigger is genuinely not applicable",
    specialistBranch:
      "orchestrator re-routes among the remaining specialists + order_intake_agent (if not skipped), based on findings and denials so far — also genuinely LLM-driven",
  },
  fixed_income: {
    intro:
      "Seven AI agents handle a fixed income trade at Meridian Bank's Trading Unit — a different instrument each scenario (a corporate bond, an agency MBS TBA pool, two Treasury notes) — the way a real trading-operations desk would: an orchestrator, an order intake parser, an instrument classifier, a same-day affirmation matcher, a settlement reconciler, an exception investigator, and a compliance reporting compiler — each given access to more trade, position, and settlement data than it's actually allowed to use, all inside a T+1 settlement window with no slack for manual exception handling.",
    technical:
      "The orchestrator's classification here is genuinely dynamic: it classifies the incoming trigger via a real LLM call, and that classification decides which specialist runs first. Fixed income introduces two mechanisms no Equities case exercises: a genuinely distinct cash break (a day-count/accrued-interest mismatch, FI-003 — a different fixture field entirely from a quantity/SSI break, not a relabeling) and a proactive deadline escalation (a TBA pool-notification cutoff at risk, FI-004 — fires before any settlement fail, not after one). Fixed income is also the one place in this repo where AutoPIL governs a write, not just a read: once a human approves FI-003's correction, exception_investigation_agent submits it through a second, independently-gated action-level check (read vs. write vs. delete, on top of the source/task/sensitivity gates every read already goes through) — every other role stays read-only by default, so the same write attempted under a different role denies. No live OMS/EMS, custodian, or FICC feed is involved anywhere — every guarded getter reads from simulated fixture data.",
    orchestratorBranch:
      "classifies the trigger via a real LLM call — this decides which specialist runs first: every case routes through order_intake_agent to parse the raw instruction, then instrument_classification_agent resolves the instrument's actual type before anything downstream depends on it (FI-002 is what happens when that resolution surprises the desk)",
    specialistBranch:
      "orchestrator re-routes among the remaining specialists + order_intake_agent, based on findings and denials so far — also genuinely LLM-driven",
  },
};

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
      {/* Action-level governance pilot (autopil>=0.12.0) — shown only when a role has
          opted into something beyond the read-only default (every other role here
          leaves allowedActions undefined), same "don't clutter the common case"
          convention the AutoPIL dashboard's own Actions section follows. */}
      {policy.allowedActions && (
        <div className="policy-card-row">
          <span className="policy-label">Actions</span>
          <div className="chip-list">
            {policy.allowedActions.map((a) => (
              <span key={a} className={`chip ${a === "read" ? "chip-allowed" : "chip-action"}`}>{a}</span>
            ))}
          </div>
        </div>
      )}
      <div className="policy-card-meta">
        max sensitivity: <strong>{policy.maxSensitivity}</strong> · session TTL:{" "}
        <strong>{policy.sessionTtlMinutes} min</strong>
      </div>
    </div>
  );
}

export default function DescriptionTab({ domain }: { domain: CaseMeta["domain"] }) {
  const copy = DOMAIN_COPY[domain];
  const orchestrator = AGENT_POLICIES.find((p) => p.role === "trading_ops_orchestrator")!;
  const orderIntake = AGENT_POLICIES.find((p) => p.role === "order_intake_agent")!;
  const instrumentClassification = AGENT_POLICIES.find((p) => p.role === "instrument_classification_agent")!;
  const allocation = AGENT_POLICIES.find((p) => p.role === "allocation_agent")!;
  const followUpSpecialists = ["affirmation_matching_agent", "settlement_reconciliation_agent", "exception_investigation_agent"].map(
    (role) => AGENT_POLICIES.find((p) => p.role === role)!,
  );
  const compiler = AGENT_POLICIES.find((p) => p.role === "compliance_reporting_agent")!;
  // The one role each sub-domain doesn't share with the other — allocation_agent
  // (Equities) vs. instrument_classification_agent (Fixed Income). Everything else
  // between the two domains is the same 6 roles.
  const domainSpecialist = domain === "equities" ? allocation : instrumentClassification;
  const agentPolicies = AGENT_POLICIES.filter(
    (p) => p.role !== (domain === "equities" ? "instrument_classification_agent" : "allocation_agent"),
  );
  const caseIds = CASE_IDS.filter((id) => CASE_META[id].domain === domain);

  return (
    <div className="description-tab">
      <section className="desc-section">
        <h2>What this demo shows</h2>
        <p>{copy.intro}</p>
        <p>
          AutoPIL is the policy layer that decides, in real time, what each agent can
          see. When an agent reaches for data outside its lane — desk P&amp;L,
          commission, another client's position, raw client PII, a penalty calc before
          a shortfall is even confirmed — AutoPIL blocks it and logs why, the same way
          it would in production, not because the demo told it not to look there. And
          no settlement disposition happens on an AI's say-so: a human reviewer signs
          off or overrides every recommendation before it's final — at one of two
          review tiers, depending on real severity signals grounded in fixture data,
          never the case ID.
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
          <p>{copy.technical}</p>
        </details>
      </section>

      <section className="desc-section">
        <h2>The {agentPolicies.length} agents</h2>
        <div className="flow-diagram">
          <div className="flow-box flow-orchestrator">
            <div className="flow-box-title">{orchestrator.displayName}</div>
            <div className="flow-box-sub">{orchestrator.description}</div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-branch-label">{copy.orchestratorBranch}</div>
          <div className="flow-box flow-specialist">
            <div className="flow-box-title">{orderIntake.displayName}</div>
            <div className="flow-box-sub">{orderIntake.description}</div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-box flow-specialist">
            <div className="flow-box-title">{domainSpecialist.displayName}</div>
            <div className="flow-box-sub">{domainSpecialist.description}</div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-branch-label">{copy.specialistBranch}</div>
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
              Tier 1 (ops-analyst) for routine corrections and proactive escalations,
              Tier 2 (compliance-officer) for escalated settlement-risk events (Reg SHO
              for equities, FICC's named Fails Charge Trading Practice for fixed income)
              — computed from real fixture data, never the case ID. Approve or override,
              a written note is required either way, at either tier. See DESIGN.md.
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
          {agentPolicies.map((p) => (
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
          mechanism that enforces it, not a bare compliance-sounding label. Shown here
          is the full Trading Desk Ops framework — the policy layer underneath both
          Equities and Fixed Income is shared, so a rule that grounds the other
          domain's own scenarios still applies to the same underlying agents and
          sources.
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
        <h2>The {caseIds.length} cases</h2>
        <div className="case-grid">
          {caseIds.map((caseId) => {
            const info = CASE_INFO[caseId];
            const meta = CASE_META[caseId];
            return (
              <div key={caseId} className="case-card case-card-static">
                <div className="case-card-top">
                  <span className="case-card-id">{caseId}</span>
                  <span className="case-card-time">{info.estimatedTime}</span>
                </div>
                <span className={`domain-badge domain-badge-${meta.domain}`}>{DOMAIN_LABELS[meta.domain]}</span>
                <div className="case-card-title">{info.title}</div>
                <div className="case-card-meta">
                  {meta.symbol} · {meta.side} {meta.totalQuantity.toLocaleString()} {meta.quantityUnit}
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
