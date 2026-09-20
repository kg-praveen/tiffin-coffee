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
    assign_tilts,
    build_plate,
    check_first_bite,
    check_overlays,
    classify_low_band,
    classify_mode,
    classify_priority,
    compute_bees_sweep,
    compute_h,
    compute_l,
    compute_qty,
    compute_score,
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
        reason = check_overlays(_name(flag_cyclical=True), _config())
        assert reason == PlateDropReason.PEAK_CYCLE

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


class TestTilts:
    def test_three_items_get_three_tilts(self) -> None:
        tilts = assign_tilts([Decimal(5), Decimal(3), Decimal(1)])
        assert tilts == [Decimal("1.25"), Decimal("1.0"), Decimal("0.75")]

    def test_single_item_gets_top_tilt(self) -> None:
        tilts = assign_tilts([Decimal(5)])
        assert tilts == [Decimal("1.25")]

    def test_empty_returns_empty(self) -> None:
        assert assign_tilts([]) == []


class TestComputeQty:
    def test_normal_clamp(self) -> None:
        assert compute_qty(Decimal(5000), Decimal(500), 1, 10) == 10

    def test_expensive_stock_clamps_to_1(self) -> None:
        assert compute_qty(Decimal(3000), Decimal(5000), 1, 10) == 1

    def test_cheap_stock_clamps_to_10(self) -> None:
        assert compute_qty(Decimal(50000), Decimal(100), 1, 10) == 10

    def test_first_bite_clamps_to_5(self) -> None:
        assert compute_qty(Decimal(50000), Decimal(100), 1, 5) == 5


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
        assert result.drops[0].reason == PlateDropReason.FASTING_NO_FIRST_BITE

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
