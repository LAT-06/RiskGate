"""In-memory stand-in for the ledger service HTTP client, for service tests."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from riskgate_contracts.ledger import LedgerAccount, LedgerEntry


class FakeLedgerClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.accounts: dict[UUID, LedgerAccount] = {}

    def create_account(self, *, customer_id: UUID, currency: str, opening_balance: int) -> UUID:
        self.calls.append(
            {
                "customer_id": customer_id,
                "currency": currency,
                "opening_balance": opening_balance,
            }
        )
        account_id = uuid4()
        self.accounts[account_id] = LedgerAccount(
            id=str(account_id),
            currency=currency,
            posted_balance=opening_balance,
            reserved_amount=0,
            available_balance=opening_balance,
        )
        return account_id

    def get_account(self, *, account_id: UUID) -> LedgerAccount:
        return self.accounts[account_id]

    def list_entries(self, *, account_id: UUID) -> list[LedgerEntry]:
        account = self.accounts[account_id]
        if account["posted_balance"] == 0:
            return []
        return [
            LedgerEntry(
                id=str(uuid4()),
                direction="CREDIT",
                amount=account["posted_balance"],
                transfer_id=None,
                created_at=datetime.now(UTC).isoformat(),
            )
        ]
