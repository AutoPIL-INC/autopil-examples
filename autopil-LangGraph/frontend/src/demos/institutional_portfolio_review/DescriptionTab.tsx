import { AGENT_POLICIES, REGULATIONS, type AgentPolicy } from "./policyData";
import { REQUEST_IDS, REQUEST_INFO } from "./types";

function PolicyCard({ policy }: { policy: AgentPolicy }) {
  return (
    <div className="policy-card">
      <div className="policy-card-name">
        {policy.displayName}{" "}
        <span className="chip" style={{ marginLeft: 6 }}>{policy.policyFile}.yaml</span>
      </div>
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
  const wealthPolicies = AGENT_POLICIES.filter((p) => p.policyFile === "wealth");
  const riskPolicies = AGENT_POLICIES.filter((p) => p.policyFile === "risk");

  return (
    <div className="description-tab">
      <section className="desc-section">
        <h2>What this demo shows</h2>
        <p>
          Eleven roles — one orchestrator plus ten specialists — enforced under{" "}
          <strong>two real AutoPIL policy files at once</strong>:{" "}
          <code>portfolio_review_wealth.yaml</code> (wealth-advisory roles) and{" "}
          <code>portfolio_review_risk.yaml</code> (risk/compliance roles). Which policy
          file governs a role is a property of the <em>role</em>, not the source it's
          reaching for — <code>credit_scores</code>, <code>loan_history</code>,{" "}
          <code>identity_records</code>, and <code>risk_models</code> are referenced by
          roles from <strong>both</strong> files, each evaluated under whichever file
          that specific role's policy lives in.
        </p>
        <p>
          Every role is handed the same full toolbelt across both catalogs — nothing in
          the tool layer restricts what a role can reach for. An orchestrator reads a
          natural-language review request and classifies it into a review type, which
          maps to a real institutional workflow (research → advisory → rebalancing →
          settlement → reporting) — modeling the process, not scripting a violation.
          What each role reaches for <em>within</em> its step stays fully emergent.
        </p>
      </section>

      <section className="desc-section">
        <h2>Orchestration flow</h2>
        <div className="flow-diagram">
          <div className="flow-box flow-orchestrator">
            <div className="flow-box-title">Portfolio Orchestrator</div>
            <div className="flow-box-sub">Classifies the request into a review type, which expands into an ordered role/task plan.</div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-branch-label">quarterly_review's plan — the flagship, longest chain (max 4 roles, kept short deliberately)</div>
          <div className="flow-row">
            <div className="flow-box flow-specialist">
              <div className="flow-box-title">Investment Analyst</div>
              <div className="flow-box-sub">market_analysis</div>
            </div>
            <div className="flow-box flow-specialist">
              <div className="flow-box-title">Wealth Advisor</div>
              <div className="flow-box-sub">portfolio_review</div>
            </div>
            <div className="flow-box flow-specialist">
              <div className="flow-box-title">Rebalancing Agent</div>
              <div className="flow-box-sub">rebalancing_recommendation</div>
            </div>
            <div className="flow-box flow-specialist">
              <div className="flow-box-title">Report Generator</div>
              <div className="flow-box-sub">quarterly_review</div>
            </div>
          </div>
          <div className="flow-branch-label">the other 4 review types are shorter — 1 to 3 roles each</div>
          <div className="flow-arrow-down" />
          <div className="flow-box flow-review">
            <div className="flow-box-title">Orchestrator Review</div>
            <div className="flow-box-sub">Continues to the next step, or — for fiduciary_benchmark only — escalates once to investment_analyst if wealth_advisor was blocked.</div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-box flow-decision">
            <div className="flow-box-title">Outcome Classification</div>
            <div className="flow-box-sub">Grounded in the real audit trail per role, not each role's self-report alone.</div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-box flow-review">
            <div className="flow-box-title">Supervisor Review</div>
            <div className="flow-box-sub">Approve the proposed outcome, or override it — see DESIGN.md's human-in-the-loop section.</div>
          </div>
        </div>
      </section>

      <section className="desc-section">
        <h2>The 5 review types</h2>
        <div className="case-grid">
          {REQUEST_IDS.map((requestId) => {
            const info = REQUEST_INFO[requestId];
            return (
              <div key={requestId} className="case-card case-card-static">
                <div className="case-card-top">
                  <span className="case-card-id">{requestId}</span>
                  <span className="case-card-time">{info.estimatedTime}</span>
                </div>
                <div className="case-card-title">{info.title}</div>
                <div className="case-card-description">{info.description}</div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="desc-section">
        <h2>Wealth-advisory roles (portfolio_review_wealth.yaml)</h2>
        <p>
          Client profile, portfolio, and market/research data. The fiduciary wall lives
          here: <code>wealth_advisor</code> is denied{" "}
          <code>catalog.wealth.other_client_portfolios</code> outright, while{" "}
          <code>investment_analyst</code> — the correct role for peer benchmarking — is
          explicitly authorized for it.
        </p>
        <div className="policy-grid">
          {wealthPolicies.map((p) => <PolicyCard key={p.role} policy={p} />)}
        </div>
      </section>

      <section className="desc-section">
        <h2>Risk & compliance roles (portfolio_review_risk.yaml)</h2>
        <p>
          AML, credit, and settlement data. <code>settlement_agent</code> is new here —
          the demo this was adapted from had tool functions for it but no matching
          policy at all, so every call it made was denied by default. It has a real
          policy in this version.
        </p>
        <div className="policy-grid">
          {riskPolicies.map((p) => <PolicyCard key={p.role} policy={p} />)}
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
    </div>
  );
}
