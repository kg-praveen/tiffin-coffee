"""Golden day 20-Sep-2026 — reconciliation of the ₹40k plate audit.

Recorded inputs: D54 trigger board (DB), 20-Sep closes (session UC2_dcced6a8713f),
pattaz-book §4 P-mults and §5 seats, partial holdings table. Locks in the audit
verdicts: seat-holders plate; hold-only, stale-holdings and lender-gate names do not.
No network.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from engine.plate import (
    CellInfo,
    Mode,
    NameInput,
    PlateConfig,
    PlateDropReason,
    build_plate,
)

TODAY = "2026-09-20"
PSU_WEIGHT_PHANTOM = Decimal("13.47")   # from the partial holdings table — advisory only

CELLS = {
    "IT": CellInfo(False, 2, 2, frozenset({"INFY", "TCS"})),
    "POWER": CellInfo(False, 2, 2, frozenset({"NTPC", "POWERGRID"})),
    "GOLD_NBFC": CellInfo(True, 1, 2, frozenset({"MUTHOOTFIN"})),
    "LENDING_BANKS": CellInfo(False, 1, 2, frozenset({"SBIN"})),
    "FMCG": CellInfo(False, 0, 2, frozenset()),
    "ANCILLARY": CellInfo(False, 1, 2, frozenset({"ARE&M"})),
    "AGRI_INPUTS": CellInfo(False, 2, 2, frozenset({"CHAMBLFERT", "COROMANDEL"})),
    "WIRES_GBL": CellInfo(False, 0, 2, frozenset()),
    "ENERGY_GAS": CellInfo(False, 1, 2, frozenset({"PETRONET"})),
}


def _n(symbol: str, price: str, low: str, trigger: str | None, *, cell: str,
       sector: str | None, status: str, bucket: str | None, held: int = 0,
       weight: str | None = None, p_book: str | None = None, no_add: bool = False,
       cyclical: bool = False, psu: bool = False, gate: bool = False,
       gate_detail: str = "FAIL", p5: str | None = None, p5ref: str | None = None) -> NameInput:
    return NameInput(
        symbol=symbol, name=symbol, price=Decimal(price), low_52w=Decimal(low),
        trigger_level=Decimal(trigger) if trigger else None,
        sector_class=sector, status=status, bucket=bucket, cell=cell,
        flag_sovereign=False, flag_psu=psu, flag_cyclical=cyclical,
        flag_probe_open=False, flag_fraud_tail=False, flag_exit_decided=False,
        p5_status=p5, p5_note_ref=p5ref, decay_expiry=None,
        qty_held_household=held,
        current_weight_pct=Decimal(weight) if weight else None,
        valuation_gate_passed=gate, valuation_gate_detail=gate_detail,
        p_mult_book=Decimal(p_book) if p_book else None,
        flag_no_add=no_add,
        owned_per_book=(bucket == "OWNED" or status == "HOLD"),
    )


NAMES = [
    # seat-holders with triggers — the five the old engine wrongly dropped as CELL_FULL
    _n("NTPC", "329.55", "315.51", "407", cell="POWER", sector="REGULATED", status="ADD",
       bucket="GBN", held=35, weight="3.32", psu=True),
    _n("INFY", "1058.77", "982.40", "1099", cell="IT", sector="IT_SERVICES", status="ADD",
       bucket="GBN", held=36, weight="10.96", p_book="1.0"),
    _n("TCS", "2190.96", "1976.80", "1939", cell="IT", sector="IT_SERVICES", status="ADD",
       bucket="GBN", held=15, weight="9.45", p_book="1.0"),
    _n("MUTHOOTFIN", "2769.56", "2671.00", "3221", cell="GOLD_NBFC", sector="LENDER",
       status="ADD", bucket="GBN", held=7, weight="5.57", p_book="1.0",
       p5="DISAGREE_NOTE", p5ref="ledger §8 05-Sep"),
    _n("POWERGRID", "263.71", "249.96", "250", cell="POWER", sector="REGULATED", status="ADD",
       bucket="GBL", psu=True),
    # the three that plated on 20-Sep
    _n("SBIN", "988.53", "850.72", "862", cell="LENDING_BANKS", sector="LENDER", status="ADD",
       bucket="GBN", held=10, weight="2.84", psu=True),
    _n("ARE&M", "795.30", "670.00", "790", cell="ANCILLARY", sector="AUTO_ANCILLARY",
       status="ADD", bucket="GBL", held=10, weight="2.29"),
    _n("ITC", "266.36", "255.50", "228", cell="FMCG", sector="FMCG", status="HOLD",
       bucket="OWNED", p_book="0.5", no_add=True, p5="BUY"),
    # hold-only / museum
    _n("WIPRO", "166.37", "163.30", "190", cell="IT", sector="IT_SERVICES", status="HOLD",
       bucket="OWNED", held=146, weight="6.98", no_add=True),
    _n("HCLTECH", "1258.56", "1030.00", "915", cell="IT", sector="IT_SERVICES", status="HOLD",
       bucket="OWNED", p_book=None, no_add=True, held=0),
    # the lender golden case, 4.56% off its low
    _n("HDFCBANK", "712.59", "681.51", "419", cell="LENDING_BANKS", sector="LENDER",
       status="HOLD", bucket="OWNED", held=5, weight="1.02", p_book="0.0",
       gate=False, gate_detail="FAIL: P/B 1.81 > justified 1.08",
       p5="AGREE_NOTE", p5ref="ledger §8 05-Sep"),
    # book says OWNED, holdings table has no row
    _n("RELIANCE", "1243.09", "1225.56", "854", cell="ENERGY_GAS", sector=None,
       status="HOLD", bucket="OWNED", gate=False,
       gate_detail="FAIL: P/E 22.52 > fair 14.20; P/B 1.86 > justified 0.41",
       p5="AGREE_NOTE", p5ref="ledger §8 05-Sep"),
    # at trigger but flagged cyclical — E6 question for Praveen, engine says no
    _n("CHAMBLFERT", "413.76", "399.61", "415", cell="AGRI_INPUTS", sector="CYCLICAL",
       status="ADD", bucket="GBN", cyclical=True),
    # at the low, not owned, gate fails
    _n("HAVELLS", "1507.00", "1491.93", "538", cell="WIRES_GBL", sector="DEFAULT",
       status="WATCH", bucket="GBL", gate=False,
       gate_detail="FAIL: P/E 57.85 > fair 14.20; P/B 10.00 > justified 1.53"),
]


@pytest.fixture(scope="module")
def result():  # type: ignore[no-untyped-def]
    cfg = PlateConfig(session_amount=Decimal(40000), today=TODAY,
                      psu_weight_pct=PSU_WEIGHT_PHANTOM, cells=CELLS, bees_price=Decimal("266.06"))
    return build_plate(NAMES, cfg)


def _drop(result, symbol: str):  # type: ignore[no-untyped-def]
    return next(d for d in result.drops if d.symbol == symbol)


class TestGolden20Sep:
    def test_plate_membership(self, result) -> None:  # type: ignore[no-untyped-def]
        assert {e.symbol for e in result.entries} == {
            "NTPC", "INFY", "TCS", "MUTHOOTFIN", "POWERGRID", "SBIN", "ARE&M",
        }

    def test_modes(self, result) -> None:  # type: ignore[no-untyped-def]
        modes = {e.symbol: e.mode for e in result.entries}
        assert modes["NTPC"] == Mode.HOCKEY
        assert modes["MUTHOOTFIN"] == Mode.HOCKEY
        assert modes["INFY"] == Mode.TIFFIN
        assert modes["TCS"] == Mode.COFFEE

    def test_clamp_and_budget(self, result) -> None:  # type: ignore[no-untyped-def]
        assert all(1 <= e.qty <= 10 for e in result.entries)
        assert result.total_with_sweep <= Decimal(40000)

    def test_hold_only_refused(self, result) -> None:  # type: ignore[no-untyped-def]
        # 26-Sep-2026: the FMCG brand gate (osep v7 §G) runs before hold-only; ITC's
        # brand ownership is not recorded yet, so it is raised for Praveen. Still refused.
        assert _drop(result, "ITC").reason == PlateDropReason.BRAND_UNVERIFIED
        assert _drop(result, "WIPRO").reason == PlateDropReason.CELL_FULL
        assert _drop(result, "HCLTECH").reason == PlateDropReason.NOT_ELIGIBLE

    def test_lender_gate_holds(self, result) -> None:  # type: ignore[no-untyped-def]
        d = _drop(result, "HDFCBANK")
        assert d.reason == PlateDropReason.FIRST_BITE_FAILED
        assert "(a)" in d.detail and "1.08" in d.detail

    def test_missing_holdings_fail_closed(self, result) -> None:  # type: ignore[no-untyped-def]
        assert _drop(result, "RELIANCE").reason == PlateDropReason.HOLDINGS_STALE

    def test_cyclical_at_trigger_is_surfaced_not_bought(self, result) -> None:  # type: ignore[no-untyped-def]
        d = _drop(result, "CHAMBLFERT")
        assert d.reason == PlateDropReason.E6_PEAK_CYCLE_CONFLICT
        assert d.h == Decimal("1.003")

    def test_not_owned_cannot_first_bite(self, result) -> None:  # type: ignore[no-untyped-def]
        d = _drop(result, "HAVELLS")
        assert d.reason == PlateDropReason.FIRST_BITE_FAILED
        assert "(d) not owned" in d.detail and "57.85" in d.detail

    def test_deterministic(self) -> None:
        cfg = PlateConfig(session_amount=Decimal(40000), today=TODAY,
                          psu_weight_pct=PSU_WEIGHT_PHANTOM, cells=CELLS,
                          bees_price=Decimal("266.06"))
        assert build_plate(NAMES, cfg) == build_plate(NAMES, cfg)
