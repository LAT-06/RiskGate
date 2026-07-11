"""SQLAlchemy models for the banking schema (the simulator side).

The banking service owns customer profiles, beneficiaries, and device
metadata. Balances live in the ledger service: `ledger_account_id` is a plain
UUID reference, never a cross-schema foreign key.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

BANKING_SCHEMA = "banking"


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("email", name="uq_customers_email"),
        UniqueConstraint("account_number", name="uq_customers_account_number"),
        {"schema": BANKING_SCHEMA},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    full_name: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(Text)
    account_number: Mapped[str] = mapped_column(String(10))
    ledger_account_id: Mapped[UUID | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Beneficiary(Base):
    __tablename__ = "beneficiaries"
    __table_args__ = (
        UniqueConstraint("customer_id", "account_number", name="uq_beneficiaries_customer_account"),
        {"schema": BANKING_SCHEMA},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey(f"{BANKING_SCHEMA}.customers.id"))
    name: Mapped[str] = mapped_column(Text)
    account_number: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        UniqueConstraint("customer_id", "fingerprint", name="uq_devices_customer_fingerprint"),
        {"schema": BANKING_SCHEMA},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey(f"{BANKING_SCHEMA}.customers.id"))
    fingerprint: Mapped[str] = mapped_column(Text)
    user_agent: Mapped[str | None] = mapped_column(Text, default=None)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
