"""Migration smoke test.

Throwaway table proving the Alembic setup works end to end against Neon.
The first real ledger migration (Milestone 2) should drop this table.

Revision ID: 0001
Revises:
Create Date: 2026-07-11

"""

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "migration_smoke_test",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("note", sa.Text, nullable=False),
        schema="ledger",
    )


def downgrade() -> None:
    op.drop_table("migration_smoke_test", schema="ledger")
