# Risk Engine

## Purpose

RiskGate evaluates transaction risk before the ledger commits funds.

It uses deterministic policies and optional behavioral anomaly signals.

## Input

RiskGate receives a normalized risk context containing:

- Authenticated user identity
- Transaction information
- Device history
- Authentication history
- Beneficiary history
- Recent transaction activity
- Behavioral aggregates
- Optional external reputation signals
- Optional anomaly score

RiskGate should not query client-controlled values as authoritative data.

## Processing Stages

1. Context collection
2. Feature calculation
3. Hard-control evaluation
4. Policy evaluation
5. Optional anomaly signal evaluation
6. Decision generation
7. Evidence persistence

## Decisions

### ALLOW

Risk is acceptable.

### CHALLENGE

Additional customer verification is required.

### HOLD

Manual investigation is required.

### DENY

A mandatory security or integrity control failed.

## Policy Requirements

Policies must be:

- Declarative
- Versioned
- Validated against a schema
- Tested
- Auditable
- Deployable independently from application code where practical

Policies must not use dynamic code execution.

## Assessment Output

Every assessment must include:

- Assessment ID
- Transaction ID
- Decision
- Score
- Matched policy IDs
- Reasons
- Policy version
- Feature version
- Evaluation timestamp

## Failure Policy

Risk evaluation failure must never silently produce `ALLOW`.