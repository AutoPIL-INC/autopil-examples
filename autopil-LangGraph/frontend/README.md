# AutoPIL Demos — Unified Live Feed

One Vite + React + TypeScript app covering every demo in `autopil-LangGraph/`, so you
don't need a separate `npm run dev` process per demo. This is **additive** — each
demo's own standalone frontend (`examples/fraud_investigation/frontend/`,
`examples/client_analysis/frontend/`) still works exactly as documented in its own
README, unchanged. Use whichever is more convenient: one demo in isolation, or all of
them from one server here.

Both demos already run on the same `langgraph dev` process (`http://localhost:2024`,
`langgraph.json` exposes both `fraud_investigation` and `client_analysis` graphs) — this
app just switches which `assistantId` it streams from based on which demo tab is
selected. No backend changes needed.

## Structure

- `src/App.tsx` — the demo switcher: a top-level nav (Fraud Investigation / Client
  Analysis), then the same Description/Execution sub-tabs each standalone app has.
- `src/demos/fraud/` — copied from `examples/fraud_investigation/frontend/src`
  (`types.ts`, `policyData.ts`, `DescriptionTab.tsx`, `ExecutionTab.tsx`).
- `src/demos/client_analysis/` — same, copied from
  `examples/client_analysis/frontend/src`.
- `src/LogoMark.tsx`, `src/index.css`, `src/App.css`, `src/main.tsx` — shared shell,
  identical to what each standalone frontend uses.

Each demo's `DescriptionTab.tsx`/`ExecutionTab.tsx` pair is self-contained (imports its
own sibling `./types`, `./policyData`), so nothing needed to change internally when
moving them here — only `App.tsx` is new.

## Run

```bash
# Terminal 1 — serve both graphs (from the repo root, i.e. autopil-LangGraph/)
.venv/bin/langgraph dev

# Terminal 2 — this app
cd frontend
npm install
npm run dev
```

Open the printed Vite URL. Pick a demo from the top nav, then Description or Execution
underneath, same as either standalone app.

## Keeping this in sync

If you change a demo's `DescriptionTab.tsx`/`ExecutionTab.tsx`/`types.ts`/`policyData.ts`
in its own `examples/*/frontend/src/`, copy the same change into the matching
`src/demos/<name>/` here — these are duplicated, not shared via a package, to keep each
standalone frontend fully independent and copy-pasteable on its own.
