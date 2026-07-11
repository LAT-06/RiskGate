from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from ledger_service.models import EntryDirection, ReservationStatus


class AccountCreate(BaseModel):
    customer_id: UUID
    currency: str = Field(pattern="^[A-Z]{3}$")
    opening_balance: int = Field(default=0, ge=0)


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    currency: str
    posted_balance: int
    reserved_amount: int
    available_balance: int


class TransferCreate(BaseModel):
    idempotency_key: str = Field(min_length=1, max_length=200)
    from_account_id: UUID
    to_account_id: UUID
    amount: int = Field(gt=0)

    @model_validator(mode="after")
    def _distinct_accounts(self) -> Self:
        if self.from_account_id == self.to_account_id:
            raise ValueError("from_account_id and to_account_id must differ")
        return self


class TransferRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    from_account_id: UUID
    to_account_id: UUID
    amount: int
    reservation_id: UUID | None
    created_at: datetime


class ReservationCreate(BaseModel):
    idempotency_key: str = Field(min_length=1, max_length=200)
    account_id: UUID
    counterparty_account_id: UUID
    amount: int = Field(gt=0)
    expires_at: AwareDatetime

    @model_validator(mode="after")
    def _distinct_accounts(self) -> Self:
        if self.account_id == self.counterparty_account_id:
            raise ValueError("account_id and counterparty_account_id must differ")
        return self


class ReservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    counterparty_account_id: UUID
    amount: int
    status: ReservationStatus
    expires_at: datetime
    created_at: datetime


class EntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    transfer_id: UUID | None
    direction: EntryDirection
    amount: int
    created_at: datetime


class ExpireDueResult(BaseModel):
    expired_count: int
