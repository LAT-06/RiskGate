from fastapi import FastAPI

app = FastAPI(
    title="Banking Service", description="Customer profiles, beneficiaries, and device metadata"
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "banking-service"}
