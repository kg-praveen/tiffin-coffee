"""tests/test_plate_extras.py — single-deployment cap, HOCKEY detection, two-pocket.

Spec: tiffin-coffee v4 §SINGLE-DEPLOYMENT CAP ("no single plate may exceed 15% of
confirmed investable surplus"), v6 §H HOCKEY row ("Nifty -5% in a week, or a name -10%
in a day"), §TWO-POCKET ladder + ledger D37 rungs, §TWO-POCKET CASH RULE (60/40).
No network. Usecase tests run on scratch_db with migration 012 applied here.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from engine.hockey import (
    MARKET,
    HockeyConfig,
    HockeyKind,
    HockeyReport,
    IndexInput,
    compute_change_pct,
    detect_hockey,
    parse_two_pocket_split,
)
from engine.invariants import check_plate, inv_deployment_cap, inv_hockey_seen
from engine.plate import (
    Mode,
    NameInput,
    PlateConfig,
    PlateDropReason,
    build_plate,
    single_deployment_cap,
)
from tools.index_moves import IndexMoves
from tools.market_snapshot import (
    MarketSnapshot,
    load_snapshot,
    newest_snapshot,
    snapshot_from_json,
    snapshot_to_json,
)
from tools.stamped import Stamped
from usecases.plate import format_plate, run_plate
from usecases.scenarios import SimContext, market_move, move_nifty, name_move

ROOT = Path(__file__).parent.parent
MIGRATION_012 = ROOT / "db" / "migrations" / "012_plate_extras.sql"
MARKET_DIR = Path(__file__).parent / "fixtures" / "market"


# ------------------------------------------------------------------ helpers ---


def _name(symbol: str, price: str, trigger: str | None = "100", low: str = "60",
          prev_close: str | None = None, **kw: object) -> NameInput:
    fields: dict[str, object] = {
        "name": symbol, "sector_class": None, "status": "ADD", "bucket": "standard",
        "cell": None, "flag_sovereign": False, "flag_psu": False, "flag_cyclical": False,
        "flag_probe_open": False, "flag_fraud_tail": False, "flag_exit_decided": False,
        "p5_status": None, "p5_note_ref": None, "decay_expiry": None,
        "qty_held_household": 10, "current_weight_pct": Decimal(1),
        "valuation_gate_passed": True,
    }
    fields.update(kw)
    return NameInput(symbol=symbol, price=Decimal(price), low_52w=Decimal(low),
                     trigger_level=Decimal(trigger) if trigger else None,
                     prev_close=Decimal(prev_close) if prev_close else None,
                     **fields)  # type: ignore[arg-type]


NAMES = [_name("AAA", "100"), _name("BBB", "95"), _name("CCC", "90")]


def _cfg(session: str = "3000", surplus: str | None = None) -> PlateConfig:
    return PlateConfig(session_amount=Decimal(session), today="2026-09-26",
                       psu_weight_pct=Decimal(0), cells={}, bees_price=Decimal(250),
                       confirmed_surplus=Decimal(surplus) if surplus else None,
                       single_deployment_cap_pct=Decimal(15))


HCFG = HockeyConfig(nifty_week_fall_pct=Decimal(5), name_day_fall_pct=Decimal(10),
                    rung1_drawdown_pct=Decimal(15), rung2_drawdown_pct=Decimal(25))


def _apply_012(db: Path) -> None:
    con = sqlite3.connect(db)
    try:
        if not con.execute("SELECT count(*) FROM policy WHERE key="
                           "'hockey_nifty_week_fall_pct'").fetchone()[0]:
            con.executescript(MIGRATION_012.read_text())
    finally:
        con.close()


@pytest.fixture
def db012(scratch_db: Path) -> Path:
    _apply_012(scratch_db)
    return scratch_db


@pytest.fixture(scope="module")
def market() -> MarketSnapshot:
    path = newest_snapshot(MARKET_DIR)
    assert path is not None
    return load_snapshot(path)


# ---------------------------------------------------- single-deployment cap ---


class TestSingleDeploymentCap:
    def test_cap_is_policy_pct_of_confirmed_surplus(self) -> None:
        assert single_deployment_cap(Decimal(200000), Decimal(15)) == Decimal("30000.00")

    def test_no_surplus_leaves_plate_unchanged_and_unchecked(self) -> None:
        r = build_plate(NAMES, _cfg())
        assert r.entries and r.deployment_cap is None and r.halt_reason is None

    def test_within_cap_is_unchanged(self) -> None:
        plain = build_plate(NAMES, _cfg())
        capped = build_plate(NAMES, _cfg(surplus="100000"))
        assert capped.entries == plain.entries
        assert capped.deployment_cap == Decimal("15000.00")
        assert capped.halt_reason is None

    def test_over_cap_halts_whole_plate_no_trim(self) -> None:
        """Spec names the cap, not a trim → NO ACTION (E9), every ranked name dropped."""
        plain = build_plate(NAMES, _cfg())
        r = build_plate(NAMES, _cfg(surplus="10000"))       # cap 1,500 < plate ~3,000
        assert r.entries == [] and r.bees_sweep_qty == 0 and r.total_with_sweep == 0
        assert r.halt_reason is not None and "1500.00" in r.halt_reason
        halted = {d.symbol for d in r.drops if d.reason == PlateDropReason.DEPLOYMENT_CAP_HALT}
        assert halted == {e.symbol for e in plain.entries}
        assert "HALT:SINGLE_DEPLOYMENT_CAP" in r.rules_fired
        assert r.residual == r.plan_amount

    def test_cap_counts_the_bees_sweep_too(self) -> None:
        """Nothing eligible → the whole ticket is a BeES sweep; that is deployment too."""
        r = build_plate([], _cfg(session="3000", surplus="10000"))
        assert r.halt_reason is not None and r.bees_sweep_qty == 0

    def test_raised_plan_can_breach_the_cap(self) -> None:
        """Praveen 26-Sep: plan raised to 1 share each — the cap binds independently."""
        pricey = [_name("AAA", "2000", trigger="2000"), _name("BBB", "1900", trigger="1900")]
        r = build_plate(pricey, _cfg(session="1000", surplus="20000"))   # cap 3,000
        assert r.halt_reason is not None

    def test_invariants_hold_on_capped_and_halted_plates(self) -> None:
        for surplus in ("100000", "10000"):
            cfg = _cfg(surplus=surplus)
            r = build_plate(NAMES, cfg)
            assert [c for c in check_plate(NAMES, cfg, r, 1, 15)
                    if c.severity.value == "VIOLATION"] == []

    def test_invariant_fires_on_a_plate_over_the_cap(self) -> None:
        uncapped = build_plate(NAMES, _cfg())              # ~Rs 1,000 per name
        plate_only = inv_deployment_cap(uncapped, _cfg(surplus="10000"))    # cap 1,500
        assert [c.symbol for c in plate_only] == ["*"]
        per_name = inv_deployment_cap(uncapped, _cfg(surplus="5000"))       # cap 750
        over = {e.symbol for e in uncapped.entries if e.amount > 750}
        assert over and {c.symbol for c in per_name} == {"*"} | over
        assert all(c.invariant == "DEPLOYMENT_CAP" for c in per_name)

    def test_invariant_fires_on_a_halted_plate_with_entries(self) -> None:
        cfg = _cfg(surplus="100000")
        r = build_plate(NAMES, cfg)
        bad = replace(r, halt_reason="x")
        assert inv_deployment_cap(bad, cfg)[0].invariant == "DEPLOYMENT_CAP"


# ------------------------------------------------------------------- hockey ---


class TestHockeyDetection:
    def _plate_and(self, names: list[NameInput], index: IndexInput | None,
                   cfg: HockeyConfig = HCFG) -> HockeyReport:
        return detect_hockey(names, build_plate(names, _cfg()), index, cfg)

    def test_calm_day_no_signal(self) -> None:
        rep = self._plate_and(NAMES, IndexInput(Decimal("-0.88"), Decimal("-12.26")))
        assert rep.signals == () and not rep.market_hockey

    def test_nifty_week_fall_inclusive_at_threshold(self) -> None:
        rep = self._plate_and(NAMES, IndexInput(Decimal(-5), Decimal(-5)))
        assert [s.kind for s in rep.signals] == [HockeyKind.NIFTY_WEEK]
        assert rep.market_hockey and rep.signals[0].symbol == MARKET
        assert self._plate_and(NAMES, IndexInput(Decimal("-4.99"), Decimal(0))).signals == ()

    def test_deepest_rung_only(self) -> None:
        r1 = self._plate_and(NAMES, IndexInput(Decimal(0), Decimal(-15)))
        assert [s.kind for s in r1.signals] == [HockeyKind.RUNG_1]
        r2 = self._plate_and(NAMES, IndexInput(Decimal(0), Decimal("-25.5")))
        assert [s.kind for s in r2.signals] == [HockeyKind.RUNG_2]
        assert self._plate_and(NAMES, IndexInput(Decimal(0), Decimal("-14.99"))).signals == ()

    def test_name_day_fall(self) -> None:
        names = [_name("AAA", "90", prev_close="100"), _name("BBB", "95", prev_close="100")]
        rep = self._plate_and(names, IndexInput(Decimal(0), Decimal(0)))
        day = rep.of(HockeyKind.NAME_DAY)
        assert [(s.symbol, s.move_pct, s.blocked_by) for s in day] == [
            ("AAA", Decimal("-10.00"), None)]

    def test_name_day_fall_on_a_dropped_name_keeps_the_drop(self) -> None:
        """'Hockey never overrides Stage-0 or a cell cap: high H x P0 = still zero.'"""
        names = [_name("AAA", "90", prev_close="100", flag_probe_open=True)]
        r = build_plate(names, _cfg())
        rep = detect_hockey(names, r, None, HCFG)
        assert r.entries == []
        assert rep.of(HockeyKind.NAME_DAY)[0].blocked_by == "PROBE_OPEN"

    def test_h_above_uses_the_plate_mode(self) -> None:
        names = [_name("AAA", "80", trigger="100")]     # H 1.25 → HOCKEY band
        r = build_plate(names, _cfg())
        assert r.entries[0].mode == Mode.HOCKEY
        rep = detect_hockey(names, r, IndexInput(Decimal(0), Decimal(0)), HCFG)
        assert [s.kind for s in rep.signals] == [HockeyKind.H_ABOVE]
        assert not rep.market_hockey

    def test_missing_inputs_are_reported_not_assumed_calm(self) -> None:
        rep = self._plate_and(NAMES, None)
        assert rep.signals == ()
        joined = " ".join(rep.not_checked)
        assert "Nifty week fall" in joined and "ladder" in joined
        assert "no previous close for 3 of 3" in joined

    def test_missing_policy_rows_are_reported(self) -> None:
        cfg = HockeyConfig(None, None, None, None)
        rep = self._plate_and(NAMES, IndexInput(Decimal(-9), Decimal(-30)), cfg)
        assert rep.signals == ()
        assert any("policy" in n for n in rep.not_checked)

    def test_detection_never_changes_the_plate(self) -> None:
        names = [_name("AAA", "90", prev_close="100")]
        r = build_plate(names, _cfg())
        before = replace(r)
        detect_hockey(names, r, IndexInput(Decimal(-9), Decimal(-30)), HCFG)
        assert r == before

    def test_change_pct(self) -> None:
        assert compute_change_pct(Decimal("715.91"), Decimal("795.45")) == Decimal("-10.00")
        assert compute_change_pct(Decimal(1), Decimal(0)) is None

    def test_invariant_catches_a_missed_signal(self) -> None:
        names = [_name("AAA", "90", prev_close="100")]
        idx = IndexInput(Decimal(-6), Decimal(-16))
        r = build_plate(names, _cfg())
        rep = detect_hockey(names, r, idx, HCFG)
        assert inv_hockey_seen(names, idx, HCFG, rep) == []
        blind = HockeyReport(signals=(), not_checked=())
        got = {(c.symbol, c.detail.split()[0]) for c in inv_hockey_seen(names, idx, HCFG, blind)}
        assert ("*", "Nifty") in got and ("AAA", "-10.00%") in got
        assert len(inv_hockey_seen(names, idx, HCFG, blind)) == 3


class TestTwoPocket:
    def test_parse_policy_split(self) -> None:
        assert parse_two_pocket_split("60/40") == (Decimal(60), Decimal(40))

    @pytest.mark.parametrize("bad", ["60", "60/30", "a/b"])
    def test_bad_split_raises(self, bad: str) -> None:
        with pytest.raises((ValueError, ArithmeticError)):
            parse_two_pocket_split(bad)


# ---------------------------------------------------------------- scenarios ---


CTX = SimContext(sector_of={"GOLDBEES": "NON_EARNING"}, seats=(), policy={})


class TestScenarioInputs:
    def test_market_move_without_recorded_nifty_measures_from_the_day(
            self, market: MarketSnapshot) -> None:
        assert market.nifty is None
        moved = market_move(Decimal(-5), "t")(market, CTX)
        assert moved.nifty is not None
        assert moved.nifty.week_change_pct.value == Decimal("-5.00")
        assert moved.nifty.drawdown_pct.value == Decimal("-5.00")
        assert moved.nifty.level is None
        assert "no Nifty recorded" in moved.nifty.week_change_pct.source

    def test_market_move_composes_on_a_recorded_nifty(self, market: MarketSnapshot) -> None:
        st = Stamped(value=Decimal("-12.26"), source="yfinance:^NSEI", as_of="2026-09-25")
        wk = Stamped(value=Decimal("-0.88"), source="yfinance:^NSEI", as_of="2026-09-25")
        base = replace(market, nifty=IndexMoves("^NSEI", None, wk, st))
        moved = move_nifty(base, Decimal(-5), "t")
        assert moved.nifty is not None
        assert moved.nifty.drawdown_pct.value == Decimal("-16.65")   # 0.8774 x 0.95
        assert moved.nifty.week_change_pct.value == Decimal("-5.84")
        assert moved.nifty.drawdown_pct.source.startswith("sim:t<-yfinance")

    def test_melt_up_never_positive_drawdown(self, market: MarketSnapshot) -> None:
        moved = market_move(Decimal(10), "t")(market, CTX)
        assert moved.nifty is not None and moved.nifty.drawdown_pct.value == 0

    def test_name_move_is_a_day_move(self, market: MarketSnapshot) -> None:
        old = market.prices.prices["INFY"].price.value
        moved = name_move("INFY", Decimal(-10), "t")(market, CTX)
        p = moved.prices.prices["INFY"]
        assert p.prev_close is not None and p.prev_close.value == old
        assert compute_change_pct(p.price.value, p.prev_close.value) == Decimal("-10.00")

    def test_market_move_is_not_a_day_move(self, market: MarketSnapshot) -> None:
        moved = market_move(Decimal(-15), "t")(market, CTX)
        assert moved.prices.prices["INFY"].prev_close is None

    def test_snapshot_round_trip_with_nifty_and_prev_close(
            self, market: MarketSnapshot) -> None:
        moved = name_move("INFY", Decimal(-10), "t")(market_move(Decimal(-5), "t")(
            market, CTX), CTX)
        again = snapshot_from_json(json.loads(json.dumps(snapshot_to_json(moved))))
        assert again == moved


# ------------------------------------------------------------------ usecase ---


class TestUsecase:
    def test_no_surplus_says_cap_not_checked(self, db012: Path,
                                             market: MarketSnapshot) -> None:
        r = run_plate(db012, Decimal(10000), market=market, today=market.recorded_at,
                      record_session=False)
        text = format_plate(r)
        assert "single-deployment cap 15% of surplus — not checked" in text
        assert "two-pocket 60/40" in text and "reserve floor Rs 1,00,000" in text
        # the recording has no Nifty and no previous closes: said, not assumed calm
        assert "hockey check incomplete" in text

    def test_surplus_within_cap(self, db012: Path, market: MarketSnapshot) -> None:
        r = run_plate(db012, Decimal(10000), market=market, today=market.recorded_at,
                      record_session=False, confirmed_surplus=Decimal(1000000))
        assert r.plate.halt_reason is None and r.plate.entries
        assert "[x] single-deployment cap 15% of Rs 10,00,000 = Rs 1,50,000" in format_plate(r)

    def test_surplus_too_small_halts_and_session_says_why(
            self, db012: Path, market: MarketSnapshot) -> None:
        r = run_plate(db012, Decimal(10000), market=market, today=market.recorded_at,
                      confirmed_surplus=Decimal(20000))          # cap Rs 3,000
        assert r.plate.entries == [] and r.plate.halt_reason is not None
        text = format_plate(r)
        assert "HALT — NO ACTION" in r.advisory_flags[0]
        assert "PLATE — NO ACTION" in text and "DO NOT EXECUTE" in text
        con = sqlite3.connect(db012)
        inputs, outputs = con.execute(
            "SELECT inputs_json, outputs_json FROM sessions WHERE run_id=?",
            (r.run_id,)).fetchone()
        con.close()
        assert json.loads(inputs)["confirmed_surplus"] == "20000"
        assert json.loads(outputs)["halt_reason"] == r.plate.halt_reason

    def test_nifty_week_fall_is_advised_not_sized(self, db012: Path,
                                                  market: MarketSnapshot) -> None:
        shocked = market_move(Decimal(-5), "nifty-5")(market, CTX)
        r = run_plate(db012, Decimal(10000), market=shocked, today=market.recorded_at,
                      record_session=False)
        assert r.hockey is not None and r.hockey.market_hockey
        lines = [f for f in r.advisory_flags if f.startswith("HOCKEY: Nifty -5.00% in a week")]
        assert lines and "needs your yes" in lines[0].lower()
        assert "[!] hockey" in format_plate(r)

    def test_rung_advisory(self, db012: Path, market: MarketSnapshot) -> None:
        shocked = market_move(Decimal(-25), "rung2")(market, CTX)
        r = run_plate(db012, Decimal(10000), market=shocked, today=market.recorded_at,
                      record_session=False)
        assert any(f.startswith("HOCKEY rung 2 reached") for f in r.advisory_flags)

    def test_flash_advisory(self, db012: Path, market: MarketSnapshot) -> None:
        shocked = name_move("INFY", Decimal(-10), "flash")(market, CTX)
        r = run_plate(db012, Decimal(10000), market=shocked, today=market.recorded_at,
                      record_session=False)
        assert r.hockey is not None
        assert [s.symbol for s in r.hockey.of(HockeyKind.NAME_DAY)] == ["INFY"]
        assert any("INFY -10.00%" in f for f in r.advisory_flags)

    def test_without_migration_012_the_checks_say_so(self, scratch_db: Path,
                                                     market: MarketSnapshot) -> None:
        shocked = market_move(Decimal(-5), "nifty-5")(market, CTX)
        r = run_plate(scratch_db, Decimal(10000), market=shocked, today=market.recorded_at,
                      record_session=False)
        assert r.hockey is not None
        assert any("hockey_nifty_week_fall_pct missing" in n for n in r.hockey.not_checked)

    def test_offline_run_reports_hockey_not_run(self, db012: Path) -> None:
        r = run_plate(db012, Decimal(10000), fetch_prices=False, record_session=False)
        assert r.hockey is not None and r.hockey.signals == ()
        assert any("no Nifty data" in n for n in r.hockey.not_checked)
