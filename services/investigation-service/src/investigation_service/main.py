from fastapi import FastAPI

app = FastAPI(
    title="Investigation Service",
    description="Investigation cases, analyst decisions, agent and RAG",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "investigation-service"}
