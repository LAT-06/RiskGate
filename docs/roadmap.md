# Build Order Roadmap

Recommended implementation order for the MVP, derived from [MVP.md](./MVP.md). It largely follows milestones 0→9, with a few adjustments for a solo side project. Milestone numbers refer to MVP.md.

## Recommended order

### 1. Repository foundation (Milestone 0) — ✅ DONE (2026-07-11)

Completed on branch `feature/ledger-service`, commit `aa3ffb3` (`feat: connect Neon and set up Alembic migrations (milestone 0)`). Neon connection verified (PostgreSQL 18, database `neondb`); Alembic set up in ledger-service with the version table inside the `ledger` schema; `make migrate` applies migrations for every service that has them; `DATABASE_URL` comes from the environment (plain Neon `postgresql://` URLs are normalized to the psycopg v3 driver); `.dockerignore` keeps `.env` out of images.

### 2. Ledger Service (Milestone 2 — BEFORE the banking simulator) — ✅ DONE (2026-07-11)

Completed on branch `feature/ledger-service`, commit `a7330f6` (`feat: implement ledger core with reservations and idempotency (milestone 2)`). Built: `ledger` schema (accounts with posted/reserved and a generated `available_balance`, append-only entries, transfers, reservations — all invariants backed by CHECK constraints); atomic operations locking accounts with `SELECT ... FOR UPDATE` in primary-key order (transfer, reserve, capture, release, expiry sweep); idempotency keys on transfers and reservations; FastAPI endpoints; 32 integration tests including a concurrent double-spend test. CI runs a `postgres:16` service container and `make migrate` before pytest.

Original rationale: the ledger is the hardest part to get correct (atomic transfers, reservations, idempotency, double-spend prevention) and every decision flow (ALLOW/HOLD) stands on top of it. It is also fully testable with unit/integration tests — no UI or fake data needed — which makes it a good fit for early, high-energy work. Building it after the UI risks bending the ledger to fit the UI.

### 3. Minimal banking simulator (Milestone 1) — ✅ DONE (2026-07-11)

Completed on branch `feature/banking-simulator`, commits `11d8ca0` (backend) and `24c6477` (customer-web frontend), merged to main 2026-07-15. Built: `banking` schema (customers, beneficiaries, devices) with its own Alembic migrations; dev identity via the `X-Customer-Id` header verified against `banking.customers`, behind the `IdentityProvider` seam (Cognito replaces it at Milestone 9); account summary and entry history proxied from the ledger; customer-web frontend (welcome, dashboard, transfer, beneficiaries, history). Caveat: the transfer form posts to the not-yet-built transaction-service (`POST :8002/transactions`), so M1's "customer can submit a transaction request" criterion fully closes when Milestone 4 brings that service up.

### 4. Risk context + YAML policy engine (Milestone 3) — ✅ DONE (2026-07-20)

Completed on branch `feature/risk-policy-engine`, commits `64e9072` (pure engine) and `daf99ef` (context + API). Built: pure deterministic engine over a strict pydantic YAML schema (allowlisted operators, ALLOW-decision policies forbidden, sha256 policy-set fingerprint, fail-closed on any error) with 6 initial policies in `policies/`; context builder computing the feature registry from banking data (internal read-only endpoints behind a `BankingClient` seam) and from risk's own assessment history; `risk` schema (assessments, policy_versions, authentication_events) with Alembic; `POST /assessments` and `POST /events/authentication`. Re-evaluations of one transaction never double-count in history windows. Two documented temporary compromises: `device_is_trusted` is derived from device age (≥ 7 days) until real trust accrual exists, and `beneficiary_previous_transaction_count` is approximated from risk's own ALLOW assessment history until transaction-service (Milestone 4) provides real transaction data.

Original rationale: the heart of the product. Needs data from steps 2–3 to compute features (`device_is_new`, `beneficiary_age_minutes`, velocity, ...). The pure policy engine (YAML parsing, allowlisted operators, evaluation) can be written and tested independently at any earlier point — it is a pure function with no dependencies.

### 5. End-to-end orchestration (Milestone 4)

The transaction service ties everything together: state machine, ALLOW commits via the ledger, HOLD reserves funds, DENY rejects, simulated CHALLENGE. At this point demo scenarios 1, 2, 5, and 6 work — this is the first "living product" milestone, so prioritize reaching it as fast as possible.

### 6. Manual investigation dashboard (Milestone 5)

Cases created from HOLD, analyst reviews evidence, approve (capture reservation) / reject (release). The roadmap is explicit: manual investigation must work without the agent. Completing this finishes scenario 3 (manual part) and scenario 4 — the MVP can then demo the full transaction lifecycle.

### 7. RAG (Milestone 6)

Write markdown playbooks, chunking, local embeddings, pgvector, retrieval. Fully separable — does not touch the already-working financial flows.

### 8. Groq Investigation Agent (Milestone 7)

Needs both case data (step 6) and RAG (step 7). This is the advisory, read-only layer — build it last among the features because nothing else depends on it, consistent with "agent failure does not block manual review".

### 9. Security & observability hardening (Milestone 8)

Do this as a final pass, *but* do not defer all of it: correlation IDs + structured logging should be wired in from step 5 (debugging multi-service orchestration without them is painful), and authorization/idempotency tests belong inside each milestone as the roadmap already requires. What remains for this step: prompt-injection tests, audit events, secret scanning in CI.

### 10. AWS deployment (Milestone 9)

The roadmap is explicit: deploy only once the local MVP is stable. For a solo side project this is definitively the last step.

## Dependency logic summary

- **Ledger before all business features** — every decision needs it, and it is the hardest part.
- **The straight line to Milestone 4** (end-to-end ALLOW/DENY) is priority number one — getting a working demo loop early keeps a side project alive.
- **Agent + RAG last** — they are the advisory layer, not on the critical path of any other feature.
- Two tasks that can be interleaved as a change of pace: the pure policy evaluator (pure function, independently testable) and writing the markdown playbook content (no code required).
