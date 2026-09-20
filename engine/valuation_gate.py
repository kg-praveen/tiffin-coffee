"""engine/valuation_gate.py — pure valuation gate functions for the OSEP engine.

Spec: osep v7 §G (gate table), tiffin-coffee v6 §first-bite (c) (sector-aware gate).
E1: pure code, no I/O. E2: all inputs are Decimal from policy/Stamped sources.
E7: each gate is defined once here; every other module calls it.
E9: fail-closed — missing data = gate FAILS.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

_Q2 = Decimal("0.01")


@dataclass(frozen=True)
class ValuationGateInput:
    """All data the valuation gate needs for one name.

    Spec: osep v7 §G — sector-appropriate gate inputs.
    """

    symbol: str
    sector_class: str | None
    pe_trailing: Decimal | None
    pb_ratio: Decimal | None
    roe_pct: Decimal | None
    gsec_yield_pct: Decimal
    cost_of_equity_spread: Decimal
    growth_g_pct: Decimal


@dataclass(frozen=True)
class ValuationGateResult:
    """Result of a valuation gate check.

    Spec: tiffin-coffee v6 §first-bite (c). E8: detail explains WHY.
    """

    passed: bool
    gate_name: str
    detail: str
    fair_pe: Decimal | None
    justified_pb: Decimal | None


def compute_fair_pe(gsec_yield_pct: Decimal) -> Decimal:
    """Fair P/E = 1 / GoI yield. Spec: osep v7 §MoS anchor (GoI yield ladder).

    At 7.04% → 14.20x. Returns Decimal(0) if yield <= 0 (E9 fail-closed).
    """
    if gsec_yield_pct <= 0:
        return Decimal(0)
    return (Decimal(100) / gsec_yield_pct).quantize(_Q2, rounding=ROUND_HALF_UP)


def compute_justified_pb(
    roe_pct: Decimal | None,
    cost_of_equity_pct: Decimal,
    growth_g_pct: Decimal,
) -> Decimal:
    """Justified P/B = (ROE - g) / (r - g). Spec: osep v7 §BANK justified P/B.

    Returns Decimal(0) when ROE is None, ROE <= g, or r <= g (E9 fail-closed).
    Never returns a negative value.
    """
    if roe_pct is None:
        return Decimal(0)
    denominator = cost_of_equity_pct - growth_g_pct
    if denominator <= 0:
        return Decimal(0)
    numerator = roe_pct - growth_g_pct
    if numerator <= 0:
        return Decimal(0)
    return (numerator / denominator).quantize(_Q2, rounding=ROUND_HALF_UP)


def gate_default_pe_ladder(
    pe_trailing: Decimal | None,
    pb_ratio: Decimal | None,
    fair_pe: Decimal,
    justified_pb: Decimal | None,
) -> ValuationGateResult:
    """DEFAULT sector gate: pass if P/E <= fair OR P/B <= justified.

    Spec: tiffin-coffee v6 §first-bite (c) — DEFAULT sectors.
    """
    pe_pass = pe_trailing is not None and fair_pe > 0 and pe_trailing <= fair_pe
    pb_pass = (
        pb_ratio is not None
        and justified_pb is not None
        and justified_pb > 0
        and pb_ratio <= justified_pb
    )

    if pe_pass and pb_pass:
        detail = (
            f"PASS: P/E {pe_trailing} <= fair {fair_pe} "
            f"AND P/B {pb_ratio} <= justified {justified_pb}"
        )
    elif pe_pass:
        detail = f"PASS: P/E {pe_trailing} <= fair {fair_pe}"
        if pb_ratio is not None and justified_pb is not None:
            detail += f" (P/B {pb_ratio} > justified {justified_pb})"
    elif pb_pass:
        detail = f"PASS: P/B {pb_ratio} <= justified {justified_pb}"
        if pe_trailing is not None:
            detail += f" (P/E {pe_trailing} > fair {fair_pe})"
    else:
        parts: list[str] = []
        if pe_trailing is None:
            parts.append("P/E unavailable")
        else:
            parts.append(f"P/E {pe_trailing} > fair {fair_pe}")
        if pb_ratio is None:
            parts.append("P/B unavailable")
        elif justified_pb is None or justified_pb <= 0:
            parts.append("justified P/B unavailable")
        else:
            parts.append(f"P/B {pb_ratio} > justified {justified_pb}")
        detail = f"FAIL: {'; '.join(parts)} (E9 fail-closed)"

    return ValuationGateResult(
        passed=pe_pass or pb_pass,
        gate_name="gate_default_pe_ladder",
        detail=detail,
        fair_pe=fair_pe,
        justified_pb=justified_pb,
    )


def gate_lender_justified_pb(
    pb_ratio: Decimal | None,
    justified_pb: Decimal,
) -> ValuationGateResult:
    """LENDER gate: pass if P/B <= justified P/B. P/E is NEVER a gate.

    Spec: osep v7 §G-LENDER, tiffin-coffee v6 §first-bite (c) defect-2 fix.
    """
    if pb_ratio is None:
        return ValuationGateResult(
            passed=False,
            gate_name="gate_lender_justified_pb",
            detail="FAIL: P/B unavailable (E9 fail-closed)",
            fair_pe=None,
            justified_pb=justified_pb,
        )
    if justified_pb <= 0:
        return ValuationGateResult(
            passed=False,
            gate_name="gate_lender_justified_pb",
            detail="FAIL: justified P/B unavailable or zero (E9 fail-closed)",
            fair_pe=None,
            justified_pb=justified_pb,
        )
    passed = pb_ratio <= justified_pb
    if passed:
        detail = f"PASS: P/B {pb_ratio} <= justified {justified_pb}"
    else:
        detail = f"FAIL: P/B {pb_ratio} > justified {justified_pb}"
    return ValuationGateResult(
        passed=passed,
        gate_name="gate_lender_justified_pb",
        detail=detail,
        fair_pe=None,
        justified_pb=justified_pb,
    )


def gate_non_earning() -> ValuationGateResult:
    """NON_EARNING gate: always False. Spec: osep v7 §G-NON_EARNING."""
    return ValuationGateResult(
        passed=False,
        gate_name="gate_non_earning",
        detail="NON_EARNING: no valuation gate; thermostat governs",
        fair_pe=None,
        justified_pb=None,
    )


def gate_cyclical() -> ValuationGateResult:
    """CYCLICAL gate: always False. Spec: osep v7 §G-CYCLICAL.

    A low trailing P/E on a cyclical is a SELL signal, not a buy signal.
    Through-cycle test pending (Book Ch.6 transcription).
    """
    return ValuationGateResult(
        passed=False,
        gate_name="gate_cyclical",
        detail="CYCLICAL: through-cycle test pending (osep G-CYCLICAL)",
        fair_pe=None,
        justified_pb=None,
    )


_ALWAYS_FALSE_SECTORS = frozenset({"NON_EARNING", "INDEX_ETF", "CYCLICAL"})
_LENDER_SECTOR = "LENDER"


def compute_valuation_gate(inp: ValuationGateInput) -> ValuationGateResult:
    """Dispatch to the sector-appropriate gate. Spec: osep v7 §G + §SC.

    Routing:
      LENDER → gate_lender_justified_pb
      NON_EARNING → gate_non_earning (always False)
      CYCLICAL → gate_cyclical (always False)
      INDEX_ETF → always False (ballast, not analysed)
      Everything else (DEFAULT, IT_SERVICES, PHARMA, etc.) → gate_default_pe_ladder
      None (unclassified) → gate_default_pe_ladder (strictest per E4)
    """
    sector = inp.sector_class

    if sector == "NON_EARNING":
        return gate_non_earning()
    if sector == "CYCLICAL":
        return gate_cyclical()
    if sector == "INDEX_ETF":
        return ValuationGateResult(
            passed=False,
            gate_name="gate_index_etf",
            detail="INDEX_ETF: ballast, not analysed",
            fair_pe=None,
            justified_pb=None,
        )

    if inp.gsec_yield_pct <= 0:
        return ValuationGateResult(
            passed=False,
            gate_name="gate_fail_closed",
            detail="FAIL: GoI yield unavailable or non-positive (E9 fail-closed)",
            fair_pe=None,
            justified_pb=None,
        )

    r_pct = inp.gsec_yield_pct + inp.cost_of_equity_spread
    fair_pe = compute_fair_pe(inp.gsec_yield_pct)
    justified_pb = compute_justified_pb(inp.roe_pct, r_pct, inp.growth_g_pct)

    if sector == _LENDER_SECTOR:
        return gate_lender_justified_pb(inp.pb_ratio, justified_pb)

    return gate_default_pe_ladder(
        inp.pe_trailing, inp.pb_ratio, fair_pe, justified_pb,
    )
