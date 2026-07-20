"""Unit tests for the pure feature computation (no DB, no banking service)."""

from datetime import UTC, datetime, timedelta

from risk_service.context import TRUSTED_DEVICE_MIN_AGE, build_features
from risk_service.features import FEATURES, FeatureValue, value_matches_type
from risk_service.history import CustomerHistory
from riskgate_contracts.banking import BankingBeneficiary, BankingDevice

NOW = datetime(2026, 7, 20, 12, 0, 0, tzinfo=UTC)


def device(fingerprint: str = "fp-1", *, age: timedelta = timedelta(days=30)) -> BankingDevice:
    seen = (NOW - age).isoformat()
    return BankingDevice(id="d-1", fingerprint=fingerprint, first_seen=seen, last_seen=seen)


def beneficiary(*, age: timedelta = timedelta(days=90)) -> BankingBeneficiary:
    return BankingBeneficiary(
        id="b-1", account_number="0000000001", created_at=(NOW - age).isoformat()
    )


def history(**overrides: object) -> CustomerHistory:
    values: dict[str, object] = {
        "prior_transactions_in_window": 0,
        "prior_amount_in_window": 0,
        "average_transaction_amount": None,
        "beneficiary_allowed_transaction_count": 0,
        "failed_logins_last_hour": 0,
        "last_ip_country": None,
    }
    values.update(overrides)
    return CustomerHistory.model_validate(values)


def build(**overrides: object) -> dict[str, FeatureValue]:
    kwargs: dict[str, object] = {
        "amount_minor": 100_000,
        "ip_country": "VN",
        "mfa_verified": False,
        "replay_detected": False,
        "device_fingerprint": "fp-1",
        "devices": [device()],
        "beneficiary": beneficiary(),
        "history": history(),
        "now": NOW,
    }
    kwargs.update(overrides)
    return build_features(**kwargs)  # type: ignore[arg-type]


def test_output_covers_the_full_feature_registry_with_valid_types() -> None:
    features = build()
    assert set(features) == set(FEATURES)
    for name, value in features.items():
        assert value_matches_type(value, FEATURES[name]), name


def test_unknown_fingerprint_is_new_and_untrusted() -> None:
    features = build(device_fingerprint="fp-unknown")
    assert features["device_is_new"] is True
    assert features["device_is_trusted"] is False


def test_device_trust_threshold_boundary() -> None:
    young = build(devices=[device(age=TRUSTED_DEVICE_MIN_AGE - timedelta(minutes=1))])
    assert young["device_is_new"] is False
    assert young["device_is_trusted"] is False
    exact = build(devices=[device(age=TRUSTED_DEVICE_MIN_AGE)])
    assert exact["device_is_trusted"] is True


def test_beneficiary_age_is_floored_minutes_and_never_negative() -> None:
    assert (
        build(beneficiary=beneficiary(age=timedelta(minutes=59, seconds=59)))[
            "beneficiary_age_minutes"
        ]
        == 59
    )
    # Clock skew: a creation timestamp slightly in the future must not go negative.
    assert (
        build(beneficiary=beneficiary(age=timedelta(seconds=-30)))["beneficiary_age_minutes"] == 0
    )


def test_amount_ratio_defaults_to_one_without_history() -> None:
    assert build()["amount_ratio_to_user_average"] == 1.0


def test_amount_ratio_uses_the_historical_average() -> None:
    features = build(amount_minor=300_000, history=history(average_transaction_amount=100_000.0))
    assert features["amount_ratio_to_user_average"] == 3.0


def test_velocity_counts_the_current_transaction() -> None:
    features = build(
        history=history(prior_transactions_in_window=4, prior_amount_in_window=500_000)
    )
    assert features["transactions_last_10_minutes"] == 5
    assert features["total_amount_last_10_minutes"] == 600_000


def test_country_changed_only_when_history_disagrees() -> None:
    assert build()["country_changed"] is False
    assert build(history=history(last_ip_country="VN"))["country_changed"] is False
    assert build(history=history(last_ip_country="US"))["country_changed"] is True


def test_caller_owned_facts_pass_through() -> None:
    features = build(mfa_verified=True, replay_detected=True)
    assert features["mfa_verified"] is True
    assert features["replay_detected"] is True
