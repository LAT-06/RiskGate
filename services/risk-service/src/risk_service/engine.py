"""Pure, deterministic evaluation of risk features against a policy set.

No I/O, no clock, no randomness: the same features and the same policy set
always produce the same decision. Malformed input raises EvaluationError —
callers must treat that as a failed evaluation and never fall back to ALLOW.
"""

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict

from risk_service.features import FEATURES, FeatureValue, value_matches_type
from risk_service.policy import Condition, Operator, Policy, PolicySet
from riskgate_contracts import RiskDecision

_MEMBERSHIP_OPERATORS = frozenset({Operator.IN, Operator.NOT_IN})

_SEVERITY: dict[RiskDecision, int] = {
    RiskDecision.ALLOW: 0,
    RiskDecision.CHALLENGE: 1,
    RiskDecision.HOLD: 2,
    RiskDecision.DENY: 3,
}


class EvaluationError(ValueError):
    """The feature mapping cannot be evaluated against the policy set."""


class MatchedPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    policy_id: str
    version: int
    decision: RiskDecision
    reason: str


class Evaluation(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision: RiskDecision
    matched: tuple[MatchedPolicy, ...]
    policy_set_fingerprint: str


def evaluate(features: Mapping[str, FeatureValue], policy_set: PolicySet) -> Evaluation:
    """Evaluate a full feature mapping; the most severe matched decision wins.

    Every feature must be registered and correctly typed, and every feature a
    policy references must be present — anything else is an EvaluationError.
    """
    for name, value in features.items():
        feature_type = FEATURES.get(name)
        if feature_type is None:
            raise EvaluationError(f"unknown feature in context: {name}")
        if not value_matches_type(value, feature_type):
            raise EvaluationError(
                f"feature {name} has invalid value {value!r} for type {feature_type}"
            )
    matched = tuple(
        MatchedPolicy(
            policy_id=policy.id,
            version=policy.version,
            decision=policy.decision,
            reason=policy.description,
        )
        for policy in policy_set.policies
        if _matches(policy, features)
    )
    decision = RiskDecision.ALLOW
    for match in matched:
        if _SEVERITY[match.decision] > _SEVERITY[decision]:
            decision = match.decision
    return Evaluation(
        decision=decision, matched=matched, policy_set_fingerprint=policy_set.fingerprint
    )


def _matches(policy: Policy, features: Mapping[str, FeatureValue]) -> bool:
    return all(_condition_holds(condition, features) for condition in policy.when.all)


def _condition_holds(condition: Condition, features: Mapping[str, FeatureValue]) -> bool:
    if condition.feature not in features:
        raise EvaluationError(f"missing feature: {condition.feature}")
    value = features[condition.feature]
    expected = condition.value
    operator = condition.operator
    if operator in _MEMBERSHIP_OPERATORS:
        if not isinstance(expected, list):  # unreachable: enforced at load time
            raise EvaluationError(f"operator {operator} requires a list value")
        return (value in expected) == (operator is Operator.IN)
    if isinstance(expected, list):  # unreachable: enforced at load time
        raise EvaluationError(f"operator {operator} does not accept a list value")
    match operator:
        case Operator.EQ:
            return value == expected
        case Operator.NE:
            return value != expected
        case Operator.GT:
            return value > expected
        case Operator.GTE:
            return value >= expected
        case Operator.LT:
            return value < expected
        case Operator.LTE:
            return value <= expected
        case _:  # unreachable: Operator is exhaustive above
            raise EvaluationError(f"unsupported operator: {operator}")
