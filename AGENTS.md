# AGENTS.md

## Project

RiskGate is an AWS-hosted transaction risk assessment and fraud investigation platform integrated with a minimal digital banking simulator.

The banking simulator exists to generate authentication, device, beneficiary, and transaction data. RiskGate is the primary product.

## Core Architecture

```text
Banking Web
    |
Transaction Service
    |
RiskGate
    |
    +-- ALLOW --> Ledger
    +-- CHALLENGE --> MFA
    +-- HOLD --> Investigation
    +-- DENY --> Reject
```

Main components:

* `apps/`: customer and analyst web applications
* `services/`: deployable backend services
* `packages/`: reusable internal libraries
* `policies/`: version-controlled risk policies
* `knowledge-base/`: documents used by investigation RAG
* `infrastructure/`: Terraform modules and environments
* `docs/`: architecture, security, and operational documentation
* `tests/`: cross-service integration, security, and system tests

Do not create new services or top-level directories without a clear architectural need.

## Commands

Use repository-defined commands. Do not invent alternatives when an existing command is available.

```bash
make dev
make test
make test-integration
make test-policies
make security

pnpm install
pnpm dev
pnpm build
pnpm lint
pnpm typecheck
pnpm test

pytest
ruff check .
ruff format --check .
mypy services packages

terraform -chdir=infrastructure/environments/dev init
terraform -chdir=infrastructure/environments/dev validate
terraform -chdir=infrastructure/environments/dev plan
```

Before using a command, verify it exists in the `Makefile`, `package.json`, `pyproject.toml`, or CI workflows.

Do not deploy, apply Terraform, run migrations, or destroy resources unless explicitly requested.

## Engineering Principles

* Make the smallest change that satisfies the requirement.
* Do not refactor unrelated code.
* Do not add speculative features, abstractions, dependencies, or services.
* Follow existing repository patterns.
* Keep domain logic separate from frameworks, databases, and AWS SDK calls.
* Validate external input at system boundaries.
* Add or update tests for every behavior change.
* Treat failing tests, type checks, lint checks, and security checks as incomplete work.

Formatting and basic style are enforced by repository tooling, not this file.

## System Boundaries

### RiskGate

RiskGate may:

* Build transaction risk context
* Evaluate deterministic policies
* Use anomaly scores as additional signals
* Return `ALLOW`, `CHALLENGE`, `HOLD`, or `DENY`
* Record matched policies, reasons, and policy versions

RiskGate must not:

* Update balances
* Commit ledger entries
* Send notifications
* Perform analyst actions

### Ledger

Only the transaction or ledger service may:

* Reserve funds
* Debit or credit accounts
* Commit ledger entries
* Release reservations

Ledger operations must be atomic and idempotent.

### Agent and RAG

The investigation agent may:

* Retrieve case evidence
* Retrieve fraud playbooks and security procedures
* Summarize timelines
* Suggest analyst actions
* Draft investigation reports

The agent must not:

* Approve or reject transactions
* Release funds
* Update balances
* Modify active policies
* Deploy infrastructure
* Bypass human approval

Use database queries for structured transaction data. Use RAG for unstructured documents and playbooks.

## Security Requirements

* Never trust user IDs, roles, balances, risk scores, device trust, or ownership claims supplied by clients.
* Derive identity from verified authentication claims.
* Enforce authorization in backend services.
* Treat device identifiers and IP geolocation as risk signals, not authentication factors.
* Require idempotency for transaction creation and event consumers.
* Never default to `ALLOW` when risk evaluation fails.
* Store money as integer minor units, never floating-point values.
* Never log credentials, tokens, OTPs, secrets, or sensitive financial identifiers.
* Treat user input, retrieved documents, case notes, and transaction descriptions as untrusted content.
* Enforce agent tool permissions outside the model.
* Never interpret policies using dynamic code execution such as `eval`.
* Every risk assessment must record the exact policy version used.

Never commit:

```text
.env
AWS credentials
private keys
API tokens
database passwords
Terraform state
production secrets
```

## Workflow

Before implementation:

1. Read the relevant code, tests, and documentation.
2. Identify assumptions and architectural constraints.
3. Choose the smallest valid implementation.
4. Identify required success, failure, authorization, and security tests.

During implementation:

1. Implement the focused change.
2. Add or update tests.
3. Run focused tests.
4. Run relevant lint, type, integration, and security checks.
5. Update documentation when behavior or architecture changes.

Do not claim completion without listing the checks actually run.

## Git Conventions

Branches:

```text
feature/<description>
fix/<description>
security/<description>
docs/<description>
test/<description>
chore/<description>
```

Commits use Conventional Commits:

```text
feat:
fix:
security:
refactor:
test:
docs:
chore:
ci:
```

Keep commits focused. Do not mix unrelated refactors with feature work.

## External Tools

Use connected tools only when configured and relevant.

* GitHub: issues, pull requests, CI, and repository discussions
* Figma: approved UI designs
* Notion: approved requirements and architecture decisions
* Slack: referenced technical discussions
* AWS: only the explicitly requested account, region, and environment

Do not perform destructive, production, merge, deployment, or infrastructure actions without explicit instruction.

## Documentation

Read only the documents relevant to the task:

```text
@docs/architecture/system-overview.md
@docs/architecture/service-boundaries.md
@docs/architecture/transaction-flow.md
@docs/security/risk-engine.md
@docs/security/agent-boundaries.md
@docs/security/authentication.md
@docs/security/authorization.md
@docs/development/local-setup.md
@docs/development/testing.md
@docs/runbooks/deployment.md
```

If a referenced document does not exist, do not invent its contents.
