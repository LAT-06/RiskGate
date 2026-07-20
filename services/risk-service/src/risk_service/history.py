"""Customer history queries over the risk schema's own records.

Until the transaction service exists (Milestone 4), the assessment log is the
only transaction history available, so velocity / average-amount /
beneficiary-familiarity features are computed from it. A transaction can be
assessed more than once (post-MFA re-evaluation), so every query counts
distinct transaction ids and excludes the transaction currently being
assessed — re-evaluation must see the same history the first evaluation saw.
"""

from datetime import datetime, timedelta
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from risk_service.models import Assessment, AuthenticationEvent
from riskgate_contracts import RiskDecision

VELOCITY_WINDOW = timedelta(minutes=10)
FAILED_LOGIN_WINDOW = timedelta(hours=1)


class CustomerHistory(BaseModel):
    model_config = ConfigDict(frozen=True)

    prior_transactions_in_window: int
    prior_amount_in_window: int
    average_transaction_amount: float | None
    beneficiary_allowed_transaction_count: int
    failed_logins_last_hour: int
    last_ip_country: str | None


def load_customer_history(
    session: Session,
    *,
    customer_id: UUID,
    beneficiary_id: UUID,
    transaction_id: UUID,
    now: datetime,
) -> CustomerHistory:
    # One row per prior transaction: the amount is identical across
    # re-evaluations of the same transaction, so min() just picks it.
    per_transaction = (
        select(
            Assessment.transaction_id.label("transaction_id"),
            func.min(Assessment.amount_minor).label("amount_minor"),
            func.min(Assessment.created_at).label("first_assessed_at"),
        )
        .where(
            Assessment.customer_id == customer_id,
            Assessment.transaction_id != transaction_id,
        )
        .group_by(Assessment.transaction_id)
        .subquery()
    )

    in_window = select(
        func.count(per_transaction.c.transaction_id),
        func.coalesce(func.sum(per_transaction.c.amount_minor), 0),
    ).where(per_transaction.c.first_assessed_at >= now - VELOCITY_WINDOW)
    prior_count, prior_amount = session.execute(in_window).one()

    average = session.scalar(select(func.avg(per_transaction.c.amount_minor)))

    beneficiary_allowed = session.scalar(
        select(func.count(func.distinct(Assessment.transaction_id))).where(
            Assessment.customer_id == customer_id,
            Assessment.beneficiary_id == beneficiary_id,
            Assessment.transaction_id != transaction_id,
            Assessment.decision == RiskDecision.ALLOW,
        )
    )

    failed_logins = session.scalar(
        select(func.count(AuthenticationEvent.id)).where(
            AuthenticationEvent.customer_id == customer_id,
            AuthenticationEvent.outcome == "failure",
            AuthenticationEvent.occurred_at >= now - FAILED_LOGIN_WINDOW,
        )
    )

    last_ip_country = session.scalar(
        select(Assessment.ip_country)
        .where(
            Assessment.customer_id == customer_id,
            Assessment.transaction_id != transaction_id,
        )
        .order_by(Assessment.created_at.desc(), Assessment.id.desc())
        .limit(1)
    )

    return CustomerHistory(
        prior_transactions_in_window=int(prior_count),
        prior_amount_in_window=int(prior_amount),
        average_transaction_amount=float(average) if average is not None else None,
        beneficiary_allowed_transaction_count=int(beneficiary_allowed or 0),
        failed_logins_last_hour=int(failed_logins or 0),
        last_ip_country=last_ip_country,
    )
