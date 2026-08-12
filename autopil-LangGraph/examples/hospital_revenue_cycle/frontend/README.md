# Hospital Revenue Cycle — Live Audit-Trail Feed

Vite + React + TypeScript viewer for the hospital_revenue_cycle demo one level up. Two
tabs:

- **Description** (`DescriptionTab.tsx`) — static reference: a visual flow diagram of
  the 6 agents, each one's actual AutoPIL policy mirrored from
  `policies/healthcare/revenue_cycle.yaml` (see `policyData.ts`), the regulations it
  maps to, and a summary of all 4 encounters. No server connection.
- **Execution** (`ExecutionTab.tsx`) — the live run. Streams the same events the CLI
  script prints — orchestrator routing, each specialist's `[ok]`/`[DENIED]` tool calls,
  findings, and the final disposition — live, via
  [`@langchain/langgraph-sdk`](https://www.npmjs.com/package/@langchain/langgraph-sdk)'s
  `useStream()` hook against a local `langgraph dev` server (`assistantId:
  "hospital_revenue_cycle"`). A dropdown picks which model runs the review — Ollama
  (local, default), Gemini, Claude/Anthropic, or Groq — set via
  `InvestigationState["provider"]` on submit. Before the disposition is final, the run
  pauses for a human revenue-cycle reviewer to Approve or Override it via
  `stream.interrupt`/`stream.submit({command: {resume: ...}})`.

## Run

```bash
# Terminal 1 — serve the graph (from the repo root, i.e. autopil-LangGraph/)
.venv/bin/langgraph dev

# Terminal 2 — this viewer
cd examples/hospital_revenue_cycle/frontend
npm install
npm run dev
```

Open the printed Vite URL (`http://localhost:5173`).
