from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ledger_service import operations
from ledger_service.models import (
    Account,
    Entry,
    EntryDirection,
    Reservation,
    ReservationStatus,
)

AccountFactory = Callable[..., UUID]


def _account(session: Session, account_id: UUID) -> Account:
    account = session.get(Account, account_id)
    assert account is not None
    return account


def _future() -> datetime:
    return datetime.now(UTC) + timedelta(hours=1)


def test_create_account_with_opening_balance(
    db_session: Session, account_factory: AccountFactory
) -> None:
    account_id = account_factory(opening_balance=10_000)
    account = _account(db_session, account_id)
    assert account.posted_balance == 10_000
    assert account.reserved_amount == 0
    assert account.available_balance == 10_000
    entries = db_session.scalars(select(Entry).where(Entry.account_id == account_id)).all()
    assert len(entries) == 1
    assert entries[0].direction is EntryDirection.CREDIT
    assert entries[0].amount == 10_000
    assert entries[0].transfer_id is None


def test_transfer_moves_funds_and_writes_double_entries(
    db_session: Session, account_factory: AccountFactory
) -> None:
    source_id = account_factory(opening_balance=10_000)
    destination_id = account_factory()

    transfer = operations.execute_transfer(
        db_session,
        idempotency_key=f"t-{uuid4()}",
        from_account_id=source_id,
        to_account_id=destination_id,
        amount=3_000,
    )
    db_session.commit()

    assert _account(db_session, source_id).posted_balance == 7_000
    assert _account(db_session, destination_id).posted_balance == 3_000
    entries = db_session.scalars(select(Entry).where(Entry.transfer_id == transfer.id)).all()
    directions = {entry.account_id: entry.direction for entry in entries}
    assert directions == {
        source_id: EntryDirection.DEBIT,
        destination_id: EntryDirection.CREDIT,
    }


def test_transfer_replay_returns_original_and_moves_funds_once(
    db_session: Session, account_factory: AccountFactory
) -> None:
    source_id = account_factory(opening_balance=10_000)
    destination_id = account_factory()
    key = f"t-{uuid4()}"

    first = operations.execute_transfer(
        db_session,
        idempotency_key=key,
        from_account_id=source_id,
        to_account_id=destination_id,
        amount=3_000,
    )
    db_session.commit()
    replay = operations.execute_transfer(
        db_session,
        idempotency_key=key,
        from_account_id=source_id,
        to_account_id=destination_id,
        amount=3_000,
    )
    db_session.commit()

    assert replay.id == first.id
    assert _account(db_session, source_id).posted_balance == 7_000


def test_transfer_replay_with_different_params_conflicts(
    db_session: Session, account_factory: AccountFactory
) -> None:
    source_id = account_factory(opening_balance=10_000)
    destination_id = account_factory()
    key = f"t-{uuid4()}"

    operations.execute_transfer(
        db_session,
        idempotency_key=key,
        from_account_id=source_id,
        to_account_id=destination_id,
        amount=3_000,
    )
    db_session.commit()
    with pytest.raises(operations.IdempotencyConflictError):
        operations.execute_transfer(
            db_session,
            idempotency_key=key,
            from_account_id=source_id,
            to_account_id=destination_id,
            amount=9_999,
        )


def test_transfer_rejects_insufficient_available_funds(
    db_session: Session, account_factory: AccountFactory
) -> None:
    source_id = account_factory(opening_balance=10_000)
    destination_id = account_factory()
    operations.create_reservation(
        db_session,
        idempotency_key=f"r-{uuid4()}",
        account_id=source_id,
        counterparty_account_id=destination_id,
        amount=8_000,
        expires_at=_future(),
    )
    db_session.commit()

    # Posted is still 10_000 but available is only 2_000.
    with pytest.raises(operations.InsufficientFundsError):
        operations.execute_transfer(
            db_session,
            idempotency_key=f"t-{uuid4()}",
            from_account_id=source_id,
            to_account_id=destination_id,
            amount=3_000,
        )


def test_transfer_rejects_currency_mismatch(
    db_session: Session, account_factory: AccountFactory
) -> None:
    source_id = account_factory(opening_balance=10_000, currency="VND")
    destination_id = account_factory(currency="USD")
    with pytest.raises(operations.CurrencyMismatchError):
        operations.execute_transfer(
            db_session,
            idempotency_key=f"t-{uuid4()}",
            from_account_id=source_id,
            to_account_id=destination_id,
            amount=1_000,
        )


def test_reservation_reduces_available_not_posted(
    db_session: Session, account_factory: AccountFactory
) -> None:
    source_id = account_factory(opening_balance=10_000)
    destination_id = account_factory()

    operations.create_reservation(
        db_session,
        idempotency_key=f"r-{uuid4()}",
        account_id=source_id,
        counterparty_account_id=destination_id,
        amount=4_000,
        expires_at=_future(),
    )
    db_session.commit()

    account = _account(db_session, source_id)
    assert account.posted_balance == 10_000
    assert account.reserved_amount == 4_000
    assert account.available_balance == 6_000


def test_reservation_replay_returns_original_and_reserves_once(
    db_session: Session, account_factory: AccountFactory
) -> None:
    source_id = account_factory(opening_balance=10_000)
    destination_id = account_factory()
    key = f"r-{uuid4()}"

    first = operations.create_reservation(
        db_session,
        idempotency_key=key,
        account_id=source_id,
        counterparty_account_id=destination_id,
        amount=4_000,
        expires_at=_future(),
    )
    db_session.commit()
    replay = operations.create_reservation(
        db_session,
        idempotency_key=key,
        account_id=source_id,
        counterparty_account_id=destination_id,
        amount=4_000,
        expires_at=_future(),
    )
    db_session.commit()

    assert replay.id == first.id
    assert _account(db_session, source_id).reserved_amount == 4_000


def test_capture_transfers_reserved_funds_and_is_idempotent(
    db_session: Session, account_factory: AccountFactory
) -> None:
    source_id = account_factory(opening_balance=10_000)
    destination_id = account_factory()
    reservation = operations.create_reservation(
        db_session,
        idempotency_key=f"r-{uuid4()}",
        account_id=source_id,
        counterparty_account_id=destination_id,
        amount=4_000,
        expires_at=_future(),
    )
    db_session.commit()

    transfer = operations.capture_reservation(db_session, reservation_id=reservation.id)
    db_session.commit()

    source = _account(db_session, source_id)
    assert source.posted_balance == 6_000
    assert source.reserved_amount == 0
    assert _account(db_session, destination_id).posted_balance == 4_000
    assert reservation.status is ReservationStatus.CAPTURED
    assert transfer.reservation_id == reservation.id
    entries = db_session.scalars(select(Entry).where(Entry.transfer_id == transfer.id)).all()
    assert len(entries) == 2

    replay = operations.capture_reservation(db_session, reservation_id=reservation.id)
    db_session.commit()
    assert replay.id == transfer.id
    assert _account(db_session, source_id).posted_balance == 6_000


def test_release_frees_funds_and_is_idempotent(
    db_session: Session, account_factory: AccountFactory
) -> None:
    source_id = account_factory(opening_balance=10_000)
    destination_id = account_factory()
    reservation = operations.create_reservation(
        db_session,
        idempotency_key=f"r-{uuid4()}",
        account_id=source_id,
        counterparty_account_id=destination_id,
        amount=4_000,
        expires_at=_future(),
    )
    db_session.commit()

    released = operations.release_reservation(db_session, reservation_id=reservation.id)
    db_session.commit()
    assert released.status is ReservationStatus.RELEASED
    account = _account(db_session, source_id)
    assert account.posted_balance == 10_000
    assert account.reserved_amount == 0

    again = operations.release_reservation(db_session, reservation_id=reservation.id)
    assert again.status is ReservationStatus.RELEASED


def test_release_after_capture_is_rejected(
    db_session: Session, account_factory: AccountFactory
) -> None:
    source_id = account_factory(opening_balance=10_000)
    destination_id = account_factory()
    reservation = operations.create_reservation(
        db_session,
        idempotency_key=f"r-{uuid4()}",
        account_id=source_id,
        counterparty_account_id=destination_id,
        amount=4_000,
        expires_at=_future(),
    )
    operations.capture_reservation(db_session, reservation_id=reservation.id)
    db_session.commit()

    with pytest.raises(operations.InvalidReservationStateError):
        operations.release_reservation(db_session, reservation_id=reservation.id)


def test_capture_of_expired_reservation_frees_funds_and_refuses(
    db_session: Session, account_factory: AccountFactory
) -> None:
    source_id = account_factory(opening_balance=10_000)
    destination_id = account_factory()
    reservation = operations.create_reservation(
        db_session,
        idempotency_key=f"r-{uuid4()}",
        account_id=source_id,
        counterparty_account_id=destination_id,
        amount=4_000,
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    db_session.commit()

    with pytest.raises(operations.ReservationExpiredError):
        operations.capture_reservation(db_session, reservation_id=reservation.id)
    db_session.commit()

    assert reservation.status is ReservationStatus.EXPIRED
    account = _account(db_session, source_id)
    assert account.posted_balance == 10_000
    assert account.reserved_amount == 0


def test_expire_due_reservations_sweep(
    db_session: Session, account_factory: AccountFactory
) -> None:
    source_id = account_factory(opening_balance=10_000)
    destination_id = account_factory()
    due = operations.create_reservation(
        db_session,
        idempotency_key=f"r-{uuid4()}",
        account_id=source_id,
        counterparty_account_id=destination_id,
        amount=2_000,
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    not_due = operations.create_reservation(
        db_session,
        idempotency_key=f"r-{uuid4()}",
        account_id=source_id,
        counterparty_account_id=destination_id,
        amount=3_000,
        expires_at=_future(),
    )
    db_session.commit()

    expired_here = db_session.scalars(
        select(Reservation).where(
            Reservation.account_id == source_id,
            Reservation.status == ReservationStatus.ACTIVE,
            Reservation.expires_at <= datetime.now(UTC),
        )
    ).all()
    assert [r.id for r in expired_here] == [due.id]

    operations.expire_due_reservations(db_session)
    db_session.commit()

    assert due.status is ReservationStatus.EXPIRED
    assert not_due.status is ReservationStatus.ACTIVE
    assert _account(db_session, source_id).reserved_amount == 3_000


def test_concurrent_transfers_cannot_overspend(
    engine: Engine, account_factory: AccountFactory
) -> None:
    source_id = account_factory(opening_balance=10_000)
    destination_a = account_factory()
    destination_b = account_factory()
    barrier = Barrier(2)

    def attempt(destination_id: UUID) -> str:
        with Session(engine) as session:
            barrier.wait(timeout=30)
            try:
                operations.execute_transfer(
                    session,
                    idempotency_key=f"t-{uuid4()}",
                    from_account_id=source_id,
                    to_account_id=destination_id,
                    amount=6_000,
                )
                session.commit()
                return "ok"
            except operations.InsufficientFundsError:
                session.rollback()
                return "insufficient"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = sorted(pool.map(attempt, [destination_a, destination_b]))

    assert results == ["insufficient", "ok"]
    with Session(engine) as session:
        assert _account(session, source_id).posted_balance == 4_000


def test_database_rejects_negative_posted_balance(
    engine: Engine, account_factory: AccountFactory
) -> None:
    account_id = account_factory(opening_balance=1_000)
    with Session(engine) as session, pytest.raises(IntegrityError):
        session.execute(
            text("UPDATE ledger.accounts SET posted_balance = -1 WHERE id = :id"),
            {"id": account_id},
        )
