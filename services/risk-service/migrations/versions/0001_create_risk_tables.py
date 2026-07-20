"""Create risk tables: assessments, policy_versions, authentication_events.

Revision ID: 0001
Revises:
Create Date: 2026-07-20

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None

SCHEMA = "risk"


def upgrade() -> None:
    op.create_table(
        "assessments",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("transaction_id", sa.Uuid, nullable=False),
        sa.Column("customer_id", sa.Uuid, nullable=False),
        sa.Column("beneficiary_id", sa.Uuid, nullable=False),
        sa.Column("amount_minor", sa.BigInteger, nullable=False),
        sa.Column("currency", sa.Text, nullable=False),
        sa.Column("ip_country", sa.String(2), nullable=False),
        sa.Column("device_fingerprint", sa.Text, nullable=False),
        sa.Column("features", JSONB, nullable=False),
        sa.Column("decision", sa.Text, nullable=False),
        sa.Column("matched", JSONB, nullable=False),
        sa.Column("policy_set_fingerprint", sa.Text, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_assessments_transaction_id", "assessments", ["transaction_id"], schema=SCHEMA
    )
    op.create_index(
        "ix_assessments_customer_created",
        "assessments",
        ["customer_id", "created_at"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_assessments_beneficiary_created",
        "assessments",
        ["beneficiary_id", "created_at"],
        schema=SCHEMA,
    )

    op.create_table(
        "policy_versions",
        sa.Column("fingerprint", sa.Text, primary_key=True),
        sa.Column("policies", JSONB, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        schema=SCHEMA,
    )

    op.create_table(
        "authentication_events",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("customer_id", sa.Uuid, nullable=False),
        sa.Column("outcome", sa.Text, nullable=False),
        sa.Column("ip_country", sa.String(2), nullable=True),
        sa.Column("device_fingerprint", sa.Text, nullable=True),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_authentication_events_customer_occurred",
        "authentication_events",
        ["customer_id", "occurred_at"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("authentication_events", schema=SCHEMA)
    op.drop_table("policy_versions", schema=SCHEMA)
    op.drop_table("assessments", schema=SCHEMA)
