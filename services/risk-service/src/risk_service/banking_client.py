from typing import Any, Protocol
from uuid import UUID

import httpx

from risk_service.settings import load_settings
from riskgate_contracts.banking import BankingBeneficiary, BankingDevice


class BankingUnavailableError(Exception):
    pass


class BankingClient(Protocol):
    def list_devices(self, *, customer_id: UUID) -> list[BankingDevice]: ...

    def get_beneficiary(
        self, *, customer_id: UUID, beneficiary_id: UUID
    ) -> BankingBeneficiary | None: ...


class HttpBankingClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def _get(self, path: str) -> httpx.Response:
        try:
            response = httpx.get(f"{self._base_url}{path}", timeout=10.0)
        except httpx.HTTPError as exc:
            raise BankingUnavailableError(str(exc)) from exc
        return response

    def list_devices(self, *, customer_id: UUID) -> list[BankingDevice]:
        response = self._get(f"/internal/customers/{customer_id}/devices")
        body = self._json_or_unavailable(response)
        return [
            BankingDevice(
                id=item["id"],
                fingerprint=item["fingerprint"],
                first_seen=item["first_seen"],
                last_seen=item["last_seen"],
            )
            for item in body
        ]

    def get_beneficiary(
        self, *, customer_id: UUID, beneficiary_id: UUID
    ) -> BankingBeneficiary | None:
        response = self._get(f"/internal/customers/{customer_id}/beneficiaries/{beneficiary_id}")
        if response.status_code == 404:
            return None
        body = self._json_or_unavailable(response)
        return BankingBeneficiary(
            id=body["id"],
            account_number=body["account_number"],
            created_at=body["created_at"],
        )

    @staticmethod
    def _json_or_unavailable(response: httpx.Response) -> Any:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise BankingUnavailableError(str(exc)) from exc
        return response.json()


def get_banking_client() -> BankingClient:
    return HttpBankingClient(load_settings().banking_service_url)
