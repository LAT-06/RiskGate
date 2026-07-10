from fastapi import FastAPI

app = FastAPI(
    title="Ledger Service", description="Accounts, balances, reservations, and ledger entries"
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ledger-service"}
