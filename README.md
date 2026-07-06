# AutoPIL Examples

Sample implementations showing how to use [AutoPIL](https://autopil.ai) — a runtime
policy enforcement, audit logging, and agent registry layer for AI agents — with
different agent frameworks.

## Contents

| Directory | Framework | What it shows |
|---|---|---|
| [`autopil-LangGraph`](./autopil-LangGraph) | LangGraph | Basics (`01_basics.py`), a multi-agent fraud investigation demo, and a client analysis demo (Databricks Unity Catalog + AWS Bedrock) — see [fraud investigation README](./autopil-LangGraph/examples/fraud_investigation/README.md) and [client analysis README](./autopil-LangGraph/examples/client_analysis/README.md) |

## Setup

Each example directory is self-contained with its own `requirements.txt` and
`.env.example`. See the README inside each directory for setup and run instructions.

Each `autopil-LangGraph` demo also has its own standalone live-viewer frontend, or you
can run [`autopil-LangGraph/frontend`](./autopil-LangGraph/frontend) once to get every
demo from a single `npm run dev` server.
