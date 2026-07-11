from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from banking_service.identity import DEV_IDENTITY_HEADER
from riskgate_test_utilities.fake_ledger import FakeLedgerClient


def _register(
    client: TestClient, tracked: list[UUID], full_name: str = "Nguyen Van A"
) -> dict[str, str]:
    response = client.post(
        "/customers", json={"full_name": full_name, "email": f"{uuid4().hex}@example.com"}
    )
    assert response.status_code == 201
    body: dict[str, str] = response.json()
    tracked.append(UUID(body["id"]))
    return body


def _auth(customer: dict[str, str]) -> dict[str, str]:
    return {DEV_IDENTITY_HEADER: customer["id"]}


def test_register_creates_ledger_account_with_opening_balance(
    client: TestClient, tracked_customers: list[UUID], fake_ledger: FakeLedgerClient
) -> None:
    customer = _register(client, tracked_customers)
    assert len(customer["account_number"]) == 10
    assert customer["account_number"].isdigit()
    assert customer["ledger_account_id"] is not None
    assert len(fake_ledger.calls) == 1
    call = fake_ledger.calls[0]
    assert call["customer_id"] == UUID(customer["id"])
    assert call["currency"] == "VND"
    assert isinstance(call["opening_balance"], int)
    assert call["opening_balance"] > 0


def test_register_rejects_duplicate_email(
    client: TestClient, tracked_customers: list[UUID]
) -> None:
    email = f"{uuid4().hex}@example.com"
    first = client.post("/customers", json={"full_name": "A", "email": email})
    tracked_customers.append(UUID(first.json()["id"]))
    duplicate = client.post("/customers", json={"full_name": "B", "email": email})
    assert duplicate.status_code == 409


def test_profile_requires_authentication(client: TestClient, tracked_customers: list[UUID]) -> None:
    assert client.get("/customers/me").status_code == 401
    malformed = client.get("/customers/me", headers={DEV_IDENTITY_HEADER: "not-a-uuid"})
    assert malformed.status_code == 401
    unknown = client.get("/customers/me", headers={DEV_IDENTITY_HEADER: str(uuid4())})
    assert unknown.status_code == 401

    customer = _register(client, tracked_customers)
    response = client.get("/customers/me", headers=_auth(customer))
    assert response.status_code == 200
    assert response.json()["id"] == customer["id"]


def test_beneficiary_creation_validates_target_account(
    client: TestClient, tracked_customers: list[UUID]
) -> None:
    customer = _register(client, tracked_customers)
    missing = client.post(
        "/customers/me/beneficiaries",
        json={"name": "Ghost", "account_number": "0000000000"},
        headers=_auth(customer),
    )
    assert missing.status_code == 404

    own = client.post(
        "/customers/me/beneficiaries",
        json={"name": "Myself", "account_number": customer["account_number"]},
        headers=_auth(customer),
    )
    assert own.status_code == 409


def test_beneficiary_create_and_list_is_scoped_to_owner(
    client: TestClient, tracked_customers: list[UUID]
) -> None:
    alice = _register(client, tracked_customers, full_name="Alice")
    bob = _register(client, tracked_customers, full_name="Bob")

    created = client.post(
        "/customers/me/beneficiaries",
        json={"name": "Bob", "account_number": bob["account_number"]},
        headers=_auth(alice),
    )
    assert created.status_code == 201

    replay = client.post(
        "/customers/me/beneficiaries",
        json={"name": "Bob", "account_number": bob["account_number"]},
        headers=_auth(alice),
    )
    assert replay.json()["id"] == created.json()["id"]

    alice_list = client.get("/customers/me/beneficiaries", headers=_auth(alice)).json()
    assert [b["account_number"] for b in alice_list] == [bob["account_number"]]

    # Ownership: Bob must not see Alice's beneficiaries.
    bob_list = client.get("/customers/me/beneficiaries", headers=_auth(bob)).json()
    assert bob_list == []


def test_account_summary_proxies_ledger_balances(
    client: TestClient, tracked_customers: list[UUID]
) -> None:
    assert client.get("/customers/me/account").status_code == 401

    customer = _register(client, tracked_customers)
    response = client.get("/customers/me/account", headers=_auth(customer))
    assert response.status_code == 200
    body = response.json()
    assert body["account_number"] == customer["account_number"]
    assert body["currency"] == "VND"
    assert body["posted_balance"] > 0
    assert body["available_balance"] == body["posted_balance"]
    assert body["reserved_amount"] == 0


def test_entries_proxies_ledger_history(client: TestClient, tracked_customers: list[UUID]) -> None:
    customer = _register(client, tracked_customers)
    response = client.get("/customers/me/entries", headers=_auth(customer))
    assert response.status_code == 200
    entries = response.json()
    assert len(entries) == 1
    assert entries[0]["direction"] == "CREDIT"
    assert entries[0]["transfer_id"] is None


def test_device_upsert_updates_last_seen_without_duplicating(
    client: TestClient, tracked_customers: list[UUID]
) -> None:
    customer = _register(client, tracked_customers)
    first = client.post(
        "/customers/me/devices",
        json={"fingerprint": "fp-1", "user_agent": "Firefox"},
        headers=_auth(customer),
    )
    assert first.status_code == 200
    second = client.post(
        "/customers/me/devices", json={"fingerprint": "fp-1"}, headers=_auth(customer)
    )
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["last_seen"] >= first.json()["last_seen"]

    devices = client.get("/customers/me/devices", headers=_auth(customer)).json()
    assert len(devices) == 1
    assert devices[0]["user_agent"] == "Firefox"
