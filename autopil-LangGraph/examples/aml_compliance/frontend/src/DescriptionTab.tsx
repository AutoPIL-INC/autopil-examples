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
  const [investigator, kyc, compliance] = AGENT_POLICIES;

  return (
    <div className="description-tab">
      <section className="desc-section">
        <h2>What this demo shows</h2>
        <p>
          Three specialist Claude/Gemini/Groq/Ollama agents, orchestrated with
          LangGraph, work an AML case under a real AutoPIL policy — split out of the
          institutional portfolio review demo, where this financial-crime-governance
          workflow sat split across two policy files despite being one coherent story.
          One dedicated policy file here instead. Each agent is a real tool-calling
          loop — not a scripted branch — and each is handed a toolbelt{" "}
          <strong>wider</strong> than what its policy actually authorizes. Nothing in
          the code tells an agent which of its tools are off-limits; it finds out the
          same way a production agent would: it calls a tool, and AutoPIL's{" "}
          <code>guard.protect()</code> either returns data or a denial reason.
        </p>
        <p>
          Every case runs the same fixed sequence — the AML investigator looks at
          transaction and watchlist signal, the KYC agent verifies identity, the
          compliance officer reviews and signs off. When a denial happens on the
          Execution tab, it's because the model reasoned its way toward an
          out-of-scope source on its own. Before the final disposition is written, a
          human compliance reviewer gets the last word: approve the proposed action,
          or override it.
        </p>
      </section>

      <section className="desc-section">
        <h2>The investigation chain</h2>
        <div className="flow-diagram">
          <div className="flow-box flow-orchestrator">
            <div className="flow-box-title">Intake</div>
            <div className="flow-box-sub">Looks up the case's reason for review — every case runs the same 3-role sequence, in the same order.</div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-box flow-specialist">
            <div className="flow-box-title">{investigator.displayName}</div>
            <div className="flow-box-sub">{investigator.description}</div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-box flow-specialist">
            <div className="flow-box-title">{kyc.displayName}</div>
            <div className="flow-box-sub">{kyc.description}</div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-box flow-sar">
            <div className="flow-box-title">{compliance.displayName}</div>
            <div className="flow-box-sub">{compliance.description}</div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-box flow-review">
            <div className="flow-box-title">Human Compliance Review</div>
            <div className="flow-box-sub">Approve the proposed disposition, or override it.</div>
          </div>
          <div className="flow-arrow-down" />
          <div className="flow-box flow-decision">
            <div className="flow-box-title">Final Disposition</div>
            <div className="flow-box-sub">Rule-based, grounded in the real signal data — not any role's self-reported finding, and not LLM-improvised.</div>
          </div>
        </div>
      </section>

      <section className="desc-section">
        <h2>Each agent's AutoPIL policy</h2>
        <p>
          This is the actual enforcement boundary — mirrored from{" "}
          <code>policies/financial_services/aml_compliance.yaml</code>, not
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
        <p>
          Mixed severity by design — a genuine SAR-worthy pattern, a watchlist false
          positive, a compliance-process case with no transaction signal at all, a
          routine cross-client audit, and a clean case that clears at every step.
        </p>
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
