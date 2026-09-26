"""tests/test_scenarios.py — shocks and the market recording, no network."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

from tools.market_snapshot import (
    MarketSnapshot,
    load_snapshot,
    newest_snapshot,
    save_snapshot,
    snapshot_from_json,
    snapshot_to_json,
)
from usecases.scenarios import (
    SimContext,
    build_catalog,
    custom_scenario,
    drop_fundamentals,
    drop_prices,
    move_prices,
    reset_lows,
    shift_gsec,
)

MARKET_DIR = Path(__file__).parent / "fixtures" / "market"


@pytest.fixture(scope="module")
def snap() -> MarketSnapshot:
    path = newest_snapshot(MARKET_DIR)
    assert path is not None, "committed market recording missing"
    return load_snapshot(path)


CTX = SimContext(sector_of={"INFY": "IT_SERVICES", "GOLDBEES": "NON_EARNING"},
                 seats=("INFY",), policy={"hockey_rung1_nifty_drawdown_pct": "15",
                                          "hockey_rung2_nifty_drawdown_pct": "25",
                                          "gsec_yield_last_known": "7.04"})


class TestRecording:
    def test_round_trip_is_lossless(self, snap: MarketSnapshot, tmp_path: Path) -> None:
        save_snapshot(snap, tmp_path / "market_x.json")
        assert load_snapshot(tmp_path / "market_x.json") == snap
        assert snapshot_from_json(snapshot_to_json(snap)) == snap

    def test_every_value_is_stamped(self, snap: MarketSnapshot) -> None:
        p = snap.prices.prices["INFY"]
        assert p.price.source.startswith("yfinance:") and p.price.as_of

    def test_newest_by_date(self, tmp_path: Path) -> None:
        for d in ("2026-09-01", "2026-10-15", "2026-09-30"):
            (tmp_path / f"market_{d}.json").write_text("{}")
        found = newest_snapshot(tmp_path)
        assert found is not None and found.name == "market_2026-10-15.json"


class TestNseSectors:
    def test_reference_list_parses(self) -> None:
        from tools.nse_sectors import newest_reference, parse_nse_industry_csv
        ref = newest_reference()
        assert ref is not None
        ind = parse_nse_industry_csv(ref.read_text())
        assert len(ind) > 700
        assert ind["INFY"] == "Information Technology"
        assert ind["RECLTD"] == "Financial Services"
        assert "Industry" not in ind.values()

    def test_nse_symbol_uses_ticker_stem(self) -> None:
        from tools.nse_sectors import nse_symbol
        assert nse_symbol("REC", "RECLTD.NS") == "RECLTD"
        assert nse_symbol("TMCV", None) == "TMCV"

    def test_register_carries_nse_sector(self) -> None:
        import sqlite3
        db = Path(__file__).parent.parent / "db" / "pattaz.db"
        with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as con:
            got = dict(con.execute("SELECT symbol, nse_sector FROM names").fetchall())
        assert got["HDFCBANK"] == "Financial Services"
        assert got["REC"] == "Financial Services"          # matched via RECLTD
        assert got["NIFTYBEES"] is None                     # ETFs are not in NSE's list
        assert sum(v is not None for v in got.values()) >= 100

    def test_every_sector_gets_a_crash(self) -> None:
        ctx = SimContext(sector_of={"INFY": "IT_SERVICES", "SBIN": "LENDER"}, seats=(),
                         policy=CTX.policy, nse_sector_of={"INFY": "Information Technology",
                                                           "SBIN": "Financial Services"})
        names = {s.name for s in build_catalog(ctx)}
        assert {"app_sector_IT_SERVICES_-12", "app_sector_LENDER_-12",
                "nse_Information_Technology_-12", "nse_Financial_Services_-12"} <= names

    def test_nse_crash_moves_only_that_sector(self, snap: MarketSnapshot) -> None:
        ctx = SimContext(sector_of={}, seats=(), policy=CTX.policy,
                         nse_sector_of={"INFY": "Information Technology",
                                        "TCS": "Information Technology",
                                        "SBIN": "Financial Services"})
        sc = next(s for s in build_catalog(ctx) if s.name == "nse_Information_Technology_-12")
        out = sc.shock(snap, ctx)
        for sym in ("INFY", "TCS"):
            assert out.prices.prices[sym].price.value < snap.prices.prices[sym].price.value
        assert out.prices.prices["SBIN"] == snap.prices.prices["SBIN"]


class TestShocks:
    def test_move_scales_price_ratios_not_earnings(self, snap: MarketSnapshot) -> None:
        out = move_prices(snap, lambda s: Decimal(-10) if s == "INFY" else None, "t")
        old, new = snap.prices.prices["INFY"], out.prices.prices["INFY"]
        assert new.price.value == (old.price.value * Decimal("0.9")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP)
        assert new.low_52w.value == min(old.low_52w.value, new.price.value)
        assert new.price.source.startswith("sim:t<-yfinance:")      # E2 provenance kept
        f0, f1 = snap.fundamentals.fundamentals["INFY"], out.fundamentals.fundamentals["INFY"]
        assert f0.pe_trailing and f1.pe_trailing and f1.pe_trailing.value < f0.pe_trailing.value
        assert f1.eps_ttm == f0.eps_ttm and f1.roe_pct == f0.roe_pct
        assert out.prices.prices["TCS"] == snap.prices.prices["TCS"]  # untouched

    def test_market_move_spares_metal(self, snap: MarketSnapshot) -> None:
        crash = next(s for s in build_catalog(CTX) if s.name == "hockey_rung1")
        out = crash.shock(snap, CTX)
        assert out.prices.prices["GOLDBEES"] == snap.prices.prices["GOLDBEES"]
        assert out.prices.prices["INFY"].price.value < snap.prices.prices["INFY"].price.value

    def test_outage_moves_prices_to_failures(self, snap: MarketSnapshot) -> None:
        out = drop_prices(snap, lambda s: s == "INFY", "t")
        assert "INFY" not in out.prices.prices and "INFY" in out.prices.failures

    def test_fundamentals_down(self, snap: MarketSnapshot) -> None:
        out = drop_fundamentals(snap, "t")
        assert out.fundamentals.fundamentals == {} and out.fundamentals.failures

    def test_gsec_shift_uses_policy_fallback_when_unrecorded(self, snap: MarketSnapshot) -> None:
        base = MarketSnapshot(snap.recorded_at, snap.prices, snap.fundamentals, gsec=None)
        up = shift_gsec(base, Decimal(50), "t", CTX)
        assert up.gsec is not None and up.gsec.value == Decimal("7.54")
        assert "policy_fallback" in up.gsec.source
        assert shift_gsec(base, None, "t").gsec is None

    def test_reset_lows(self, snap: MarketSnapshot) -> None:
        out = reset_lows(snap, "t")
        assert all(p.low_52w.value == p.price.value for p in out.prices.prices.values())

    def test_what_if_composes(self, snap: MarketSnapshot) -> None:
        sc = custom_scenario(nifty_pct=Decimal(-10), name_pcts={"INFY": Decimal(-10)})
        out = sc.shock(snap, CTX)
        c = Decimal("0.01")
        once = (snap.prices.prices["INFY"].price.value * Decimal("0.9")).quantize(
            c, rounding=ROUND_HALF_UP)
        expected = (once * Decimal("0.9")).quantize(c, rounding=ROUND_HALF_UP)
        assert out.prices.prices["INFY"].price.value == expected
        assert "market -10%" in sc.title and "INFY -10%" in sc.title

    def test_catalog_names_unique_and_stable(self) -> None:
        names = [s.name for s in build_catalog(CTX)]
        assert len(names) == len(set(names))
        assert names[0] == "baseline" and "flash_INFY_-10" in names
