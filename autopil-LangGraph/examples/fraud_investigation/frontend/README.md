# Fraud Investigation — Live Audit-Trail Feed

Vite + React + TypeScript viewer for the fraud investigation demo one level up. Streams
the same events the CLI script prints — orchestrator routing, each specialist's
`[ok]`/`[DENIED]` tool calls, findings, and the final disposition — live, via
[`@langchain/langgraph-sdk`](https://www.npmjs.com/package/@langchain/langgraph-sdk)'s
`useStream()` hook against a local `langgraph dev` server.

A dropdown lets you pick which model runs the investigation — Gemini (free, default),
Claude/Anthropic, Groq, or a local Ollama model — set via
`InvestigationState["provider"]` on submit. Before the disposition is final, the run
pauses for a human reviewer to Approve or Override it via
`stream.interrupt`/`stream.submit({command: {resume: ...}})`.

See [`../README.md`](../README.md#run-live-viewer) for setup and run instructions.
