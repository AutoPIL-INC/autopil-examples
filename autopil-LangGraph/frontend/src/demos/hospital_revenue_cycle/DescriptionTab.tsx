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
  const specialists = AGENT_POLICIES.slice(1, 5);
  const billingCompliance = AGENT_POLICIES[5];

  return (
    <div className="description-tab">
      <section className="desc-section">
        <h2>What this demo shows</h2>
        <p>
          Six AI agents work a hospital revenue-cycle case the way a real clinical
          documentation, coding, and billing team would — an orchestrator, a clinical
          documentation specialist, a CDI (clinical documentation improvement) specialist,
          a medical coder, a charge reconciliation agent, and a billing compliance
          reviewer — each given access to more patient data than it's actually allowed to
          use.
        </p>
        <p>
          AutoPIL is the policy layer that decides, in real time, what each agent can see.
          When an agent reaches for PHI outside its lane, AutoPIL blocks it and logs why —
          the same way it would in production, not because the demo told it not to look
          there. And no claim correction happens on an AI's say-so: a human revenue-cycle
          reviewer signs off or overrides every recommendation before it's final.
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
            toward an out-of-scope source on its own — not a scripted demo beat. No live
            EHR or billing system is involved anywhere — every guarded getter reads from
            simulated fixture data.
          </p>
        </details>
      </section>

      <section className="desc-section">
        <h2>The 6 agents</h2>
        <div className="flow-diagram">
          <div className="flow-box flow-orchestrator">
            <div className="flow-box-title">{orchestrator.displayName}</div>
            <div className="flow-box-sub">{orchestrator.description}</div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-branch-label">routes to 1–4 specialists, in whatever order it reasons makes sense</div>
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
            <div className="flow-box-title">{billingCompliance.displayName}</div>
            <div className="flow-box-sub">{billingCompliance.description}</div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-box flow-sar">
            <div className="flow-box-title">Revenue Summary</div>
            <div className="flow-box-sub">
              {orchestrator.displayName} compiles the final revenue-recovery narrative from
              compiled findings only — same role it plays at intake, reused rather than a
              separate 7th role.
            </div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-box flow-review">
            <div className="flow-box-title">Human Revenue-Cycle Review</div>
            <div className="flow-box-sub">Approve the proposed disposition, or override it — see DESIGN.md.</div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-box flow-decision">
            <div className="flow-box-title">Final Disposition</div>
            <div className="flow-box-sub">Rule-based, not LLM-improvised — an LLM can draft the narrative, it shouldn't decide the billing action.</div>
          </div>
        </div>
      </section>

      <section className="desc-section">
        <h2>Each agent's AutoPIL policy</h2>
        <p>
          This is the actual enforcement boundary — mirrored from{" "}
          <code>policies/healthcare/revenue_cycle.yaml</code>, not invented for display.
          Every allowed/denied source below is checked by AutoPIL at retrieval time,
          regardless of what the agent's own toolbelt makes available.
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
        <h2>The 4 encounters</h2>
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
