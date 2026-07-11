from typing import Protocol
from uuid import UUID

import httpx

from banking_service.settings import load_settings


class LedgerUnavailableError(Exception):
    pass


class LedgerClient(Protocol):
    def create_account(self, *, customer_id: UUID, currency: str, opening_balance: int) -> UUID: ...


class HttpLedgerClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def create_account(self, *, customer_id: UUID, currency: str, opening_balance: int) -> UUID:
        try:
            response = httpx.post(
                f"{self._base_url}/accounts",
                json={
                    "customer_id": str(customer_id),
                    "currency": currency,
                    "opening_balance": opening_balance,
                },
                timeout=10.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LedgerUnavailableError(str(exc)) from exc
        return UUID(response.json()["id"])


def get_ledger_client() -> LedgerClient:
    return HttpLedgerClient(load_settings().ledger_service_url)
