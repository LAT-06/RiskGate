"""Schema validation and loading of YAML policies (fail-closed on any defect)."""

from pathlib import Path

import pytest
import yaml

from risk_service.policy import PolicyError, load_policy_set

REPO_ROOT = Path(__file__).resolve().parents[3]


def write_policy(directory: Path, name: str = "policy.yaml", **overrides: object) -> Path:
    body: dict[str, object] = {
        "id": "TEST_POLICY",
        "version": 1,
        "description": "Test policy.",
        "decision": "CHALLENGE",
        "when": {"all": [{"feature": "device_is_new", "operator": "eq", "value": True}]},
    }
    body.update(overrides)
    path = directory / name
    path.write_text(yaml.safe_dump(body))
    return path


def condition(feature: str, operator: str, value: object) -> dict[str, object]:
    return {"all": [{"feature": feature, "operator": operator, "value": value}]}


def test_loads_repository_policies() -> None:
    policy_set = load_policy_set(REPO_ROOT / "policies")
    assert {policy.id for policy in policy_set.policies} == {
        "NEW_DEVICE",
        "NEW_BENEFICIARY",
        "HIGH_AMOUNT_RATIO",
        "TRANSACTION_VELOCITY",
        "FAILED_LOGIN_BURST",
        "REPLAY_DETECTED",
    }
    assert all(policy.version == 1 for policy in policy_set.policies)
    assert len(policy_set.fingerprint) == 64


def test_fingerprint_is_stable_across_loads() -> None:
    first = load_policy_set(REPO_ROOT / "policies")
    second = load_policy_set(REPO_ROOT / "policies")
    assert first.fingerprint == second.fingerprint


def test_fingerprint_changes_when_a_policy_changes(tmp_path: Path) -> None:
    write_policy(tmp_path)
    before = load_policy_set(tmp_path).fingerprint
    write_policy(tmp_path, version=2)
    assert load_policy_set(tmp_path).fingerprint != before


def test_valid_policy_loads(tmp_path: Path) -> None:
    write_policy(tmp_path)
    policy_set = load_policy_set(tmp_path)
    assert policy_set.policies[0].id == "TEST_POLICY"
    assert policy_set.policies[0].when.all[0].feature == "device_is_new"


def test_empty_directory_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(PolicyError, match="no policy files"):
        load_policy_set(tmp_path)


def test_unknown_operator_is_rejected(tmp_path: Path) -> None:
    write_policy(tmp_path, when=condition("failed_logins_last_hour", "regex", 3))
    with pytest.raises(PolicyError):
        load_policy_set(tmp_path)


def test_unknown_feature_is_rejected(tmp_path: Path) -> None:
    write_policy(tmp_path, when=condition("astrological_sign", "eq", True))
    with pytest.raises(PolicyError, match="unknown feature"):
        load_policy_set(tmp_path)


def test_unknown_top_level_field_is_rejected(tmp_path: Path) -> None:
    write_policy(tmp_path, script="import os")
    with pytest.raises(PolicyError):
        load_policy_set(tmp_path)


def test_unknown_condition_field_is_rejected(tmp_path: Path) -> None:
    write_policy(
        tmp_path,
        when={"all": [{"feature": "device_is_new", "operator": "eq", "value": True, "exec": "rm"}]},
    )
    with pytest.raises(PolicyError):
        load_policy_set(tmp_path)


def test_missing_required_field_is_rejected(tmp_path: Path) -> None:
    body: dict[str, object] = {"id": "TEST_POLICY", "version": 1, "decision": "HOLD"}
    (tmp_path / "policy.yaml").write_text(yaml.safe_dump(body))
    with pytest.raises(PolicyError):
        load_policy_set(tmp_path)


def test_allow_decision_is_rejected(tmp_path: Path) -> None:
    write_policy(tmp_path, decision="ALLOW")
    with pytest.raises(PolicyError, match="escalate"):
        load_policy_set(tmp_path)


def test_unknown_decision_is_rejected(tmp_path: Path) -> None:
    write_policy(tmp_path, decision="MAYBE")
    with pytest.raises(PolicyError):
        load_policy_set(tmp_path)


def test_duplicate_policy_id_is_rejected(tmp_path: Path) -> None:
    write_policy(tmp_path, name="a.yaml")
    write_policy(tmp_path, name="b.yaml")
    with pytest.raises(PolicyError, match="duplicate policy id"):
        load_policy_set(tmp_path)


def test_invalid_yaml_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "policy.yaml").write_text("id: [unclosed")
    with pytest.raises(PolicyError, match="invalid YAML"):
        load_policy_set(tmp_path)


def test_non_mapping_yaml_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "policy.yaml").write_text("- just\n- a\n- list\n")
    with pytest.raises(PolicyError, match="YAML mapping"):
        load_policy_set(tmp_path)


def test_ordering_operator_on_boolean_feature_is_rejected(tmp_path: Path) -> None:
    write_policy(tmp_path, when=condition("device_is_new", "gt", True))
    with pytest.raises(PolicyError, match="not valid for boolean"):
        load_policy_set(tmp_path)


def test_membership_operator_requires_list(tmp_path: Path) -> None:
    write_policy(tmp_path, when=condition("failed_logins_last_hour", "in", 3))
    with pytest.raises(PolicyError, match="requires a list"):
        load_policy_set(tmp_path)


def test_membership_operator_rejects_empty_list(tmp_path: Path) -> None:
    write_policy(tmp_path, when=condition("failed_logins_last_hour", "in", []))
    with pytest.raises(PolicyError, match="non-empty list"):
        load_policy_set(tmp_path)


def test_scalar_operator_rejects_list(tmp_path: Path) -> None:
    write_policy(tmp_path, when=condition("failed_logins_last_hour", "eq", [1, 2]))
    with pytest.raises(PolicyError, match="does not accept a list"):
        load_policy_set(tmp_path)


def test_value_type_must_match_feature_type(tmp_path: Path) -> None:
    write_policy(tmp_path, when=condition("beneficiary_age_minutes", "eq", True))
    with pytest.raises(PolicyError, match="not a valid"):
        load_policy_set(tmp_path)


def test_string_value_is_rejected(tmp_path: Path) -> None:
    write_policy(tmp_path, when=condition("failed_logins_last_hour", "gte", "3"))
    with pytest.raises(PolicyError):
        load_policy_set(tmp_path)


def test_non_finite_float_value_is_rejected(tmp_path: Path) -> None:
    write_policy(tmp_path, when=condition("amount_ratio_to_user_average", "gte", float("nan")))
    with pytest.raises(PolicyError, match="not a valid"):
        load_policy_set(tmp_path)


def test_version_zero_is_rejected(tmp_path: Path) -> None:
    write_policy(tmp_path, version=0)
    with pytest.raises(PolicyError):
        load_policy_set(tmp_path)


def test_lowercase_policy_id_is_rejected(tmp_path: Path) -> None:
    write_policy(tmp_path, id="lowercase_id")
    with pytest.raises(PolicyError):
        load_policy_set(tmp_path)


def test_empty_condition_group_is_rejected(tmp_path: Path) -> None:
    write_policy(tmp_path, when={"all": []})
    with pytest.raises(PolicyError):
        load_policy_set(tmp_path)
