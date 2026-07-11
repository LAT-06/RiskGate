from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ledger_service import operations
from ledger_service.api import router

app = FastAPI(
    title="Ledger Service", description="Accounts, balances, reservations, and ledger entries"
)
app.include_router(router)

_NOT_FOUND_ERRORS = (operations.AccountNotFoundError, operations.ReservationNotFoundError)


@app.exception_handler(operations.LedgerError)
def ledger_error_handler(request: Request, exc: operations.LedgerError) -> JSONResponse:
    status_code = 404 if isinstance(exc, _NOT_FOUND_ERRORS) else 409
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ledger-service"}
