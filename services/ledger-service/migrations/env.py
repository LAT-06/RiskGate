from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, text

from ledger_service.models import LEDGER_SCHEMA, Base
from ledger_service.settings import load_settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=load_settings().database_url,
        literal_binds=True,
        version_table_schema=LEDGER_SCHEMA,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(load_settings().database_url)
    with engine.connect() as connection:
        # The schema must exist before Alembic can create its version table in it.
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {LEDGER_SCHEMA}"))
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=LEDGER_SCHEMA,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
