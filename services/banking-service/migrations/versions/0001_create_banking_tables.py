"""Create banking tables: customers, beneficiaries, devices.

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

SCHEMA = "banking"


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("full_name", sa.Text, nullable=False),
        sa.Column("email", sa.Text, nullable=False),
        sa.Column("account_number", sa.String(10), nullable=False),
        sa.Column("ledger_account_id", sa.Uuid, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("email", name="uq_customers_email"),
        sa.UniqueConstraint("account_number", name="uq_customers_account_number"),
        schema=SCHEMA,
    )

    op.create_table(
        "beneficiaries",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("customer_id", sa.Uuid, sa.ForeignKey(f"{SCHEMA}.customers.id"), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("account_number", sa.String(10), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "customer_id", "account_number", name="uq_beneficiaries_customer_account"
        ),
        schema=SCHEMA,
    )

    op.create_table(
        "devices",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("customer_id", sa.Uuid, sa.ForeignKey(f"{SCHEMA}.customers.id"), nullable=False),
        sa.Column("fingerprint", sa.Text, nullable=False),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column(
            "first_seen", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "last_seen", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("customer_id", "fingerprint", name="uq_devices_customer_fingerprint"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("devices", schema=SCHEMA)
    op.drop_table("beneficiaries", schema=SCHEMA)
    op.drop_table("customers", schema=SCHEMA)
