"""Golden day 10-Sep-2026 — CLAUDE.md §5.

HDFC Bank at a fresh 52-week low with P/B above justified must produce quantity 0
(lender gate; tiffin-coffee v6 §first-bite (c)). The old OR-gate let P/E 13.1x
rescue it and plated 5 shares — the control exception that motivated defect-2.
No network: every input is a recorded stamp.
"""
from __future__ import annotations

from decimal import Decimal

from engine.plate import NameInput, PlateConfig, PlateDropReason, build_plate
from engine.valuation_gate import ValuationGateInput, compute_valuation_gate

GOI_10SEP = Decimal("7.04")       # ledger D54 anchor
COE_SPREAD = Decimal("6.09")      # policy cost_of_equity_spread_over_gsec
GROWTH_G = Decimal(5)             # policy growth_g


def _hdfc_gate(pe: Decimal | None) -> tuple[bool, str]:
    r = compute_valuation_gate(ValuationGateInput(
        symbol="HDFCBANK", sector_class="LENDER",
        pe_trailing=pe, pb_ratio=Decimal("1.8"), roe_pct=Decimal("13.8"),
        gsec_yield_pct=GOI_10SEP, cost_of_equity_spread=COE_SPREAD, growth_g_pct=GROWTH_G,
    ))
    return r.passed, r.detail


def _hdfc_input(gate_passed: bool, gate_detail: str) -> NameInput:
    return NameInput(
        symbol="HDFCBANK", name="HDFC Bank",
        price=Decimal(712), low_52w=Decimal(712),      # fresh 52-week low, L = 0.0%
        trigger_level=Decimal(419),                     # post-bonus trigger (D47)
        sector_class="LENDER", status="HOLD", bucket="OWNED", cell="LENDING_BANKS",
        flag_sovereign=False, flag_psu=False, flag_cyclical=False,
        flag_probe_open=False, flag_fraud_tail=False, flag_exit_decided=False,
        p5_status="AGREE_NOTE", p5_note_ref="ledger §8 05-Sep", decay_expiry=None,
        qty_held_household=5, current_weight_pct=Decimal(3),
        valuation_gate_passed=gate_passed, valuation_gate_detail=gate_detail,
        owned_per_book=True,
    )


def _config() -> PlateConfig:
    return PlateConfig(session_amount=Decimal(35000), today="2026-09-10",
                       psu_weight_pct=Decimal(15), cells={}, bees_price=Decimal(265))


class TestGoldenHdfc10Sep:
    def test_lender_gate_fails_on_pb(self) -> None:
        passed, detail = _hdfc_gate(pe=Decimal("13.1"))
        assert passed is False
        assert "1.8" in detail and "1.08" in detail

    def test_cheap_pe_cannot_rescue_a_lender(self) -> None:
        """v6 defect-2: P/E is not even an input to the lender gate."""
        with_pe, _ = _hdfc_gate(pe=Decimal("13.1"))
        without_pe, _ = _hdfc_gate(pe=None)
        assert with_pe is without_pe is False

    def test_plate_quantity_is_zero(self) -> None:
        passed, detail = _hdfc_gate(pe=Decimal("13.1"))
        result = build_plate([_hdfc_input(passed, detail)], _config())
        assert result.entries == []
        drop = result.drops[0]
        assert drop.reason == PlateDropReason.FIRST_BITE_FAILED
        assert drop.l_pct == Decimal("0.00")
        assert "(c) gate" in drop.detail and "1.08" in drop.detail
        assert "(a)" not in drop.detail and "(d)" not in drop.detail

    def test_deterministic(self) -> None:
        passed, detail = _hdfc_gate(pe=Decimal("13.1"))
        a = build_plate([_hdfc_input(passed, detail)], _config())
        b = build_plate([_hdfc_input(passed, detail)], _config())
        assert a == b
