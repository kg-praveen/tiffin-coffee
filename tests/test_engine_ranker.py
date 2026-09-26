"""tests/test_engine_ranker.py — engine/ranker.py (UC3) on synthetic inputs, no I/O.

The ranker never changes a rule: every variant is a real build_plate run on a choice
the spec hands to a human (ticket inside the band, trim the bottom-scoring names), and
any variant that breaks a law (engine/invariants.py VIOLATION) is thrown away.
"""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from engine.invariants import Check, Severity, check_plate
from engine.plate import NameInput, PlateConfig, PlateDropReason
from engine.ranker import (
    Criterion,
    RankerPolicy,
    Variant,
    VariantKind,
    candidate_amounts,
    generate_variants,
    load_ranker_policy,
    parse_criteria,
    rank_variants,
    score_variants,
)

D = Decimal
TODAY = "2026-09-25"
POLICY_VALUES = {
    "ticket_band_min": "5000",
    "ticket_band_max": "10000",
    "breadth_min": "8",
    "breadth_max": "15",
    "ranker_criteria_order": "ticket_band,no_raise,breadth,residual",
}


@pytest.fixture
def pol() -> RankerPolicy:
    return load_ranker_policy(POLICY_VALUES)


def _n(symbol: str, price: str, trigger: str, low: str | None = None) -> NameInput:
    """An H-eligible name with no overlays and no cell (build path, P=MISSING)."""
    return NameInput(
        symbol=symbol, name=symbol, price=D(price),
        low_52w=D(low) if low else D(price) * D("0.7"),
        trigger_level=D(trigger), sector_class="DEFAULT", status="ADD", bucket="GBN",
        cell=None, flag_sovereign=False, flag_psu=False, flag_cyclical=False,
        flag_probe_open=False, flag_fraud_tail=False, flag_exit_decided=False,
        p5_status=None, p5_note_ref=None, decay_expiry=None, qty_held_household=0,
        current_weight_pct=None, valuation_gate_passed=False,
    )


def _cfg(amount: str = "7500") -> PlateConfig:
    return PlateConfig(session_amount=D(amount), today=TODAY, psu_weight_pct=D(0),
                       cells={}, bees_price=D("264"))


def _wide(n: int = 18) -> list[NameInput]:
    """n cheap names; the first half FULL_MEALS (H~1.1), the rest TIFFIN (H~1.0)."""
    out = []
    for i in range(n):
        trig = "110" if i < n // 2 else "100"
        out.append(_n(f"N{i:02d}", "100", trig))
    return out


# ------------------------------------------------------------------ policy ---


class TestPolicy:
    def test_criteria_parsed_in_order(self) -> None:
        assert parse_criteria("breadth, residual") == (Criterion.BREADTH, Criterion.RESIDUAL)

    @pytest.mark.parametrize("bad", ["", "breadth,breadth", "breadth,cheapest"])
    def test_bad_criteria_fail_closed(self, bad: str) -> None:
        with pytest.raises(ValueError):
            parse_criteria(bad)

    def test_missing_policy_key_fails_closed(self) -> None:
        values = {k: v for k, v in POLICY_VALUES.items() if k != "ranker_criteria_order"}
        with pytest.raises(KeyError):
            load_ranker_policy(values)

    def test_loaded(self, pol: RankerPolicy) -> None:
        assert (pol.ticket_band_min, pol.ticket_band_max) == (D(5000), D(10000))
        assert (pol.breadth_min, pol.breadth_max) == (8, 15)
        assert pol.criteria[0] == Criterion.TICKET_BAND


# ---------------------------------------------------------------- variants ---


class TestCandidateAmounts:
    def test_inside_band(self, pol: RankerPolicy) -> None:
        assert candidate_amounts(D(7500), pol) == [
            (VariantKind.AS_ASKED, D(7500)), (VariantKind.BAND_LOW, D(5000)),
            (VariantKind.BAND_HIGH, D(10000))]

    def test_asked_equals_band_top_is_not_duplicated(self, pol: RankerPolicy) -> None:
        assert candidate_amounts(D(10000), pol) == [
            (VariantKind.AS_ASKED, D(10000)), (VariantKind.BAND_LOW, D(5000))]

    def test_outside_band_still_shown(self, pol: RankerPolicy) -> None:
        kinds = [k for k, _ in candidate_amounts(D(25000), pol)]
        assert kinds == [VariantKind.AS_ASKED, VariantKind.BAND_LOW, VariantKind.BAND_HIGH]


class TestGenerate:
    def test_every_variant_accounts_for_every_name(self, pol: RankerPolicy) -> None:
        names = _wide()
        for v in generate_variants(names, _cfg(), pol):
            syms = sorted([e.symbol for e in v.result.entries]
                          + [d.symbol for d in v.result.drops])
            assert syms == sorted(n.symbol for n in names), v.label
            assert v.violations == [], (v.label, v.violations)

    def test_trim_only_when_breadth_above_ceiling(self, pol: RankerPolicy) -> None:
        assert not any(v.trimmed for v in generate_variants(_wide(10), _cfg(), pol))
        trims = [v for v in generate_variants(_wide(18), _cfg(), pol) if v.trimmed]
        assert trims and all(len(v.result.entries) == pol.breadth_max for v in trims)

    def test_trim_drops_the_bottom_scores_with_a_reason(self, pol: RankerPolicy) -> None:
        v = next(v for v in generate_variants(_wide(18), _cfg(), pol) if v.trimmed)
        # all TIFFIN names tie on score; the tie breaks by symbol as build_plate ranks
        assert v.trimmed == ("N15", "N16", "N17")
        drops = {d.symbol: d for d in v.result.drops}
        for s in v.trimmed:
            assert drops[s].reason == PlateDropReason.BREADTH_TRIMMED
            assert drops[s].what_would_change.strip()
        assert all(f"BREADTH_TRIM:{s}" in v.result.rules_fired for s in v.trimmed)

    def test_trimmed_variant_obeys_every_law(self, pol: RankerPolicy) -> None:
        names = _wide(18)
        v = next(v for v in generate_variants(names, _cfg(), pol) if v.trimmed)
        checks = check_plate(names, v.config, v.result, pol.breadth_min, pol.breadth_max)
        assert [c for c in checks if c.severity == Severity.VIOLATION] == []
        assert "BREADTH" not in {c.invariant for c in checks}

    def test_clamp_holds_in_every_variant(self, pol: RankerPolicy) -> None:
        for v in generate_variants(_wide(3), _cfg("10000"), pol):
            assert all(1 <= e.qty <= 10 for e in v.result.entries)


# ----------------------------------------------------------------- scoring ---


class TestRank:
    def test_breadth_above_ceiling_prefers_the_trim(self, pol: RankerPolicy) -> None:
        r = rank_variants(_wide(18), _cfg("7500"), pol)
        assert r.best is not None
        assert r.best.variant.trimmed
        # every trim spends to the rupee (residual 0) → the tie rule: smaller plan wins
        assert {s.variant.result.residual for s in r.ranked if s.variant.trimmed} == {D(0)}
        assert r.best.variant.session_amount == D(5000)
        assert r.why and "breadth" in r.why[-1]

    def test_raised_budget_loses_to_an_honest_band_top(self, pol: RankerPolicy) -> None:
        names = [_n(f"X{i}", "2000", "2100") for i in range(4)]   # 1 each = 8000
        r = rank_variants(names, _cfg("5000"), pol)
        assert r.best is not None
        assert r.best.variant.kind == VariantKind.BAND_HIGH
        raised = next(s for s in r.ranked if s.variant.kind == VariantKind.AS_ASKED)
        assert raised.variant.result.plan_amount == D(8000)
        assert not raised.mark(Criterion.NO_RAISE).ok

    def test_out_of_band_ask_loses_on_the_ticket_rule(self, pol: RankerPolicy) -> None:
        r = rank_variants(_wide(6), _cfg("25000"), pol)
        assert r.best is not None
        assert r.best.variant.kind != VariantKind.AS_ASKED
        asked = next(s for s in r.ranked if s.variant.kind == VariantKind.AS_ASKED)
        assert not asked.mark(Criterion.TICKET_BAND).ok

    def test_least_residual_decides_when_rules_tie(self, pol: RankerPolicy) -> None:
        r = rank_variants(_wide(9), _cfg("7500"), pol)
        assert r.best is not None
        residuals = [s.variant.result.residual for s in r.ranked
                     if all(s.mark(c).ok for c in pol.criteria if c != Criterion.RESIDUAL)]
        assert r.best.variant.result.residual == min(residuals)

    def test_criteria_order_comes_from_policy(self, pol: RankerPolicy) -> None:
        names = _wide(18)
        default = rank_variants(names, _cfg("7500"), pol)
        residual_first = rank_variants(
            names, _cfg("7500"),
            replace(pol, criteria=(Criterion.RESIDUAL, Criterion.TICKET_BAND)))
        assert default.best is not None and residual_first.best is not None
        assert residual_first.best.variant.result.residual == min(
            s.variant.result.residual for s in residual_first.ranked)

    def test_deterministic_and_order_independent(self, pol: RankerPolicy) -> None:
        names = _wide(18)
        a = rank_variants(names, _cfg(), pol)
        b = rank_variants(list(reversed(names)), _cfg(), pol)
        assert a.best is not None and b.best is not None
        assert [s.variant.label for s in a.ranked] == [s.variant.label for s in b.ranked]
        assert a.best.variant.result.entries == b.best.variant.result.entries

    def test_nothing_eligible_is_still_ranked(self, pol: RankerPolicy) -> None:
        r = rank_variants([], _cfg(), pol)
        assert r.best is not None
        assert r.best.variant.result.entries == []
        assert not r.best.mark(Criterion.BREADTH).ok


class TestViolationsDiscarded:
    def test_a_variant_with_a_violation_is_never_ranked(self, pol: RankerPolicy) -> None:
        good = generate_variants(_wide(9), _cfg(), pol)
        bad = replace(good[0], label="corrupt",
                      checks=(Check("QTY_CLAMP", Severity.VIOLATION, "N00", "qty=11"),))
        r = score_variants([bad, *good[1:]], pol)
        assert "corrupt" not in [s.variant.label for s in r.ranked]
        assert [v.label for v in r.discarded] == ["corrupt"]

    def test_all_discarded_is_no_action(self, pol: RankerPolicy) -> None:
        good = generate_variants(_wide(9), _cfg(), pol)
        bad = [replace(v, checks=(Check("TOTALS", Severity.VIOLATION, "*", "x"),))
               for v in good]
        r = score_variants(bad, pol)
        assert r.best is None and r.ranked == ()

    def test_violations_property(self, pol: RankerPolicy) -> None:
        v: Variant = generate_variants(_wide(9), _cfg(), pol)[0]
        assert v.violations == []
