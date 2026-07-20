"""Pure computation of the feature registry from raw records.

All I/O (banking client calls, history queries) happens in the API layer;
this module only turns already-fetched records into the features the engine
evaluates, so it is unit-testable without a database or a banking service.
"""

from datetime import UTC, datetime, timedelta

from risk_service.features import FeatureValue
from risk_service.history import CustomerHistory
from riskgate_contracts.banking import BankingBeneficiary, BankingDevice

# A device counts as trusted once it has been registered this long. Stand-in
# for real trust accrual (e.g. marking a device trusted after a successful MFA
# on it), which needs banking-side state we don't have yet.
TRUSTED_DEVICE_MIN_AGE = timedelta(days=7)


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def build_features(
    *,
    amount_minor: int,
    ip_country: str,
    mfa_verified: bool,
    replay_detected: bool,
    device_fingerprint: str,
    devices: list[BankingDevice],
    beneficiary: BankingBeneficiary,
    history: CustomerHistory,
    now: datetime,
) -> dict[str, FeatureValue]:
    device = next((d for d in devices if d["fingerprint"] == device_fingerprint), None)
    device_is_trusted = (
        device is not None
        and now - _parse_timestamp(device["first_seen"]) >= TRUSTED_DEVICE_MIN_AGE
    )

    beneficiary_age = now - _parse_timestamp(beneficiary["created_at"])
    beneficiary_age_minutes = max(0, int(beneficiary_age.total_seconds() // 60))

    average = history.average_transaction_amount
    amount_ratio = 1.0 if average is None or average <= 0 else amount_minor / average

    return {
        "device_is_new": device is None,
        "device_is_trusted": device_is_trusted,
        "beneficiary_age_minutes": beneficiary_age_minutes,
        "beneficiary_previous_transaction_count": history.beneficiary_allowed_transaction_count,
        "amount_ratio_to_user_average": amount_ratio,
        # The transaction being assessed counts toward its own window.
        "transactions_last_10_minutes": history.prior_transactions_in_window + 1,
        "total_amount_last_10_minutes": history.prior_amount_in_window + amount_minor,
        "failed_logins_last_hour": history.failed_logins_last_hour,
        "country_changed": history.last_ip_country is not None
        and history.last_ip_country != ip_country,
        "mfa_verified": mfa_verified,
        "replay_detected": replay_detected,
    }
