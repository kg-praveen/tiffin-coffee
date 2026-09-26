"""tests/test_ranker_usecase.py — UC3 ranker on the recorded 25-Sep market, no network.

Runs on a scratch register with migration 014 applied (the shared register only gets
the policy row at integration). Proves: the variants are shown side by side, the best is
marked with a reason, ONE UC3_RANKER session is written, and nothing else changes.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from tools.market_snapshot import MarketSnapshot, load_snapshot
from usecases import plate as plate_uc
from usecases import ranker as ranker_uc
from usecases.ranker import format_ranker, main, run_ranker, shown_drops

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
    assert "BEST (provisional ranking):" in out and "as you asked" in out
    assert "SIDE BY SIDE" in out and "WHY IT WINS" in out
    for sym in ("INFY", "MUTHOOTFIN", "SBIN"):
        assert sym in out
    assert "Nothing was placed or changed" in out


def test_default_amount_is_the_band_top(db: Path, market: MarketSnapshot) -> None:
    r = run_ranker(db, None, market=market, market_source="recording",
                   today=market.recorded_at, record_session=False)
    assert r.asked == D(10000)


def _session_row(db: Path, run_id: str) -> tuple[dict, dict, list]:
    con = sqlite3.connect(db)
    row = con.execute("SELECT inputs_json, outputs_json, drops_json FROM sessions "
                      "WHERE run_id = ?", (run_id,)).fetchone()
    con.close()
    return json.loads(row[0]), json.loads(row[1]), json.loads(row[2])


def test_missing_policy_row_is_no_action_with_a_session(
        scratch_db: Path, market: MarketSnapshot) -> None:
    """CLAUDE.md §3 / E9: a failed run prints NO ACTION — <reason> and still writes
    a UC3_RANKER session with verdict NO_ACTION."""
    r = run_ranker(scratch_db, D(7500), market=market, market_source="recording",
                   today=market.recorded_at)
    assert r.best is None and r.no_action_reason is not None
    assert "migration 014" in r.no_action_reason
    out = format_ranker(r)
    assert "NO ACTION — ranker policy unusable" in out
    assert "OPEN QUESTION for Praveen" in out
    assert [u for rid, u in _sessions(scratch_db) if rid == r.run_id] == ["UC3_RANKER"]
    _, outputs, _ = _session_row(scratch_db, r.run_id)
    assert outputs["verdict"] == "NO_ACTION"
    assert "migration 014" in outputs["no_action_reason"]


def test_no_config_is_no_action_with_a_session(
        db: Path, market: MarketSnapshot, monkeypatch: pytest.MonkeyPatch) -> None:
    real = ranker_uc.run_plate

    def no_config(*a: object, **k: object) -> plate_uc.PlateRunResult:
        return replace(real(*a, **k), config=None)  # type: ignore[arg-type]
    monkeypatch.setattr(ranker_uc, "run_plate", no_config)
    r = run_ranker(db, D(7500), market=market, market_source="recording",
                   today=market.recorded_at)
    assert r.best is None
    assert "NO ACTION — the plate run returned no config" in format_ranker(r)
    _, outputs, _ = _session_row(db, r.run_id)
    assert outputs["verdict"] == "NO_ACTION"


def test_cli_without_a_recording_is_no_action(
        db: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["--db", str(db), "--market", str(tmp_path / "missing.json")])
    assert code == 1
    assert "NO ACTION — no market data" in capsys.readouterr().out
    assert [u for _, u in _sessions(db)][-1] == "UC3_RANKER"


def test_output_lists_every_drop_and_the_inputs(db: Path, market: MarketSnapshot) -> None:
    """E8: inputs with as-of stamps and GoI yield; every dropped name (best variant +
    unpriced) with its reason and what would change."""
    r = run_ranker(db, D(7500), market=market, market_source="recording X",
                   today=market.recorded_at)
    out = format_ranker(r)
    inputs = next(ln for ln in out.splitlines() if ln.startswith("INPUTS:"))
    assert "market as of 2026-09-25 (recording X)" in inputs
    assert f"GoI 10y {r.plate_run.gsec_yield_pct}%" in inputs  # type: ignore[union-attr]
    drops = shown_drops(r)
    assert r.best is not None and len(drops) >= len(r.best.variant.result.drops)
    assert all(d in drops for d in r.plate_run.unpriced)  # type: ignore[union-attr]
    assert "DROPPED" in out
    for d in drops:
        assert f"  - {d.symbol}: {d.reason.name}" in out
    assert out.count("what would change:") == len(drops)
    _, _, sess_drops = _session_row(db, r.run_id)
    assert {x["symbol"] for x in sess_drops} >= {d.symbol for d in drops}


def test_ranking_is_marked_provisional(db: Path, market: MarketSnapshot) -> None:
    r = run_ranker(db, D(7500), market=market, market_source="recording",
                   today=market.recorded_at)
    out = format_ranker(r)
    assert ("OPEN QUESTION for Praveen: confirm ranking order "
            "ticket_band > no_raise > breadth > residual") in out
    assert "BEST (provisional ranking):" in out and "PROVISIONAL" in out
    _, outputs, _ = _session_row(db, r.run_id)
    assert outputs["ranking_status"] == "PROVISIONAL"
    assert outputs["open_questions"][0].startswith("OPEN QUESTION for Praveen")


def test_asked_outside_band_says_so_and_shows_the_asked_plate(
        db: Path, market: MarketSnapshot) -> None:
    r = run_ranker(db, D(25000), market=market, market_source="recording",
                   today=market.recorded_at, record_session=False)
    out = format_ranker(r)
    assert ("VERDICT: your Rs 25,000 is outside your Rs 5,000-Rs 10,000 ticket band; "
            "within the band the best is") in out
    assert "AS ASKED (Rs 25,000, outside the band):" in out
    assert "Rs 25,000 as you asked" in out


def test_inside_band_has_no_outside_band_verdict(db: Path, market: MarketSnapshot) -> None:
    r = run_ranker(db, D(7500), market=market, market_source="recording",
                   today=market.recorded_at, record_session=False)
    assert "outside your" not in format_ranker(r)


def test_closing_line_names_invariants_and_points_at_advisory(
        db: Path, market: MarketSnapshot) -> None:
    r = run_ranker(db, D(7500), market=market, market_source="recording",
                   today=market.recorded_at, record_session=False)
    plain = replace(r, plate_run=replace(r.plate_run, advisory_flags=[]))  # type: ignore[type-var]
    out = format_ranker(plain)
    assert "passed every invariant check (engine/invariants)" in out
    assert "see ADVISORY" not in out
    held = replace(r, plate_run=replace(  # type: ignore[type-var]
        r.plate_run, advisory_flags=["BLOCK: holdings", "WARN: E6 caps-off conflict — X"]))
    out = format_ranker(held)
    assert "2 ADVISORY flag(s) (BLOCK/E6) hold it — see ADVISORY above" in out
    assert "DO NOT EXECUTE" in out


def test_cli_replays_the_recording(db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["--db", str(db), "--amount", "7500", "--market", str(MARKET),
                 "--no-session"])
    assert code == 0
    out = capsys.readouterr().out
    assert "market 2026-09-25" in out and "BEST (provisional ranking):" in out
    assert not [u for _, u in _sessions(db) if u == "UC3_RANKER"]
