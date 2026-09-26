"""tests/test_ranker_usecase.py — UC3 ranker on the recorded 25-Sep market, no network.

Runs on a scratch register with migration 014 applied (the shared register only gets
the policy row at integration). Proves: the variants are shown side by side, the best is
marked with a reason, ONE UC3_RANKER session is written, and nothing else changes.
"""
from __future__ import annotations

import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest

from tools.market_snapshot import MarketSnapshot, load_snapshot
from usecases import plate as plate_uc
from usecases.ranker import format_ranker, main, run_ranker

ROOT = Path(__file__).parent.parent
MARKET = ROOT / "tests" / "fixtures" / "market" / "market_2026-09-25.json"
MIGRATION = ROOT / "db" / "migrations" / "014_plate_ranker.sql"
D = Decimal


@pytest.fixture
def db(scratch_db: Path) -> Path:
    con = sqlite3.connect(scratch_db)
    con.executescript(MIGRATION.read_text())
    con.commit()
    con.close()
    return scratch_db


@pytest.fixture
def market() -> MarketSnapshot:
    return load_snapshot(MARKET)


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_a: object, **_k: object) -> None:
        raise AssertionError("network call in a replay test")
    for fn in ("fetch_prices_batch", "fetch_fundamentals_batch", "fetch_gsec_yield",
               "fetch_result_dates_batch"):
        monkeypatch.setattr(plate_uc, fn, boom)


def _sessions(db: Path) -> list[tuple[str, str]]:
    con = sqlite3.connect(db)
    rows = con.execute("SELECT run_id, usecase FROM sessions ORDER BY rowid").fetchall()
    con.close()
    return rows


def _state_without_sessions(db: Path) -> list[str]:
    con = sqlite3.connect(db)
    lines = [ln for ln in con.iterdump() if 'INTO "sessions"' not in ln]
    con.close()
    return lines


def test_best_is_marked_and_explained(db: Path, market: MarketSnapshot) -> None:
    r = run_ranker(db, D(7500), market=market, market_source="recording",
                   today=market.recorded_at)
    labels = [s.variant.label for s in r.ranking.ranked]
    assert labels[0] == "AS_ASKED@7500"
    assert set(labels) == {"AS_ASKED@7500", "BAND_LOW@5000", "BAND_HIGH@10000"}
    assert r.ranking.best is not None and r.ranking.discarded == ()
    low = next(s for s in r.ranking.ranked if s.variant.label == "BAND_LOW@5000")
    assert low.variant.result.plan_amount > D(5000)     # 1 each costs more → raised
    assert any("no_raise" in w for w in r.ranking.why)
    assert any("residual" in w for w in r.ranking.why)


def test_writes_one_uc3_session_and_changes_nothing_else(
        db: Path, market: MarketSnapshot) -> None:
    before_sessions = _sessions(db)
    before_state = _state_without_sessions(db)
    r = run_ranker(db, D(10000), market=market, market_source="recording",
                   today=market.recorded_at)
    after = _sessions(db)
    assert after[:len(before_sessions)] == before_sessions
    assert after[len(before_sessions):] == [(r.run_id, "UC3_RANKER")]
    assert _state_without_sessions(db) == before_state


def test_report_in_plain_words(db: Path, market: MarketSnapshot) -> None:
    r = run_ranker(db, D(7500), market=market, market_source="recording",
                   today=market.recorded_at, record_session=False)
    out = format_ranker(r)
    assert out.splitlines()[0].startswith("PLATE RANKER")
    assert "BEST:" in out and "as you asked" in out
    assert "SIDE BY SIDE" in out and "WHY IT WINS" in out
    for sym in ("INFY", "MUTHOOTFIN", "SBIN"):
        assert sym in out
    assert "Nothing was placed or changed" in out


def test_default_amount_is_the_band_top(db: Path, market: MarketSnapshot) -> None:
    r = run_ranker(db, None, market=market, market_source="recording",
                   today=market.recorded_at, record_session=False)
    assert r.asked == D(10000)


def test_missing_policy_row_fails_closed(scratch_db: Path, market: MarketSnapshot) -> None:
    with pytest.raises(ValueError, match="migration 014"):
        run_ranker(scratch_db, D(7500), market=market, market_source="recording",
                   today=market.recorded_at, record_session=False)
    assert not [u for _, u in _sessions(scratch_db) if u == "UC3_RANKER"]


def test_cli_replays_the_recording(db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["--db", str(db), "--amount", "7500", "--market", str(MARKET),
                 "--no-session"])
    assert code == 0
    out = capsys.readouterr().out
    assert "market 2026-09-25" in out and "BEST:" in out
    assert not [u for _, u in _sessions(db) if u == "UC3_RANKER"]
