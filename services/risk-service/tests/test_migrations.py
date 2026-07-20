from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from risk_service.models import RISK_SCHEMA, Base

SERVICE_DIR = Path(__file__).resolve().parents[1]


def test_alembic_scripts_parse_with_single_head() -> None:
    config = Config(str(SERVICE_DIR / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_heads() == ["0001"]


def test_all_tables_live_in_the_risk_schema() -> None:
    assert set(Base.metadata.tables) == {
        f"{RISK_SCHEMA}.assessments",
        f"{RISK_SCHEMA}.policy_versions",
        f"{RISK_SCHEMA}.authentication_events",
    }
    for table in Base.metadata.tables.values():
        assert table.schema == RISK_SCHEMA
