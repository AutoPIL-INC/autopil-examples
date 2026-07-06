import { AGENT_POLICIES, REGULATIONS, type AgentPolicy } from "./policyData";
import { REQUEST_IDS, REQUEST_INFO } from "./types";

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
          An orchestrator reads a natural-language business request and decides which
          role should handle it and what task/purpose it falls under — that's a real
          model decision, not a lookup table. When a denial happens on the Execution
          tab, it's because the assigned role reasoned its way toward a source its task
          doesn't cover, exercising one of four distinct enforcement paths:{" "}
          <code>denied_sources</code>, <code>denied_tasks</code>,{" "}
          <code>task_bindings</code> purpose limitation, or the sensitivity ceiling.
        </p>
      </section>

      <section className="desc-section">
        <h2>Orchestration flow</h2>
        <div className="flow-diagram">
          <div className="flow-box flow-orchestrator">
            <div className="flow-box-title">Governance Orchestrator</div>
            <div className="flow-box-sub">Reads the request, assigns a role and a task_type — the purpose the request falls under.</div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-branch-label">assigned to exactly one of the three roles</div>
          <div className="flow-row">
            <div className="flow-box flow-specialist">
              <div className="flow-box-title">{junior.displayName}</div>
              <div className="flow-box-sub">{junior.description}</div>
            </div>
            <div className="flow-box flow-specialist">
              <div className="flow-box-title">{senior.displayName}</div>
              <div className="flow-box-sub">{senior.description}</div>
            </div>
            <div className="flow-box flow-specialist">
              <div className="flow-box-title">{wealth.displayName}</div>
              <div className="flow-box-sub">{wealth.description}</div>
            </div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-box flow-review">
            <div className="flow-box-title">Orchestrator Review</div>
            <div className="flow-box-sub">If the assigned role was blocked, decide whether to escalate to senior_analyst (one attempt) or accept the outcome as final.</div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-box flow-decision">
            <div className="flow-box-title">Outcome Classification</div>
            <div className="flow-box-sub">Grounded in the real audit trail, not the model's self-report alone — completed, completed-with-intervention, or blocked.</div>
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
        <h2>The 3 requests</h2>
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
    </div>
  );
}
