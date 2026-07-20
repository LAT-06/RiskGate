"""SQLAlchemy models for the risk schema.

Assessments are the append-only record of every risk decision — and also the
data the velocity/average features are computed from. A transaction may have
several assessments (post-MFA re-evaluation), so history queries always count
distinct transaction ids. Policy set snapshots are stored once per fingerprint
so any assessment can be replayed against the exact policies it saw.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

RISK_SCHEMA = "risk"


class Base(DeclarativeBase):
    pass


class Assessment(Base):
    __tablename__ = "assessments"
    __table_args__ = (
        Index("ix_assessments_customer_created", "customer_id", "created_at"),
        Index("ix_assessments_beneficiary_created", "beneficiary_id", "created_at"),
        {"schema": RISK_SCHEMA},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    transaction_id: Mapped[UUID] = mapped_column(index=True)
    customer_id: Mapped[UUID] = mapped_column()
    beneficiary_id: Mapped[UUID] = mapped_column()
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(Text)
    ip_country: Mapped[str] = mapped_column(String(2))
    device_fingerprint: Mapped[str] = mapped_column(Text)
    features: Mapped[dict[str, Any]] = mapped_column(JSONB)
    decision: Mapped[str] = mapped_column(Text)
    matched: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    policy_set_fingerprint: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PolicyVersion(Base):
    __tablename__ = "policy_versions"
    __table_args__ = ({"schema": RISK_SCHEMA},)

    fingerprint: Mapped[str] = mapped_column(Text, primary_key=True)
    policies: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuthenticationEvent(Base):
    __tablename__ = "authentication_events"
    __table_args__ = (
        Index("ix_authentication_events_customer_occurred", "customer_id", "occurred_at"),
        {"schema": RISK_SCHEMA},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column()
    outcome: Mapped[str] = mapped_column(Text)
    ip_country: Mapped[str | None] = mapped_column(String(2), default=None)
    device_fingerprint: Mapped[str | None] = mapped_column(Text, default=None)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
