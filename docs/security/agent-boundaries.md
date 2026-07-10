# Agent Boundaries

## Purpose

The investigation agent assists fraud analysts after an investigation
case has been created.

It is not part of the synchronous transaction authorization path.

## Allowed Capabilities

The agent may:

- Read transaction evidence
- Read risk assessments
- Read authentication and device history
- Retrieve fraud playbooks
- Retrieve security procedures
- Summarize case timelines
- Suggest analyst actions
- Draft investigation reports

## Prohibited Capabilities

The agent must not:

- Approve transactions
- Reject transactions
- Release or reserve funds
- Update account balances
- Modify ledger entries
- Change user roles
- Modify active risk policies
- Deploy code or infrastructure
- Execute unrestricted database queries

## Data Retrieval

Structured data must be retrieved through explicit tools or repository
queries.

RAG is limited to unstructured documents such as:

- Fraud playbooks
- Investigation procedures
- Security policies
- Sanitized historical case reports

## Security Controls

- Tool access must be enforced outside the model.
- Tool parameters must be validated.
- The agent must use least-privilege credentials.
- Retrieved content must be treated as untrusted.
- User-controlled fields may contain prompt injection.
- Sensitive actions require explicit human confirmation.
- Agent output must reference supporting evidence.

## Failure Behavior

Agent failure must not block manual investigation.

The analyst dashboard must remain usable without the agent.