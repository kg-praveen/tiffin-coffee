"""tests/test_engine_valuation_gate.py — pure-function tests for engine/valuation_gate.py.

Spec: osep v7 §G (gate table), tiffin-coffee v6 §first-bite (c). No network, no DB.
"""
from __future__ import annotations

from decimal import Decimal

from engine.valuation_gate import (
    ValuationGateInput,
    compute_fair_pe,
    compute_justified_pb,
    compute_valuation_gate,
    gate_cyclical,
    gate_default_pe_ladder,
    gate_lender_justified_pb,
    gate_non_earning,
)

GOI = Decimal("7.04")
SPREAD = Decimal("6.09")
G = Decimal(5)


def _inp(
    symbol: str = "TEST",
    sector_class: str | None = "DEFAULT",
    pe: Decimal | None = Decimal(12),
    pb: Decimal | None = Decimal("1.5"),
    roe: Decimal | None = Decimal(18),
    gsec: Decimal = GOI,
    spread: Decimal = SPREAD,
    g: Decimal = G,
) -> ValuationGateInput:
    return ValuationGateInput(
        symbol=symbol,
        sector_class=sector_class,
        pe_trailing=pe,
        pb_ratio=pb,
        roe_pct=roe,
        gsec_yield_pct=gsec,
        cost_of_equity_spread=spread,
        growth_g_pct=g,
    )


# --------------------------------------------------- compute_fair_pe ---


class TestComputeFairPe:
    def test_at_7_04_pct(self) -> None:
        assert compute_fair_pe(Decimal("7.04")) == Decimal("14.20")

    def test_at_6_82_pct(self) -> None:
        assert compute_fair_pe(Decimal("6.82")) == Decimal("14.66")

    def test_at_10_pct(self) -> None:
        assert compute_fair_pe(Decimal(10)) == Decimal(10)

    def test_zero_yield_returns_zero(self) -> None:
        assert compute_fair_pe(Decimal(0)) == Decimal(0)

    def test_negative_yield_returns_zero(self) -> None:
        assert compute_fair_pe(Decimal(-1)) == Decimal(0)


# ----------------------------------------------- compute_justified_pb ---


class TestComputeJustifiedPb:
    def test_sbi_roe_18(self) -> None:
        r = Decimal("13.13")
        result = compute_justified_pb(Decimal(18), r, Decimal(5))
        assert result == Decimal("1.60")

    def test_hdfc_roe_13_8(self) -> None:
        r = Decimal("13.13")
        result = compute_justified_pb(Decimal("13.8"), r, Decimal(5))
        assert result == Decimal("1.08")

    def test_muthoot_roe_31(self) -> None:
        r = Decimal("13.13")
        result = compute_justified_pb(Decimal(31), r, Decimal(5))
        assert result == Decimal("3.20")

    def test_roe_none_returns_zero(self) -> None:
        assert compute_justified_pb(None, Decimal(13), Decimal(5)) == Decimal(0)

    def test_roe_below_g_returns_zero(self) -> None:
        assert compute_justified_pb(Decimal("1.8"), Decimal(13), Decimal(5)) == Decimal(0)

    def test_roe_equals_g_returns_zero(self) -> None:
        assert compute_justified_pb(Decimal(5), Decimal(13), Decimal(5)) == Decimal(0)

    def test_r_equals_g_returns_zero(self) -> None:
        assert compute_justified_pb(Decimal(18), Decimal(5), Decimal(5)) == Decimal(0)

    def test_r_below_g_returns_zero(self) -> None:
        assert compute_justified_pb(Decimal(18), Decimal(3), Decimal(5)) == Decimal(0)

    def test_negative_roe_returns_zero(self) -> None:
        assert compute_justified_pb(Decimal(-5), Decimal(13), Decimal(5)) == Decimal(0)

    def test_roe_equals_r(self) -> None:
        result = compute_justified_pb(Decimal("13.13"), Decimal("13.13"), Decimal(5))
        assert result == Decimal("1.00")


# ----------------------------------------- gate_default_pe_ladder ---


class TestGateDefaultPeLadder:
    def test_pe_below_fair_passes(self) -> None:
        result = gate_default_pe_ladder(
            Decimal(12), Decimal("2.0"), Decimal("14.20"), Decimal("1.60"),
        )
        assert result.passed is True
        assert "P/E 12" in result.detail

    def test_pb_below_justified_passes(self) -> None:
        result = gate_default_pe_ladder(
            Decimal(20), Decimal("1.2"), Decimal("14.20"), Decimal("1.60"),
        )
        assert result.passed is True
        assert "P/B 1.2" in result.detail

    def test_both_pass(self) -> None:
        result = gate_default_pe_ladder(
            Decimal(12), Decimal("1.2"), Decimal("14.20"), Decimal("1.60"),
        )
        assert result.passed is True
        assert "AND" in result.detail

    def test_both_fail(self) -> None:
        result = gate_default_pe_ladder(
            Decimal(25), Decimal("3.0"), Decimal("14.20"), Decimal("1.60"),
        )
        assert result.passed is False
        assert "FAIL" in result.detail

    def test_pe_none_pb_below_passes(self) -> None:
        result = gate_default_pe_ladder(
            None, Decimal("1.2"), Decimal("14.20"), Decimal("1.60"),
        )
        assert result.passed is True

    def test_pe_none_pb_none_fails(self) -> None:
        result = gate_default_pe_ladder(
            None, None, Decimal("14.20"), Decimal("1.60"),
        )
        assert result.passed is False
        assert "unavailable" in result.detail

    def test_pe_none_pb_above_fails(self) -> None:
        result = gate_default_pe_ladder(
            None, Decimal("3.0"), Decimal("14.20"), Decimal("1.60"),
        )
        assert result.passed is False

    def test_fair_pe_zero_fails(self) -> None:
        result = gate_default_pe_ladder(
            Decimal(5), Decimal("1.0"), Decimal(0), Decimal("1.60"),
        )
        assert result.passed is True  # P/B still passes

    def test_justified_pb_zero_pe_passes(self) -> None:
        result = gate_default_pe_ladder(
            Decimal(12), Decimal("2.0"), Decimal("14.20"), Decimal(0),
        )
        assert result.passed is True  # P/E passes

    def test_both_unavailable_justified_zero(self) -> None:
        result = gate_default_pe_ladder(
            None, Decimal("1.0"), Decimal("14.20"), Decimal(0),
        )
        assert result.passed is False


# ---------------------------------------- gate_lender_justified_pb ---


class TestGateLenderJustifiedPb:
    def test_sbi_passes(self) -> None:
        result = gate_lender_justified_pb(Decimal("1.55"), Decimal("1.60"))
        assert result.passed is True
        assert "PASS" in result.detail

    def test_hdfc_fails(self) -> None:
        result = gate_lender_justified_pb(Decimal("1.80"), Decimal("1.08"))
        assert result.passed is False
        assert "1.80" in result.detail
        assert "1.08" in result.detail

    def test_pb_none_fails(self) -> None:
        result = gate_lender_justified_pb(None, Decimal("1.60"))
        assert result.passed is False
        assert "unavailable" in result.detail

    def test_justified_zero_fails(self) -> None:
        result = gate_lender_justified_pb(Decimal("0.8"), Decimal(0))
        assert result.passed is False
        assert "zero" in result.detail

    def test_pb_at_justified_passes(self) -> None:
        result = gate_lender_justified_pb(Decimal("1.60"), Decimal("1.60"))
        assert result.passed is True


# ----------------------------------------- gate_non_earning/cyclical ---


class TestAlwaysFalseGates:
    def test_non_earning_always_false(self) -> None:
        result = gate_non_earning()
        assert result.passed is False
        assert "thermostat" in result.detail

    def test_cyclical_always_false(self) -> None:
        result = gate_cyclical()
        assert result.passed is False
        assert "through-cycle" in result.detail


# ------------------------------------------ compute_valuation_gate ---


class TestComputeValuationGate:
    def test_lender_dispatches_to_pb_gate(self) -> None:
        result = compute_valuation_gate(_inp(
            sector_class="LENDER", pb=Decimal("1.55"), roe=Decimal(18),
        ))
        assert result.gate_name == "gate_lender_justified_pb"
        assert result.passed is True

    def test_lender_hdfc_fails(self) -> None:
        result = compute_valuation_gate(_inp(
            symbol="HDFCBANK", sector_class="LENDER",
            pe=Decimal("13.1"), pb=Decimal("1.80"), roe=Decimal("13.8"),
        ))
        assert result.passed is False
        assert result.gate_name == "gate_lender_justified_pb"
        assert result.justified_pb == Decimal("1.08")

    def test_default_dispatches_to_pe_ladder(self) -> None:
        result = compute_valuation_gate(_inp(sector_class="DEFAULT", pe=Decimal(12)))
        assert result.gate_name == "gate_default_pe_ladder"
        assert result.passed is True

    def test_it_services_uses_default_gate(self) -> None:
        result = compute_valuation_gate(_inp(sector_class="IT_SERVICES", pe=Decimal(12)))
        assert result.gate_name == "gate_default_pe_ladder"

    def test_pharma_uses_default_gate(self) -> None:
        result = compute_valuation_gate(_inp(sector_class="PHARMA", pe=Decimal(12)))
        assert result.gate_name == "gate_default_pe_ladder"

    def test_fmcg_uses_default_gate(self) -> None:
        result = compute_valuation_gate(_inp(sector_class="FMCG", pe=Decimal(12)))
        assert result.gate_name == "gate_default_pe_ladder"

    def test_auto_oem_uses_default_gate(self) -> None:
        result = compute_valuation_gate(_inp(sector_class="AUTO_OEM", pe=Decimal(12)))
        assert result.gate_name == "gate_default_pe_ladder"

    def test_insurer_uses_default_gate(self) -> None:
        result = compute_valuation_gate(_inp(sector_class="INSURER", pe=Decimal(12)))
        assert result.gate_name == "gate_default_pe_ladder"

    def test_regulated_uses_default_gate(self) -> None:
        result = compute_valuation_gate(_inp(sector_class="REGULATED", pe=Decimal(12)))
        assert result.gate_name == "gate_default_pe_ladder"

    def test_non_earning_always_false(self) -> None:
        result = compute_valuation_gate(_inp(sector_class="NON_EARNING"))
        assert result.passed is False
        assert result.gate_name == "gate_non_earning"

    def test_cyclical_always_false(self) -> None:
        result = compute_valuation_gate(_inp(sector_class="CYCLICAL"))
        assert result.passed is False
        assert result.gate_name == "gate_cyclical"

    def test_index_etf_always_false(self) -> None:
        result = compute_valuation_gate(_inp(sector_class="INDEX_ETF"))
        assert result.passed is False
        assert result.gate_name == "gate_index_etf"

    def test_none_sector_uses_default(self) -> None:
        result = compute_valuation_gate(_inp(sector_class=None, pe=Decimal(12)))
        assert result.gate_name == "gate_default_pe_ladder"

    def test_fail_closed_on_zero_gsec(self) -> None:
        result = compute_valuation_gate(_inp(gsec=Decimal(0), pe=Decimal(5)))
        assert result.passed is False

    def test_result_carries_fair_pe(self) -> None:
        result = compute_valuation_gate(_inp(sector_class="DEFAULT"))
        assert result.fair_pe == Decimal("14.20")

    def test_lender_result_carries_justified_pb(self) -> None:
        result = compute_valuation_gate(_inp(
            sector_class="LENDER", roe=Decimal(18), pb=Decimal("1.55"),
        ))
        assert result.justified_pb == Decimal("1.60")
