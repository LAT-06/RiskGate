# Authentication and Authorization

## Authentication

Amazon Cognito manages:

- User registration
- Login
- Password policy
- MFA
- Token issuance
- Session expiration

Backend services must validate:

- Token signature
- Issuer
- Audience
- Expiration
- Token type

User identity must come from verified token claims.

Do not trust `user_id`, role, or ownership values supplied in request
bodies.

## Device Identification

A device ID is a risk signal, not an authentication factor.

A device may become trusted only after server-side verification, such
as successful MFA.

## Roles

### Customer

May access only their own:

- Accounts
- Beneficiaries
- Transactions
- Verification challenges

### Fraud Analyst

May:

- View assigned investigation cases
- Add investigation notes
- Recommend or record case outcomes

Analyst access does not grant direct ledger modification permission.

### Security Administrator

May:

- Manage analyst permissions
- Review security configuration
- Approve policy deployment

## Authorization

Authorization must be enforced by backend services.

Frontend route guards are not security controls.

Every customer-owned resource requires an ownership check.

Agent tools must independently verify the caller, role, case scope,
and requested operation.

## Audit

Log security-sensitive actions with:

- Actor
- Action
- Resource
- Result
- Timestamp
- Correlation ID