from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from risk_service.banking_client import BankingClient, BankingUnavailableError, get_banking_client
from risk_service.context import build_features
from risk_service.db import get_session
from risk_service.engine import EvaluationError, evaluate
from risk_service.history import load_customer_history
from risk_service.models import Assessment, AuthenticationEvent, PolicyVersion
from risk_service.policy import PolicyError, PolicySet, load_policy_set
from risk_service.schemas import (
    AssessmentCreate,
    AssessmentRead,
    AuthenticationEventCreate,
    AuthenticationEventRead,
    MatchedPolicyRead,
)
from risk_service.settings import load_settings

router = APIRouter()

SessionDep = Annotated[Session, Depends(get_session)]
BankingDep = Annotated[BankingClient, Depends(get_banking_client)]


@lru_cache(maxsize=1)
def get_policy_set() -> PolicySet:
    return load_policy_set(load_settings().policies_dir)


def _record_policy_version(session: Session, policy_set: PolicySet) -> None:
    snapshot = [policy.model_dump(mode="json") for policy in policy_set.policies]
    session.execute(
        insert(PolicyVersion)
        .values(fingerprint=policy_set.fingerprint, policies=snapshot)
        .on_conflict_do_nothing(index_elements=["fingerprint"])
    )


@router.post("/assessments", status_code=201)
def create_assessment(
    body: AssessmentCreate, session: SessionDep, banking: BankingDep
) -> AssessmentRead:
    try:
        policy_set = get_policy_set()
    except PolicyError as exc:
        # Fail closed: a broken policy directory must never turn into ALLOW.
        raise HTTPException(status_code=500, detail="policy set failed to load") from exc

    try:
        devices = banking.list_devices(customer_id=body.customer_id)
        beneficiary = banking.get_beneficiary(
            customer_id=body.customer_id, beneficiary_id=body.beneficiary_id
        )
    except BankingUnavailableError as exc:
        raise HTTPException(status_code=502, detail="banking service unavailable") from exc
    if beneficiary is None:
        raise HTTPException(status_code=422, detail="beneficiary not found for customer")

    now = datetime.now(UTC)
    history = load_customer_history(
        session,
        customer_id=body.customer_id,
        beneficiary_id=body.beneficiary_id,
        transaction_id=body.transaction_id,
        now=now,
    )
    features = build_features(
        amount_minor=body.amount_minor,
        ip_country=body.ip_country,
        mfa_verified=body.mfa_verified,
        replay_detected=body.replay_detected,
        device_fingerprint=body.device_fingerprint,
        devices=devices,
        beneficiary=beneficiary,
        history=history,
        now=now,
    )
    try:
        evaluation = evaluate(features, policy_set)
    except EvaluationError as exc:
        raise HTTPException(status_code=500, detail="risk evaluation failed") from exc

    _record_policy_version(session, policy_set)
    assessment = Assessment(
        transaction_id=body.transaction_id,
        customer_id=body.customer_id,
        beneficiary_id=body.beneficiary_id,
        amount_minor=body.amount_minor,
        currency=body.currency,
        ip_country=body.ip_country,
        device_fingerprint=body.device_fingerprint,
        features=dict(features),
        decision=evaluation.decision,
        matched=[match.model_dump(mode="json") for match in evaluation.matched],
        policy_set_fingerprint=evaluation.policy_set_fingerprint,
        created_at=now,
    )
    session.add(assessment)
    session.commit()

    return AssessmentRead(
        id=assessment.id,
        transaction_id=assessment.transaction_id,
        decision=evaluation.decision,
        matched_policies=[
            MatchedPolicyRead(
                policy_id=match.policy_id,
                version=match.version,
                decision=match.decision,
                reason=match.reason,
            )
            for match in evaluation.matched
        ],
        policy_set_fingerprint=evaluation.policy_set_fingerprint,
        features=features,
        created_at=now,
    )


@router.post("/events/authentication", status_code=201)
def record_authentication_event(
    body: AuthenticationEventCreate, session: SessionDep
) -> AuthenticationEventRead:
    event = AuthenticationEvent(
        customer_id=body.customer_id,
        outcome=body.outcome,
        ip_country=body.ip_country,
        device_fingerprint=body.device_fingerprint,
        occurred_at=datetime.now(UTC),
    )
    session.add(event)
    session.commit()
    return AuthenticationEventRead(
        id=event.id,
        customer_id=event.customer_id,
        outcome=event.outcome,
        occurred_at=event.occurred_at,
    )
