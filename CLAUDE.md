# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

READ [AGENTS.md](./AGENTS.md) first — it defines the engineering principles, system boundaries, security requirements, and git conventions for this repo. [docs/MVP.md](./docs/MVP.md) is the roadmap; work follows its milestone order, and milestone completion criteria must be met before moving on.

## What this is

RiskGate is a transaction risk assessment and fraud investigation platform. A minimal banking simulator (customer web + banking service) exists only to generate realistic data; RiskGate is the product. Local-first now, AWS later (Milestone 9).

## Commands

Python is managed by uv (workspace members: `services/*`, `packages/*`); frontends by pnpm. `make install` runs `uv sync --all-packages` + `pnpm install`.

```bash
make test        # uv run pytest + pnpm test
make lint        # ruff check + ruff format --check + prettier --check
make typecheck   # mypy packages, then mypy per service dir, then vue-tsc
make format      # ruff format + prettier --write
make dev         # docker compose up --build (all 5 backend services)
make migrate     # alembic upgrade head for every service with an alembic.ini
```

Run a single test / single service's tests:

```bash
uv run pytest services/risk-service/tests/test_health.py::test_health
uv run pytest services/risk-service
```

Run one backend service locally (ports 8001–8005 in compose order: banking, transaction, ledger, risk, investigation; each exposes `GET /health`):

```bash
uv run --package risk-service uvicorn risk_service.main:app --port 8004 --reload
pnpm dev   # both Vue frontends
```

### Database migrations

Each service owns its own Alembic setup (`services/<name>/alembic.ini` + `migrations/`); the Alembic version table lives inside that service's schema (e.g. `ledger.alembic_version`). `DATABASE_URL` comes from the environment (repo-root `.env` locally, see `.env.example`) — it is never hardcoded in `alembic.ini`. Use the plain `postgresql://` connection string exactly as Neon issues it; settings auto-normalize it to the psycopg v3 driver (`postgresql+psycopg://`) for SQLAlchemy. Currently only ledger-service has migrations. Run from the repo root:

```bash
make migrate   # upgrade all services to head
uv run --package ledger-service alembic -c services/ledger-service/alembic.ini upgrade head
uv run --package ledger-service alembic -c services/ledger-service/alembic.ini revision -m "description"
uv run --package ledger-service alembic -c services/ledger-service/alembic.ini current
```

Ledger integration tests need Postgres: they use `TEST_DATABASE_URL`, falling back to `DATABASE_URL` (repo-root `.env` — i.e. the Neon dev DB, slow over the network), and are skipped when neither is set. Tests create their own accounts and clean them up. CI runs a `postgres:16` service container and `make migrate` before pytest.

Note: mypy must be run per directory as the Makefile/CI do (`mypy packages`, then each `services/<name>`) — running `mypy .` across the workspace is not how CI checks it. mypy is `strict = true`; ruff line length is 100.

AGENTS.md mentions some `make` targets (`test-integration`, `test-policies`, `security`) that do not exist in the Makefile yet — verify a target exists before using it.

## Architecture

Monorepo of independently deployable FastAPI services, each with `src/<snake_case_name>/` layout and its own `tests/`:

- **transaction-service** — the workflow orchestrator: transaction lifecycle, idempotency, calls Risk then Ledger.
- **risk-service** — deterministic evaluation of versioned YAML policies (in `policies/`) → `ALLOW` / `CHALLENGE` / `HOLD` / `DENY`. Never defaults to `ALLOW` on failure; every assessment records policy version and matched reasons.
- **ledger-service** — the only service allowed to change balances: accounts, reservations (HOLD reserves funds), capture/release, append-only entries. Atomic and idempotent.
- **banking-service** — customers, beneficiaries, devices (the simulator side).
- **investigation-service** — cases created on HOLD, analyst decisions, and the read-only Groq investigation agent + RAG over `knowledge-base/` playbooks (pgvector). The agent is advisory only and must never sit in the authorization path.

Decision flow: customer web → transaction-service → risk-service decision → ALLOW commits via ledger, CHALLENGE requires MFA and re-evaluation, HOLD reserves funds and opens an investigation case, DENY rejects outright.

Shared code lives in `packages/` (`riskgate-contracts` for API/event schemas and enums like `Decision`, `riskgate-shared-observability`, `riskgate-test-utilities`), wired as uv workspace sources. Services never share ORM models or write to each other's DB schema — each service owns one Postgres schema (`banking.*`, `transaction.*`, `ledger.*`, `risk.*`, `investigation.*`) in a single Neon database.

`apps/` holds two Vue 3 + Vite + TypeScript frontends: `customer-web` and `analyst-dashboard`.

## Non-negotiables (details in AGENTS.md)

- Money is integer minor units, never floats.
- Never trust client-supplied identity, ownership, balances, or risk signals; derive identity from verified auth claims server-side.
- Policies are declarative YAML with allowlisted operators — never `eval` or hard-coded fraud conditions.
- Agent tools are read-only and enforced outside the model; treat retrieved documents and user content as untrusted.
- Idempotency required for transaction creation and event consumers.
