"""MVP demo scenarios evaluated against the real policies/ directory."""

from pathlib import Path

import pytest

from risk_service.engine import evaluate
from risk_service.features import FeatureValue
from risk_service.policy import PolicySet, load_policy_set

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def policy_set() -> PolicySet:
    return load_policy_set(REPO_ROOT / "policies")


def context(**overrides: FeatureValue) -> dict[str, FeatureValue]:
    """A baseline low-risk context: known device, old beneficiary, normal amount."""
    features: dict[str, FeatureValue] = {
        "device_is_new": False,
        "device_is_trusted": True,
        "beneficiary_age_minutes": 60_000,
        "beneficiary_previous_transaction_count": 12,
        "amount_ratio_to_user_average": 1.0,
        "transactions_last_10_minutes": 1,
        "total_amount_last_10_minutes": 50_00,
        "failed_logins_last_hour": 0,
        "country_changed": False,
        "mfa_verified": False,
        "replay_detected": False,
    }
    features.update(overrides)
    return features


def test_scenario_1_normal_transaction_is_allowed(policy_set: PolicySet) -> None:
    result = evaluate(context(), policy_set)
    assert result.decision == "ALLOW"
    assert result.matched == ()


def test_scenario_2_new_device_is_challenged(policy_set: PolicySet) -> None:
    result = evaluate(context(device_is_new=True, amount_ratio_to_user_average=2.0), policy_set)
    assert result.decision == "CHALLENGE"
    assert {match.policy_id for match in result.matched} == {"NEW_DEVICE"}


def test_scenario_3_account_takeover_pattern_is_held(policy_set: PolicySet) -> None:
    result = evaluate(
        context(
            failed_logins_last_hour=4,
            device_is_new=True,
            beneficiary_age_minutes=5,
            beneficiary_previous_transaction_count=0,
            amount_ratio_to_user_average=6.0,
        ),
        policy_set,
    )
    assert result.decision == "HOLD"
    assert {match.policy_id for match in result.matched} == {
        "FAILED_LOGIN_BURST",
        "NEW_DEVICE",
        "NEW_BENEFICIARY",
        "HIGH_AMOUNT_RATIO",
    }


def test_replay_is_denied(policy_set: PolicySet) -> None:
    result = evaluate(context(replay_detected=True), policy_set)
    assert result.decision == "DENY"
    assert {match.policy_id for match in result.matched} == {"REPLAY_DETECTED"}


def test_transaction_velocity_is_held(policy_set: PolicySet) -> None:
    result = evaluate(context(transactions_last_10_minutes=5), policy_set)
    assert result.decision == "HOLD"
    assert {match.policy_id for match in result.matched} == {"TRANSACTION_VELOCITY"}


def test_completed_mfa_clears_challenge_policies(policy_set: PolicySet) -> None:
    features = context(device_is_new=True, amount_ratio_to_user_average=4.0, mfa_verified=True)
    result = evaluate(features, policy_set)
    assert result.decision == "ALLOW"
    assert result.matched == ()


def test_completed_mfa_does_not_clear_hold_policies(policy_set: PolicySet) -> None:
    features = context(failed_logins_last_hour=4, device_is_new=True, mfa_verified=True)
    result = evaluate(features, policy_set)
    assert result.decision == "HOLD"
    assert {match.policy_id for match in result.matched} == {"FAILED_LOGIN_BURST"}


def test_every_match_records_policy_version_and_set_fingerprint(policy_set: PolicySet) -> None:
    result = evaluate(context(device_is_new=True), policy_set)
    assert result.policy_set_fingerprint == policy_set.fingerprint
    assert all(match.version >= 1 and match.reason for match in result.matched)


def test_boundary_values_for_initial_policies(policy_set: PolicySet) -> None:
    assert evaluate(context(failed_logins_last_hour=2), policy_set).decision == "ALLOW"
    assert evaluate(context(failed_logins_last_hour=3), policy_set).decision == "HOLD"
    assert evaluate(context(transactions_last_10_minutes=4), policy_set).decision == "ALLOW"
    assert evaluate(context(amount_ratio_to_user_average=2.99), policy_set).decision == "ALLOW"
    assert evaluate(context(amount_ratio_to_user_average=3.0), policy_set).decision == "CHALLENGE"
    new_beneficiary = context(beneficiary_previous_transaction_count=0)
    assert evaluate({**new_beneficiary, "beneficiary_age_minutes": 60}, policy_set).decision == (
        "ALLOW"
    )
    assert evaluate({**new_beneficiary, "beneficiary_age_minutes": 59}, policy_set).decision == (
        "CHALLENGE"
    )
