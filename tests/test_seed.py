"""Seed integrity — runs with no network. Mirrors CLAUDE.md §3 data rules."""
import pathlib
import sqlite3

import pytest
DB = pathlib.Path(__file__).parent.parent / "db" / "pattaz.db"
@pytest.fixture(scope="module")
def con(): return sqlite3.connect(DB)
def test_tables_exist(con):
    names = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
    assert {"names","triggers","fundamentals","holdings","cells","policy","decisions","sessions"} <= names
def test_every_name_has_as_of(con):
    assert con.execute("select count(*) from names where as_of is null or as_of=''").fetchone()[0] == 0
def test_no_trigger_on_sold_or_banned(con):
    assert con.execute("select count(*) from triggers t join names n using(symbol) where n.status in ('SOLD','NEVER_ADD')").fetchone()[0] == 0
def test_active_triggers_have_a_basis(con):
    rows = con.execute("select symbol from triggers where active=1 and kind in ('BUY','NEXT_BUY','CRASH_SHELF') and basis_eps_date is null").fetchall()
    assert rows == [], f"active buy triggers without an EPS basis (E3): {rows}"
def test_lender_gate_policy_present(con):
    assert con.execute("select value from policy where key='lender_first_bite_gate'").fetchone()[0] == "JUSTIFIED_PB_ONLY"
def test_e6_conflicts_are_visible(con):
    assert con.execute("select count(*) from names where notes like '%E6 CONFLICT%'").fetchone()[0] >= 2
