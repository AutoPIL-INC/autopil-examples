# AutoPIL Examples

Sample implementations showing how to use [AutoPIL](https://autopil.ai) — a runtime
policy enforcement, audit logging, and agent registry layer for AI agents — with
different agent frameworks.

## Demos

All demos below live under [`autopil-LangGraph`](./autopil-LangGraph), orchestrated
with [LangGraph](https://www.langchain.com/langgraph). Each is reasoning-driven: agents
get a real tool-calling loop and a toolbelt wider than their AutoPIL policy actually
authorizes, so a denial happens because the model reasoned its way toward an
out-of-scope source — not because a scripted branch forced it to.

| Demo | What it shows | Links |
|---|---|---|
| **Fraud Investigation** | 5 specialist agents (orchestrator, transaction analyst, account profiler, KYC specialist, SAR generator) investigate fraud cases, with a human-in-the-loop compliance review before the disposition is final. | [README](./autopil-LangGraph/examples/fraud_investigation/README.md) · [DESIGN](./autopil-LangGraph/examples/fraud_investigation/DESIGN.md) |
| **Client Analysis** | 3 roles (junior analyst, senior analyst, wealth advisor) share the *exact same* Databricks Unity Catalog toolbelt — AutoPIL's policy, not the tool layer, decides what each role can reach, including purpose limitation (`task_bindings`) and a sensitivity-ceiling case. AWS Bedrock-first provider chain. | [README](./autopil-LangGraph/examples/client_analysis/README.md) · [DESIGN](./autopil-LangGraph/examples/client_analysis/DESIGN.md) |
| **Institutional Portfolio Review** | 8 roles enforced under *two* real AutoPIL policy files at once — which file governs a role is a property of the role, not the source it reaches for. A single orchestrator classifies each review into a real institutional workflow (research → advisory → rebalancing → settlement → reporting). | [README](./autopil-LangGraph/examples/institutional_portfolio_review/README.md) · [DESIGN](./autopil-LangGraph/examples/institutional_portfolio_review/DESIGN.md) |
| **AML & Compliance** | 3 roles (AML investigator, KYC agent, compliance officer) run a fixed investigation chain — split out of Institutional Portfolio Review, where this financial-crime-governance workflow sat split across two policy files. One dedicated policy file, human-in-the-loop sign-off before the disposition is final. | [README](./autopil-LangGraph/examples/aml_compliance/README.md) · [DESIGN](./autopil-LangGraph/examples/aml_compliance/DESIGN.md) |

Also included: [`01_basics.py`](./autopil-LangGraph/01_basics.py), a minimal
LangGraph nodes/edges/routing example with no AutoPIL involved.

## Setup

Each example directory is self-contained with its own `requirements.txt` and
`.env.example`. See the README inside each directory for setup and run instructions.

## Live viewer

Each demo has its own standalone browser frontend under `examples/<demo>/frontend/`.
Or run [`autopil-LangGraph/frontend`](./autopil-LangGraph/frontend) once to get every
demo from a single `npm run dev` server — same `langgraph dev` backend, one nav to
switch between demos instead of running a separate frontend per demo.
