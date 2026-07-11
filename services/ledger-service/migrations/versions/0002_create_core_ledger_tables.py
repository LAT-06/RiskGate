"""Create core ledger tables: accounts, reservations, transfers, entries.

Also drops the Milestone 0 smoke-test table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-11

"""

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | None = None
depends_on: str | None = None

SCHEMA = "ledger"


def upgrade() -> None:
    op.drop_table("migration_smoke_test", schema=SCHEMA)

    op.create_table(
        "accounts",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("customer_id", sa.Uuid, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("posted_balance", sa.BigInteger, nullable=False),
        sa.Column("reserved_amount", sa.BigInteger, nullable=False),
        sa.Column(
            "available_balance",
            sa.BigInteger,
            sa.Computed("posted_balance - reserved_amount", persisted=True),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("posted_balance >= 0", name="ck_accounts_posted_balance_non_negative"),
        sa.CheckConstraint("reserved_amount >= 0", name="ck_accounts_reserved_amount_non_negative"),
        sa.CheckConstraint(
            "reserved_amount <= posted_balance", name="ck_accounts_reserved_within_posted"
        ),
        schema=SCHEMA,
    )
    op.create_index("ix_ledger_accounts_customer_id", "accounts", ["customer_id"], schema=SCHEMA)

    op.create_table(
        "reservations",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("idempotency_key", sa.Text, nullable=False),
        sa.Column("account_id", sa.Uuid, sa.ForeignKey(f"{SCHEMA}.accounts.id"), nullable=False),
        sa.Column(
            "counterparty_account_id",
            sa.Uuid,
            sa.ForeignKey(f"{SCHEMA}.accounts.id"),
            nullable=False,
        ),
        sa.Column("amount", sa.BigInteger, nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_reservations_idempotency_key"),
        sa.CheckConstraint("amount > 0", name="ck_reservations_amount_positive"),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'CAPTURED', 'RELEASED', 'EXPIRED')",
            name="ck_reservations_status_valid",
        ),
        sa.CheckConstraint(
            "account_id <> counterparty_account_id", name="ck_reservations_distinct_accounts"
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_reservations_account_id_status",
        "reservations",
        ["account_id", "status"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_reservations_active_expires_at",
        "reservations",
        ["expires_at"],
        schema=SCHEMA,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    op.create_table(
        "transfers",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("idempotency_key", sa.Text, nullable=False),
        sa.Column(
            "from_account_id", sa.Uuid, sa.ForeignKey(f"{SCHEMA}.accounts.id"), nullable=False
        ),
        sa.Column("to_account_id", sa.Uuid, sa.ForeignKey(f"{SCHEMA}.accounts.id"), nullable=False),
        sa.Column("amount", sa.BigInteger, nullable=False),
        sa.Column(
            "reservation_id", sa.Uuid, sa.ForeignKey(f"{SCHEMA}.reservations.id"), nullable=True
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_transfers_idempotency_key"),
        sa.CheckConstraint("amount > 0", name="ck_transfers_amount_positive"),
        sa.CheckConstraint(
            "from_account_id <> to_account_id", name="ck_transfers_distinct_accounts"
        ),
        schema=SCHEMA,
    )

    op.create_table(
        "entries",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("account_id", sa.Uuid, sa.ForeignKey(f"{SCHEMA}.accounts.id"), nullable=False),
        sa.Column("transfer_id", sa.Uuid, sa.ForeignKey(f"{SCHEMA}.transfers.id"), nullable=True),
        sa.Column("direction", sa.String(6), nullable=False),
        sa.Column("amount", sa.BigInteger, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("amount > 0", name="ck_entries_amount_positive"),
        sa.CheckConstraint("direction IN ('DEBIT', 'CREDIT')", name="ck_entries_direction_valid"),
        schema=SCHEMA,
    )
    op.create_index("ix_ledger_entries_account_id", "entries", ["account_id"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_table("entries", schema=SCHEMA)
    op.drop_table("transfers", schema=SCHEMA)
    op.drop_table("reservations", schema=SCHEMA)
    op.drop_table("accounts", schema=SCHEMA)

    op.create_table(
        "migration_smoke_test",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("note", sa.Text, nullable=False),
        schema=SCHEMA,
    )
