"""Ledger operations: the only code allowed to change balances.

Every operation runs inside the caller's transaction (the caller commits) and
locks the rows it touches with SELECT ... FOR UPDATE, always acquiring account
locks in primary-key order so concurrent operations cannot deadlock. Database
CHECK constraints back up every balance invariant enforced here.

Idempotency: transfers and reservations carry a client-supplied idempotency
key. Replaying a key with identical parameters returns the original row;
replaying it with different parameters raises IdempotencyConflictError.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ledger_service.models import (
    Account,
    Entry,
    EntryDirection,
    Reservation,
    ReservationStatus,
    Transfer,
)


class LedgerError(Exception):
    """Base class for domain errors raised by ledger operations."""


class AccountNotFoundError(LedgerError):
    pass


class ReservationNotFoundError(LedgerError):
    pass


class InsufficientFundsError(LedgerError):
    pass


class CurrencyMismatchError(LedgerError):
    pass


class InvalidReservationStateError(LedgerError):
    pass


class ReservationExpiredError(LedgerError):
    """Raised by capture when the reservation's expiry has passed.

    The expiration transition (status EXPIRED, reserved funds freed) has
    already been applied to the session; the caller must commit it.
    """


class IdempotencyConflictError(LedgerError):
    """Same idempotency key reused with different parameters."""


def _now() -> datetime:
    return datetime.now(UTC)


def _lock_accounts(session: Session, *account_ids: UUID) -> dict[UUID, Account]:
    accounts: dict[UUID, Account] = {}
    for account_id in sorted(set(account_ids)):
        account = session.scalar(
            select(Account)
            .where(Account.id == account_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if account is None:
            raise AccountNotFoundError(f"account {account_id} not found")
        accounts[account_id] = account
    return accounts


def _lock_reservation(session: Session, reservation_id: UUID) -> Reservation:
    reservation = session.scalar(
        select(Reservation)
        .where(Reservation.id == reservation_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if reservation is None:
        raise ReservationNotFoundError(f"reservation {reservation_id} not found")
    return reservation


def _expire(session: Session, reservation: Reservation) -> None:
    account = _lock_accounts(session, reservation.account_id)[reservation.account_id]
    account.reserved_amount -= reservation.amount
    reservation.status = ReservationStatus.EXPIRED
    session.flush()


def create_account(
    session: Session, *, customer_id: UUID, currency: str, opening_balance: int = 0
) -> Account:
    if opening_balance < 0:
        raise ValueError("opening_balance must be >= 0")
    account = Account(
        customer_id=customer_id,
        currency=currency,
        posted_balance=opening_balance,
        reserved_amount=0,
    )
    session.add(account)
    session.flush()
    if opening_balance > 0:
        session.add(
            Entry(
                account_id=account.id,
                transfer_id=None,
                direction=EntryDirection.CREDIT,
                amount=opening_balance,
            )
        )
        session.flush()
    return account


def execute_transfer(
    session: Session,
    *,
    idempotency_key: str,
    from_account_id: UUID,
    to_account_id: UUID,
    amount: int,
) -> Transfer:
    existing = session.scalar(select(Transfer).where(Transfer.idempotency_key == idempotency_key))
    if existing is not None:
        replayed = (from_account_id, to_account_id, amount, None)
        original = (
            existing.from_account_id,
            existing.to_account_id,
            existing.amount,
            existing.reservation_id,
        )
        if replayed != original:
            raise IdempotencyConflictError(f"idempotency key {idempotency_key!r} already used")
        return existing

    accounts = _lock_accounts(session, from_account_id, to_account_id)
    source = accounts[from_account_id]
    destination = accounts[to_account_id]
    if source.currency != destination.currency:
        raise CurrencyMismatchError(f"{source.currency} -> {destination.currency}")
    if source.available_balance < amount:
        raise InsufficientFundsError(
            f"available {source.available_balance} < transfer amount {amount}"
        )

    source.posted_balance -= amount
    destination.posted_balance += amount
    transfer = Transfer(
        idempotency_key=idempotency_key,
        from_account_id=from_account_id,
        to_account_id=to_account_id,
        amount=amount,
    )
    session.add(transfer)
    session.flush()
    session.add_all(
        [
            Entry(
                account_id=source.id,
                transfer_id=transfer.id,
                direction=EntryDirection.DEBIT,
                amount=amount,
            ),
            Entry(
                account_id=destination.id,
                transfer_id=transfer.id,
                direction=EntryDirection.CREDIT,
                amount=amount,
            ),
        ]
    )
    session.flush()
    return transfer


def create_reservation(
    session: Session,
    *,
    idempotency_key: str,
    account_id: UUID,
    counterparty_account_id: UUID,
    amount: int,
    expires_at: datetime,
) -> Reservation:
    existing = session.scalar(
        select(Reservation).where(Reservation.idempotency_key == idempotency_key)
    )
    if existing is not None:
        replayed = (account_id, counterparty_account_id, amount)
        original = (existing.account_id, existing.counterparty_account_id, existing.amount)
        if replayed != original:
            raise IdempotencyConflictError(f"idempotency key {idempotency_key!r} already used")
        return existing

    account = _lock_accounts(session, account_id)[account_id]
    counterparty = session.get(Account, counterparty_account_id)
    if counterparty is None:
        raise AccountNotFoundError(f"account {counterparty_account_id} not found")
    if account.currency != counterparty.currency:
        raise CurrencyMismatchError(f"{account.currency} -> {counterparty.currency}")
    if account.available_balance < amount:
        raise InsufficientFundsError(
            f"available {account.available_balance} < reservation amount {amount}"
        )

    account.reserved_amount += amount
    reservation = Reservation(
        idempotency_key=idempotency_key,
        account_id=account_id,
        counterparty_account_id=counterparty_account_id,
        amount=amount,
        status=ReservationStatus.ACTIVE,
        expires_at=expires_at,
    )
    session.add(reservation)
    session.flush()
    return reservation


def capture_reservation(
    session: Session, *, reservation_id: UUID, now: datetime | None = None
) -> Transfer:
    now = now or _now()
    reservation = _lock_reservation(session, reservation_id)

    if reservation.status is ReservationStatus.CAPTURED:
        transfer = session.scalar(select(Transfer).where(Transfer.reservation_id == reservation.id))
        if transfer is None:
            raise InvalidReservationStateError(
                f"reservation {reservation_id} is CAPTURED but has no transfer"
            )
        return transfer
    if reservation.status is not ReservationStatus.ACTIVE:
        raise InvalidReservationStateError(f"reservation {reservation_id} is {reservation.status}")
    if reservation.expires_at <= now:
        _expire(session, reservation)
        raise ReservationExpiredError(f"reservation {reservation_id} expired")

    accounts = _lock_accounts(session, reservation.account_id, reservation.counterparty_account_id)
    source = accounts[reservation.account_id]
    destination = accounts[reservation.counterparty_account_id]

    source.posted_balance -= reservation.amount
    source.reserved_amount -= reservation.amount
    destination.posted_balance += reservation.amount
    reservation.status = ReservationStatus.CAPTURED
    transfer = Transfer(
        idempotency_key=f"capture:{reservation.id}",
        from_account_id=source.id,
        to_account_id=destination.id,
        amount=reservation.amount,
        reservation_id=reservation.id,
    )
    session.add(transfer)
    session.flush()
    session.add_all(
        [
            Entry(
                account_id=source.id,
                transfer_id=transfer.id,
                direction=EntryDirection.DEBIT,
                amount=reservation.amount,
            ),
            Entry(
                account_id=destination.id,
                transfer_id=transfer.id,
                direction=EntryDirection.CREDIT,
                amount=reservation.amount,
            ),
        ]
    )
    session.flush()
    return transfer


def release_reservation(
    session: Session, *, reservation_id: UUID, now: datetime | None = None
) -> Reservation:
    now = now or _now()
    reservation = _lock_reservation(session, reservation_id)

    if reservation.status in (ReservationStatus.RELEASED, ReservationStatus.EXPIRED):
        return reservation
    if reservation.status is ReservationStatus.CAPTURED:
        raise InvalidReservationStateError(f"reservation {reservation_id} is CAPTURED")
    if reservation.expires_at <= now:
        _expire(session, reservation)
        return reservation

    account = _lock_accounts(session, reservation.account_id)[reservation.account_id]
    account.reserved_amount -= reservation.amount
    reservation.status = ReservationStatus.RELEASED
    session.flush()
    return reservation


def expire_due_reservations(session: Session, *, now: datetime | None = None) -> int:
    now = now or _now()
    due = session.scalars(
        select(Reservation)
        .where(Reservation.status == ReservationStatus.ACTIVE, Reservation.expires_at <= now)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).all()
    for reservation in due:
        _expire(session, reservation)
    return len(due)
