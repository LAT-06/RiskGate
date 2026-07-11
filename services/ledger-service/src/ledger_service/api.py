from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ledger_service import operations
from ledger_service.db import get_session
from ledger_service.models import Account, Entry, Transfer
from ledger_service.schemas import (
    AccountCreate,
    AccountRead,
    EntryRead,
    ExpireDueResult,
    ReservationCreate,
    ReservationRead,
    TransferCreate,
    TransferRead,
)

router = APIRouter()

SessionDep = Annotated[Session, Depends(get_session)]


@router.post("/accounts", status_code=201)
def create_account(body: AccountCreate, session: SessionDep) -> AccountRead:
    account = operations.create_account(
        session,
        customer_id=body.customer_id,
        currency=body.currency,
        opening_balance=body.opening_balance,
    )
    session.commit()
    return AccountRead.model_validate(account)


@router.get("/accounts/{account_id}")
def get_account(account_id: UUID, session: SessionDep) -> AccountRead:
    account = session.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail=f"account {account_id} not found")
    return AccountRead.model_validate(account)


@router.get("/accounts/{account_id}/entries")
def list_entries(account_id: UUID, session: SessionDep) -> list[EntryRead]:
    if session.get(Account, account_id) is None:
        raise HTTPException(status_code=404, detail=f"account {account_id} not found")
    entries = session.scalars(
        select(Entry).where(Entry.account_id == account_id).order_by(Entry.created_at, Entry.id)
    ).all()
    return [EntryRead.model_validate(entry) for entry in entries]


@router.post("/transfers", status_code=201)
def create_transfer(body: TransferCreate, session: SessionDep) -> TransferRead:
    def run() -> Transfer:
        return operations.execute_transfer(
            session,
            idempotency_key=body.idempotency_key,
            from_account_id=body.from_account_id,
            to_account_id=body.to_account_id,
            amount=body.amount,
        )

    try:
        transfer = run()
        session.commit()
    except IntegrityError:
        # Lost a race on the idempotency key; re-run to return the winner's row.
        session.rollback()
        transfer = run()
        session.commit()
    return TransferRead.model_validate(transfer)


@router.post("/reservations", status_code=201)
def create_reservation(body: ReservationCreate, session: SessionDep) -> ReservationRead:
    def run() -> ReservationRead:
        reservation = operations.create_reservation(
            session,
            idempotency_key=body.idempotency_key,
            account_id=body.account_id,
            counterparty_account_id=body.counterparty_account_id,
            amount=body.amount,
            expires_at=body.expires_at,
        )
        return ReservationRead.model_validate(reservation)

    try:
        result = run()
        session.commit()
    except IntegrityError:
        session.rollback()
        result = run()
        session.commit()
    return result


@router.post("/reservations/{reservation_id}/capture")
def capture_reservation(reservation_id: UUID, session: SessionDep) -> TransferRead:
    try:
        transfer = operations.capture_reservation(session, reservation_id=reservation_id)
    except operations.ReservationExpiredError as exc:
        # Persist the ACTIVE -> EXPIRED transition (funds already freed in-session).
        session.commit()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    session.commit()
    return TransferRead.model_validate(transfer)


@router.post("/reservations/{reservation_id}/release")
def release_reservation(reservation_id: UUID, session: SessionDep) -> ReservationRead:
    reservation = operations.release_reservation(session, reservation_id=reservation_id)
    session.commit()
    return ReservationRead.model_validate(reservation)


@router.post("/reservations/expire-due")
def expire_due_reservations(session: SessionDep) -> ExpireDueResult:
    count = operations.expire_due_reservations(session)
    session.commit()
    return ExpireDueResult(expired_count=count)
