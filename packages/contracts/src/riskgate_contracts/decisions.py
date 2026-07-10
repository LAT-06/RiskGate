from enum import StrEnum


class RiskDecision(StrEnum):
    ALLOW = "ALLOW"
    CHALLENGE = "CHALLENGE"
    HOLD = "HOLD"
    DENY = "DENY"
