from fastapi import FastAPI

from risk_service.api import router

app = FastAPI(
    title="Risk Service", description="Deterministic YAML policy evaluation and risk decisions"
)
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "risk-service"}
