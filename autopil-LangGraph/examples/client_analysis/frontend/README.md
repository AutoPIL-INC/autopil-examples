# Client Analysis — Live Audit-Trail Feed

Vite + React + TypeScript viewer for the client analysis demo one level up. Two
tabs:

- **Description** (`DescriptionTab.tsx`) — static reference: an orchestration flow
  diagram, each role's actual AutoPIL policy mirrored from
  `policies/financial_services/client_analysis.yaml` (see `policyData.ts`), the
  regulations it maps to, and a summary of all 3 requests. No server connection.
- **Execution** (`ExecutionTab.tsx`) — the live run. Streams the same events the CLI
  script prints — orchestrator role/task assignment, each role's `[ok]`/`[DENIED]` tool
  calls, findings, and the final outcome classification — live, via
  [`@langchain/langgraph-sdk`](https://www.npmjs.com/package/@langchain/langgraph-sdk)'s
  `useStream()` hook against a local `langgraph dev` server. A dropdown picks which
  model runs the request — Ollama (local, default), AWS Bedrock, Gemini, Claude/Anthropic,
  or Groq — set via `GovernanceState["provider"]` on submit.

See [`../README.md`](../README.md#run-live-viewer) for setup and run instructions.
