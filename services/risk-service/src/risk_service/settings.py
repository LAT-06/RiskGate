from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo-root .env is a local-development fallback only; real environment
# variables always take precedence, and the file does not exist in containers.
_REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_REPO_ROOT / ".env", extra="ignore")

    database_url: str
    banking_service_url: str = "http://localhost:8001"
    # The Docker image copies the whole repo, so the repo-root default holds
    # both locally and in containers.
    policies_dir: Path = _REPO_ROOT / "policies"

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
