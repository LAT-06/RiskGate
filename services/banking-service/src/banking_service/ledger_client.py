from typing import Any, Protocol
from uuid import UUID

import httpx

from banking_service.settings import load_settings
from riskgate_contracts.ledger import LedgerAccount, LedgerEntry


class LedgerUnavailableError(Exception):
    pass


class LedgerClient(Protocol):
    def create_account(self, *, customer_id: UUID, currency: str, opening_balance: int) -> UUID: ...

    def get_account(self, *, account_id: UUID) -> LedgerAccount: ...

    def list_entries(self, *, account_id: UUID) -> list[LedgerEntry]: ...


class HttpLedgerClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, json: dict[str, Any] | None = None) -> Any:
        try:
            response = httpx.request(method, f"{self._base_url}{path}", json=json, timeout=10.0)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LedgerUnavailableError(str(exc)) from exc
        return response.json()

    def create_account(self, *, customer_id: UUID, currency: str, opening_balance: int) -> UUID:
        body = self._request(
            "POST",
            "/accounts",
            json={
                "customer_id": str(customer_id),
                "currency": currency,
                "opening_balance": opening_balance,
            },
        )
        return UUID(body["id"])

    def get_account(self, *, account_id: UUID) -> LedgerAccount:
        body = self._request("GET", f"/accounts/{account_id}")
        return LedgerAccount(
            id=body["id"],
            currency=body["currency"],
            posted_balance=body["posted_balance"],
            reserved_amount=body["reserved_amount"],
            available_balance=body["available_balance"],
        )

    def list_entries(self, *, account_id: UUID) -> list[LedgerEntry]:
        body = self._request("GET", f"/accounts/{account_id}/entries")
        return [
            LedgerEntry(
                id=item["id"],
                direction=item["direction"],
                amount=item["amount"],
                transfer_id=item["transfer_id"],
                created_at=item["created_at"],
            )
            for item in body
        ]


def get_ledger_client() -> LedgerClient:
    return HttpLedgerClient(load_settings().ledger_service_url)
