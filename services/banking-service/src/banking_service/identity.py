"""Local development identity, behind the interface Cognito will replace.

AGENTS.md requires identity from verified auth claims. There is no IdP in
local development, so the dev provider trusts an X-Customer-Id header ONLY as
a stand-in and still verifies the customer exists. The `get_current_customer`
dependency is the single seam where a Cognito JWT verifier plugs in at
Milestone 9 — no other code may read identity from the request.
"""

from typing import Annotated, Protocol
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from banking_service.db import get_session
from banking_service.models import Customer

DEV_IDENTITY_HEADER = "X-Customer-Id"


class IdentityProvider(Protocol):
    def authenticate(self, request: Request, session: Session) -> Customer | None: ...


class DevHeaderIdentityProvider:
    def authenticate(self, request: Request, session: Session) -> Customer | None:
        raw = request.headers.get(DEV_IDENTITY_HEADER)
        if raw is None:
            return None
        try:
            customer_id = UUID(raw)
        except ValueError:
            return None
        return session.get(Customer, customer_id)


_provider: IdentityProvider = DevHeaderIdentityProvider()


def get_current_customer(
    request: Request, session: Annotated[Session, Depends(get_session)]
) -> Customer:
    customer = _provider.authenticate(request, session)
    if customer is None:
        raise HTTPException(status_code=401, detail="authentication required")
    return customer


CurrentCustomer = Annotated[Customer, Depends(get_current_customer)]
