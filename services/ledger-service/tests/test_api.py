from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from ledger_service.db import get_session
from ledger_service.main import app

AccountFactory = Callable[..., UUID]


@pytest.fixture
def client(engine: Engine) -> Iterator[TestClient]:
    def override_get_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_create_and_get_account(client: TestClient, tracked_accounts: list[UUID]) -> None:
    created = client.post(
        "/accounts",
        json={"customer_id": str(uuid4()), "currency": "VND", "opening_balance": 5_000},
    )
    assert created.status_code == 201
    account_id = created.json()["id"]
    tracked_accounts.append(UUID(account_id))

    fetched = client.get(f"/accounts/{account_id}")
    assert fetched.status_code == 200
    body = fetched.json()
    assert body["posted_balance"] == 5_000
    assert body["available_balance"] == 5_000
    assert body["reserved_amount"] == 0


def test_get_missing_account_returns_404(client: TestClient) -> None:
    assert client.get(f"/accounts/{uuid4()}").status_code == 404


def test_transfer_endpoint_is_idempotent(
    client: TestClient, account_factory: AccountFactory
) -> None:
    source_id = account_factory(opening_balance=10_000)
    destination_id = account_factory()
    payload = {
        "idempotency_key": f"t-{uuid4()}",
        "from_account_id": str(source_id),
        "to_account_id": str(destination_id),
        "amount": 3_000,
    }

    first = client.post("/transfers", json=payload)
    replay = client.post("/transfers", json=payload)
    assert first.status_code == 201
    assert replay.status_code == 201
    assert first.json()["id"] == replay.json()["id"]
    assert client.get(f"/accounts/{source_id}").json()["posted_balance"] == 7_000


def test_transfer_endpoint_rejects_insufficient_funds(
    client: TestClient, account_factory: AccountFactory
) -> None:
    source_id = account_factory(opening_balance=1_000)
    destination_id = account_factory()
    response = client.post(
        "/transfers",
        json={
            "idempotency_key": f"t-{uuid4()}",
            "from_account_id": str(source_id),
            "to_account_id": str(destination_id),
            "amount": 2_000,
        },
    )
    assert response.status_code == 409


def test_transfer_endpoint_rejects_same_account(
    client: TestClient, account_factory: AccountFactory
) -> None:
    account_id = account_factory(opening_balance=1_000)
    response = client.post(
        "/transfers",
        json={
            "idempotency_key": f"t-{uuid4()}",
            "from_account_id": str(account_id),
            "to_account_id": str(account_id),
            "amount": 100,
        },
    )
    assert response.status_code == 422


def test_reservation_capture_flow(client: TestClient, account_factory: AccountFactory) -> None:
    source_id = account_factory(opening_balance=10_000)
    destination_id = account_factory()
    expires_at = (datetime.now(UTC) + timedelta(hours=1)).isoformat()

    reserved = client.post(
        "/reservations",
        json={
            "idempotency_key": f"r-{uuid4()}",
            "account_id": str(source_id),
            "counterparty_account_id": str(destination_id),
            "amount": 4_000,
            "expires_at": expires_at,
        },
    )
    assert reserved.status_code == 201
    reservation_id = reserved.json()["id"]
    account = client.get(f"/accounts/{source_id}").json()
    assert account["posted_balance"] == 10_000
    assert account["available_balance"] == 6_000

    captured = client.post(f"/reservations/{reservation_id}/capture")
    assert captured.status_code == 200
    assert captured.json()["reservation_id"] == reservation_id
    account = client.get(f"/accounts/{source_id}").json()
    assert account["posted_balance"] == 6_000
    assert account["reserved_amount"] == 0
    assert client.get(f"/accounts/{destination_id}").json()["posted_balance"] == 4_000


def test_reservation_release_flow(client: TestClient, account_factory: AccountFactory) -> None:
    source_id = account_factory(opening_balance=10_000)
    destination_id = account_factory()
    expires_at = (datetime.now(UTC) + timedelta(hours=1)).isoformat()

    reserved = client.post(
        "/reservations",
        json={
            "idempotency_key": f"r-{uuid4()}",
            "account_id": str(source_id),
            "counterparty_account_id": str(destination_id),
            "amount": 4_000,
            "expires_at": expires_at,
        },
    )
    reservation_id = reserved.json()["id"]

    released = client.post(f"/reservations/{reservation_id}/release")
    assert released.status_code == 200
    assert released.json()["status"] == "RELEASED"
    account = client.get(f"/accounts/{source_id}").json()
    assert account["available_balance"] == 10_000


def test_entries_endpoint_lists_account_history(
    client: TestClient, account_factory: AccountFactory
) -> None:
    source_id = account_factory(opening_balance=10_000)
    destination_id = account_factory()
    client.post(
        "/transfers",
        json={
            "idempotency_key": f"t-{uuid4()}",
            "from_account_id": str(source_id),
            "to_account_id": str(destination_id),
            "amount": 1_000,
        },
    )

    entries = client.get(f"/accounts/{source_id}/entries").json()
    directions = [entry["direction"] for entry in entries]
    assert directions == ["CREDIT", "DEBIT"]
