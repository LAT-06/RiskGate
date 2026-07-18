"""Registry of risk features that policies may reference.

Policies can only reference features declared here; the policy loader
rejects anything else. Feature values are computed server-side by the
risk context builder — never taken from client-supplied risk signals.
"""

import math
from enum import StrEnum

FeatureValue = bool | int | float


class FeatureType(StrEnum):
    BOOL = "bool"
    INT = "int"
    FLOAT = "float"


# Initial feature set from MVP.md §6. `replay_detected` backs the
# REPLAY_DETECTED policy: it is set when a request replays an already-used
# idempotency key, which only the caller orchestrating the transaction can see.
FEATURES: dict[str, FeatureType] = {
    "device_is_new": FeatureType.BOOL,
    "device_is_trusted": FeatureType.BOOL,
    "beneficiary_age_minutes": FeatureType.INT,
    "beneficiary_previous_transaction_count": FeatureType.INT,
    "amount_ratio_to_user_average": FeatureType.FLOAT,
    "transactions_last_10_minutes": FeatureType.INT,
    "total_amount_last_10_minutes": FeatureType.INT,
    "failed_logins_last_hour": FeatureType.INT,
    "country_changed": FeatureType.BOOL,
    "mfa_verified": FeatureType.BOOL,
    "replay_detected": FeatureType.BOOL,
}


def value_matches_type(value: object, feature_type: FeatureType) -> bool:
    """Whether a scalar is usable as a value of the given feature type.

    bool is checked before int because it is an int subclass; non-finite
    floats are rejected everywhere — they can silently disable a condition.
    """
    if isinstance(value, float) and not math.isfinite(value):
        return False
    if feature_type is FeatureType.BOOL:
        return isinstance(value, bool)
    if feature_type is FeatureType.INT:
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, int | float) and not isinstance(value, bool)
