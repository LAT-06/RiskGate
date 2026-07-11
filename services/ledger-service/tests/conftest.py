"""Database fixtures for ledger integration tests.

Tests run against TEST_DATABASE_URL, falling back to DATABASE_URL (repo-root
.env), and are skipped when neither is configured. Tests only touch rows for
accounts they create themselves (random UUIDs) and delete them on teardown, so
a shared development database stays clean.
"""

import os
from collections.abc import Callable, Iterator
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import Engine, create_engine, delete, or_, text
from sqlalchemy.orm import Session

from ledger_service import operations
from ledger_service.models import Account, Base, Entry, Reservation, Transfer
from ledger_service.settings import load_settings

AccountFactory = Callable[..., UUID]


def _database_url() -> str | None:
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url
    try:
        return load_settings().database_url
    except ValidationError:
        return None


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    url = _database_url()
    if url is None:
        pytest.skip("neither TEST_DATABASE_URL nor DATABASE_URL is configured")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS ledger"))
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(engine: Engine, tracked_accounts: list[UUID]) -> Iterator[Session]:
    # Depends on tracked_accounts so this teardown runs first: the rollback
    # releases any FOR UPDATE locks before the cleanup DELETEs need them.
    with Session(engine) as session:
        yield session
        session.rollback()


@pytest.fixture
def tracked_accounts(engine: Engine) -> Iterator[list[UUID]]:
    ids: list[UUID] = []
    yield ids
    if not ids:
        return
    with Session(engine) as session:
        session.execute(delete(Entry).where(Entry.account_id.in_(ids)))
        session.execute(
            delete(Transfer).where(
                or_(Transfer.from_account_id.in_(ids), Transfer.to_account_id.in_(ids))
            )
        )
        session.execute(delete(Reservation).where(Reservation.account_id.in_(ids)))
        session.execute(delete(Account).where(Account.id.in_(ids)))
        session.commit()


@pytest.fixture
def account_factory(engine: Engine, tracked_accounts: list[UUID]) -> AccountFactory:
    def make(opening_balance: int = 0, currency: str = "VND") -> UUID:
        with Session(engine) as session:
            account = operations.create_account(
                session,
                customer_id=uuid4(),
                currency=currency,
                opening_balance=opening_balance,
            )
            session.commit()
            account_id = account.id
        tracked_accounts.append(account_id)
        return account_id

    return make
