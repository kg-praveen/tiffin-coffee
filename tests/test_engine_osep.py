"""tests/test_engine_osep.py — UC4 engine: every stage, the verdict, trigger and expiry.

Spec: osep v7. Pure — no network, no DB.
"""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from engine.osep import (
    Bucket,
    Judgment,
    OsepInput,
    OsepPolicy,
    Status,
    analyse,
    derive_trigger,
    p5_line,
    stage0_checks,
)

D = Decimal
POL = OsepPolicy(gsec_yield_pct=D("7.119"), coe_spread=D("6.09"), growth_g=D(5),
                 promoter_kill_pct=D(26), promoter_net_sell_flag_pct=D(2), stage1_gate=35,
                 decay_gbn_days=30, decay_gbl_days=90, decay_hard_pass_days=180,
                 cap_name_pct=D(20), cap_sector_pct=D(40))
GOOD = Judgment(sovereign_directed=False, thesis_verifiable=True, governance_clean=True,
                industry_durable=True, investable=True, stage1_score=36,
                thesis_type="RE-RATING")
# R Systems, 25/26-Sep-2026 inputs (the case that exposed the minority-interest EPS)
RSYS = OsepInput(
    symbol="RSYSTEMS", today="2026-09-26", sector_class="IT_SERVICES", price=D("235.62"),
    eps_ttm=D("16.27"), bvps=D("92.69"), roe_pct=D("17.33"), pe=D("14.48"), pb=D("2.54"),
    promoter_pct_series=[D("51.93"), D("51.90"), D("51.89"), D("51.88"), D("51.85")],
    total_debt=D("2708480000"), equity=D("10982680000"),
    net_income_hist=[D(1862), D(1312), D(1401), D(1397)],
    revenue_hist=[D(19582), D(17417), D(16845), D(15158)],
    ocf_hist=[D(2199), D(2353), D(2114), D(964)], judgment=GOOD)


def _c(checks: list, rule: str):  # type: ignore[no-untyped-def]
    return next(c for c in checks if c.rule == rule)


class TestStage0:
    def test_promoter_below_26_kills(self) -> None:
        inp = replace(RSYS, promoter_pct_series=[D(30), D(28), D(27), D(26), D("25.9")])
        assert _c(stage0_checks(inp, POL), "promoter ≥ 26%").status == Status.FAIL

    def test_promoter_exempt_bank(self) -> None:
        inp = replace(RSYS, promoter_pct_series=[D(0)] * 5,
                      judgment=replace(GOOD, promoter_exempt=True))
        assert _c(stage0_checks(inp, POL), "promoter ≥ 26%").status == Status.EXEMPT

    def test_p4_is_a_flag_not_a_kill(self) -> None:
        inp = replace(RSYS, promoter_pct_series=[D(60), D(59), D(58), D(58), D("57.5")])
        c = _c(stage0_checks(inp, POL), "P4 promoter net selling")
        assert c.status == Status.FLAG
        assert analyse(inp, POL).bucket != Bucket.HARD_PASS

    def test_solvency_fail_and_lender_exempt(self) -> None:
        weak = replace(RSYS, equity=D(100), total_debt=D(60))
        assert _c(stage0_checks(weak, POL), "solvency").status == Status.FAIL
        lender = replace(weak, sector_class="LENDER")
        assert _c(stage0_checks(lender, POL), "solvency").status == Status.EXEMPT

    def test_cumulative_losses_and_growing_losses(self) -> None:
        loss = replace(RSYS, net_income_hist=[D(-300), D(-200), D(50), D(40)],
                       revenue_hist=[D(900), D(700), D(500), D(400)])
        checks = stage0_checks(loss, POL)
        assert _c(checks, "cumulative profit").status == Status.FAIL
        assert _c(checks, "loss scales with volume").status == Status.FAIL

    def test_unresearched_judgment_is_unknown(self) -> None:
        inp = replace(RSYS, judgment=Judgment())
        assert _c(stage0_checks(inp, POL), "P1 sovereign control").status == Status.UNKNOWN


class TestTrigger:
    def test_default_ladder(self) -> None:
        trig, basis = derive_trigger(RSYS, POL)
        assert trig == D("228.59") and "16.27" in basis

    def test_lender_uses_justified_pb(self) -> None:
        hdfc = replace(RSYS, sector_class="LENDER", bvps=D("393.81"), roe_pct=D("13.84"))
        trig, basis = derive_trigger(hdfc, POL)
        assert trig is not None and "justified P/B" in basis
        assert trig < D(450)       # P/B ~1.07x on ~₹394 book

    def test_no_trigger_for_cyclical_or_gold(self) -> None:
        for sec in ("CYCLICAL", "NON_EARNING", "INDEX_ETF"):
            assert derive_trigger(replace(RSYS, sector_class=sec), POL)[0] is None

    def test_negative_eps_has_no_trigger(self) -> None:
        assert derive_trigger(replace(RSYS, eps_ttm=D(-3)), POL)[0] is None


class TestVerdict:
    def test_rsystems_is_good_buy_later_above_fair(self) -> None:
        v = analyse(RSYS, POL)
        assert v.bucket == Bucket.GOOD_BUY_LATER
        assert v.trigger == D("228.59") and v.thesis_type == "RE-RATING"
        assert v.expiry == "2026-12-25"                       # GBL = 90 days
        assert any("228.59" in w for w in v.what_would_change)

    def test_below_fair_is_good_buy_now(self) -> None:
        v = analyse(replace(RSYS, price=D(220), pe=D("13.52"), pb=D("1.4")), POL)
        assert v.bucket == Bucket.GOOD_BUY_NOW and v.expiry == "2026-10-26"

    def test_missing_judgments_is_incomplete_never_a_buy(self) -> None:
        v = analyse(replace(RSYS, price=D(150), judgment=Judgment()), POL)
        assert v.bucket == Bucket.INCOMPLETE
        assert "thesis type" in " ".join(v.missing)
        assert v.expiry is None

    def test_missing_thesis_type_alone_blocks(self) -> None:
        v = analyse(replace(RSYS, judgment=replace(GOOD, thesis_type=None)), POL)
        assert v.bucket == Bucket.INCOMPLETE

    def test_kill_switch_is_hard_pass_for_180_days(self) -> None:
        v = analyse(replace(RSYS, judgment=replace(GOOD, sovereign_directed=True)), POL)
        assert v.bucket == Bucket.HARD_PASS and v.expiry == "2027-03-25"

    def test_low_quality_score_is_hard_pass(self) -> None:
        v = analyse(replace(RSYS, judgment=replace(GOOD, stage1_score=30)), POL)
        assert v.bucket == Bucket.HARD_PASS

    def test_fmcg_brand_gate(self) -> None:
        vbl = replace(RSYS, sector_class="FMCG", brand_owned=False)
        assert analyse(vbl, POL).bucket == Bucket.HARD_PASS
        unknown = replace(RSYS, sector_class="FMCG", brand_owned=None)
        assert analyse(unknown, POL).bucket == Bucket.INCOMPLETE

    def test_standing_exclusion_is_no_action(self) -> None:
        v = analyse(replace(RSYS, standing_exclusion="register status NEVER_ADD"), POL)
        assert v.bucket == Bucket.NO_ACTION

    def test_no_price_is_no_action(self) -> None:
        assert analyse(replace(RSYS, price=None), POL).bucket == Bucket.NO_ACTION

    def test_new_name_needs_a_sector_class(self) -> None:
        v = analyse(replace(RSYS, sector_class=None), POL)
        assert v.bucket == Bucket.INCOMPLETE and any("sector class" in m for m in v.missing)

    def test_deterministic(self) -> None:
        assert analyse(RSYS, POL) == analyse(RSYS, POL)


class TestP5:
    def test_avoid_without_note_blocks(self) -> None:
        text, blocks = p5_line(replace(RSYS, p5_status="AVOID"), True)
        assert blocks and "written disagreement" in text

    def test_buy_but_osep_fails_is_no_action(self) -> None:
        text, blocks = p5_line(replace(RSYS, p5_status="BUY"), False)
        assert not blocks and "anti-tip" in text
