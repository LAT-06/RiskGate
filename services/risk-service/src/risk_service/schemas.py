from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from risk_service.features import FeatureValue
from riskgate_contracts import RiskDecision


class AssessmentCreate(BaseModel):
    """Facts owned by the caller (transaction-service) — never risk signals.

    mfa_verified and replay_detected are the two exceptions by design: MFA
    completion and idempotency-replay detection are facts the orchestrator
    itself is authoritative for.
    """

    transaction_id: UUID
    customer_id: UUID
    beneficiary_id: UUID
    amount_minor: int = Field(gt=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    device_fingerprint: str = Field(min_length=1, max_length=200)
    ip_country: str = Field(pattern=r"^[A-Z]{2}$")
    mfa_verified: bool
    replay_detected: bool


class MatchedPolicyRead(BaseModel):
    policy_id: str
    version: int
    decision: RiskDecision
    reason: str


class AssessmentRead(BaseModel):
    id: UUID
    transaction_id: UUID
    decision: RiskDecision
    matched_policies: list[MatchedPolicyRead]
    policy_set_fingerprint: str
    features: dict[str, FeatureValue]
    created_at: datetime


class AuthenticationEventCreate(BaseModel):
    customer_id: UUID
    outcome: Literal["success", "failure"]
    ip_country: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    device_fingerprint: str | None = Field(default=None, max_length=200)


class AuthenticationEventRead(BaseModel):
    id: UUID
    customer_id: UUID
    outcome: str
    occurred_at: datetime
