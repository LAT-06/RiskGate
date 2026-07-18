"""Behavior of the pure policy evaluator: matching, severity, and fail-closed errors."""

import pytest

from risk_service.engine import EvaluationError, evaluate
from risk_service.features import FeatureValue
from risk_service.policy import Policy, PolicySet

FINGERPRINT = "0" * 64


def make_policy(
    policy_id: str,
    decision: str,
    conditions: list[dict[str, object]],
    version: int = 1,
) -> Policy:
    return Policy.model_validate(
        {
            "id": policy_id,
            "version": version,
            "description": f"{policy_id} test policy.",
            "decision": decision,
            "when": {"all": conditions},
        }
    )


def make_set(*policies: Policy) -> PolicySet:
    return PolicySet(policies=policies, fingerprint=FINGERPRINT)


def cond(feature: str, operator: str, value: object) -> dict[str, object]:
    return {"feature": feature, "operator": operator, "value": value}


VELOCITY_HOLD = make_policy("VEL", "HOLD", [cond("transactions_last_10_minutes", "gte", 5)])
NEW_DEVICE_CHALLENGE = make_policy("DEV", "CHALLENGE", [cond("device_is_new", "eq", True)])
REPLAY_DENY = make_policy("REP", "DENY", [cond("replay_detected", "eq", True)])


def test_no_match_returns_allow_with_empty_matches() -> None:
    result = evaluate({"transactions_last_10_minutes": 1}, make_set(VELOCITY_HOLD))
    assert result.decision == "ALLOW"
    assert result.matched == ()
    assert result.policy_set_fingerprint == FINGERPRINT


def test_match_records_policy_id_version_decision_and_reason() -> None:
    policy = make_policy("VEL", "HOLD", [cond("transactions_last_10_minutes", "gte", 5)], version=7)
    result = evaluate({"transactions_last_10_minutes": 5}, make_set(policy))
    assert result.decision == "HOLD"
    (match,) = result.matched
    assert match.policy_id == "VEL"
    assert match.version == 7
    assert match.decision == "HOLD"
    assert match.reason == "VEL test policy."


def test_all_conditions_must_hold() -> None:
    policy = make_policy(
        "BOTH",
        "HOLD",
        [cond("device_is_new", "eq", True), cond("failed_logins_last_hour", "gte", 3)],
    )
    features: dict[str, FeatureValue] = {"device_is_new": True, "failed_logins_last_hour": 2}
    assert evaluate(features, make_set(policy)).decision == "ALLOW"
    features["failed_logins_last_hour"] = 3
    assert evaluate(features, make_set(policy)).decision == "HOLD"


def test_most_severe_matched_decision_wins() -> None:
    features: dict[str, FeatureValue] = {
        "device_is_new": True,
        "transactions_last_10_minutes": 9,
        "replay_detected": False,
    }
    policy_set = make_set(NEW_DEVICE_CHALLENGE, VELOCITY_HOLD, REPLAY_DENY)
    result = evaluate(features, policy_set)
    assert result.decision == "HOLD"
    assert {match.policy_id for match in result.matched} == {"DEV", "VEL"}
    features["replay_detected"] = True
    assert evaluate(features, policy_set).decision == "DENY"


@pytest.mark.parametrize(
    ("operator", "value", "expected"),
    [
        ("gte", 3, True),
        ("gt", 3, False),
        ("gt", 2, True),
        ("lt", 3, False),
        ("lt", 4, True),
        ("lte", 3, True),
        ("eq", 3, True),
        ("ne", 3, False),
        ("ne", 4, True),
        ("in", [1, 3, 5], True),
        ("in", [2, 4], False),
        ("not_in", [2, 4], True),
        ("not_in", [1, 3], False),
    ],
)
def test_operator_boundaries(operator: str, value: object, expected: bool) -> None:
    policy = make_policy("OP", "HOLD", [cond("failed_logins_last_hour", operator, value)])
    result = evaluate({"failed_logins_last_hour": 3}, make_set(policy))
    assert (result.decision == "HOLD") is expected


def test_float_feature_compares_against_int_and_float_values() -> None:
    policy = make_policy("RATIO", "HOLD", [cond("amount_ratio_to_user_average", "gte", 3)])
    assert evaluate({"amount_ratio_to_user_average": 3.0}, make_set(policy)).decision == "HOLD"
    assert evaluate({"amount_ratio_to_user_average": 2.9}, make_set(policy)).decision == "ALLOW"


def test_missing_referenced_feature_raises() -> None:
    with pytest.raises(EvaluationError, match="missing feature"):
        evaluate({}, make_set(VELOCITY_HOLD))


def test_unknown_context_feature_raises() -> None:
    with pytest.raises(EvaluationError, match="unknown feature"):
        evaluate({"gut_feeling": True}, make_set(VELOCITY_HOLD))


def test_mistyped_context_value_raises() -> None:
    with pytest.raises(EvaluationError, match="invalid value"):
        evaluate({"transactions_last_10_minutes": True}, make_set(VELOCITY_HOLD))


def test_non_finite_context_value_raises() -> None:
    with pytest.raises(EvaluationError, match="invalid value"):
        evaluate({"amount_ratio_to_user_average": float("nan")}, make_set(VELOCITY_HOLD))


def test_evaluation_is_deterministic() -> None:
    features: dict[str, FeatureValue] = {
        "device_is_new": True,
        "transactions_last_10_minutes": 9,
        "replay_detected": False,
    }
    policy_set = make_set(NEW_DEVICE_CHALLENGE, VELOCITY_HOLD, REPLAY_DENY)
    assert evaluate(features, policy_set) == evaluate(features, policy_set)
