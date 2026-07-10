from fastapi import FastAPI

app = FastAPI(
    title="Risk Service", description="Deterministic YAML policy evaluation and risk decisions"
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "risk-service"}
