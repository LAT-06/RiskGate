# Transaction Flow

## Transaction Submission

The customer submits:

- Source account ID
- Beneficiary ID
- Amount
- Currency
- Device ID
- Idempotency key

The client must not provide authoritative values for:

- User ID
- Account ownership
- Device trust
- Risk score
- Beneficiary age
- Transaction frequency

## Request Validation

The transaction service:

1. Derives user identity from verified authentication claims.
2. Validates request format.
3. Verifies account ownership.
4. Verifies beneficiary ownership.
5. Checks the idempotency key.
6. Checks account status and available balance.

## Risk Evaluation

The context builder retrieves:

- Current device information
- Source IP and approximate country
- Authentication history
- Beneficiary history
- Transaction history
- Behavioral aggregates

RiskGate returns:

- `ALLOW`
- `CHALLENGE`
- `HOLD`
- `DENY`

## ALLOW

The ledger atomically reserves or transfers funds and creates ledger
entries.

## CHALLENGE

The transaction remains uncommitted until the customer completes
additional verification.

After successful verification, the transaction is evaluated again.

## HOLD

The transaction enters `PENDING_REVIEW`.

The system publishes a held transaction event and creates an
investigation case.

## DENY

The request is rejected without committing funds.

Typical hard-deny reasons include:

- Replay
- Invalid ownership
- Locked account
- Invalid request integrity
- Absolute transaction limit violation

## Failure Behavior

RiskGate failures must not default to `ALLOW`.

The transaction should enter a retry or hold state.