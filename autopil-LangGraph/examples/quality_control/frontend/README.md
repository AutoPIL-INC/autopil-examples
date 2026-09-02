# Quality Control — Live Audit-Trail Feed

Vite + React + TypeScript viewer for the quality_control demo one level up. Two tabs:

- **Description** (`DescriptionTab.tsx`) — static reference: a visual flow diagram of
  the 5 agents (including the one deliberate departure from every sibling demo's
  shape — `defect_detection_agent` always runs first via a fixed graph edge, not an
  LLM routing choice), each one's actual AutoPIL policy mirrored from
  `policies/manufacturing/quality_control.yaml` (see `policyData.ts`), the
  regulations it maps to, and a summary of all 4 cases. No server connection.
- **Execution** (`ExecutionTab.tsx`) — the live run. Streams the same events the CLI
  script prints — the orchestrator's fixed first step, the re-routing loop among the
  3 follow-up specialists, each specialist's `[ok]`/`[DENIED]` tool calls, findings,
  and the final disposition — live, via
  [`@langchain/langgraph-sdk`](https://www.npmjs.com/package/@langchain/langgraph-sdk)'s
  `useStream()` hook against a local `langgraph dev` server (`assistantId:
  "quality_control"`). A dropdown picks which model runs the investigation — Ollama
  (local, default), Gemini, Claude/Anthropic, or Groq — set via
  `InvestigationState["provider"]` on submit. Before the disposition is final, the
  run pauses for a human quality reviewer to Approve or Override it via
  `stream.interrupt`/`stream.submit({command: {resume: ...}})`. Unlike this repo's
  other human-in-the-loop demos, **a written note is required to Approve, not just to
  Override** — `decision_node` itself re-interrupts on an empty note, and this UI
  disables both buttons until one is typed, so a disposition can never finalize with
  no rationale on record.

## Run

```bash
# Terminal 1 — serve the graph (from the repo root, i.e. autopil-LangGraph/)
.venv/bin/langgraph dev

# Terminal 2 — this viewer
cd examples/quality_control/frontend
npm install
npm run dev
```

Open the printed Vite URL (`http://localhost:5173`).
