from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from ledger_service.settings import load_settings

SERVICE_DIR = Path(__file__).resolve().parents[1]


def test_settings_reads_database_url_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:secret@localhost/riskgate")
    assert load_settings().database_url == "postgresql+psycopg://user:secret@localhost/riskgate"


def test_settings_normalizes_plain_postgresql_url_to_psycopg3(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:secret@localhost/riskgate")
    assert load_settings().database_url == "postgresql+psycopg://user:secret@localhost/riskgate"


def test_alembic_scripts_parse_with_single_head() -> None:
    config = Config(str(SERVICE_DIR / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_heads() == ["0002"]


def test_migrations_are_reversible() -> None:
    config = Config(str(SERVICE_DIR / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)
    for revision in scripts.walk_revisions():
        module = scripts.get_revision(revision.revision).module
        assert callable(module.upgrade)
        assert callable(module.downgrade)
