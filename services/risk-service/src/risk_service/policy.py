"""Declarative YAML risk policies: schema, validation, and loading.

Policies are data, never code. Conditions reference registered features
through a fixed allowlist of operators; unknown fields, features, and
operators are rejected at load time, and no dynamic code is ever executed.
"""

import hashlib
import json
from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    ValidationError,
    model_validator,
)

from risk_service.features import FEATURES, FeatureType, value_matches_type
from riskgate_contracts import RiskDecision


class PolicyError(ValueError):
    """A policy file is missing, malformed, or fails schema validation."""


class Operator(StrEnum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"


_ORDERING_OPERATORS = frozenset({Operator.GT, Operator.GTE, Operator.LT, Operator.LTE})
_MEMBERSHIP_OPERATORS = frozenset({Operator.IN, Operator.NOT_IN})

Scalar = StrictBool | StrictInt | StrictFloat


class Condition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    feature: str
    operator: Operator
    value: Scalar | list[Scalar]

    @model_validator(mode="after")
    def _check_against_registry(self) -> "Condition":
        feature_type = FEATURES.get(self.feature)
        if feature_type is None:
            raise PolicyError(f"unknown feature: {self.feature}")
        if feature_type is FeatureType.BOOL and self.operator not in (Operator.EQ, Operator.NE):
            raise PolicyError(f"operator {self.operator} is not valid for boolean {self.feature}")
        if self.operator in _MEMBERSHIP_OPERATORS:
            if not isinstance(self.value, list):
                raise PolicyError(f"operator {self.operator} requires a list value")
            if not self.value:
                raise PolicyError(f"operator {self.operator} requires a non-empty list")
            items = self.value
        else:
            if isinstance(self.value, list):
                raise PolicyError(f"operator {self.operator} does not accept a list value")
            items = [self.value]
        for item in items:
            if not value_matches_type(item, feature_type):
                raise PolicyError(
                    f"value {item!r} is not a valid {feature_type} for feature {self.feature}"
                )
        return self


class ConditionGroup(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    all: list[Condition] = Field(min_length=1)


class Policy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$")
    version: StrictInt = Field(ge=1)
    description: str = Field(min_length=1)
    decision: RiskDecision
    when: ConditionGroup

    @model_validator(mode="after")
    def _forbid_allow(self) -> "Policy":
        # ALLOW is only ever the absence of matches — a policy that grants it
        # could mask escalation and would break "never default to ALLOW".
        if self.decision is RiskDecision.ALLOW:
            raise PolicyError("policies may only escalate; ALLOW is the no-match default")
        return self


class PolicySet(BaseModel):
    model_config = ConfigDict(frozen=True)

    policies: tuple[Policy, ...]
    fingerprint: str


def load_policy_set(directory: Path) -> PolicySet:
    """Load and validate every ``*.yaml`` policy in a directory.

    Fails closed: any unreadable, malformed, or duplicate policy aborts the
    whole load. The fingerprint is a sha256 over the canonical content of all
    policies, so any change to any policy changes the recorded version.
    """
    paths = sorted(directory.glob("*.yaml"))
    if not paths:
        raise PolicyError(f"no policy files found in {directory}")
    policies: dict[str, Policy] = {}
    for path in paths:
        try:
            raw = yaml.safe_load(path.read_text())
        except yaml.YAMLError as exc:
            raise PolicyError(f"{path.name}: invalid YAML: {exc}") from exc
        if not isinstance(raw, dict):
            raise PolicyError(f"{path.name}: policy must be a YAML mapping")
        try:
            policy = Policy.model_validate(raw)
        except ValidationError as exc:
            raise PolicyError(f"{path.name}: {exc}") from exc
        if policy.id in policies:
            raise PolicyError(f"{path.name}: duplicate policy id {policy.id}")
        policies[policy.id] = policy
    ordered = tuple(policies[policy_id] for policy_id in sorted(policies))
    canonical = json.dumps(
        [policy.model_dump(mode="json") for policy in ordered],
        sort_keys=True,
        separators=(",", ":"),
    )
    fingerprint = hashlib.sha256(canonical.encode()).hexdigest()
    return PolicySet(policies=ordered, fingerprint=fingerprint)
