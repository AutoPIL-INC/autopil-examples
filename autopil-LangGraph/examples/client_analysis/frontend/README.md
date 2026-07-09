# Client Analysis — Live Audit-Trail Feed

Vite + React + TypeScript viewer for the client analysis demo one level up. Two
tabs:

- **Description** (`DescriptionTab.tsx`) — static reference: the 3-tier escalation flow
  diagram, each role's actual AutoPIL policy mirrored from
  `policies/financial_services/client_analysis.yaml` (see `policyData.ts`), the
  regulations it maps to, and a summary of all 5 customers in the queue. No server
  connection.
- **Execution** (`ExecutionTab.tsx`) — the live run. Streams the same events the CLI
  script prints — intake, each tier's `[ok]`/`[DENIED]` tool calls and proposed action —
  live, via
  [`@langchain/langgraph-sdk`](https://www.npmjs.com/package/@langchain/langgraph-sdk)'s
  `useStream()` hook against a local `langgraph dev` server. A case can pause up to 3
  times (once per tier it reaches); the review panel lets you approve, override, or
  escalate at each pause, tracked via a `resolvedTiers` set rather than a single
  boolean so a later tier's review shows up correctly even after an earlier one was
  resolved. A dropdown picks which model runs the review — Ollama (local, default), AWS
  Bedrock, Gemini, Claude/Anthropic, or Groq — set via `ClientReviewState["provider"]`
  on submit.

See [`../README.md`](../README.md#run-live-viewer) for setup and run instructions.
