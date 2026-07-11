"""SQLAlchemy models for the ledger schema.

Invariants enforced by the database, not just application code:
- money is BIGINT minor units (never floats),
- posted_balance and reserved_amount never go negative,
- reserved_amount never exceeds posted_balance,
- available_balance is a generated column (posted - reserved), never written directly,
- entries are append-only: nothing in this service updates or deletes them.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

LEDGER_SCHEMA = "ledger"


class ReservationStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CAPTURED = "CAPTURED"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"


class EntryDirection(StrEnum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint("posted_balance >= 0", name="ck_accounts_posted_balance_non_negative"),
        CheckConstraint("reserved_amount >= 0", name="ck_accounts_reserved_amount_non_negative"),
        CheckConstraint(
            "reserved_amount <= posted_balance", name="ck_accounts_reserved_within_posted"
        ),
        {"schema": LEDGER_SCHEMA},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    customer_id: Mapped[UUID] = mapped_column(index=True)
    currency: Mapped[str] = mapped_column(String(3))
    posted_balance: Mapped[int] = mapped_column(BigInteger, default=0)
    reserved_amount: Mapped[int] = mapped_column(BigInteger, default=0)
    available_balance: Mapped[int] = mapped_column(
        BigInteger, Computed("posted_balance - reserved_amount", persisted=True)
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_reservations_idempotency_key"),
        CheckConstraint("amount > 0", name="ck_reservations_amount_positive"),
        CheckConstraint(
            "status IN ('ACTIVE', 'CAPTURED', 'RELEASED', 'EXPIRED')",
            name="ck_reservations_status_valid",
        ),
        CheckConstraint(
            "account_id <> counterparty_account_id", name="ck_reservations_distinct_accounts"
        ),
        Index("ix_reservations_account_id_status", "account_id", "status"),
        Index(
            "ix_reservations_active_expires_at",
            "expires_at",
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        {"schema": LEDGER_SCHEMA},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    idempotency_key: Mapped[str] = mapped_column(Text)
    account_id: Mapped[UUID] = mapped_column(ForeignKey(f"{LEDGER_SCHEMA}.accounts.id"))
    counterparty_account_id: Mapped[UUID] = mapped_column(
        ForeignKey(f"{LEDGER_SCHEMA}.accounts.id")
    )
    amount: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[ReservationStatus] = mapped_column(
        SAEnum(ReservationStatus, native_enum=False, create_constraint=False, length=16),
        default=ReservationStatus.ACTIVE,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Transfer(Base):
    __tablename__ = "transfers"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_transfers_idempotency_key"),
        CheckConstraint("amount > 0", name="ck_transfers_amount_positive"),
        CheckConstraint("from_account_id <> to_account_id", name="ck_transfers_distinct_accounts"),
        {"schema": LEDGER_SCHEMA},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    idempotency_key: Mapped[str] = mapped_column(Text)
    from_account_id: Mapped[UUID] = mapped_column(ForeignKey(f"{LEDGER_SCHEMA}.accounts.id"))
    to_account_id: Mapped[UUID] = mapped_column(ForeignKey(f"{LEDGER_SCHEMA}.accounts.id"))
    amount: Mapped[int] = mapped_column(BigInteger)
    # Set when the transfer is the capture of a HOLD reservation.
    reservation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(f"{LEDGER_SCHEMA}.reservations.id")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Entry(Base):
    __tablename__ = "entries"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_entries_amount_positive"),
        CheckConstraint("direction IN ('DEBIT', 'CREDIT')", name="ck_entries_direction_valid"),
        {"schema": LEDGER_SCHEMA},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(ForeignKey(f"{LEDGER_SCHEMA}.accounts.id"), index=True)
    # NULL only for opening-balance deposits made by the banking simulator.
    transfer_id: Mapped[UUID | None] = mapped_column(ForeignKey(f"{LEDGER_SCHEMA}.transfers.id"))
    direction: Mapped[EntryDirection] = mapped_column(
        SAEnum(EntryDirection, native_enum=False, create_constraint=False, length=6)
    )
    amount: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
