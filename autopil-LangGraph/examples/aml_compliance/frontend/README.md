# AML & Compliance — Live Audit-Trail Feed

Vite + React + TypeScript viewer for the AML & compliance demo one level up. Two
tabs:

- **Description** (`DescriptionTab.tsx`) — static reference: a visual flow diagram of
  the 3-role investigation chain, each one's actual AutoPIL policy mirrored from
  `policies/financial_services/aml_compliance.yaml` (see `policyData.ts`), the
  regulations it maps to, and a summary of all 5 cases. No server connection.
- **Execution** (`ExecutionTab.tsx`) — the live run. Streams the same events the CLI
  script prints — intake, each role's `[ok]`/`[DENIED]` tool calls, findings, and the
  final disposition — live, via
  [`@langchain/langgraph-sdk`](https://www.npmjs.com/package/@langchain/langgraph-sdk)'s
  `useStream()` hook against a local `langgraph dev` server. A dropdown picks which
  model runs the investigation — Ollama (local, default), Gemini, Claude/Anthropic, or
  Groq — set via `AMLCaseState["provider"]` on submit. Before the disposition is
  final, the run pauses for a human reviewer to Approve or Override it via
  `stream.interrupt`/`stream.submit({command: {resume: ...}})`.

See [`../README.md`](../README.md#run-live-viewer) for setup and run instructions.
