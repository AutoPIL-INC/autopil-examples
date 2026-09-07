# Trading Desk Ops — Live Audit-Trail Feed

Vite + React + TypeScript viewer for the trading_desk_ops demo one level up. Two tabs:

- **Description** (`DescriptionTab.tsx`) — static reference: a visual flow diagram of
  the 7 agents (including the one departure from every sibling demo's shape —
  `trading_ops_orchestrator`'s trigger classification is a genuinely dynamic LLM
  decision that decides which specialist runs first, not a fixed graph edge), each
  one's actual AutoPIL policy mirrored from
  `policies/financial_services/trading_desk_ops.yaml` (see `policyData.ts`), the
  compliance framework it maps to (SEC Rule 15c6-1/15c6-2/15c3-3/17a-4, DTCC/NSCC CNS,
  Reg SHO, FINRA CAT, FINRA Rule 5310, information barriers/MNPI), and a summary of all
  5 EQ-### cases. No server connection.
- **Execution** (`ExecutionTab.tsx`) — the live run. Streams the same events the CLI
  script prints — the orchestrator's live trigger classification (and, when a role is
  genuinely not applicable to the trigger, a distinct "skipped" row — e.g.
  `order_intake_agent` on EQ-004's PM-rebalance path), the re-routing loop among the
  remaining specialists, each specialist's `[ok]`/`[DENIED]` tool calls (denials tied
  inline to whichever regulation actually grounds that boundary, where one applies),
  findings, and the final disposition — live, via
  [`@langchain/langgraph-sdk`](https://www.npmjs.com/package/@langchain/langgraph-sdk)'s
  `useStream()` hook against a local `langgraph dev` server (`assistantId:
  "trading_desk_ops"`). A dropdown picks which model runs the case — Ollama (local,
  default), Gemini, Claude/Anthropic, or Groq — set via
  `TradingOpsState["provider"]` on submit. Before the disposition is final, the run
  pauses for a human reviewer to Approve or Override it via
  `stream.interrupt`/`stream.submit({command: {resume: ...}})` — **at one of two
  reviewer tiers**, visually distinguished (a Tier 1 ops-analyst review renders with an
  accent border/badge; a Tier 2 compliance-officer review — the Reg SHO escalation
  path, EQ-005 — renders in red), computed server-side from real fixture data, never
  from the case ID. Same as `quality_control`'s reviewer form: **a written note is
  required to Approve, not just to Override**, at both tiers — `decision_node` itself
  re-interrupts on an empty note, and this UI disables both buttons until one is typed.

## Run

```bash
# Terminal 1 — serve the graph (from the repo root, i.e. autopil-LangGraph/)
.venv/bin/langgraph dev

# Terminal 2 — this viewer
cd examples/trading_desk_ops/frontend
npm install
npm run dev
```

Open the printed Vite URL (`http://localhost:5173`).
