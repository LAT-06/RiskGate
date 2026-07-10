from fastapi import FastAPI

app = FastAPI(
    title="Transaction Service", description="Transaction lifecycle and workflow orchestration"
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "transaction-service"}
