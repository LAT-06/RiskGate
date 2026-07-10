# Service Boundaries

## Banking API

Responsibilities:

- Customer profile
- Device registration
- Beneficiary management
- Account display
- Authentication integration

Must not:

- Evaluate transaction risk
- Update the ledger directly
- Perform investigation actions

## Transaction Service

Responsibilities:

- Validate transaction requests
- Verify account and beneficiary ownership
- Enforce idempotency
- Request a RiskGate assessment
- Execute approved ledger operations
- Publish transaction events

Must not:

- Define fraud policies
- Perform analyst investigation
- Use an LLM for transaction authorization

## RiskGate

Responsibilities:

- Build risk context
- Calculate risk features
- Evaluate policies
- Consume anomaly scores
- Return ALLOW, CHALLENGE, HOLD, or DENY
- Store assessment evidence and policy version

Must not:

- Update balances
- Commit ledger entries
- Notify customers
- Approve investigation cases

## Ledger

Responsibilities:

- Reserve funds
- Debit and credit accounts
- Create append-only ledger entries
- Prevent double spending
- Enforce idempotency

## Investigation Service

Responsibilities:

- Create investigation cases
- Store case status and evidence
- Assign analysts
- Record analyst decisions
- Trigger approved follow-up actions

## Agent and RAG

Responsibilities:

- Retrieve case evidence
- Retrieve relevant playbooks
- Summarize timelines
- Recommend investigation steps
- Draft reports

Must not:

- Approve or reject transactions
- Release funds
- Modify active policies
- Execute unrestricted tools