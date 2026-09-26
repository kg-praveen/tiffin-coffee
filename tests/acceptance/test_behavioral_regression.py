"""The acceptance suite — spec/MIGRATION-AND-VALIDATION.md §"Behavioral regression".

CLAUDE.md §5: one parametrized test per row of the 22-case table. Each case replays
the decision Praveen already approved (or the safe outcome) through the real engine.

Rows whose engine path is NOT BUILT yet are `xfail(strict=True)` with the missing
capability named: they fail today for the stated reason, and the day the capability
lands they XPASS — which fails the build until the marker is removed. The table's
coverage therefore can never silently drift. No network; the register is read-only.
"""
from __future__ import annotations

import re
import sqlite3
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path

import pytest

from engine.morning_board import DropReason, check_armability
from engine.plate import (
    CellInfo,
    NameInput,
    PlateConfig,
    PlateDropReason,
    PlateResult,
    build_plate,
)
from engine.valuation_gate import ValuationGateInput, compute_valuation_gate
from tools.market_snapshot import load_snapshot, newest_snapshot
from tools.prices import BatchPriceResult
from usecases.plate import run_plate

ROOT = Path(__file__).resolve().parent.parent.parent
SEED_DB = ROOT / "db" / "pattaz.db"
MARKET_DIR = ROOT / "tests" / "fixtures" / "market"
TODAY = "2026-09-20"
GSEC = Decimal("7.04")          # ledger §3 D54 anchor — the recorded input for these replays
SPREAD = Decimal("6.09")        # policy cost_of_equity_spread_over_gsec
G = Decimal(5)                  # policy growth_g

CELLS = {
    "IT": CellInfo(False, 2, 2, frozenset({"INFY", "TCS"})),
    "LENDING_BANKS": CellInfo(False, 1, 2, frozenset({"SBIN"})),
    "GOLD_NBFC": CellInfo(True, 1, 2, frozenset({"MUTHOOTFIN"})),
    "POWER": CellInfo(False, 2, 2, frozenset({"NTPC", "POWERGRID"})),
}


def _ro() -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{SEED_DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _n(symbol: str, price: str, low: str, trigger: str | None = None, *,
       sector: str | None = "DEFAULT", status: str = "ADD", bucket: str | None = "GBN",
       cell: str | None = None, held: int = 0, gate: bool = False, **flags: object
       ) -> NameInput:
    base: dict[str, object] = dict(
        flag_sovereign=False, flag_psu=False, flag_cyclical=False, flag_probe_open=False,
        flag_fraud_tail=False, flag_exit_decided=False, p5_status=None, p5_note_ref=None,
        decay_expiry=None, current_weight_pct=None, p_mult_book=None, flag_no_add=False,
    )
    base.update(flags)
    return NameInput(
        symbol=symbol, name=symbol, price=Decimal(price), low_52w=Decimal(low),
        trigger_level=Decimal(trigger) if trigger else None, sector_class=sector,
        status=status, bucket=bucket, cell=cell, qty_held_household=held,
        valuation_gate_passed=gate, valuation_gate_detail="",
        owned_per_book=(bucket == "OWNED" or status == "HOLD"), **base,  # type: ignore[arg-type]
    )


def _plate(*names: NameInput, psu: str = "10") -> PlateResult:
    cfg = PlateConfig(session_amount=Decimal(40000), today=TODAY,
                      psu_weight_pct=Decimal(psu), cells=CELLS, bees_price=Decimal(266))
    return build_plate(list(names), cfg)


def _gate(sector: str | None, pe: str | None, pb: str | None, roe: str | None):  # type: ignore[no-untyped-def]
    return compute_valuation_gate(ValuationGateInput(
        symbol="X", sector_class=sector, pe_trailing=Decimal(pe) if pe else None,
        pb_ratio=Decimal(pb) if pb else None, roe_pct=Decimal(roe) if roe else None,
        gsec_yield_pct=GSEC, cost_of_equity_spread=SPREAD, growth_g_pct=G))


def _entry_syms(r: PlateResult) -> set[str]:
    return {e.symbol for e in r.entries}


def _reason(r: PlateResult, sym: str) -> PlateDropReason:
    return next(d.reason for d in r.drops if d.symbol == sym)


# ------------------------------------------------------------------ the 22 ---


def case_01_muthoot_add() -> None:
    """Muthoot add (unlocked 05-Sep): LENDER, P5 DISAGREE note exists → still plates."""
    m = _n("MUTHOOTFIN", "2769.56", "2671", "3221", sector="LENDER", cell="GOLD_NBFC",
           held=7, p5_status="DISAGREE_NOTE", p5_note_ref="ledger §8 05-Sep",
           p_mult_book=Decimal("1.0"))
    assert "MUTHOOTFIN" in _entry_syms(_plate(m))
    vetoed = _n("MUTHOOTFIN", "2769.56", "2671", "3221", sector="LENDER", cell="GOLD_NBFC",
                held=7, p5_status="AVOID", p_mult_book=Decimal("1.0"))
    assert _reason(_plate(vetoed), "MUTHOOTFIN") == PlateDropReason.P5_VETO


def case_02_hdfc_first_bite_zero() -> None:
    """HDFC at a fresh low (10-Sep): P/B 1.87 > justified; P/E 13.1 cannot rescue → 0."""
    g = _gate("LENDER", "13.1", "1.87", "13.84")
    assert not g.passed and g.gate_name == "gate_lender_justified_pb"
    hdfc = _n("HDFCBANK", "681.90", "681.90", "419", sector="LENDER", status="HOLD",
              bucket="OWNED", cell="LENDING_BANKS", held=126, gate=g.passed)
    r = _plate(hdfc)
    assert r.entries == [] and _reason(r, "HDFCBANK") == PlateDropReason.FIRST_BITE_FAILED


def case_03_icici_gtt_cannot_rearm() -> None:
    """ICICI 1,300 GTT (cancelled, name sold): no live trigger; SOLD blocks re-arming."""
    with _ro() as con:
        assert con.execute("SELECT status FROM names WHERE symbol='ICICIBANK'"
                           ).fetchone()["status"] == "SOLD"
        assert con.execute("SELECT count(*) c FROM triggers WHERE symbol='ICICIBANK' "
                           "AND active=1").fetchone()["c"] == 0
    a = check_armability("ICICIBANK", "BUY", True, "2026-09-01", None, TODAY,
                         "ICICIBANK.NS", "SOLD", False, result_dates=("2026-07-19",),
                         results_max_age_days=150)
    assert not a.armable and a.drop_reason == DropReason.STATUS_BLOCKED


def case_04_basis_predates_last_result() -> None:
    """Stale-basis trigger (the 5-week invalid-trigger incident): basis older than the
    latest results → NOT ARMABLE, price never classified (E3). Unknown dates → same (E9)."""
    a = check_armability("X", "BUY", True, "2026-07-01", None, TODAY, "X.NS", "ADD",
                         False, result_dates=("2026-04-20", "2026-08-10", "2026-10-23"),
                         results_max_age_days=150)
    assert not a.armable and a.drop_reason == DropReason.STALE_BASIS
    b = check_armability("X", "BUY", True, "2026-08-15", None, TODAY, "X.NS", "ADD",
                         False, result_dates=("2026-08-10", "2026-10-23"), results_max_age_days=150)
    assert b.armable                       # basis after the latest results; Oct is future
    c = check_armability("X", "BUY", True, "2026-08-15", None, TODAY, "X.NS", "ADD",
                         False, result_dates=None, results_max_age_days=150)
    assert not c.armable and c.drop_reason == DropReason.RESULT_DATE_UNKNOWN


def case_05_corporate_action_stale() -> None:
    """NOT BUILT: armability needs trailing-12m corporate actions (HDFC 560-vs-419)."""
    a = check_armability("X", "BUY", True, "2026-09-01", None, TODAY, "X.NS", "ADD",
                         False, result_dates=("2026-07-20",), results_max_age_days=150,
                         corporate_action_on="2026-08-20")  # type: ignore[call-arg]
    assert not a.armable


def case_06_unknown_name_default_ladder() -> None:
    """Unclassified name → DEFAULT ladder (E4 strictest), never a silent sector guess."""
    g = _gate(None, "30", "5", "12")
    assert g.gate_name == "gate_default_pe_ladder" and not g.passed


def case_07_conglomerate_strictest_gate() -> None:
    """NOT BUILT: osep §SC edge rule — ambiguous sector → strictest applicable gate."""
    from engine.classify import classify_sector  # type: ignore[import-not-found]
    assert classify_sector is not None


def case_08_demerged_tmcv_watch_only(tmp_path: Path) -> None:
    """Demerged TMCV: no ticker until classified fresh → never priced, never plated."""
    db = tmp_path / "pattaz.db"
    db.write_bytes(SEED_DB.read_bytes())
    snap_path = newest_snapshot(MARKET_DIR)
    assert snap_path is not None
    r = run_plate(db, Decimal(40000), market=load_snapshot(snap_path), today="2026-09-25",
                  record_session=False)
    assert "TMCV" not in _entry_syms(r.plate)
    assert any(d.symbol == "TMCV" and d.reason == PlateDropReason.NO_TICKER
               for d in r.unpriced)


def case_09_ongc_sovereign() -> None:
    """ONGC cheapest-on-H: P1 sovereign → zero (overlay #2), however high H is."""
    r = _plate(_n("ONGC", "200", "195", "400", status="WATCH", flag_sovereign=True))
    assert _reason(r, "ONGC") == PlateDropReason.SOVEREIGN


def case_10_bob_fraud_tail() -> None:
    """BoB 0.7x book passes P/B, but the legacy-fraud flag holds it (overlay #10)."""
    assert _gate("LENDER", None, "0.7", "14").passed
    r = _plate(_n("BANKBARODA", "240", "238", "300", sector="LENDER", status="WATCH",
                  cell="LENDING_BANKS", gate=True, flag_fraud_tail=True))
    assert _reason(r, "BANKBARODA") == PlateDropReason.FRAUD_TAIL


def case_11_irfc_buy_and_sell() -> None:
    """IRFC on the sell list can never be bought the same session (overlay #7)."""
    r = _plate(_n("IRFC", "100", "99", "150", status="SELL", bucket="OWNED", held=200,
                  flag_exit_decided=True))
    assert _reason(r, "IRFC") == PlateDropReason.EXIT_DECIDED


def case_12_tata_headline_no_tip() -> None:
    """Tata Sons 'value-unlock' headline (14-Sep): a tip, not a thesis → Tata Steel stays out."""
    with _ro() as con:
        row = con.execute("SELECT flag_exit_decided, flag_cyclical FROM names "
                          "WHERE symbol='TATASTEEL'").fetchone()
    ts = _n("TATASTEEL", "140", "138", "200", sector="CYCLICAL", status="HOLD",
            bucket="OWNED", held=50, flag_exit_decided=bool(row["flag_exit_decided"]),
            flag_cyclical=bool(row["flag_cyclical"]))
    assert "TATASTEEL" not in _entry_syms(_plate(ts))


def case_13_goldbees_non_earning() -> None:
    """GOLDBEES: G-NON-EARNING — no valuation gate ever passes; thermostat only."""
    g = _gate("NON_EARNING", "1", "0.1", "50")
    assert not g.passed
    r = _plate(_n("GOLDBEES", "80", "80", sector="NON_EARNING", bucket="BALLAST", held=389,
                  gate=g.passed))
    assert _reason(r, "GOLDBEES") == PlateDropReason.FIRST_BITE_FAILED


def case_14_ntpc_gbn() -> None:
    """NTPC GBN: REGULATED≠DIRECTED → default ladder; D1 waived (CONVICTION-OVERRIDE)."""
    assert _gate("REGULATED", "13", "1.8", "13").passed
    with _ro() as con:
        notes = con.execute("SELECT notes FROM triggers WHERE symbol='NTPC' AND active=1"
                            ).fetchone()["notes"]
    assert "CONVICTION-OVERRIDE" in notes
    r = _plate(_n("NTPC", "329.55", "315.51", "407", sector="REGULATED", cell="POWER",
                  held=35, flag_psu=True))
    assert "NTPC" in _entry_syms(r)


def case_15_income_sleeve() -> None:
    """IndiGrid: REIT veto-INPUT only; sleeve unfunded → P5 AVOID with no note vetoes,
    and the register gives it no ticker (never priced)."""
    r = _plate(_n("INDIGRID", "150", "146", "170", sector="REIT_INVIT", status="WATCH",
                  bucket="GBL", p5_status="AVOID"))
    assert _reason(r, "INDIGRID") == PlateDropReason.P5_VETO
    with _ro() as con:
        assert con.execute("SELECT yf_ticker FROM names WHERE symbol='INDIGRID'"
                           ).fetchone()["yf_ticker"] is None


def case_16_vbl_brand_gate() -> None:
    """VBL: FMCG brand-OWNERSHIP hard gate (osep v7 §G) fails adds even when cheap; an
    FMCG name whose ownership is not recorded is raised, not bought (E4/E9)."""
    r = _plate(_n("VBL", "450", "450", sector="FMCG", status="HOLD", bucket="OWNED",
                  held=20, gate=True, brand_owned=False))
    assert _reason(r, "VBL") == PlateDropReason.BRAND_NOT_OWNED
    with _ro() as con:
        assert con.execute("SELECT brand_owned FROM names WHERE symbol='VBL'"
                           ).fetchone()["brand_owned"] == 0
    hul = _plate(_n("HINDUNILVR", "2400", "2400", sector="FMCG", status="HOLD",
                    bucket="OWNED", held=5, gate=True))
    assert _reason(hul, "HINDUNILVR") == PlateDropReason.BRAND_UNVERIFIED


def case_17_doctrine_not_live() -> None:
    """Manappuram's 2025 'better' quote (E2: doctrine ≠ live input): P5 BUY cannot rescue
    today's failed justified-P/B gate."""
    g = _gate("LENDER", "8", "2.2", "16")
    assert not g.passed
    r = _plate(_n("MANAPPURAM", "260", "260", sector="LENDER", status="HOLD",
                  bucket="OWNED", cell="GOLD_NBFC", held=100, gate=g.passed,
                  p5_status="BUY"))
    assert _reason(r, "MANAPPURAM") == PlateDropReason.FIRST_BITE_FAILED


def case_18_drl_guardrail() -> None:
    """Dr Reddy's: live quality probe + exit decided → never plated."""
    r = _plate(_n("DRREDDY", "1200", "1190", "1500", sector="PHARMA", status="SELL",
                  bucket="OWNED", held=28, flag_probe_open=True, flag_exit_decided=True))
    assert r.entries == [] and _reason(r, "DRREDDY") in {
        PlateDropReason.PROBE_OPEN, PlateDropReason.EXIT_DECIDED}


def case_19_missing_price_names_input(tmp_path: Path) -> None:
    """Unfetchable price → NO ACTION naming the missing input ('not found' ≠ a result)."""
    db = tmp_path / "pattaz.db"
    db.write_bytes(SEED_DB.read_bytes())
    snap_path = newest_snapshot(MARKET_DIR)
    assert snap_path is not None
    snap = load_snapshot(snap_path)
    prices = {k: v for k, v in snap.prices.prices.items() if k != "NTPC"}
    blind = type(snap)(snap.recorded_at, BatchPriceResult(prices, {"NTPC": "HTTP 503"}),
                       snap.fundamentals, snap.gsec)
    r = run_plate(db, Decimal(40000), market=blind, today="2026-09-25", record_session=False)
    assert "NTPC" not in _entry_syms(r.plate)
    d = next(d for d in r.unpriced if d.symbol == "NTPC")
    assert d.reason == PlateDropReason.PRICE_FETCH_FAILED and "HTTP 503" in d.detail


def case_20_caps_off_is_e6() -> None:
    """Caps-off on a first bite blocked only by a cell cap → E6 HALT, never decided."""
    fb = _n("CUB", "150", "150", sector="LENDER", status="HOLD", bucket="OWNED",
            cell="GOLD_NBFC", held=50, gate=True)
    r = _plate(fb)
    assert r.entries == [] and _reason(r, "CUB") == PlateDropReason.E6_CAPS_OFF_CONFLICT


def case_21_wipro_first_bite_max() -> None:
    """OPEN E6: the table expects Wipro at its low → first-bite max (≤5), no build. The
    engine surfaces the §12b caps-off conflict instead (IT cell full, hold-no-add D48).
    Praveen to rule: pattaz-book §12b vs ledger v4.9 D44 (caps-off on a live consider)."""
    w = _n("WIPRO", "163.64", "161.66", "190", sector="IT_SERVICES", status="HOLD",
           bucket="OWNED", cell="IT", held=146, gate=True, flag_no_add=True)
    r = _plate(w)
    e = next(e for e in r.entries if e.symbol == "WIPRO")
    assert e.is_first_bite and e.qty <= 5


def case_22_no_stale_duplicate_rule() -> None:
    """E7 edit protocol (defect-1 replay): killed phantoms never reappear in code, and every
    plate threshold the policy table carries is read from it (T1/T2/T6 greps)."""
    code = "\n".join(p.read_text() for d in ("engine", "usecases")
                     for p in (ROOT / d).glob("*.py"))
    for phantom in (r"Decimal\(\"1\.3\"\)", r"\b1\.3x\b", r"4\.2%", r"23-24x", r"5%/20x"):
        assert not re.search(phantom, code), f"killed phantom back in code: {phantom}"
    plate_uc = (ROOT / "usecases" / "plate.py").read_text()
    for key in ("eligible_h_min", "eligible_l_max", "qty_clamp_min", "qty_clamp_max",
                "first_bite_qty_max", "first_bite_l_max", "cap_psu_regulated_pct"):
        assert f'_policy_decimal(policy, "{key}")' in plate_uc, f"{key} not read from policy"


# ------------------------------------------------------------------ table ---

_NOT_BUILT = "NOT BUILT — "
CASES: list[object] = [
    pytest.param(case_01_muthoot_add, id="01-muthoot-add"),
    pytest.param(case_02_hdfc_first_bite_zero, id="02-hdfc-first-bite-zero"),
    pytest.param(case_03_icici_gtt_cannot_rearm, id="03-icici-gtt"),
    pytest.param(case_04_basis_predates_last_result, id="04-stale-basis"),
    pytest.param(case_05_corporate_action_stale, id="05-corporate-action",
                 marks=pytest.mark.xfail(raises=TypeError, strict=True,
                                         reason=_NOT_BUILT + "corporate-action validity")),
    pytest.param(case_06_unknown_name_default_ladder, id="06-unknown-name"),
    pytest.param(case_07_conglomerate_strictest_gate, id="07-conglomerate",
                 marks=pytest.mark.xfail(raises=ImportError, strict=True,
                                         reason=_NOT_BUILT + "osep §SC classifier")),
    pytest.param(case_08_demerged_tmcv_watch_only, id="08-tmcv"),
    pytest.param(case_09_ongc_sovereign, id="09-ongc"),
    pytest.param(case_10_bob_fraud_tail, id="10-bob"),
    pytest.param(case_11_irfc_buy_and_sell, id="11-irfc"),
    pytest.param(case_12_tata_headline_no_tip, id="12-tata-headline"),
    pytest.param(case_13_goldbees_non_earning, id="13-goldbees"),
    pytest.param(case_14_ntpc_gbn, id="14-ntpc"),
    pytest.param(case_15_income_sleeve, id="15-income-sleeve"),
    pytest.param(case_16_vbl_brand_gate, id="16-vbl"),
    pytest.param(case_17_doctrine_not_live, id="17-manappuram"),
    pytest.param(case_18_drl_guardrail, id="18-drl"),
    pytest.param(case_19_missing_price_names_input, id="19-missing-price"),
    pytest.param(case_20_caps_off_is_e6, id="20-caps-off"),
    pytest.param(case_21_wipro_first_bite_max, id="21-wipro",
                 marks=pytest.mark.xfail(raises=StopIteration, strict=True,
                                         reason="OPEN E6 — §12b vs D44, Praveen to rule")),
    pytest.param(case_22_no_stale_duplicate_rule, id="22-e7-greps"),
]


@pytest.mark.parametrize("case", CASES)
def test_behavioral_regression(case: Callable[..., None], tmp_path: Path) -> None:
    if "tmp_path" in case.__code__.co_varnames[: case.__code__.co_argcount]:
        case(tmp_path)
    else:
        case()


def test_table_has_22_rows() -> None:
    assert len(CASES) == 22
