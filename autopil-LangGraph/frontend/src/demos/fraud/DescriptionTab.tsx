import { AGENT_POLICIES, REGULATIONS, type AgentPolicy } from "./policyData";
import { CASE_IDS, CASE_INFO } from "./types";

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
  const specialists = AGENT_POLICIES.slice(1, 4);
  const sarGenerator = AGENT_POLICIES[4];

  return (
    <div className="description-tab">
      <section className="desc-section">
        <h2>What this demo shows</h2>
        <p>
          Five AI agents work a fraud case the way a real investigations team would — an
          orchestrator, a transaction analyst, an account profiler, a KYC specialist, and
          a report writer — each given access to more data than it's actually allowed to
          use.
        </p>
        <p>
          AutoPIL is the policy layer that decides, in real time, what each agent can see.
          When an agent reaches for data outside its lane, AutoPIL blocks it and logs why
          — the same way it would in production, not because the demo told it not to look
          there. And no case closes on an AI's say-so: a human compliance reviewer signs
          off or overrides every recommendation before it's final.
        </p>
        <details className="desc-technical">
          <summary>How this actually works, technically</summary>
          <p>
            Each specialist runs a real tool-calling loop — not a scripted branch — on
            whichever model you pick (Claude, Gemini, Groq, or Ollama), and each is handed
            a toolbelt <strong>wider</strong> than what its policy actually authorizes.
            Nothing in the code tells a specialist which of its tools are off-limits; it
            finds out the same way a production agent would: it calls a tool, and
            AutoPIL's <code>guard.protect()</code> either returns data or a denial reason.
          </p>
          <p>
            Every denial you see on the Execution tab is the model reasoning its way
            toward an out-of-scope source on its own — not a scripted demo beat.
          </p>
        </details>
      </section>

      <section className="desc-section">
        <h2>The 5 agents</h2>
        <div className="flow-diagram">
          <div className="flow-box flow-orchestrator">
            <div className="flow-box-title">{orchestrator.displayName}</div>
            <div className="flow-box-sub">{orchestrator.description}</div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-branch-label">routes to 1–3 specialists, in whatever order it reasons makes sense</div>
          <div className="flow-row">
            {specialists.map((p) => (
              <div key={p.role} className="flow-box flow-specialist">
                <div className="flow-box-title">{p.displayName}</div>
                <div className="flow-box-sub">{p.description}</div>
              </div>
            ))}
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-box flow-sar">
            <div className="flow-box-title">{sarGenerator.displayName}</div>
            <div className="flow-box-sub">{sarGenerator.description}</div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-box flow-review">
            <div className="flow-box-title">Human Compliance Review</div>
            <div className="flow-box-sub">Approve the proposed disposition, or override it — see DESIGN.md §7.4.</div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-box flow-decision">
            <div className="flow-box-title">Final Disposition</div>
            <div className="flow-box-sub">Rule-based, not LLM-improvised — an LLM can draft the narrative, it shouldn't decide the action.</div>
          </div>
        </div>
      </section>

      <section className="desc-section">
        <h2>Each agent's AutoPIL policy</h2>
        <p>
          This is the actual enforcement boundary — mirrored from{" "}
          <code>policies/financial_services/fraud_investigation.yaml</code>, not
          invented for display. Every allowed/denied source below is checked by AutoPIL
          at retrieval time, regardless of what the agent's own toolbelt makes available.
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
        <h2>The 5 cases</h2>
        <div className="case-grid">
          {CASE_IDS.map((caseId) => {
            const info = CASE_INFO[caseId];
            return (
              <div key={caseId} className="case-card case-card-static">
                <div className="case-card-top">
                  <span className="case-card-id">{caseId}</span>
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
