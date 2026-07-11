from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo-root .env is a local-development fallback only; real environment
# variables always take precedence, and the file does not exist in containers.
_REPO_ROOT_ENV_FILE = Path(__file__).resolve().parents[4] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_REPO_ROOT_ENV_FILE, extra="ignore")

    database_url: str
    ledger_service_url: str = "http://localhost:8003"
    # Fake initial balance for simulated accounts, in integer minor units.
    opening_balance: int = 100_000_000
    # Browser origins allowed to call this service (the customer web app).
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("database_url")
    @classmethod
    def _force_psycopg3_driver(cls, value: str) -> str:
        # Neon hands out plain postgresql:// URLs, which SQLAlchemy would route
        # to psycopg2; only psycopg (v3) is installed.
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value


def load_settings() -> Settings:
    # Fields are populated from the environment at runtime, which mypy cannot see.
    return Settings()  # type: ignore[call-arg]
