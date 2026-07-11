from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from banking_service.api import router
from banking_service.settings import load_settings

app = FastAPI(
    title="Banking Service", description="Customer profiles, beneficiaries, and device metadata"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=load_settings().cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "banking-service"}
