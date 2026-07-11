"""Fixtures for banking integration tests.

Same database strategy as ledger-service: TEST_DATABASE_URL, falling back to
DATABASE_URL (repo-root .env), skipped when neither is set. Tests only touch
customers they create and delete them on teardown.
"""

import os
from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import Engine, create_engine, delete, text
from sqlalchemy.orm import Session

from banking_service.db import get_session
from banking_service.ledger_client import get_ledger_client
from banking_service.main import app
from banking_service.models import Base, Beneficiary, Customer, Device
from banking_service.settings import load_settings
from riskgate_test_utilities.fake_ledger import FakeLedgerClient


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
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS banking"))
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def tracked_customers(engine: Engine) -> Iterator[list[UUID]]:
    ids: list[UUID] = []
    yield ids
    if not ids:
        return
    with Session(engine) as session:
        session.execute(delete(Device).where(Device.customer_id.in_(ids)))
        session.execute(delete(Beneficiary).where(Beneficiary.customer_id.in_(ids)))
        session.execute(delete(Customer).where(Customer.id.in_(ids)))
        session.commit()


@pytest.fixture
def fake_ledger() -> FakeLedgerClient:
    return FakeLedgerClient()


@pytest.fixture
def client(engine: Engine, fake_ledger: FakeLedgerClient) -> Iterator[TestClient]:
    def override_get_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_ledger_client] = lambda: fake_ledger
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
