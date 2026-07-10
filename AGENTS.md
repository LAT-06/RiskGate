# AGENTS.md

Instructions for AI coding agents working in the RiskGate repository.

## 1. Project Overview

RiskGate is an AWS-deployed transaction risk assessment and fraud investigation platform integrated with a simulated digital banking application.

The banking simulator exists only to generate authentication, device, beneficiary, transaction, and behavioral data for RiskGate.

The primary product is RiskGate, not the banking simulator.

RiskGate performs:

* Transaction context collection
* Policy-based risk evaluation
* Behavioral anomaly detection
* `ALLOW`, `CHALLENGE`, `HOLD`, or `DENY` decisions
* Investigation case creation
* Agent-assisted fraud investigation
* Security logging and audit trails

The LLM agent must never directly approve transactions, reject transactions, release funds, update balances, or modify production policies.

---

## 2. Technology Stack

### Frontend

* Vue 3
* TypeScript
* Vite
* Pinia
* Vue Router
* Tailwind CSS
* Axios
* Vitest
* Playwright

### Backend

* Python 3.12
* FastAPI
* Pydantic
* SQLAlchemy
* Alembic
* Boto3
* Pytest
* Ruff
* MyPy

### Cloud

* AWS Cognito
* Amazon API Gateway
* AWS Lambda
* Amazon DynamoDB
* Amazon Aurora PostgreSQL
* Amazon EventBridge
* Amazon SQS
* Amazon S3
* Amazon CloudFront
* AWS WAF
* AWS KMS
* AWS Secrets Manager
* Amazon CloudWatch
* Amazon Bedrock
* Bedrock Knowledge Bases

### Infrastructure and CI/CD

* Terraform
* Docker
* GitHub Actions
* Checkov
* Trivy
* Semgrep or CodeQL
* Gitleaks

---

## 3. Repository Structure

```text
riskgate-platform/
├── apps/
│   ├── banking-web/
│   │   ├── src/
│   │   │   ├── api/
│   │   │   ├── components/
│   │   │   ├── composables/
│   │   │   ├── layouts/
│   │   │   ├── pages/
│   │   │   ├── router/
│   │   │   ├── stores/
│   │   │   ├── types/
│   │   │   └── utils/
│   │   └── tests/
│   │
│   └── analyst-dashboard/
│       ├── src/
│       │   ├── api/
│       │   ├── components/
│       │   ├── composables/
│       │   ├── layouts/
│       │   ├── pages/
│       │   ├── router/
│       │   ├── stores/
│       │   ├── types/
│       │   └── utils/
│       └── tests/
│
├── services/
│   ├── banking-api/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   ├── domain/
│   │   │   ├── repositories/
│   │   │   ├── services/
│   │   │   └── main.py
│   │   └── tests/
│   │
│   ├── transaction-service/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   ├── domain/
│   │   │   ├── ledger/
│   │   │   ├── repositories/
│   │   │   ├── services/
│   │   │   └── main.py
│   │   └── tests/
│   │
│   ├── riskgate/
│   │   ├── app/
│   │   │   ├── context/
│   │   │   ├── decision/
│   │   │   ├── features/
│   │   │   ├── models/
│   │   │   ├── policies/
│   │   │   ├── repositories/
│   │   │   └── service.py
│   │   └── tests/
│   │
│   ├── investigation-service/
│   │   ├── app/
│   │   │   ├── agent/
│   │   │   ├── api/
│   │   │   ├── domain/
│   │   │   ├── rag/
│   │   │   ├── repositories/
│   │   │   └── services/
│   │   └── tests/
│   │
│   └── event-workers/
│       ├── audit-worker/
│       ├── case-worker/
│       ├── notification-worker/
│       └── tests/
│
├── packages/
│   ├── policy-engine/
│   ├── policy-schema/
│   ├── shared-python/
│   ├── shared-typescript/
│   └── audit-logger/
│
├── policies/
│   ├── transaction-risk.yaml
│   ├── account-takeover.yaml
│   └── replay-protection.yaml
│
├── knowledge-base/
│   ├── fraud-playbooks/
│   ├── investigation-guides/
│   ├── security-policies/
│   └── sanitized-case-reports/
│
├── infrastructure/
│   ├── modules/
│   └── environments/
│       ├── dev/
│       ├── staging/
│       └── production/
│
├── database/
│   ├── migrations/
│   └── seed/
│
├── tests/
│   ├── contract/
│   ├── integration/
│   ├── load/
│   ├── policy/
│   ├── security/
│   └── system/
│
├── docs/
│   ├── architecture/
│   ├── security/
│   ├── runbooks/
│   └── development/
│
├── scripts/
├── .github/
│   └── workflows/
├── AGENTS.md
├── Makefile
├── package.json
├── pnpm-workspace.yaml
└── pyproject.toml
```

### Directory responsibilities

* `apps/` contains browser applications.
* `services/` contains deployable backend services and Lambda handlers.
* `packages/` contains reusable libraries that are not independently deployed.
* `policies/` contains version-controlled declarative risk policies.
* `knowledge-base/` contains documents used by the investigation RAG system.
* `infrastructure/` contains Terraform modules and environment configuration.
* `database/` contains relational database migrations and development seed data.
* `tests/` contains cross-service tests.
* `docs/` contains detailed architecture, security, and operational documentation.
* `scripts/` contains repeatable development and maintenance scripts.

Do not create new top-level directories without a documented architectural reason.

---

## 4. Commands

Use commands defined in the repository. Do not invent replacement commands when an existing command is available.

### Initial setup

```bash
corepack enable
pnpm install
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Copy the development environment template:

```bash
cp .env.example .env
```

Never commit `.env`.

### Run all local services

```bash
make dev
```

### Run frontend applications

```bash
pnpm --filter banking-web dev
pnpm --filter analyst-dashboard dev
```

### Build frontend applications

```bash
pnpm build
```

### Run backend locally

```bash
make backend-dev
```

Run an individual FastAPI service:

```bash
uvicorn services.banking_api.app.main:app --reload
uvicorn services.transaction_service.app.main:app --reload
uvicorn services.investigation_service.app.main:app --reload
```

### Frontend lint and type checking

```bash
pnpm lint
pnpm typecheck
```

### Backend lint and type checking

```bash
ruff check .
ruff format --check .
mypy services packages
```

Format backend code:

```bash
ruff format .
ruff check . --fix
```

### Run all tests

```bash
make test
```

### Frontend unit tests

```bash
pnpm test
```

Run one frontend test file:

```bash
pnpm vitest run path/to/file.spec.ts
```

### Backend unit tests

```bash
pytest
```

Run one backend test file:

```bash
pytest services/riskgate/tests/test_decision_engine.py
```

Run one test:

```bash
pytest services/riskgate/tests/test_decision_engine.py::test_high_risk_transaction_is_held
```

### Integration tests

```bash
make test-integration
```

### Policy tests

```bash
make test-policies
```

### End-to-end tests

```bash
pnpm test:e2e
```

### Security checks

```bash
make security
```

Equivalent individual commands:

```bash
semgrep scan --config auto .
gitleaks detect --source .
trivy fs .
checkov -d infrastructure
```

### Database migrations

Create a migration:

```bash
alembic revision --autogenerate -m "describe_change"
```

Apply migrations:

```bash
alembic upgrade head
```

Rollback one migration:

```bash
alembic downgrade -1
```

### Local AWS dependencies

Start local development dependencies:

```bash
docker compose up -d
```

Stop local dependencies:

```bash
docker compose down
```

Reset local development data:

```bash
make reset-local
```

### Terraform

Initialize an environment:

```bash
terraform -chdir=infrastructure/environments/dev init
```

Validate:

```bash
terraform -chdir=infrastructure/environments/dev validate
```

Plan:

```bash
terraform -chdir=infrastructure/environments/dev plan
```

Apply development infrastructure:

```bash
terraform -chdir=infrastructure/environments/dev apply
```

Never apply staging or production infrastructure unless the user explicitly requests it.

Never run:

```bash
terraform destroy
```

unless the user explicitly requests destruction of that exact environment.

### Deployment

Deploy development:

```bash
make deploy-dev
```

Deploy staging:

```bash
make deploy-staging
```

Production deployment requires an approved pull request and manual GitHub Actions approval.

Do not deploy directly to production from a local machine.

---

## 5. Architecture Rules

### Primary system boundary

The banking simulator creates transactions and supporting behavioral data.

RiskGate evaluates transaction risk before the ledger commits funds.

```text
Banking Simulator
        |
        v
Transaction Service
        |
        v
RiskGate
        |
        +--> ALLOW
        +--> CHALLENGE
        +--> HOLD
        +--> DENY
        |
        v
Ledger or Investigation Workflow
```

### Synchronous path

The synchronous transaction path contains only:

1. Authentication
2. Authorization
3. Input validation
4. Idempotency validation
5. Risk context collection
6. Policy evaluation
7. Decision generation
8. Ledger execution when allowed

Keep this path deterministic and low-latency.

### Asynchronous path

Use EventBridge and SQS for:

* Investigation case creation
* Notifications
* Audit export
* Analytics
* Non-critical enrichment
* Agent-generated case summaries

A notification failure must not roll back a completed transaction.

### Agent boundary

The investigation agent may:

* Retrieve transaction evidence
* Retrieve login and device history
* Retrieve relevant fraud playbooks
* Summarize timelines
* Suggest analyst actions
* Draft investigation reports

The investigation agent must not:

* Approve transactions
* Reject transactions
* Release reserved funds
* Update balances
* Revoke sessions without explicit human action
* Change user roles
* Modify production policies
* Deploy infrastructure
* Write directly to the ledger

Agent outputs are recommendations, not authoritative decisions.

### RAG boundary

Use RAG for unstructured knowledge:

* Fraud playbooks
* Investigation procedures
* Security policies
* Rule documentation
* Sanitized historical reports

Do not use vector retrieval as a replacement for structured database queries.

Retrieve transaction amounts, timestamps, device records, login events, and case states through explicit repositories or agent tools.

### Risk Engine boundary

RiskGate must return a deterministic assessment containing:

* Assessment ID
* Transaction ID
* Policy version
* Feature version
* Risk score
* Decision
* Matched policies
* Reasons
* Evaluation timestamp

RiskGate must not:

* Modify account balances
* Commit ledger entries
* Send notifications
* Render user-facing responses
* Perform analyst actions

### Ledger boundary

Only the transaction or ledger service may:

* Reserve balances
* Debit accounts
* Credit accounts
* Commit ledger entries
* Release reservations

All ledger operations must be atomic and idempotent.

---

## 6. Code Style

### General principles

* Prefer simple code over speculative abstractions.
* Make the smallest change that satisfies the request.
* Do not refactor unrelated code.
* Do not add dependencies without a clear requirement.
* Do not add infrastructure that the requested feature does not require.
* Keep domain logic separate from frameworks and AWS SDK calls.
* Do not hide unclear assumptions.
* Preserve existing repository patterns unless they are demonstrably incorrect.

### TypeScript

* TypeScript strict mode is required.
* Do not use `any`.
* Prefer `unknown` followed by explicit validation.
* Use named exports instead of default exports.
* Use `type` for data shapes unless declaration merging is required.
* Keep API DTOs separate from domain models.
* Validate external data at application boundaries.
* Prefer Composition API with `<script setup lang="ts">`.
* Keep Pinia stores focused on shared application state.
* Do not place request logic directly inside Vue components.
* Put API clients in `src/api/`.
* Put reusable stateful behavior in `src/composables/`.
* Use Tailwind CSS utilities.
* Do not create standalone CSS files unless Tailwind cannot express the requirement cleanly.
* Do not add animation unless it serves a defined interaction requirement.

Example:

```ts
export type RiskDecision = "ALLOW" | "CHALLENGE" | "HOLD" | "DENY";
```

### Python

* Python 3.12 features are allowed.
* All public functions require type annotations.
* Use Pydantic models for API boundary validation.
* Use domain dataclasses or explicit domain models internally.
* Do not pass unvalidated dictionaries through domain code.
* Use dependency injection for repositories and external clients.
* Do not call Boto3 directly from policy or domain logic.
* Do not catch broad `Exception` unless re-raising with meaningful context.
* Do not use mutable default arguments.
* Use UTC timestamps.
* Use timezone-aware `datetime`.
* Store money as integers in minor currency units.
* Do not use floating-point types for money.

### FastAPI

* Keep route handlers thin.
* Route handlers may authenticate, validate, call an application service, and translate results into HTTP responses.
* Business logic belongs in service or domain layers.
* Database access belongs in repositories.
* Do not return internal exception details to clients.
* Do not expose database models directly as API responses.

### Database

* Use explicit database migrations.
* Do not modify production schemas manually.
* Every migration must include a downgrade path where practical.
* Ledger records are append-only.
* Do not update or delete historical ledger entries.
* Do not use database-generated floating-point calculations for money.
* Use transactions for balance and ledger changes.

### DynamoDB

* Design access patterns before creating a table or index.
* Do not use table scans in request paths.
* Use conditional writes for idempotency and concurrency controls.
* Use TTL only for data that may safely expire.
* Do not rely on TTL for immediate deletion.
* Use server-generated timestamps and identifiers.

### Policies

* Risk policies must be declarative.
* Do not hard-code individual fraud rules across service code.
* Every policy requires:

  * Stable policy ID
  * Version
  * Description
  * Enabled state
  * Conditions
  * Effect
  * Test cases
* Never use Python `eval`, JavaScript `eval`, or dynamic code execution to interpret policies.
* Policy operators must come from an explicit allowlist.
* Policy changes require historical replay tests before deployment.
* The model anomaly score may be an input signal but may not directly authorize a transaction.

### Terraform

* Use reusable modules where the same resource pattern appears more than once.
* Do not create abstraction layers for one-off resources without a concrete need.
* Pin provider versions.
* Encrypt state.
* Use remote state locking.
* Do not commit Terraform state.
* Do not hard-code secrets.
* Apply least-privilege IAM policies.
* Avoid wildcard IAM actions and resources unless documented and unavoidable.
* Public exposure must be intentional and documented.
* Enable logging, encryption, and retention settings explicitly.

---

## 7. Testing Requirements

Every feature must include tests.

A feature is incomplete until its required tests pass.

### Backend changes

Include as applicable:

* Unit tests for domain logic
* Repository tests
* API tests
* Authorization tests
* Integration tests
* Failure-path tests
* Idempotency tests
* Concurrency tests

### Frontend changes

Include as applicable:

* Component tests
* Store tests
* Form validation tests
* API failure-state tests
* Permission and route-guard tests
* Playwright tests for critical workflows

### Risk policy changes

Every policy change requires:

* Positive matching case
* Negative non-matching case
* Boundary-value case
* Missing-field behavior
* Conflicting-policy behavior when relevant
* Historical replay result
* Expected false-positive impact

### Security-sensitive changes

Include abuse cases, not only successful cases.

Examples:

* Customer attempts to access another user's transaction
* Analyst attempts to update the ledger
* Reused idempotency key
* Tampered beneficiary identifier
* Missing or invalid JWT
* Stale MFA challenge
* Duplicate EventBridge delivery
* Prompt injection inside transaction metadata
* Agent attempts to call an unauthorized tool

### Test behavior

Tests must be deterministic.

Do not:

* Depend on execution order
* Use real production services
* Use arbitrary sleep calls
* Require unrestricted internet access
* Assert against unstable LLM prose

For agent tests, assert:

* Tools called
* Tool authorization
* Structured output schema
* Required evidence references
* Prohibited action rejection

Do not assert exact natural-language wording unless wording itself is the requirement.

---

## 8. Workflow

### Before coding

1. Read this file.
2. Read the relevant documents in `docs/`.
3. Inspect existing code and tests in the affected area.
4. State assumptions and identify unclear requirements.
5. Identify the smallest valid implementation.
6. Identify required security and failure-path tests.

Do not start implementation while a material requirement remains ambiguous.

### Feature workflow

```text
Understand
  |
  v
Plan
  |
  v
Implement minimum change
  |
  v
Add or update tests
  |
  v
Run focused tests
  |
  v
Run lint and type checks
  |
  v
Run broader regression tests
  |
  v
Update documentation
```

### Branch naming

Use:

```text
feature/<short-description>
fix/<short-description>
security/<short-description>
refactor/<short-description>
docs/<short-description>
test/<short-description>
chore/<short-description>
```

Examples:

```text
feature/risk-policy-versioning
security/validate-agent-tool-access
fix/duplicate-ledger-entry
```

### Commit messages

Use Conventional Commits:

```text
feat:
fix:
security:
refactor:
test:
docs:
chore:
ci:
build:
```

Examples:

```text
feat(riskgate): add beneficiary age feature
security(api): enforce transaction ownership
test(policy): add replay detection boundary cases
```

Keep commits focused.

Do not mix unrelated refactors with feature changes.

### Pull requests

Every pull request must include:

* Problem being solved
* Scope of the change
* Architectural impact
* Security impact
* Tests added
* Commands executed
* Migration or deployment notes
* Screenshots for visible UI changes
* Policy replay result for risk-policy changes

Required review:

* Application review for backend or frontend changes
* Security review for authentication, authorization, ledger, policy, agent, or IAM changes
* Infrastructure review for Terraform changes
* Manual approval for production deployment

### Definition of done

A task is complete only when:

* Requested behavior is implemented
* Tests are added and passing
* Lint and type checks pass
* Security implications are handled
* No unrelated changes are included
* Relevant documentation is updated
* Deployment or migration steps are documented

---

## 9. Security Gotchas

### Secrets

Never commit:

```text
.env
*.tfstate
*.tfstate.*
AWS credentials
database passwords
private keys
JWT signing keys
API tokens
Bedrock credentials
production identifiers
```

Use:

* AWS Secrets Manager
* GitHub Actions secrets
* Local `.env` files excluded by Git

### Authentication

* Do not trust `user_id` supplied in request bodies.
* Derive the authenticated user from verified Cognito claims.
* Validate JWT issuer, audience, expiration, and token use.
* MFA completion must be verified server-side.
* Device IDs are risk signals, not authentication factors.

### Authorization

* Every customer-owned resource requires an ownership check.
* Frontend route guards are not authorization controls.
* Analyst and administrator permissions must be enforced in backend services.
* The agent role must have read-only access to case evidence unless a specific tool requires otherwise.
* Human confirmation is required for sensitive investigation actions.

### Transactions

* Every transaction creation request requires an idempotency key.
* Use conditional writes or database constraints to prevent duplicate execution.
* Risk approval does not guarantee sufficient balance.
* Balance and ledger integrity remain the responsibility of the ledger service.
* Never default to `ALLOW` when RiskGate is unavailable.
* Use `HOLD` or an explicit retry state on risk evaluation failure.

### Money

* Represent money using integer minor units.
* Never use `float`.
* Validate currency and amount together.
* Do not trust client-calculated balances, limits, totals, or fees.

### Logging

Never log:

* Passwords
* OTP values
* Access tokens
* Refresh tokens
* Authorization headers
* Session secrets
* Database credentials
* Full account identifiers
* Raw personally identifiable data without a defined requirement

Every security-sensitive action should log:

* Actor
* Action
* Resource
* Result
* Timestamp
* Correlation ID
* Source context
* Policy version when relevant

### Agent and RAG

Treat all retrieved and user-controlled text as untrusted.

Transaction descriptions, beneficiary names, analyst notes, uploaded documents, and historical case reports may contain prompt injection.

The agent must:

* Use an explicit tool allowlist
* Validate tool parameters
* Enforce permissions outside the model
* Return structured output
* Cite retrieved evidence
* Separate retrieved content from system instructions
* Refuse prohibited actions
* Operate with least-privilege IAM permissions

Do not allow retrieved documents to redefine:

* Agent permissions
* Tool behavior
* System policies
* Transaction decisions
* Approval requirements

### Policies

* Policy configuration is executable security logic.
* Validate policy files against the policy schema.
* Reject unknown fields and unsupported operators.
* Sign or checksum production policy bundles.
* Record the exact policy version used for each assessment.
* Do not let an agent write directly to active policy storage.
* Agent-generated policy proposals must enter through a reviewed pull request.

### Event-driven processing

* EventBridge and SQS delivery may occur more than once.
* Every consumer must be idempotent.
* Configure retries and dead-letter queues.
* Do not assume event ordering unless explicitly guaranteed.
* Store processed event IDs when duplicate processing would cause harm.

### Infrastructure

* Do not expose Aurora or internal services publicly.
* Do not use `0.0.0.0/0` for administrative access.
* Do not create wildcard IAM permissions for convenience.
* Enable encryption for data stores and queues.
* Require TLS.
* Restrict audit-log deletion.
* Log administrative AWS actions through CloudTrail.

---

## 10. External Tools and MCP Servers

Use external tools only when they are configured and the task requires them.

Do not assume an MCP server exists because a product is mentioned in documentation.

### GitHub

Use GitHub integration for:

* Reading issues
* Reading pull requests
* Reviewing existing discussions
* Checking CI failures
* Creating or updating a pull request when explicitly requested

Do not merge, close, or delete resources without explicit instruction.

### Figma

Use Figma integration only for:

* Reading approved designs
* Inspecting components, spacing, typography, and states
* Comparing implementation with the source design

Do not invent designs when an approved Figma source exists.

### Notion

Use Notion integration only for:

* Reading product requirements
* Reading architecture decisions
* Reading approved policy definitions
* Updating project documentation when explicitly requested

Repository documentation remains authoritative for implementation details unless an approved requirement says otherwise.

### Slack

Use Slack integration only for:

* Reading referenced technical discussions
* Finding decisions not yet copied into repository documentation
* Preparing a summary when explicitly requested

Do not treat informal Slack discussion as final approval unless the responsible owner clearly states a decision.

### AWS

Use AWS tools only against the explicitly requested environment.

Default to development.

Never modify staging or production without explicit instruction.

Before any AWS write action:

1. Confirm the target account.
2. Confirm the target region.
3. Confirm the environment.
4. Review the planned resource changes.
5. Use least-privilege credentials.

---

## 11. Documentation References

Read only the documents relevant to the current task.

### Architecture

* `@docs/architecture/system-overview.md`
* `@docs/architecture/service-boundaries.md`
* `@docs/architecture/transaction-flow.md`
* `@docs/architecture/event-driven-workflows.md`
* `@docs/architecture/data-model.md`

### RiskGate

* `@docs/security/risk-context.md`
* `@docs/security/policy-engine.md`
* `@docs/security/risk-decisions.md`
* `@docs/security/anomaly-detection.md`
* `@docs/security/policy-lifecycle.md`

### Authentication and authorization

* `@docs/security/authentication.md`
* `@docs/security/authorization.md`
* `@docs/security/device-trust.md`
* `@docs/security/session-management.md`

### Agent and RAG

* `@docs/security/agent-boundaries.md`
* `@docs/security/agent-tool-permissions.md`
* `@docs/security/rag-ingestion.md`
* `@docs/security/prompt-injection.md`
* `@docs/security/human-approval.md`

### Ledger and transactions

* `@docs/architecture/ledger.md`
* `@docs/architecture/idempotency.md`
* `@docs/architecture/transaction-state-machine.md`
* `@docs/architecture/concurrency-control.md`

### Operations

* `@docs/runbooks/deployment.md`
* `@docs/runbooks/riskgate-failure.md`
* `@docs/runbooks/queue-dlq.md`
* `@docs/runbooks/incident-response.md`
* `@docs/runbooks/policy-rollback.md`

### Development

* `@docs/development/local-setup.md`
* `@docs/development/testing.md`
* `@docs/development/database-migrations.md`
* `@docs/development/terraform.md`
* `@docs/development/release-process.md`

If a referenced document does not exist, do not invent its contents. Either create it as part of an explicitly requested documentation task or report that it is missing.

---

## 12. Agent Decision Rules

When modifying this repository:

1. Do not assume.
2. Do not silently choose between materially different interpretations.
3. Prefer the simplest implementation that satisfies the requirement.
4. Do not add speculative flexibility.
5. Do not create a new service when a module in an existing service is sufficient.
6. Do not introduce an LLM where deterministic logic is required.
7. Do not put database access inside risk-policy definitions.
8. Do not put transaction execution inside RiskGate.
9. Do not let agent output bypass human approval.
10. Do not finish a feature without tests.

When a proposed implementation violates these boundaries, stop and identify the conflict before coding.
