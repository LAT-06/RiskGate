from sqlalchemy import BigInteger

from ledger_service.models import LEDGER_SCHEMA, Base

MONEY_COLUMNS = ("amount", "posted_balance", "reserved_amount", "available_balance")


def test_all_tables_live_in_the_ledger_schema() -> None:
    assert set(Base.metadata.tables) == {
        f"{LEDGER_SCHEMA}.accounts",
        f"{LEDGER_SCHEMA}.reservations",
        f"{LEDGER_SCHEMA}.transfers",
        f"{LEDGER_SCHEMA}.entries",
    }
    for table in Base.metadata.tables.values():
        assert table.schema == LEDGER_SCHEMA


def test_money_columns_are_bigint_minor_units() -> None:
    money_columns_found = 0
    for table in Base.metadata.tables.values():
        for name in MONEY_COLUMNS:
            if name in table.c:
                assert isinstance(table.c[name].type, BigInteger), f"{table.name}.{name}"
                money_columns_found += 1
    assert money_columns_found == 6


def test_available_balance_is_generated_not_writable() -> None:
    accounts = Base.metadata.tables[f"{LEDGER_SCHEMA}.accounts"]
    assert accounts.c.available_balance.computed is not None


def test_entries_have_no_updated_at_column() -> None:
    entries = Base.metadata.tables[f"{LEDGER_SCHEMA}.entries"]
    assert "updated_at" not in entries.c
