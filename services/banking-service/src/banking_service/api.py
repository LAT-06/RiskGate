from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from banking_service.db import get_session
from banking_service.identity import CurrentCustomer
from banking_service.ledger_client import LedgerClient, LedgerUnavailableError, get_ledger_client
from banking_service.models import Beneficiary, Customer, Device
from banking_service.schemas import (
    AccountEntry,
    AccountSummary,
    BeneficiaryCreate,
    BeneficiaryRead,
    CustomerCreate,
    CustomerRead,
    DeviceRead,
    DeviceUpsert,
)
from banking_service.settings import load_settings

router = APIRouter()

SessionDep = Annotated[Session, Depends(get_session)]
LedgerDep = Annotated[LedgerClient, Depends(get_ledger_client)]

CURRENCY = "VND"


def _allocate_account_number(session: Session) -> str:
    for _ in range(5):
        candidate = f"{uuid4().int % 10**10:010d}"
        taken = session.scalar(select(Customer.id).where(Customer.account_number == candidate))
        if taken is None:
            return candidate
    raise RuntimeError("could not allocate a unique account number")


@router.post("/customers", status_code=201)
def register_customer(body: CustomerCreate, session: SessionDep, ledger: LedgerDep) -> CustomerRead:
    duplicate = session.scalar(select(Customer.id).where(Customer.email == body.email))
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="email already registered")

    customer = Customer(
        full_name=body.full_name,
        email=body.email,
        account_number=_allocate_account_number(session),
    )
    session.add(customer)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="email already registered") from exc

    try:
        customer.ledger_account_id = ledger.create_account(
            customer_id=customer.id,
            currency=CURRENCY,
            opening_balance=load_settings().opening_balance,
        )
    except LedgerUnavailableError as exc:
        session.rollback()
        raise HTTPException(status_code=502, detail="ledger service unavailable") from exc
    session.commit()
    return CustomerRead.model_validate(customer)


@router.get("/customers/me")
def get_profile(current: CurrentCustomer) -> CustomerRead:
    return CustomerRead.model_validate(current)


@router.get("/customers/me/account")
def get_account_summary(current: CurrentCustomer, ledger: LedgerDep) -> AccountSummary:
    if current.ledger_account_id is None:
        raise HTTPException(status_code=502, detail="account not provisioned")
    try:
        account = ledger.get_account(account_id=current.ledger_account_id)
    except LedgerUnavailableError as exc:
        raise HTTPException(status_code=502, detail="ledger service unavailable") from exc
    return AccountSummary(
        account_number=current.account_number,
        currency=account["currency"],
        posted_balance=account["posted_balance"],
        reserved_amount=account["reserved_amount"],
        available_balance=account["available_balance"],
    )


@router.get("/customers/me/entries")
def list_account_entries(current: CurrentCustomer, ledger: LedgerDep) -> list[AccountEntry]:
    if current.ledger_account_id is None:
        raise HTTPException(status_code=502, detail="account not provisioned")
    try:
        entries = ledger.list_entries(account_id=current.ledger_account_id)
    except LedgerUnavailableError as exc:
        raise HTTPException(status_code=502, detail="ledger service unavailable") from exc
    return [AccountEntry.model_validate(entry) for entry in entries]


@router.post("/customers/me/beneficiaries", status_code=201)
def create_beneficiary(
    body: BeneficiaryCreate, current: CurrentCustomer, session: SessionDep
) -> BeneficiaryRead:
    existing = session.scalar(
        select(Beneficiary).where(
            Beneficiary.customer_id == current.id,
            Beneficiary.account_number == body.account_number,
        )
    )
    if existing is not None:
        return BeneficiaryRead.model_validate(existing)

    target = session.scalar(
        select(Customer.id).where(Customer.account_number == body.account_number)
    )
    if target is None:
        raise HTTPException(status_code=404, detail="account number not found")
    if target == current.id:
        raise HTTPException(status_code=409, detail="cannot add your own account")

    beneficiary = Beneficiary(
        customer_id=current.id, name=body.name, account_number=body.account_number
    )
    session.add(beneficiary)
    session.commit()
    return BeneficiaryRead.model_validate(beneficiary)


@router.get("/customers/me/beneficiaries")
def list_beneficiaries(current: CurrentCustomer, session: SessionDep) -> list[BeneficiaryRead]:
    beneficiaries = session.scalars(
        select(Beneficiary)
        .where(Beneficiary.customer_id == current.id)
        .order_by(Beneficiary.created_at, Beneficiary.id)
    ).all()
    return [BeneficiaryRead.model_validate(b) for b in beneficiaries]


@router.post("/customers/me/devices")
def upsert_device(body: DeviceUpsert, current: CurrentCustomer, session: SessionDep) -> DeviceRead:
    device = session.scalar(
        select(Device).where(
            Device.customer_id == current.id, Device.fingerprint == body.fingerprint
        )
    )
    if device is None:
        device = Device(
            customer_id=current.id, fingerprint=body.fingerprint, user_agent=body.user_agent
        )
        session.add(device)
    else:
        device.last_seen = func.now()
        if body.user_agent is not None:
            device.user_agent = body.user_agent
    session.commit()
    return DeviceRead.model_validate(device)


@router.get("/customers/me/devices")
def list_devices(current: CurrentCustomer, session: SessionDep) -> list[DeviceRead]:
    devices = session.scalars(
        select(Device)
        .where(Device.customer_id == current.id)
        .order_by(Device.first_seen, Device.id)
    ).all()
    return [DeviceRead.model_validate(d) for d in devices]
