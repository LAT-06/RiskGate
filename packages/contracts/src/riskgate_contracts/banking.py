"""Read models of the banking service internal HTTP API, shared by its consumers."""

from typing import TypedDict


class BankingDevice(TypedDict):
    id: str
    fingerprint: str
    first_seen: str
    last_seen: str


class BankingBeneficiary(TypedDict):
    id: str
    account_number: str
    created_at: str
