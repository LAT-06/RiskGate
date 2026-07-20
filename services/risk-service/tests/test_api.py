"""Integration tests for the decision API against a real database.

Banking data comes from the in-memory fake client; history features come from
rows these tests create through the API itself.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from risk_service.banking_client import BankingUnavailableError, get_banking_client
from risk_service.main import app
from risk_service.models import Assessment, PolicyVersion
from riskgate_contracts.banking import BankingBeneficiary, BankingDevice
from riskgate_test_utilities.fake_banking import FakeBankingClient


def _seed_banking(
    fake: FakeBankingClient,
    customer_id: UUID,
    beneficiary_id: UUID,
    *,
    fingerprint: str = "fp-1",
    device_age: timedelta = timedelta(days=30),
    beneficiary_age: timedelta = timedelta(days=90),
) -> None:
    now = datetime.now(UTC)
    fake.devices[customer_id] = [
        BankingDevice(
            id=str(uuid4()),
            fingerprint=fingerprint,
            first_seen=(now - device_age).isoformat(),
            last_seen=now.isoformat(),
        )
    ]
    fake.beneficiaries[(customer_id, beneficiary_id)] = BankingBeneficiary(
        id=str(beneficiary_id),
        account_number="0000000001",
        created_at=(now - beneficiary_age).isoformat(),
    )


def _payload(customer_id: UUID, beneficiary_id: UUID, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "transaction_id": str(uuid4()),
        "customer_id": str(customer_id),
        "beneficiary_id": str(beneficiary_id),
        "amount_minor": 100_000,
        "currency": "VND",
        "device_fingerprint": "fp-1",
        "ip_country": "VN",
        "mfa_verified": False,
        "replay_detected": False,
    }
    payload.update(overrides)
    return payload


def _new_customer(
    client_fake: FakeBankingClient, tracked: list[UUID], **seed_overrides: Any
) -> tuple[UUID, UUID]:
    customer_id, beneficiary_id = uuid4(), uuid4()
    tracked.append(customer_id)
    _seed_banking(client_fake, customer_id, beneficiary_id, **seed_overrides)
    return customer_id, beneficiary_id


def test_baseline_transaction_is_allowed_and_persisted(
    client: TestClient,
    fake_banking: FakeBankingClient,
    tracked_customers: list[UUID],
    engine: Engine,
) -> None:
    customer_id, beneficiary_id = _new_customer(fake_banking, tracked_customers)
    response = client.post("/assessments", json=_payload(customer_id, beneficiary_id))
    assert response.status_code == 201
    body = response.json()
    assert body["decision"] == "ALLOW"
    assert body["matched_policies"] == []
    assert body["features"]["device_is_new"] is False
    assert body["features"]["device_is_trusted"] is True
    assert body["features"]["transactions_last_10_minutes"] == 1

    with Session(engine) as session:
        stored = session.scalars(
            select(Assessment).where(Assessment.customer_id == customer_id)
        ).one()
        assert stored.decision == "ALLOW"
        assert stored.features == body["features"]
        assert stored.policy_set_fingerprint == body["policy_set_fingerprint"]
        snapshot = session.get(PolicyVersion, stored.policy_set_fingerprint)
        assert snapshot is not None
        assert {p["id"] for p in snapshot.policies} >= {"NEW_DEVICE", "REPLAY_DETECTED"}


def test_new_device_is_challenged_then_cleared_by_mfa_reevaluation(
    client: TestClient, fake_banking: FakeBankingClient, tracked_customers: list[UUID]
) -> None:
    customer_id, beneficiary_id = _new_customer(fake_banking, tracked_customers)
    payload = _payload(customer_id, beneficiary_id, device_fingerprint="fp-brand-new")

    first = client.post("/assessments", json=payload).json()
    assert first["decision"] == "CHALLENGE"
    assert [m["policy_id"] for m in first["matched_policies"]] == ["NEW_DEVICE"]

    # Post-MFA re-evaluation of the same transaction: the CHALLENGE clears and
    # the transaction does not count itself twice in the velocity window.
    second = client.post("/assessments", json={**payload, "mfa_verified": True}).json()
    assert second["decision"] == "ALLOW"
    assert second["features"]["transactions_last_10_minutes"] == 1


def test_transaction_velocity_holds_the_fifth_transaction(
    client: TestClient, fake_banking: FakeBankingClient, tracked_customers: list[UUID]
) -> None:
    customer_id, beneficiary_id = _new_customer(fake_banking, tracked_customers)
    for _ in range(4):
        response = client.post("/assessments", json=_payload(customer_id, beneficiary_id))
        assert response.json()["decision"] == "ALLOW"

    fifth = client.post("/assessments", json=_payload(customer_id, beneficiary_id)).json()
    assert fifth["features"]["transactions_last_10_minutes"] == 5
    assert fifth["decision"] == "HOLD"
    assert "TRANSACTION_VELOCITY" in [m["policy_id"] for m in fifth["matched_policies"]]


def test_amount_far_above_average_is_challenged(
    client: TestClient, fake_banking: FakeBankingClient, tracked_customers: list[UUID]
) -> None:
    customer_id, beneficiary_id = _new_customer(fake_banking, tracked_customers)
    client.post("/assessments", json=_payload(customer_id, beneficiary_id, amount_minor=100_000))

    spike = client.post(
        "/assessments", json=_payload(customer_id, beneficiary_id, amount_minor=300_000)
    ).json()
    assert spike["features"]["amount_ratio_to_user_average"] == 3.0
    assert spike["decision"] == "CHALLENGE"
    assert [m["policy_id"] for m in spike["matched_policies"]] == ["HIGH_AMOUNT_RATIO"]


def test_replay_is_denied(
    client: TestClient, fake_banking: FakeBankingClient, tracked_customers: list[UUID]
) -> None:
    customer_id, beneficiary_id = _new_customer(fake_banking, tracked_customers)
    response = client.post(
        "/assessments", json=_payload(customer_id, beneficiary_id, replay_detected=True)
    ).json()
    assert response["decision"] == "DENY"
    assert [m["policy_id"] for m in response["matched_policies"]] == ["REPLAY_DETECTED"]


def test_failed_login_burst_holds_even_with_mfa(
    client: TestClient, fake_banking: FakeBankingClient, tracked_customers: list[UUID]
) -> None:
    customer_id, beneficiary_id = _new_customer(fake_banking, tracked_customers)
    for _ in range(3):
        event = client.post(
            "/events/authentication",
            json={"customer_id": str(customer_id), "outcome": "failure"},
        )
        assert event.status_code == 201

    response = client.post(
        "/assessments", json=_payload(customer_id, beneficiary_id, mfa_verified=True)
    ).json()
    assert response["features"]["failed_logins_last_hour"] == 3
    assert response["decision"] == "HOLD"
    assert [m["policy_id"] for m in response["matched_policies"]] == ["FAILED_LOGIN_BURST"]


def test_successful_logins_do_not_count_as_failures(
    client: TestClient, fake_banking: FakeBankingClient, tracked_customers: list[UUID]
) -> None:
    customer_id, beneficiary_id = _new_customer(fake_banking, tracked_customers)
    client.post(
        "/events/authentication", json={"customer_id": str(customer_id), "outcome": "success"}
    )
    response = client.post("/assessments", json=_payload(customer_id, beneficiary_id)).json()
    assert response["features"]["failed_logins_last_hour"] == 0


def test_unknown_beneficiary_is_rejected(
    client: TestClient, fake_banking: FakeBankingClient, tracked_customers: list[UUID]
) -> None:
    customer_id, _ = _new_customer(fake_banking, tracked_customers)
    response = client.post("/assessments", json=_payload(customer_id, uuid4()))
    assert response.status_code == 422


def test_banking_outage_fails_closed_with_502(
    client: TestClient, tracked_customers: list[UUID]
) -> None:
    class DownBankingClient:
        def list_devices(self, *, customer_id: UUID) -> list[BankingDevice]:
            raise BankingUnavailableError("connection refused")

        def get_beneficiary(
            self, *, customer_id: UUID, beneficiary_id: UUID
        ) -> BankingBeneficiary | None:
            raise BankingUnavailableError("connection refused")

    app.dependency_overrides[get_banking_client] = DownBankingClient
    customer_id = uuid4()
    tracked_customers.append(customer_id)
    response = client.post("/assessments", json=_payload(customer_id, uuid4()))
    assert response.status_code == 502
