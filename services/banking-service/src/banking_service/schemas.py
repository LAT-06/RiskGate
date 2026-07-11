from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CustomerCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    email: str = Field(max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str
    account_number: str
    ledger_account_id: UUID | None
    created_at: datetime


class BeneficiaryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    account_number: str = Field(pattern=r"^\d{10}$")


class BeneficiaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    account_number: str
    created_at: datetime


class DeviceUpsert(BaseModel):
    fingerprint: str = Field(min_length=1, max_length=200)
    user_agent: str | None = Field(default=None, max_length=500)


class DeviceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    fingerprint: str
    user_agent: str | None
    first_seen: datetime
    last_seen: datetime
