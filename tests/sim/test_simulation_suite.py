"""tests/sim/test_simulation_suite.py — UC5 in CI: every scenario, every law, no network.

Replays the committed market recording through the real UC1 board and UC2 plate
(scratch copy of the register) under every catalog scenario at three session sizes.
Any VIOLATION fails the build; FINDINGS are reported, never failed (spec-legal).
"""
from __future__ import annotations

import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest

from store.repo import PattazRepo
from tools.market_snapshot import MarketSnapshot, load_snapshot, newest_snapshot
from usecases.scenarios import Scenario, build_catalog
from usecases.simulate import (
    MARKET_DIR,
    SimulationResult,
    format_simulation,
    load_context,
    main,
    run_simulation,
)

SEED_DB = Path(__file__).parent.parent.parent / "db" / "pattaz.db"
MIGRATION_012 = SEED_DB.parent / "migrations" / "012_plate_extras.sql"
AMOUNTS = (Decimal(5000), Decimal(10000), Decimal(40000))
CATALOG: list[Scenario] = build_catalog(load_context(SEED_DB))


@pytest.fixture(scope="module")
def market() -> MarketSnapshot:
    path = newest_snapshot(MARKET_DIR)
    assert path is not None
    return load_snapshot(path)


@pytest.fixture(scope="module")
def suite(market: MarketSnapshot, tmp_path_factory: pytest.TempPathFactory) -> SimulationResult:
    db = tmp_path_factory.mktemp("sim") / "pattaz.db"
    db.write_bytes(SEED_DB.read_bytes())
    _apply_012(db)
    return run_simulation(db, market, CATALOG, AMOUNTS, record_session=False)


def _apply_012(db: Path) -> None:
    """HOCKEY thresholds (migration 012) until the lead folds them into the register."""
    con = sqlite3.connect(db)
    try:
        have = con.execute("SELECT count(*) FROM policy WHERE key="
                           "'hockey_nifty_week_fall_pct'").fetchone()[0]
        if not have:
            con.executescript(MIGRATION_012.read_text())
    finally:
        con.close()


def _outcomes(r: SimulationResult, name: str) -> list:  # type: ignore[type-arg]
    return [o for o in r.outcomes if o.scenario == name]


@pytest.mark.parametrize("scenario", [s.name for s in CATALOG])
def test_scenario_obeys_every_law(suite: SimulationResult, scenario: str) -> None:
    for o in _outcomes(suite, scenario):
        assert o.violations == [], f"{scenario} @ {o.amount}: {o.violations}"


def test_cross_scenario_gate_monotone(suite: SimulationResult) -> None:
    assert [c for c in suite.cross_checks if c.severity.value == "VIOLATION"] == []


def test_price_feed_down_is_no_action(suite: SimulationResult) -> None:
    for o in _outcomes(suite, "price_feed_down"):
        assert o.entries == () and o.sweep_qty == 0 and o.fired == ()


def test_fundamentals_down_allows_no_first_bite(suite: SimulationResult) -> None:
    for o in _outcomes(suite, "fundamentals_down"):
        assert not any(e.is_first_bite for e in o.entries)


def test_stale_clock_expires_verdicts(suite: SimulationResult) -> None:
    base = _outcomes(suite, "baseline")[0]
    late = _outcomes(suite, "clock_+45d")[0]
    assert late.drops_by_reason.get("DECAY_EXPIRED", 0) > base.drops_by_reason.get(
        "DECAY_EXPIRED", 0)
    assert len(late.entries) <= len(base.entries)


def test_crash_fires_more_triggers_than_baseline(suite: SimulationResult) -> None:
    base = _outcomes(suite, "baseline")[0]
    crash = _outcomes(suite, "hockey_rung2")[0]
    assert len(crash.fired) >= len(base.fired)
    assert set(base.fired) <= set(crash.fired)


def test_canara_is_raised_for_review_not_bought(suite: SimulationResult) -> None:
    """Praveen 26-Sep: Canara (WITHDRAWN) passing every gate at -15% is raised for
    analysis with its register reason — never bought silently."""
    for o in _outcomes(suite, "hockey_rung1"):
        assert "CANBK" not in {e.symbol for e in o.entries}
        assert o.drops_by_reason.get("REVIEW_FIRST", 0) >= 1


def test_results_dates_down_arms_no_trigger(suite: SimulationResult) -> None:
    """E3/E9: without results dates no basis is provably fresh — nothing fires, and
    only first bites (which need no trigger) can reach a plate."""
    for o in _outcomes(suite, "results_dates_down"):
        assert o.fired == ()
        assert all(e.is_first_bite for e in o.entries)


def test_stale_basis_after_october_results(suite: SimulationResult) -> None:
    """clock +45d crosses the October results: 1-Sep triggers go stale and disarm."""
    base = _outcomes(suite, "baseline")[0]
    late = _outcomes(suite, "clock_+45d")[0]
    assert len(late.fired) < len(base.fired)


def test_results_week_holds_every_stock(suite: SimulationResult) -> None:
    """Results in 2 days for everyone → nothing with results dates is bought."""
    for o in _outcomes(suite, "results_week"):
        assert o.drops_by_reason.get("EVENT_HOLD", 0) >= 1
        assert o.entries == () or all(e.symbol in {"NIFTYBEES", "GOLDBEES", "JUNIORBEES"}
                                      for e in o.entries)


def test_bees_missing_means_no_sweep(suite: SimulationResult) -> None:
    for o in _outcomes(suite, "bees_missing"):
        assert o.sweep_qty == 0


def test_report_leads_with_verdict(suite: SimulationResult) -> None:
    text = format_simulation(suite)
    assert text.splitlines()[1].startswith("VERDICT: PASS")
    assert "HOCKEY DETECTED" in text


def test_only_unpriced_flash_names_go_undetected(suite: SimulationResult,
                                                 market: MarketSnapshot) -> None:
    """A flash on a name the recording never priced moves nothing — the report says
    NOT DETECTED for it (honest), and for nothing else."""
    text = format_simulation(suite)
    line = next((ln for ln in text.splitlines() if "NOT DETECTED" in ln), "")
    missed = line.split(": ", 1)[1].split(", ") if line else []
    for sc in missed:
        assert sc.startswith("flash_"), sc
        assert sc.removeprefix("flash_").removesuffix("_-10") not in market.prices.prices


def test_nifty_week_fall_is_hockey(suite: SimulationResult) -> None:
    """tiffin v6 §H: 'Nifty -5% in a week' is HOCKEY — now seen, not just H > 1.15."""
    for o in _outcomes(suite, "nifty_week_-5"):
        assert any(h.startswith("NIFTY_WEEK") for h in o.hockey), o.hockey
        assert not any(h.startswith("RUNG") for h in o.hockey)


def test_ladder_rungs_are_detected(suite: SimulationResult) -> None:
    """ledger D37: rung 1 at Nifty -15%, rung 2 at -25% (deepest rung reported)."""
    for o in _outcomes(suite, "hockey_rung1"):
        assert any(h.startswith("RUNG_1") for h in o.hockey), o.hockey
    for o in _outcomes(suite, "hockey_rung2"):
        assert any(h.startswith("RUNG_2") for h in o.hockey), o.hockey


def test_flash_fall_is_name_day_hockey(suite: SimulationResult,
                                      market: MarketSnapshot) -> None:
    """tiffin v6 §H: 'a name -10% in a day' — every flash on a priced name flags it."""
    flashes = [s for s in CATALOG if "flash" in s.tags]
    assert flashes
    for sc in flashes:
        sym = sc.name.removeprefix("flash_").removesuffix("_-10")
        if sym not in market.prices.prices:
            continue
        for o in _outcomes(suite, sc.name):
            assert any(h.startswith(f"NAME_DAY {sym} ") for h in o.hockey), (sc.name, o.hockey)


def test_calm_baseline_has_no_market_hockey(suite: SimulationResult) -> None:
    for o in _outcomes(suite, "baseline"):
        assert o.hockey == ()


def test_session_written_once_to_register(market: MarketSnapshot, scratch_db: Path) -> None:
    base = [s for s in CATALOG if s.name == "baseline"]

    def _count() -> tuple[int, int]:
        with PattazRepo(scratch_db) as repo:
            c = repo._con
            return (c.execute("SELECT count(*) FROM sessions WHERE usecase='UC5_SIMULATION'"
                              ).fetchone()[0],
                    c.execute("SELECT count(*) FROM sessions WHERE usecase='UC2_PLATE'"
                              ).fetchone()[0])

    before = _count()
    r = run_simulation(scratch_db, market, base, (Decimal(10000),))
    after = _count()
    assert after == (before[0] + 1, before[1])     # one UC5 row, no UC2 rows
    assert r.run_id.startswith("UC5_")


def test_cli_what_if(scratch_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["--db", str(scratch_db), "what-if", "--nifty", "-15",
                 "--name", "INFY:-5", "--amount", "25000", "--no-session"])
    out = capsys.readouterr().out
    assert code == 0
    assert out.startswith("What if: market -15%, INFY -5%")
    assert "rehearsal, never an order" in out


def test_cli_run_single_scenario(scratch_db: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["--db", str(scratch_db), "run", "--scenario", "baseline", "--no-session"])
    assert code == 0 and "VERDICT: PASS" in capsys.readouterr().out


def test_ticker_differs_from_symbol_is_still_considered(market: MarketSnapshot,
                                                         scratch_db: Path) -> None:
    """REC trades as RECLTD.NS: the plate must key prices by register symbol, so REC is
    judged (NEVER_ADD → STATUS_BLOCKED), not silently unpriced."""
    from usecases.plate import run_plate
    r = run_plate(scratch_db, Decimal(10000), market=market, today=market.recorded_at,
                  record_session=False)
    assert {d.symbol: d.reason.name for d in r.plate.drops}.get("REC") == "STATUS_BLOCKED"
    assert "REC" not in {d.symbol for d in r.unpriced}
