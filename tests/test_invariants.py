"""tests/test_invariants.py — engine/invariants.py catches what it claims to catch.

A law checker that always passes is worthless, so every invariant is shown both
holding on the golden 20-Sep plate AND firing on a deliberately corrupted copy.
"""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from engine.invariants import (
    Severity,
    check_plate,
    find_budget_and_breadth,
    find_register_zero_bucket,
    inv_accounting,
    inv_drops_explained,
    inv_eligibility,
    inv_fail_closed,
    inv_gate_monotone,
    inv_no_banned_entry,
    inv_priced_from_input,
    inv_qty_clamp,
    inv_totals,
)
from engine.plate import PlateConfig, PlateResult, build_plate
from tests.golden.test_golden_20sep2026 import CELLS, NAMES, PSU_WEIGHT_PHANTOM, TODAY


@pytest.fixture(scope="module")
def cfg() -> PlateConfig:
    return PlateConfig(session_amount=Decimal(40000), today=TODAY,
                       psu_weight_pct=PSU_WEIGHT_PHANTOM, cells=CELLS,
                       bees_price=Decimal("266.06"))


@pytest.fixture(scope="module")
def plate(cfg: PlateConfig) -> PlateResult:
    return build_plate(NAMES, cfg)


def _names(checks: list, inv: str) -> set[str]:  # type: ignore[type-arg]
    return {c.symbol for c in checks if c.invariant == inv}


class TestGoldenPlateObeysEveryLaw:
    def test_no_violations(self, plate: PlateResult, cfg: PlateConfig) -> None:
        checks = check_plate(NAMES, cfg, plate, 8, 15)
        assert [c for c in checks if c.severity == Severity.VIOLATION] == []

    def test_breadth_is_only_a_finding(self, plate: PlateResult, cfg: PlateConfig) -> None:
        checks = check_plate(NAMES, cfg, plate, 8, 15)
        assert {c.invariant for c in checks} == {"BREADTH"}   # 7 names < 8
        assert all(c.severity == Severity.FINDING for c in checks)


class TestEachInvariantFires:
    def test_accounting_catches_a_lost_name(self, plate: PlateResult) -> None:
        lost = replace(plate, drops=[d for d in plate.drops if d.symbol != "HDFCBANK"])
        assert _names(inv_accounting(NAMES, lost), "ACCOUNTING") == {"HDFCBANK"}

    def test_accounting_catches_a_double_count(self, plate: PlateResult) -> None:
        twice = replace(plate, drops=[*plate.drops, plate.drops[0]])
        assert plate.drops[0].symbol in _names(inv_accounting(NAMES, twice), "ACCOUNTING")

    def test_unexplained_drop(self, plate: PlateResult) -> None:
        bad = replace(plate, drops=[replace(plate.drops[0], what_would_change=" ")])
        assert inv_drops_explained(bad)[0].invariant == "DROP_EXPLAINED"

    def test_qty_eleven(self, plate: PlateResult, cfg: PlateConfig) -> None:
        e = replace(plate.entries[0], qty=11)
        assert inv_qty_clamp(replace(plate, entries=[e]), cfg)[0].symbol == e.symbol

    def test_first_bite_over_five(self, plate: PlateResult, cfg: PlateConfig) -> None:
        e = replace(plate.entries[0], qty=6, is_first_bite=True)
        assert inv_qty_clamp(replace(plate, entries=[e]), cfg)

    def test_price_not_from_input(self, plate: PlateResult) -> None:
        e = replace(plate.entries[0], price=plate.entries[0].price + 1)
        assert inv_priced_from_input(NAMES, replace(plate, entries=[e]))

    def test_exit_list_name_on_plate(self, plate: PlateResult, cfg: PlateConfig) -> None:
        sym = plate.entries[0].symbol
        names = [replace(n, flag_exit_decided=True) if n.symbol == sym else n for n in NAMES]
        assert _names(inv_no_banned_entry(names, plate, cfg), "NO_BANNED_ENTRY") == {sym}

    def test_psu_name_over_cap(self, plate: PlateResult, cfg: PlateConfig) -> None:
        over = replace(cfg, psu_weight_pct=Decimal(26))
        assert "NTPC" in _names(inv_no_banned_entry(NAMES, plate, over), "NO_BANNED_ENTRY")

    def test_hdfc_law_lender_bite_on_failed_gate(self, plate: PlateResult,
                                                 cfg: PlateConfig) -> None:
        """CLAUDE.md §5 golden law: HDFC at the low with P/B above justified → qty 0."""
        hdfc = next(n for n in NAMES if n.symbol == "HDFCBANK")
        bite = replace(plate.entries[0], symbol="HDFCBANK", price=hdfc.price,
                       qty=5, is_first_bite=True)
        checks = inv_eligibility(NAMES, replace(plate, entries=[bite]), cfg)
        assert checks and "sector valuation gate failed" in checks[0].detail

    def test_totals_tampered(self, plate: PlateResult) -> None:
        assert inv_totals(replace(plate, total_stock_amount=Decimal(1)))

    def test_over_session_is_finding(self, plate: PlateResult) -> None:
        small = replace(plate, session_amount=Decimal(1000))
        f = find_budget_and_breadth(small, 1, 99)
        assert [c.invariant for c in f] == ["OVER_SESSION"]
        assert f[0].severity == Severity.FINDING

    def test_withdrawn_bucket_is_finding(self, plate: PlateResult) -> None:
        sym = plate.entries[0].symbol
        names = [replace(n, bucket="WITHDRAWN") if n.symbol == sym else n for n in NAMES]
        f = find_register_zero_bucket(names, plate)
        assert [(c.symbol, c.severity) for c in f] == [(sym, Severity.FINDING)]
        assert find_register_zero_bucket(NAMES, plate) == []

    def test_fail_closed(self, plate: PlateResult) -> None:
        assert inv_fail_closed(plate)
        assert inv_fail_closed(replace(plate, entries=[], bees_sweep_qty=0)) == []

    def test_gate_monotone(self, plate: PlateResult) -> None:
        bite = replace(plate.entries[0], is_first_bite=True)
        tighter = replace(plate, entries=[bite])
        assert inv_gate_monotone(plate, tighter)[0].symbol == bite.symbol
        assert inv_gate_monotone(tighter, tighter) == []
