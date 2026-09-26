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
from datetime import date
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
    hockey_rules_fired,
    latest_completed_session,
    parse_two_pocket_split,
    stale_market_data_reason,
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
        with sqlite3.connect(scratch_db) as con:       # simulate a pre-012 register
            con.execute("DELETE FROM policy WHERE key IN ('hockey_nifty_week_fall_pct', "
                        "'hockey_name_day_fall_pct')")
        shocked = market_move(Decimal(-5), "nifty-5")(market, CTX)
        r = run_plate(scratch_db, Decimal(10000), market=shocked, today=market.recorded_at,
                      record_session=False)
        assert r.hockey is not None
        assert any("hockey_nifty_week_fall_pct missing" in n for n in r.hockey.not_checked)

    def test_offline_run_reports_hockey_not_run(self, db012: Path) -> None:
        r = run_plate(db012, Decimal(10000), fetch_prices=False, record_session=False)
        assert r.hockey is not None and r.hockey.signals == ()
        assert any("no Nifty data" in n for n in r.hockey.not_checked)


# ------------------------------------------- review fixes (fix/plate-extras) ---


def _session_row(db: Path, run_id: str) -> tuple[dict, dict, list[str]]:
    con = sqlite3.connect(db)
    try:
        inputs, outputs, rules = con.execute(
            "SELECT inputs_json, outputs_json, rules_fired FROM sessions WHERE run_id=?",
            (run_id,)).fetchone()
    finally:
        con.close()
    return json.loads(inputs), json.loads(outputs), (rules or "").split(",")


class TestCapPolicyOnly:
    """E2: the cap % comes only from policy — no bare default in PlateConfig."""

    def test_no_default_pct(self) -> None:
        cfg = PlateConfig(session_amount=Decimal(3000), today="2026-09-26",
                          psu_weight_pct=Decimal(0), cells={}, bees_price=Decimal(250),
                          confirmed_surplus=Decimal(10000))
        assert cfg.single_deployment_cap_pct is None
        r = build_plate(NAMES, cfg)
        assert r.deployment_cap is None and r.halt_reason is None and r.entries
        assert inv_deployment_cap(r, cfg) == []

    def test_usecase_without_policy_row_says_not_checkable(
            self, db012: Path, market: MarketSnapshot) -> None:
        con = sqlite3.connect(db012)
        con.execute("DELETE FROM policy WHERE key='single_deployment_cap_pct'")
        con.commit()
        con.close()
        r = run_plate(db012, Decimal(10000), market=market, today=market.recorded_at,
                      record_session=False, confirmed_surplus=Decimal(20000))
        assert r.config is not None and r.config.single_deployment_cap_pct is None
        assert r.plate.halt_reason is None
        assert "single-deployment cap — not checkable" in format_plate(r)


class TestE6CapVsBeesFloor:
    """E6: cap below 1 NIFTYBEES → tiffin v4 cap vs tiffin v6 BeES NO-SKIP, NO ACTION."""

    def test_conflict_halts_and_names_both_rules(self) -> None:
        cfg = _cfg(surplus="1000")                         # cap 150 < BeES 250
        r = build_plate(NAMES, cfg)
        assert r.e6_conflict == ("tiffin v4 SINGLE-DEPLOYMENT CAP",
                                 "tiffin v6 BeES FLOOR NO-SKIP")
        assert r.entries == [] and r.bees_sweep_qty == 0 and r.total_with_sweep == 0
        assert r.halt_reason is not None and "E6 CONFLICT" in r.halt_reason
        assert "E6:CONFLICT:SINGLE_DEPLOYMENT_CAP_vs_BEES_FLOOR_NO_SKIP" in r.rules_fired
        assert "HALT:SINGLE_DEPLOYMENT_CAP" not in r.rules_fired
        reasons = {d.reason for d in r.drops if d.symbol in {"AAA", "BBB", "CCC"}}
        assert reasons == {PlateDropReason.E6_CAP_VS_BEES_FLOOR}
        assert [c for c in check_plate(NAMES, cfg, r, 1, 15)
                if c.severity.value == "VIOLATION"] == []

    def test_conflict_even_with_nothing_eligible(self) -> None:
        r = build_plate([], _cfg(surplus="1000"))
        assert r.e6_conflict is not None and r.bees_sweep_qty == 0

    def test_cap_at_one_unit_is_not_a_conflict(self) -> None:
        r = build_plate([], _cfg(session="250", surplus="1666.67"))   # cap 250.00
        assert r.e6_conflict is None

    def test_invariant_fires_when_conflict_is_settled_silently(self) -> None:
        cfg = _cfg(surplus="1000")
        silent = replace(build_plate(NAMES, cfg), e6_conflict=None)
        assert any("no E6 conflict" in c.detail for c in inv_deployment_cap(silent, cfg))

    def test_usecase_reports_conflict_no_action(self, db012: Path,
                                                market: MarketSnapshot) -> None:
        r = run_plate(db012, Decimal(10000), market=market, today=market.recorded_at,
                      confirmed_surplus=Decimal(1000))     # cap 150 < NIFTYBEES 263.99
        assert r.plate.e6_conflict is not None and r.plate.entries == []
        first = r.advisory_flags[0]
        assert first.startswith("E6 CONFLICT — NO ACTION")
        assert "tiffin v4 SINGLE-DEPLOYMENT CAP" in first
        assert "tiffin v6 BeES FLOOR NO-SKIP" in first
        text = format_plate(r)
        assert "PLATE — NO ACTION (E6 CONFLICT" in text and "DO NOT EXECUTE" in text
        _, outputs, rules = _session_row(db012, r.run_id)
        assert outputs["e6_conflict"] == list(r.plate.e6_conflict)
        assert "E6:CONFLICT:SINGLE_DEPLOYMENT_CAP_vs_BEES_FLOOR_NO_SKIP" in rules


class TestHockeyRulesFired:
    """E8: every HOCKEY detection appears in rules_fired by name."""

    def test_labels(self) -> None:
        names = [_name("AAA", "90", prev_close="100"), _name("HHH", "80", trigger="100")]
        rep = detect_hockey(names, build_plate(names, _cfg()),
                            IndexInput(Decimal(-6), Decimal(-16)), HCFG)
        assert hockey_rules_fired(rep) == ["HOCKEY:NIFTY_WEEK", "HOCKEY:RUNG_1",
                                           "HOCKEY:NAME_DAY:AAA", "HOCKEY:H_ABOVE:HHH"]

    def test_usecase_rules_fired_carry_hockey(self, db012: Path,
                                              market: MarketSnapshot) -> None:
        shocked = name_move("INFY", Decimal(-10), "flash")(
            market_move(Decimal(-25), "rung2")(market, CTX), CTX)
        r = run_plate(db012, Decimal(10000), market=shocked, today=market.recorded_at)
        fired = r.plate.rules_fired
        assert "HOCKEY:NIFTY_WEEK" in fired and "HOCKEY:RUNG_2" in fired
        assert "HOCKEY:NAME_DAY:INFY" in fired
        _, _, rules = _session_row(db012, r.run_id)
        assert "HOCKEY:RUNG_2" in rules and "HOCKEY:NAME_DAY:INFY" in rules


class TestMarketDataFreshness:
    """E3: index / previous-close data older than the latest session is dropped (live)."""

    @pytest.mark.parametrize(("run", "latest"), [
        ("2026-09-26", "2026-09-25"),    # Sat → Fri
        ("2026-09-27", "2026-09-25"),    # Sun → Fri
        ("2026-09-28", "2026-09-25"),    # Mon → Fri
        ("2026-09-29", "2026-09-28"),    # Tue → Mon
    ])
    def test_latest_completed_session(self, run: str, latest: str) -> None:
        assert latest_completed_session(date.fromisoformat(run)) == date.fromisoformat(latest)

    def test_stale_reason(self) -> None:
        assert stale_market_data_reason(date(2026, 9, 25), date(2026, 9, 28)) is None
        why = stale_market_data_reason(date(2026, 9, 25), date(2026, 9, 29))
        assert why is not None and "2026-09-28" in why and "stale" in why

    @staticmethod
    def _live(monkeypatch: pytest.MonkeyPatch, market: MarketSnapshot,
              nifty_as_of: str) -> None:
        """Stand in for every live adapter (no network): the recorded day, INFY -10%
        on the day, and a Nifty -6% week stamped `nifty_as_of`."""
        import usecases.plate as uc
        flashed = name_move("INFY", Decimal(-10), "flash")(market, CTX)
        wk = Stamped(value=Decimal(-6), source="yfinance:^NSEI", as_of=nifty_as_of)
        dd = Stamped(value=Decimal(-8), source="yfinance:^NSEI", as_of=nifty_as_of)

        def no_gsec() -> Stamped[Decimal]:
            raise ValueError("offline")

        monkeypatch.setattr(uc, "fetch_prices_batch", lambda _t: flashed.prices)
        monkeypatch.setattr(uc, "fetch_fundamentals_batch", lambda _t: flashed.fundamentals)
        monkeypatch.setattr(uc, "fetch_result_dates_batch", lambda _t: flashed.results)
        monkeypatch.setattr(uc, "fetch_gsec_yield", no_gsec)
        monkeypatch.setattr(uc, "fetch_nifty_moves",
                            lambda: IndexMoves("^NSEI", None, wk, dd))

    def test_live_fresh_inputs_are_checked(self, db012: Path, market: MarketSnapshot,
                                           monkeypatch: pytest.MonkeyPatch) -> None:
        self._live(monkeypatch, market, "2026-09-25")
        r = run_plate(db012, Decimal(10000), today="2026-09-28", record_session=False)
        assert r.nifty is not None
        assert "HOCKEY:NIFTY_WEEK" in r.plate.rules_fired
        assert "HOCKEY:NAME_DAY:INFY" in r.plate.rules_fired

    def test_live_stale_inputs_are_dropped_with_a_reason(
            self, db012: Path, market: MarketSnapshot,
            monkeypatch: pytest.MonkeyPatch) -> None:
        self._live(monkeypatch, market, "2026-09-25")
        r = run_plate(db012, Decimal(10000), today="2026-09-29")
        assert r.hockey is not None and r.nifty is None
        assert not [s for s in r.hockey.signals if s.kind != HockeyKind.H_ABOVE]
        joined = " ".join(r.hockey.not_checked)
        assert "not checked (stale index data" in joined
        assert "stale price data" in joined and "INFY" in joined
        assert not any(f.startswith(("HOCKEY:NIFTY", "HOCKEY:RUNG", "HOCKEY:NAME_DAY"))
                       for f in r.plate.rules_fired)
        inputs, _, _ = _session_row(db012, r.run_id)
        assert inputs["nifty_dropped"] is not None
        assert "INFY" in inputs["prev_close_dropped_stale"]

    def test_replay_is_not_filtered(self, db012: Path, market: MarketSnapshot) -> None:
        shocked = market_move(Decimal(-5), "nifty-5")(market, CTX)
        r = run_plate(db012, Decimal(10000), market=shocked, today="2026-10-30",
                      record_session=False)
        assert r.hockey is not None and r.hockey.market_hockey


class TestOpenQuestions:
    """Praveen's open decisions are printed every run and written to the session."""

    def test_every_open_question_is_in_the_output(self, db012: Path,
                                                  market: MarketSnapshot) -> None:
        r = run_plate(db012, Decimal(10000), market=market, today=market.recorded_at)
        qs = [f for f in r.advisory_flags if f.startswith("OPEN QUESTION for Praveen:")]
        text = " ".join(qs)
        assert len(qs) == 7
        for needle in ("trim the plate to the cap, or halt", "HALTS",
                       "per plate", "per day", "confirmed investable surplus",
                       "two-pocket 60/40 base", "7 calendar days", "close-to-close",
                       "52 weeks", "Stage-0", "H > 1.15", "§14 1(v)"):
            assert needle in text, needle
        assert "OPEN QUESTION for Praveen:" in format_plate(r)
        _, outputs, _ = _session_row(db012, r.run_id)
        assert outputs["open_questions"] == qs
