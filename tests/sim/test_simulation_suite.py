"""tests/sim/test_simulation_suite.py — UC5 in CI: every scenario, every law, no network.

Replays the committed market recording through the real UC1 board and UC2 plate
(scratch copy of the register) under every catalog scenario at three session sizes.
Any VIOLATION fails the build; FINDINGS are reported, never failed (spec-legal).
"""
from __future__ import annotations

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
    return run_simulation(db, market, CATALOG, AMOUNTS, record_session=False)


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


def test_canara_withdrawn_surfaces_in_rung1(suite: SimulationResult) -> None:
    """26-Sep: at -15% Canara (WITHDRAWN, PSU, owned) first-bites while PSU < 25% —
    surfaced for Praveen, never silently allowed or silently blocked."""
    o = _outcomes(suite, "hockey_rung1")[-1]
    if any(e.symbol == "CANBK" for e in o.entries):
        assert any(c.invariant == "REGISTER_ZERO_BUCKET" and c.symbol == "CANBK"
                   for c in o.findings)


def test_bees_missing_means_no_sweep(suite: SimulationResult) -> None:
    for o in _outcomes(suite, "bees_missing"):
        assert o.sweep_qty == 0


def test_report_leads_with_verdict(suite: SimulationResult) -> None:
    text = format_simulation(suite)
    assert text.splitlines()[1].startswith("VERDICT: PASS")
    assert "NOT MODELLED" in text


def test_session_written_once_to_register(market: MarketSnapshot, scratch_db: Path) -> None:
    base = [s for s in CATALOG if s.name == "baseline"]
    r = run_simulation(scratch_db, market, base, (Decimal(10000),))
    with PattazRepo(scratch_db) as repo:
        rows = repo._con.execute(
            "SELECT usecase FROM sessions WHERE run_id LIKE 'UC5_%' OR run_id LIKE 'UC2_%'"
        ).fetchall()
    assert [row["usecase"] for row in rows] == ["UC5_SIMULATION"]
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
