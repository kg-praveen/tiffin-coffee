"""tests/test_sync_holdings.py — UC2.1 CSV path on a scratch copy of the seed DB.

No network: fetch_prices=False, so every line is unpriced and equity is 0 — the
test checks the import, zeroing, session write and the report shape.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from store.repo import PattazRepo
from usecases.sync_holdings import format_sync, run_sync_holdings_csv

FIXTURES = Path(__file__).parent / "fixtures"
SEED_DB = Path(__file__).parent.parent / "db" / "pattaz.db"


@pytest.fixture
def db(tmp_path: Path) -> Path:
    dst = tmp_path / "pattaz.db"
    shutil.copy(SEED_DB, dst)
    return dst


class TestSyncHoldingsCsv:
    def test_import_writes_newest_rows_and_zeroes_absent(self, db: Path) -> None:
        r = run_sync_holdings_csv(db, FIXTURES / "household_equity_05sep2026.csv",
                                  fetch_prices=False)
        # the fixture is dated 05-Sep: OLDER than the seeded 21-Sep snapshot, so it
        # must not become the newest row for anything it names
        assert r.rows_written > 0
        repo = PattazRepo(db)
        try:
            hdfc = {h.account: h.qty for h in repo.get_holdings_for("HDFCBANK")}
            assert hdfc["ZERODHA_P"] == 126
            assert any(h.as_of == "2026-09-05" for h in repo.load_holdings_history())
        finally:
            repo.close()

    def test_newer_snapshot_supersedes_and_records_exits(self, db: Path, tmp_path: Path) -> None:
        f = tmp_path / "household_equity_30sep2026.csv"
        f.write_text(
            "Stock,LTP,Total Qty,Kite-P Qty,Int-P Qty,Int-V Qty,Total Value,Overlap,Accounts\n"
            "INFY,1000,9,9,0,0,9000.00,No,K\n"
        )
        r = run_sync_holdings_csv(db, f, fetch_prices=False)
        assert r.as_of == "2026-09-30"
        assert r.exits_recorded > 0
        repo = PattazRepo(db)
        try:
            newest = {(h.account, h.symbol): h.qty for h in repo.load_holdings()}
            assert newest[("ZERODHA_P", "INFY")] == 9
            assert newest[("ZERODHA_P", "HDFCBANK")] == 0      # recorded exit
            assert newest[("INTEGRATED_V", "INFY")] == 0
            assert repo.held_pairs() == {("ZERODHA_P", "INFY")}
        finally:
            repo.close()

    def test_session_written(self, db: Path) -> None:
        r = run_sync_holdings_csv(db, FIXTURES / "household_equity_05sep2026.csv",
                                  fetch_prices=False)
        repo = PattazRepo(db)
        try:
            row = repo._con.execute(
                "SELECT usecase FROM sessions WHERE run_id = ?", (r.run_id,)
            ).fetchone()
            assert row is not None and row["usecase"] == "UC2_1_SYNC_HOLDINGS"
        finally:
            repo.close()

    def test_format_lists_unpriced_and_no_prices_means_no_breaches(self, db: Path) -> None:
        r = run_sync_holdings_csv(db, FIXTURES / "household_equity_05sep2026.csv",
                                  fetch_prices=False)
        text = format_sync(r)
        assert "HOUSEHOLD HOLDINGS — snapshot 2026-09-05" in text
        assert "UNPRICED" in text
        assert r.cap_breaches == []
        assert any(ln.symbol == "AGARIND" and not ln.in_register for ln in r.lines)
