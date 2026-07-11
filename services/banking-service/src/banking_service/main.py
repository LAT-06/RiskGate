from fastapi import FastAPI

from banking_service.api import router

app = FastAPI(
    title="Banking Service", description="Customer profiles, beneficiaries, and device metadata"
)
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "banking-service"}
