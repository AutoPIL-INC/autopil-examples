# Institutional Portfolio Review — Live Audit-Trail Feed

Vite + React + TypeScript viewer for the institutional portfolio review demo one level
up. Two tabs:

- **Description** (`DescriptionTab.tsx`) — static reference: an orchestration flow
  diagram, the 11 roles split by which of the two real AutoPIL policy files governs
  them (`policies/financial_services/portfolio_review_wealth.yaml` /
  `portfolio_review_risk.yaml`, mirrored in `policyData.ts`), the regulations they map
  to, and a summary of all 5 review types. No server connection.
- **Execution** (`ExecutionTab.tsx`) — the live run. Streams the same events the CLI
  script prints — the orchestrator's review-type classification and role/task plan,
  each role's `[ok]`/`[DENIED]` tool calls, findings, and the outcome classification —
  live, via
  [`@langchain/langgraph-sdk`](https://www.npmjs.com/package/@langchain/langgraph-sdk)'s
  `useStream()` hook against a local `langgraph dev` server. A dropdown picks which
  model runs the review — Ollama (local, default), AWS Bedrock, Gemini,
  Claude/Anthropic, or Groq — set via `ReviewState["provider"]` on submit. Before the
  outcome is final, the run pauses for a supervisor to Approve or Override it via
  `stream.submit({command: {resume: ...}})`.

See [`../README.md`](../README.md#run-live-viewer) for setup and run instructions.
