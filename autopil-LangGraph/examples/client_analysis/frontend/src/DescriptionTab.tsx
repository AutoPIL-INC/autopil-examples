import { AGENT_POLICIES, REGULATIONS, type AgentPolicy } from "./policyData";
import { CUSTOMER_IDS, CLIENT_REVIEWS } from "./types";

function PolicyCard({ policy }: { policy: AgentPolicy }) {
  return (
    <div className="policy-card">
      <div className="policy-card-name">{policy.displayName}</div>
      <div className="policy-card-desc">{policy.description}</div>
      <div className="policy-card-row">
        <span className="policy-label">Allowed</span>
        <div className="chip-list">
          {policy.allowedSources.length === 0
            ? <span className="chip chip-denied">none listed — see denied below</span>
            : policy.allowedSources.map((s) => (
                <span key={s} className="chip chip-allowed">{s}</span>
              ))}
        </div>
      </div>
      <div className="policy-card-row">
        <span className="policy-label">Denied</span>
        <div className="chip-list">
          {policy.deniedSources.length === 0
            ? <span className="chip chip-allowed">none — gated by task_bindings / sensitivity instead</span>
            : policy.deniedSources.map((s) => (
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
  const [junior, senior, wealth] = AGENT_POLICIES;

  return (
    <div className="description-tab">
      <section className="desc-section">
        <h2>What this demo shows</h2>
        <p>
          Three roles — junior analyst, senior analyst, wealth advisor — share the{" "}
          <strong>exact same toolbelt</strong>: all 8 Unity Catalog tables are offered
          to every role, with no restriction in the tool layer at all. "You don't give
          each role a different tool set. You give every agent the same tools and let
          policy control what succeeds." AutoPIL's <code>guard.protect()</code> is what
          actually decides what each role can reach, at retrieval time.
        </p>
        <p>
          Every customer review starts at junior_analyst. That tier gathers data with
          its own tool-calling loop, proposes a concrete next action for the client, and
          a human reviewer decides: approve it, override it with a different action, or
          escalate the case to the next tier for a second look — senior_analyst, then
          wealth_advisor. When a denial happens on the Execution tab, it's because a
          tier reasoned its way toward a source its task doesn't cover, exercising one
          of four distinct enforcement paths: <code>denied_sources</code>,{" "}
          <code>denied_tasks</code>, <code>task_bindings</code> purpose limitation, or
          the sensitivity ceiling.
        </p>
      </section>

      <section className="desc-section">
        <h2>Escalation flow</h2>
        <div className="flow-diagram">
          <div className="flow-box flow-orchestrator">
            <div className="flow-box-title">Intake</div>
            <div className="flow-box-sub">Looks up the customer's review reason — every case starts at junior_analyst.</div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-box flow-specialist">
            <div className="flow-box-title">{junior.displayName}</div>
            <div className="flow-box-sub">{junior.description}</div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-box flow-review">
            <div className="flow-box-title">Human Review — Junior Tier</div>
            <div className="flow-box-sub">Approve the proposed action, override it, or escalate to senior_analyst.</div>
          </div>
          <div className="flow-branch-label">escalate</div>
          <div className="flow-box flow-specialist">
            <div className="flow-box-title">{senior.displayName}</div>
            <div className="flow-box-sub">{senior.description}</div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-box flow-review">
            <div className="flow-box-title">Human Review — Senior Tier</div>
            <div className="flow-box-sub">Approve, override, or escalate to wealth_advisor.</div>
          </div>
          <div className="flow-branch-label">escalate</div>
          <div className="flow-box flow-specialist">
            <div className="flow-box-title">{wealth.displayName}</div>
            <div className="flow-box-sub">{wealth.description}</div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-box flow-review">
            <div className="flow-box-title">Human Review — Wealth Advisor Tier</div>
            <div className="flow-box-sub">Top of the chain — approve or override only, nothing left to escalate to.</div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-box flow-decision">
            <div className="flow-box-title">Disposition</div>
            <div className="flow-box-sub">Records which tier closed the case, the full path of tiers visited, and every human decision along the way.</div>
          </div>
        </div>
      </section>

      <section className="desc-section">
        <h2>Each role's AutoPIL policy</h2>
        <p>
          This is the actual enforcement boundary — mirrored from{" "}
          <code>policies/financial_services/client_analysis.yaml</code>, not
          invented for display. Every allowed/denied source below is checked by AutoPIL
          at retrieval time, regardless of what the role's own toolbelt makes available.
        </p>
        <div className="policy-grid">
          {AGENT_POLICIES.map((p) => (
            <PolicyCard key={p.role} policy={p} />
          ))}
        </div>
      </section>

      <section className="desc-section">
        <h2>Regulations this maps to</h2>
        <ul className="regulation-list">
          {REGULATIONS.map((r) => (
            <li key={r.id}>
              <span className="regulation-id">{r.id}</span> — {r.name}
            </li>
          ))}
        </ul>
      </section>

      <section className="desc-section">
        <h2>The 5 customers</h2>
        <p>
          Mixed complexity by design — some close at junior_analyst, some escalate
          once, one can reach all the way to wealth_advisor. Which tiers a case
          actually visits depends on what each tier's own finding recommends and what
          the human reviewer decides at each step — not guaranteed on every run, same
          disclosure as the fraud investigation demo's own cases.
        </p>
        <div className="case-grid">
          {CUSTOMER_IDS.map((customerId) => {
            const review = CLIENT_REVIEWS[customerId];
            return (
              <div key={customerId} className="case-card case-card-static">
                <div className="case-card-top">
                  <span className="case-card-id">{customerId}</span>
                  <span className="case-card-time">Priority: {review.priority}</span>
                </div>
                <div className="case-card-description">{review.reasonForReview}</div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
