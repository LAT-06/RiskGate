"""In-memory stand-in for the banking service HTTP client, for service tests."""

from uuid import UUID

from riskgate_contracts.banking import BankingBeneficiary, BankingDevice


class FakeBankingClient:
    def __init__(self) -> None:
        self.devices: dict[UUID, list[BankingDevice]] = {}
        self.beneficiaries: dict[tuple[UUID, UUID], BankingBeneficiary] = {}

    def list_devices(self, *, customer_id: UUID) -> list[BankingDevice]:
        return list(self.devices.get(customer_id, []))

    def get_beneficiary(
        self, *, customer_id: UUID, beneficiary_id: UUID
    ) -> BankingBeneficiary | None:
        return self.beneficiaries.get((customer_id, beneficiary_id))
