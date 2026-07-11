"""Read models of the ledger service HTTP API, shared by its consumers."""

from typing import TypedDict


class LedgerAccount(TypedDict):
    id: str
    currency: str
    posted_balance: int
    reserved_amount: int
    available_balance: int


class LedgerEntry(TypedDict):
    id: str
    direction: str
    amount: int
    transfer_id: str | None
    created_at: str
