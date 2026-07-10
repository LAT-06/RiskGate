# RiskGate

Local-first transaction risk assessment and fraud investigation platform, integrated with a minimal banking simulator. See [docs/MVP.md](docs/MVP.md) for the full roadmap and [AGENTS.md](AGENTS.md) for engineering rules.

## Repository layout

```text
apps/
  customer-web/          Vue 3 customer banking UI
  analyst-dashboard/     Vue 3 analyst investigation UI
services/
  banking-service/       Customers, beneficiaries, devices
  transaction-service/   Transaction lifecycle & orchestration
  ledger-service/        Balances, reservations, entries
  risk-service/          YAML policy evaluation → ALLOW/CHALLENGE/HOLD/DENY
  investigation-service/ Cases, analyst decisions, agent & RAG
packages/
  contracts/             Shared API/event schemas and identifiers
  shared-observability/  Logging & correlation helpers
  test-utilities/        Shared test helpers
policies/                Versioned YAML risk policies
knowledge-base/          Fraud playbooks for RAG
infrastructure/          Docker & (later) Terraform
docs/                    Architecture & security documentation
```

## Prerequisites

- Python ≥ 3.12 with [uv](https://docs.astral.sh/uv/)
- Node ≥ 20 with [pnpm](https://pnpm.io/)
- Docker + Compose (optional, for containerized dev)

## Quickstart

```bash
make install          # uv sync + pnpm install
cp .env.example .env  # fill in DATABASE_URL, GROQ_API_KEY

# Run one backend service
uv run --package risk-service uvicorn risk_service.main:app --port 8004 --reload

# Run the frontends
pnpm dev
```

Each service exposes `GET /health`.

## Checks

```bash
make lint       # ruff + prettier/vue-tsc
make typecheck  # mypy + vue-tsc
make test       # pytest + frontend tests
```
