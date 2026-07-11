"""In-memory stand-in for the ledger service HTTP client, for service tests."""

from uuid import UUID, uuid4


class FakeLedgerClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create_account(self, *, customer_id: UUID, currency: str, opening_balance: int) -> UUID:
        self.calls.append(
            {
                "customer_id": customer_id,
                "currency": currency,
                "opening_balance": opening_balance,
            }
        )
        return uuid4()
