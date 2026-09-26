"""tests/test_engine_plate.py — pure-function tests for engine/plate.py.

Spec: tiffin-coffee v6 formula, E1-E9 contract. No network, no DB.
"""
from __future__ import annotations

from decimal import Decimal

from engine.plate import (
    CellInfo,
    LowBand,
    Mode,
    NameInput,
    PlateConfig,
    PlateDropReason,
    PriorityTier,
    build_plate,
    check_first_bite,
    check_overlays,
    classify_low_band,
    classify_mode,
    classify_priority,
    compute_bees_sweep,
    compute_h,
    compute_l,
    compute_score,
    size_by_rank,
)

# ------------------------------------------------------------- helpers ---

def _name(
    symbol: str = "TEST",
    name: str = "Test Corp",
    price: Decimal = Decimal(100),
    low_52w: Decimal = Decimal(95),
    trigger_level: Decimal | None = Decimal(100),
    status: str = "ADD",
    bucket: str | None = "standard",
    qty_held_household: int = 10,
    current_weight_pct: Decimal | None = Decimal(3),
    valuation_gate_passed: bool = False,
    **kwargs: object,
) -> NameInput:
    defaults = {
        "cell": None,
        "sector_class": None,
        "flag_sovereign": False,
        "flag_psu": False,
        "flag_cyclical": False,
        "flag_probe_open": False,
        "flag_fraud_tail": False,
        "flag_exit_decided": False,
        "p5_status": None,
        "p5_note_ref": None,
        "decay_expiry": None,
    }
    defaults.update(kwargs)
    return NameInput(
        symbol=symbol, name=name, price=price, low_52w=low_52w,
        trigger_level=trigger_level, status=status, bucket=bucket,
        qty_held_household=qty_held_household,
        current_weight_pct=current_weight_pct,
        valuation_gate_passed=valuation_gate_passed,
        **defaults,  # type: ignore[arg-type]
    )


def _config(
    session_amount: Decimal = Decimal(40000),
    bees_price: Decimal | None = Decimal(265),
) -> PlateConfig:
    return PlateConfig(
        session_amount=session_amount,
        today="2026-09-20",
        psu_weight_pct=Decimal(15),
        cells={},
        bees_price=bees_price,
    )


# --------------------------------------------------- classify_mode ---


class TestClassifyMode:
    def test_hockey(self) -> None:
        mode, mult = classify_mode(Decimal("1.20"))
        assert mode == Mode.HOCKEY
        assert mult == Decimal("3.0")

    def test_full_meals(self) -> None:
        mode, mult = classify_mode(Decimal("1.10"))
        assert mode == Mode.FULL_MEALS
        assert mult == Decimal("3.0")

    def test_tiffin(self) -> None:
        mode, mult = classify_mode(Decimal("1.00"))
        assert mode == Mode.TIFFIN
        assert mult == Decimal("1.0")

    def test_coffee(self) -> None:
        mode, mult = classify_mode(Decimal("0.90"))
        assert mode == Mode.COFFEE
        assert mult == Decimal("0.5")

    def test_fasting(self) -> None:
        mode, mult = classify_mode(Decimal("0.80"))
        assert mode == Mode.FASTING
        assert mult == Decimal(0)

    def test_boundary_hockey(self) -> None:
        mode, _mult = classify_mode(Decimal("1.15"))
        assert mode == Mode.HOCKEY

    def test_boundary_coffee_low(self) -> None:
        mode, _mult = classify_mode(Decimal("0.85"))
        assert mode == Mode.COFFEE


# ------------------------------------------------- classify_low_band ---


class TestClassifyLowBand:
    def test_at_the_low(self) -> None:
        band, mult = classify_low_band(Decimal("1.5"))
        assert band == LowBand.AT_THE_LOW
        assert mult == Decimal("1.5")

    def test_on_the_low(self) -> None:
        band, mult = classify_low_band(Decimal("3.0"))
        assert band == LowBand.ON_THE_LOW
        assert mult == Decimal("1.25")

    def test_near_the_low(self) -> None:
        band, mult = classify_low_band(Decimal(10))
        assert band == LowBand.NEAR_THE_LOW
        assert mult == Decimal("1.0")

    def test_mid_range(self) -> None:
        band, mult = classify_low_band(Decimal(20))
        assert band == LowBand.MID_RANGE
        assert mult == Decimal("0.5")

    def test_off_the_low(self) -> None:
        band, mult = classify_low_band(Decimal(35))
        assert band == LowBand.OFF_THE_LOW
        assert mult == Decimal("0.25")

    def test_exactly_zero(self) -> None:
        band, _mult = classify_low_band(Decimal(0))
        assert band == LowBand.AT_THE_LOW


# ----------------------------------------------- classify_priority ---


class TestClassifyPriority:
    def test_missing_weight_returns_missing(self) -> None:
        tier, mult = classify_priority(None, "standard")
        assert tier == PriorityTier.MISSING
        assert mult == Decimal("1.5")

    def test_below_10pct_fill_is_missing(self) -> None:
        tier, _mult = classify_priority(Decimal("0.3"), "standard")
        assert tier == PriorityTier.MISSING

    def test_building_range(self) -> None:
        tier, mult = classify_priority(Decimal(2), "standard")
        assert tier == PriorityTier.BUILDING
        assert mult == Decimal("1.0")

    def test_maintenance_range(self) -> None:
        tier, mult = classify_priority(Decimal(4), "standard")
        assert tier == PriorityTier.MAINTENANCE
        assert mult == Decimal("0.5")

    def test_blocked_at_target(self) -> None:
        tier, mult = classify_priority(Decimal(6), "standard")
        assert tier == PriorityTier.BLOCKED
        assert mult == Decimal(0)


# ---------------------------------------------------- compute_h/l ---


class TestComputeHL:
    def test_h_at_trigger(self) -> None:
        assert compute_h(Decimal(100), Decimal(100)) == Decimal("1.000")

    def test_h_below_trigger(self) -> None:
        h = compute_h(Decimal(100), Decimal(80))
        assert h == Decimal("1.250")

    def test_h_above_trigger(self) -> None:
        h = compute_h(Decimal(100), Decimal(120))
        assert h < Decimal("0.85")

    def test_l_at_the_low(self) -> None:
        l_pct = compute_l(Decimal(100), Decimal(99))
        assert l_pct == Decimal("1.01")

    def test_l_above_low(self) -> None:
        l_pct = compute_l(Decimal(120), Decimal(100))
        assert l_pct == Decimal("20.00")


# ------------------------------------------------- check_overlays ---


class TestCheckOverlays:
    def test_clean_name_passes(self) -> None:
        assert check_overlays(_name(), _config()) is None

    def test_sovereign_drops(self) -> None:
        reason = check_overlays(_name(flag_sovereign=True), _config())
        assert reason == PlateDropReason.SOVEREIGN

    def test_cyclical_drops(self) -> None:
        reason = check_overlays(_name(flag_cyclical=True, status="WATCH"), _config())
        assert reason == PlateDropReason.PEAK_CYCLE

    def test_cyclical_with_register_add_is_e6(self) -> None:
        """Chambal D59/D61: register ADD vs overlay #3 → E6, surfaced not bought."""
        reason = check_overlays(_name(flag_cyclical=True, status="ADD"), _config())
        assert reason == PlateDropReason.E6_PEAK_CYCLE_CONFLICT

    def test_psu_under_cap_passes(self) -> None:
        assert check_overlays(_name(flag_psu=True), _config()) is None

    def test_psu_over_cap_drops(self) -> None:
        cfg = PlateConfig(
            session_amount=Decimal(40000), today="2026-09-20",
            psu_weight_pct=Decimal(26), cells={}, bees_price=Decimal(265),
        )
        reason = check_overlays(_name(flag_psu=True), cfg)
        assert reason == PlateDropReason.PSU_CAP

    def test_cell_full_drops(self) -> None:
        cfg = PlateConfig(
            session_amount=Decimal(40000), today="2026-09-20",
            psu_weight_pct=Decimal(15),
            cells={"IT": CellInfo(is_full=True, active_add_count=2, max_adds=2)},
            bees_price=Decimal(265),
        )
        reason = check_overlays(_name(cell="IT"), cfg)
        assert reason == PlateDropReason.CELL_FULL

    def test_p5_avoid_without_note_drops(self) -> None:
        reason = check_overlays(
            _name(p5_status="AVOID", p5_note_ref=None), _config(),
        )
        assert reason == PlateDropReason.P5_VETO

    def test_p5_avoid_with_note_passes(self) -> None:
        assert check_overlays(
            _name(p5_status="AVOID", p5_note_ref="D42"), _config(),
        ) is None

    def test_fraud_tail_drops(self) -> None:
        reason = check_overlays(_name(flag_fraud_tail=True), _config())
        assert reason == PlateDropReason.FRAUD_TAIL

    def test_probe_open_drops(self) -> None:
        reason = check_overlays(_name(flag_probe_open=True), _config())
        assert reason == PlateDropReason.PROBE_OPEN

    def test_decay_expired_drops(self) -> None:
        reason = check_overlays(
            _name(decay_expiry="2026-09-01"), _config(),
        )
        assert reason == PlateDropReason.DECAY_EXPIRED

    def test_decay_future_passes(self) -> None:
        assert check_overlays(
            _name(decay_expiry="2026-12-01"), _config(),
        ) is None


# ----------------------------------------------- check_first_bite ---


class TestCheckFirstBite:
    def test_all_conditions_met(self) -> None:
        assert check_first_bite(
            Decimal("1.5"), True, True, True, "DEFAULT",
        )

    def test_not_at_the_low(self) -> None:
        assert not check_first_bite(
            Decimal("3.0"), True, True, True, "DEFAULT",
        )

    def test_not_owned(self) -> None:
        assert not check_first_bite(
            Decimal("1.0"), True, True, False, "DEFAULT",
        )

    def test_gate_failed(self) -> None:
        assert not check_first_bite(
            Decimal("1.0"), True, False, True, "DEFAULT",
        )

    def test_non_earning_always_false(self) -> None:
        assert not check_first_bite(
            Decimal("0.5"), True, True, True, "NON_EARNING",
        )


# ------------------------------------------------- scoring & sizing ---


class TestScoring:
    def test_score_product(self) -> None:
        s = compute_score(Decimal("3.0"), Decimal("1.25"), Decimal("1.5"))
        assert s == Decimal("5.625")

    def test_score_zero_if_any_zero(self) -> None:
        assert compute_score(Decimal(0), Decimal("1.25"), Decimal("1.5")) == Decimal(0)


class TestSizeByRank:
    """Praveen 26-Sep-2026: find the names, fit the budget, raise it only if 1 share of
    each doesn't fit, spread the rest by rank (1-10 clamp kept)."""

    D = Decimal

    def test_fits_budget_and_spreads_by_rank(self) -> None:
        r = size_by_rank([self.D(100)] * 4, [10] * 4, self.D(2000), 1)
        assert r.plan_amount == self.D(2000)
        assert r.qtys == sorted(r.qtys, reverse=True)       # higher rank, more shares
        assert r.qtys[0] > r.qtys[-1]
        assert sum(q * 100 for q in r.qtys) <= 2000

    def test_one_share_each_too_dear_raises_plan_exactly(self) -> None:
        prices = [self.D(2800), self.D(2100), self.D(1000), self.D(980), self.D(800),
                  self.D(330), self.D(290), self.D(270)]
        r = size_by_rank(prices, [10] * 8, self.D(5000), 1)
        assert r.plan_amount == sum(prices)                  # raised to the 1-share cost
        assert r.qtys == [1] * 8                             # nothing left to spread

    def test_never_over_plan(self) -> None:
        prices = [self.D(2900), self.D(170), self.D(1250), self.D(415), self.D(88)]
        for amount in (1000, 5000, 10000, 25000, 40000):
            r = size_by_rank(prices, [10, 10, 10, 5, 10], self.D(amount), 1)
            spent = sum(p * q for p, q in zip(prices, r.qtys, strict=True))
            assert spent <= r.plan_amount
            assert all(1 <= q <= mx for q, mx in zip(r.qtys, [10, 10, 10, 5, 10],
                                                        strict=True))

    def test_clamp_holds_with_a_huge_budget(self) -> None:
        r = size_by_rank([self.D(100), self.D(100)], [10, 5], self.D(1_000_000), 1)
        assert r.qtys == [10, 5]

    def test_empty(self) -> None:
        assert size_by_rank([], [], self.D(10000), 1).qtys == []

    def test_deterministic(self) -> None:
        args = ([self.D(300), self.D(250), self.D(90)], [10, 10, 10], self.D(10000), 1)
        assert size_by_rank(*args) == size_by_rank(*args)


class TestBeesSweep:
    def test_sweep_computes_qty(self) -> None:
        qty, amount = compute_bees_sweep(Decimal(1000), Decimal(265))
        assert qty == 3
        assert amount == Decimal("795.00")

    def test_no_bees_price(self) -> None:
        qty, _amount = compute_bees_sweep(Decimal(1000), None)
        assert qty == 0

    def test_residual_less_than_one_unit(self) -> None:
        qty, _amount = compute_bees_sweep(Decimal(200), Decimal(265))
        assert qty == 0


# --------------------------------------------------- build_plate ---


class TestBuildPlate:
    def test_single_eligible_name(self) -> None:
        names = [_name(
            symbol="INFY", name="Infosys",
            price=Decimal(1860), low_52w=Decimal(1358),
            trigger_level=Decimal(1900),
            current_weight_pct=Decimal(3),
        )]
        result = build_plate(names, _config())
        assert len(result.entries) == 1
        assert result.entries[0].symbol == "INFY"
        assert result.entries[0].qty >= 1
        assert result.entries[0].qty <= 10

    def test_sold_name_dropped(self) -> None:
        names = [_name(status="SOLD")]
        result = build_plate(names, _config())
        assert len(result.entries) == 0
        assert len(result.drops) == 1
        assert result.drops[0].reason == PlateDropReason.STATUS_BLOCKED

    def test_exit_decided_dropped(self) -> None:
        names = [_name(flag_exit_decided=True)]
        result = build_plate(names, _config())
        assert len(result.entries) == 0
        assert result.drops[0].reason == PlateDropReason.EXIT_DECIDED

    def test_fasting_without_low_dropped(self) -> None:
        names = [_name(
            price=Decimal(200), low_52w=Decimal(100),
            trigger_level=Decimal(100),
        )]
        result = build_plate(names, _config())
        assert len(result.entries) == 0
        assert result.drops[0].reason == PlateDropReason.NOT_ELIGIBLE
        assert "price ≤ 117.65" in result.drops[0].what_would_change

    def test_sovereign_overlay_drops(self) -> None:
        names = [_name(flag_sovereign=True)]
        result = build_plate(names, _config())
        assert len(result.entries) == 0
        assert result.drops[0].reason == PlateDropReason.SOVEREIGN

    def test_bees_sweep_on_empty_plate(self) -> None:
        result = build_plate([], _config(bees_price=Decimal(265)))
        assert result.bees_sweep_qty > 0

    def test_multiple_names_scored_and_tilted(self) -> None:
        names = [
            _name(symbol="A", price=Decimal(100), low_52w=Decimal(98),
                  trigger_level=Decimal(105), current_weight_pct=Decimal(1)),
            _name(symbol="B", price=Decimal(200), low_52w=Decimal(190),
                  trigger_level=Decimal(210), current_weight_pct=Decimal(2)),
            _name(symbol="C", price=Decimal(50), low_52w=Decimal(48),
                  trigger_level=Decimal(55), current_weight_pct=Decimal(1)),
        ]
        result = build_plate(names, _config())
        assert len(result.entries) == 3
        assert result.entries[0].score >= result.entries[1].score
        assert result.total_stock_amount > 0

    def test_first_bite_caps_qty_at_5(self) -> None:
        names = [_name(
            symbol="FB", price=Decimal(50), low_52w=Decimal("49.5"),
            trigger_level=None,
            qty_held_household=5,
            valuation_gate_passed=True,
            sector_class="DEFAULT",
        )]
        result = build_plate(names, _config())
        assert len(result.entries) == 1
        assert result.entries[0].is_first_bite
        assert result.entries[0].qty <= 5

    def test_no_trigger_no_low_dropped(self) -> None:
        names = [_name(
            trigger_level=None,
            price=Decimal(200), low_52w=Decimal(100),
        )]
        result = build_plate(names, _config())
        assert len(result.entries) == 0

    def test_plate_result_has_all_fields(self) -> None:
        names = [_name(
            price=Decimal(100), low_52w=Decimal(98),
            trigger_level=Decimal(105),
        )]
        result = build_plate(names, _config())
        assert result.session_amount == Decimal(40000)
        assert result.total_with_sweep == result.total_stock_amount + result.bees_sweep_amount


# ------------------------------------------------ audit fixes (21-Sep) ---


from typing import ClassVar  # noqa: E402

from engine.plate import priority_from_book  # noqa: E402


def _cfg_cells(cells: dict[str, CellInfo], psu: Decimal = Decimal(15)) -> PlateConfig:
    return PlateConfig(
        session_amount=Decimal(40000), today="2026-09-21",
        psu_weight_pct=psu, cells=cells, bees_price=Decimal(265),
    )


class TestCellSeatHolders:
    """Overlay #5: the cap limits ADD seats; a seat-holder is never self-blocked."""

    IT: ClassVar[dict[str, CellInfo]] = {
        "IT": CellInfo(is_full=False, active_add_count=2, max_adds=2,
                       active_adds=frozenset({"INFY", "TCS"})),
    }

    def test_seat_holder_plates(self) -> None:
        res = build_plate([_name(symbol="INFY", cell="IT", price=Decimal(1000),
                                 low_52w=Decimal(950), trigger_level=Decimal(1040))],
                          _cfg_cells(self.IT))
        assert [e.symbol for e in res.entries] == ["INFY"]

    def test_non_seat_holder_blocked(self) -> None:
        res = build_plate([_name(symbol="WIPRO", cell="IT", price=Decimal(166),
                                 low_52w=Decimal(163), trigger_level=Decimal(190))],
                          _cfg_cells(self.IT))
        assert res.drops[0].reason == PlateDropReason.CELL_FULL
        assert "seat" in res.drops[0].what_would_change

    def test_full_cell_still_lets_seat_holder_through(self) -> None:
        gold = {"GOLD_NBFC": CellInfo(is_full=True, active_add_count=1, max_adds=2,
                                      active_adds=frozenset({"MUTHOOTFIN"}))}
        res = build_plate([_name(symbol="MUTHOOTFIN", cell="GOLD_NBFC",
                                 price=Decimal(2770), low_52w=Decimal(2671),
                                 trigger_level=Decimal(3221))], _cfg_cells(gold))
        assert [e.symbol for e in res.entries] == ["MUTHOOTFIN"]
        assert res.entries[0].mode == Mode.HOCKEY


class TestDropReasonSplit:
    def test_no_trigger_off_the_low(self) -> None:
        res = build_plate([_name(trigger_level=None, price=Decimal(200), low_52w=Decimal(100))],
                          _config())
        d = res.drops[0]
        assert d.reason == PlateDropReason.NO_TRIGGER
        assert "underwrite" in d.what_would_change

    def test_not_eligible_names_the_price_needed(self) -> None:
        res = build_plate([_name(trigger_level=Decimal(85), price=Decimal(120),
                                 low_52w=Decimal(100))], _config())
        d = res.drops[0]
        assert d.reason == PlateDropReason.NOT_ELIGIBLE
        assert "price ≤ 100.00" in d.what_would_change

    def test_first_bite_failed_lists_each_condition(self) -> None:
        res = build_plate([_name(
            trigger_level=Decimal(50), price=Decimal(100), low_52w=Decimal(99),
            qty_held_household=0, valuation_gate_passed=False,
            valuation_gate_detail="FAIL: P/E 40 > fair 14.20; P/B 9 > justified 1.5",
        )], _config())
        d = res.drops[0]
        assert d.reason == PlateDropReason.FIRST_BITE_FAILED
        assert "(c) gate: FAIL: P/E 40" in d.detail
        assert "(d) not owned" in d.detail
        assert "(a)" not in d.detail  # L=1.01% passes

    def test_every_drop_says_what_would_change(self) -> None:
        names = [
            _name(symbol="A", status="SOLD"),
            _name(symbol="B", flag_exit_decided=True),
            _name(symbol="C", trigger_level=None, price=Decimal(200), low_52w=Decimal(100)),
            _name(symbol="D", flag_sovereign=True),
            _name(symbol="E", flag_cyclical=True),
        ]
        res = build_plate(names, _config())
        assert len(res.drops) == 5
        assert all(d.what_would_change for d in res.drops)


class TestHoldingsIntegrity:
    """CLAUDE.md §3: missing holdings for a book-owned name → fail closed."""

    def test_owned_per_book_without_row_is_stale(self) -> None:
        res = build_plate([_name(symbol="RELIANCE", status="HOLD", bucket="OWNED",
                                 owned_per_book=True, qty_held_household=0,
                                 current_weight_pct=None)], _config())
        assert res.drops[0].reason == PlateDropReason.HOLDINGS_STALE
        assert "HOLDINGS_STALE:RELIANCE" in res.rules_fired

    def test_book_p_mult_substitutes_for_missing_row(self) -> None:
        res = build_plate([_name(symbol="TCS", status="ADD", bucket="GBN",
                                 owned_per_book=True, qty_held_household=0,
                                 current_weight_pct=None,
                                 p_mult_book=Decimal("1.0"))], _config())
        assert [e.symbol for e in res.entries] == ["TCS"]
        assert res.entries[0].p_tier == PriorityTier.BUILDING

    def test_new_name_without_row_is_missing_tier(self) -> None:
        res = build_plate([_name(symbol="NEW", status="ADD", bucket="GBL",
                                 owned_per_book=False, qty_held_household=0,
                                 current_weight_pct=None)], _config())
        assert res.entries[0].p_tier == PriorityTier.MISSING


class TestNoAddAndBookPriority:
    def test_hold_only_blocked_on_build_path(self) -> None:
        res = build_plate([_name(symbol="ITC", flag_no_add=True, p_mult_book=Decimal("0.5"),
                                 price=Decimal(266), low_52w=Decimal(255),
                                 trigger_level=Decimal(228))], _config())
        assert res.drops[0].reason == PlateDropReason.NO_ADD_HOLD_ONLY
        assert "first bite" in res.drops[0].what_would_change

    def test_hold_only_still_allows_first_bite(self) -> None:
        res = build_plate([_name(symbol="WIPRO", flag_no_add=True, qty_held_household=146,
                                 price=Decimal(164), low_52w=Decimal("163.3"),
                                 trigger_level=Decimal(120), valuation_gate_passed=True)],
                          _config())
        assert [e.symbol for e in res.entries] == ["WIPRO"]
        assert res.entries[0].is_first_bite and res.entries[0].qty <= 5

    def test_priority_from_book_mapping(self) -> None:
        assert priority_from_book(Decimal(0)) == (PriorityTier.BLOCKED, Decimal(0))
        assert priority_from_book(Decimal("0.5")) == (PriorityTier.MAINTENANCE, Decimal("0.5"))
        assert priority_from_book(Decimal("1.0")) == (PriorityTier.BUILDING, Decimal("1.0"))
        assert priority_from_book(Decimal("1.5")) == (PriorityTier.MISSING, Decimal("1.5"))

    def test_book_blocked_drops_on_build_path(self) -> None:
        res = build_plate([_name(symbol="HDFCBANK", p_mult_book=Decimal(0),
                                 price=Decimal(500), low_52w=Decimal(450),
                                 trigger_level=Decimal(500))], _config())
        assert res.drops[0].reason == PlateDropReason.P_BLOCKED


class TestE6CapsOffConflict:
    """First bite passes quality but is blocked only by cell/P → surface, never decide."""

    def test_cell_blocked_first_bite_is_e6(self) -> None:
        it = {"IT": CellInfo(is_full=False, active_add_count=2, max_adds=2,
                             active_adds=frozenset({"INFY", "TCS"}))}
        res = build_plate([_name(symbol="WIPRO", cell="IT", qty_held_household=146,
                                 price=Decimal(164), low_52w=Decimal("163.3"),
                                 trigger_level=Decimal(120), valuation_gate_passed=True)],
                          _cfg_cells(it))
        d = res.drops[0]
        assert d.reason == PlateDropReason.E6_CAPS_OFF_CONFLICT
        assert "cell cap" in d.detail and "§12b" in d.detail
        assert "E6:CAPS_OFF:WIPRO" in res.rules_fired

    def test_p_blocked_first_bite_is_e6(self) -> None:
        res = build_plate([_name(symbol="HDFCBANK", p_mult_book=Decimal(0), qty_held_household=5,
                                 price=Decimal(700), low_52w=Decimal(700),
                                 trigger_level=Decimal(419), valuation_gate_passed=True,
                                 sector_class="LENDER")], _config())
        assert res.drops[0].reason == PlateDropReason.E6_CAPS_OFF_CONFLICT
        assert "P=0" in res.drops[0].detail

    def test_quality_overlay_is_never_waived_for_first_bite(self) -> None:
        res = build_plate([_name(symbol="BOB", flag_fraud_tail=True, qty_held_household=10,
                                 price=Decimal(100), low_52w=Decimal(100),
                                 trigger_level=Decimal(50), valuation_gate_passed=True)],
                          _config())
        assert res.drops[0].reason == PlateDropReason.FRAUD_TAIL


class TestPlateEntryCarriesOrderData:
    def test_entry_has_price_and_tier(self) -> None:
        res = build_plate([_name()], _config())
        e = res.entries[0]
        assert e.price == Decimal(100)
        assert e.p_tier == PriorityTier.BUILDING


class TestBuildPathFirstBiteIsE6:
    """Wipro 10-Sep precedent: H would build, cell/no-add blocks it, but the name is
    at the low, owned and passes the gate → §12b question, not a plain CELL_FULL."""

    IT: ClassVar[dict[str, CellInfo]] = {
        "IT": CellInfo(is_full=False, active_add_count=2, max_adds=2,
                       active_adds=frozenset({"INFY", "TCS"})),
    }

    def test_cell_blocked_at_low_owned_gate_pass_is_e6(self) -> None:
        res = build_plate([_name(symbol="WIPRO", cell="IT", qty_held_household=170,
                                 price=Decimal("164.55"), low_52w=Decimal("163.30"),
                                 trigger_level=Decimal(190), valuation_gate_passed=True)],
                          _cfg_cells(self.IT))
        d = res.drops[0]
        assert d.reason == PlateDropReason.E6_CAPS_OFF_CONFLICT
        assert "cell cap" in d.detail and "gate PASS" in d.detail

    def test_no_add_at_low_owned_gate_pass_is_e6(self) -> None:
        res = build_plate([_name(symbol="ITC", flag_no_add=True, qty_held_household=438,
                                 price=Decimal(256), low_52w=Decimal("255.5"),
                                 trigger_level=Decimal(228), valuation_gate_passed=True)],
                          _config())
        assert res.drops[0].reason == PlateDropReason.E6_CAPS_OFF_CONFLICT
        assert "hold-only" in res.drops[0].detail

    def test_cell_blocked_but_gate_fails_stays_cell_full(self) -> None:
        res = build_plate([_name(symbol="WIPRO", cell="IT", qty_held_household=170,
                                 price=Decimal("164.55"), low_52w=Decimal("163.30"),
                                 trigger_level=Decimal(190), valuation_gate_passed=False)],
                          _cfg_cells(self.IT))
        assert res.drops[0].reason == PlateDropReason.CELL_FULL

    def test_cell_blocked_off_the_low_stays_cell_full(self) -> None:
        res = build_plate([_name(symbol="WIPRO", cell="IT", qty_held_household=170,
                                 price=Decimal(180), low_52w=Decimal("163.30"),
                                 trigger_level=Decimal(190), valuation_gate_passed=True)],
                          _cfg_cells(self.IT))
        assert res.drops[0].reason == PlateDropReason.CELL_FULL


class TestReviewFirst:
    """Praveen 26-Sep-2026: a don't-buy name that passes every gate is raised with its
    register reason for analysis — never bought silently, never dropped silently."""

    def test_withdrawn_first_bite_is_raised_with_reason(self) -> None:
        from tests.acceptance.test_behavioral_regression import _n, _plate
        c = _n("CANBK", "107", "107", sector="LENDER", status="WATCH", bucket="WITHDRAWN",
               cell="LENDING_BANKS", held=17, gate=True,
               register_note="Watch Q2 provisions; PSU cap")
        r = _plate(c)
        assert r.entries == []
        d = next(d for d in r.drops if d.symbol == "CANBK")
        assert d.reason == PlateDropReason.REVIEW_FIRST
        assert "Watch Q2 provisions" in d.detail and "Praveen approves" in d.what_would_change

    def test_same_name_as_owned_bucket_plates(self) -> None:
        from tests.acceptance.test_behavioral_regression import _n, _plate
        c = _n("CANBK", "107", "107", sector="LENDER", status="WATCH", bucket="OWNED",
               cell="LENDING_BANKS", held=17, gate=True)
        assert [e.symbol for e in _plate(c).entries] == ["CANBK"]


class TestResultsWeekPause:
    """tiffin v6 §procedure step 6: results within 5 calendar days → hold, unless
    Praveen opts in ('event risk, your call')."""

    def _run(self, next_date: str | None, opt_in: frozenset[str] = frozenset()):  # type: ignore[no-untyped-def]
        from dataclasses import replace

        from tests.acceptance.test_behavioral_regression import CELLS, _n
        n = replace(_n("INFY", "1000", "980", "1100", sector="IT_SERVICES", cell=None,
                       held=10), next_result_date=next_date)
        cfg = PlateConfig(session_amount=Decimal(10000), today="2026-10-18",
                          psu_weight_pct=Decimal(10), cells=CELLS, bees_price=Decimal(266),
                          event_hold_days=5, event_opt_in=opt_in)
        return build_plate([n], cfg)

    def test_results_in_five_days_is_held(self) -> None:
        r = self._run("2026-10-23")
        assert r.entries == [] and r.drops[0].reason == PlateDropReason.EVENT_HOLD
        assert "5 day(s)" in r.drops[0].detail

    def test_results_today_is_held(self) -> None:
        assert self._run("2026-10-18").drops[0].reason == PlateDropReason.EVENT_HOLD

    def test_six_days_out_is_bought(self) -> None:
        assert [e.symbol for e in self._run("2026-10-24").entries] == ["INFY"]

    def test_past_or_unknown_date_is_bought(self) -> None:
        assert self._run("2026-07-23").entries and self._run(None).entries

    def test_opt_in_buys_anyway(self) -> None:
        assert self._run("2026-10-20", frozenset({"INFY"})).entries


class TestCapsOffWaiver:
    """D6/D44 via a one-session register waiver (D70 Wipro, 28-Sep): lifts cell cap,
    hold-only and P=0 — never a quality overlay, valuation gate or ban."""

    def _wipro(self, **kw):  # type: ignore[no-untyped-def]
        from tests.acceptance.test_behavioral_regression import _n
        return _n("WIPRO", "164.02", "161.66", "190", sector="IT_SERVICES", status="HOLD",
                  bucket="OWNED", cell="IT", held=185, gate=True, flag_no_add=True, **kw)

    def _cfg(self, waived: frozenset[str]) -> PlateConfig:
        from tests.acceptance.test_behavioral_regression import CELLS
        return PlateConfig(session_amount=Decimal(10000), today="2026-09-28",
                           psu_weight_pct=Decimal(10), cells=CELLS, bees_price=Decimal(264),
                           caps_off_waived=waived)

    def test_without_waiver_it_is_the_e6_question(self) -> None:
        r = build_plate([self._wipro()], self._cfg(frozenset()))
        assert r.entries == [] and r.drops[0].reason == PlateDropReason.E6_CAPS_OFF_CONFLICT

    def test_waiver_plates_it_with_the_normal_clamp(self) -> None:
        r = build_plate([self._wipro()], self._cfg(frozenset({"WIPRO"})))
        assert [e.symbol for e in r.entries] == ["WIPRO"]
        assert 1 <= r.entries[0].qty <= 10
        assert "CAPS_OFF_WAIVED:WIPRO" in r.rules_fired

    def test_waiver_never_lifts_a_quality_overlay(self) -> None:
        r = build_plate([self._wipro(flag_probe_open=True)], self._cfg(frozenset({"WIPRO"})))
        assert r.entries == [] and r.drops[0].reason == PlateDropReason.PROBE_OPEN
