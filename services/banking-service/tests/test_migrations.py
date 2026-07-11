from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from banking_service.models import BANKING_SCHEMA, Base

SERVICE_DIR = Path(__file__).resolve().parents[1]


def test_alembic_scripts_parse_with_single_head() -> None:
    config = Config(str(SERVICE_DIR / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_heads() == ["0001"]


def test_all_tables_live_in_the_banking_schema() -> None:
    assert set(Base.metadata.tables) == {
        f"{BANKING_SCHEMA}.customers",
        f"{BANKING_SCHEMA}.beneficiaries",
        f"{BANKING_SCHEMA}.devices",
    }
    for table in Base.metadata.tables.values():
        assert table.schema == BANKING_SCHEMA
