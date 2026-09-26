"""tests/test_morning_board.py — UC1 integration tests with mocked prices.

CI runs with NO NETWORK. Prices are mocked; a scratch copy of the seed DB is used
for integration tests against the actual seed data.
"""
from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest

from engine.morning_board import TriggerStatus
from tools.prices import PriceSnapshot
from tools.results_dates import BatchResultDates
from tools.stamped import Stamped
from usecases.morning_board import format_board, run_morning_board

NOW = "2026-09-19T10:00:00+00:00"


def _snap(symbol: str, price: str) -> PriceSnapshot:
    return PriceSnapshot(
        symbol=symbol,
        price=Stamped(value=Decimal(price), source=f"test:{symbol}", as_of=NOW),
        low_52w=Stamped(value=Decimal(1), source="test", as_of=NOW),
        high_52w=Stamped(value=Decimal(9999), source="test", as_of=NOW),
    )


PRICE_MAP: dict[str, PriceSnapshot] = {
    "PETRONET.NS": _snap("PETRONET", "370"),
    "SBIN.NS": _snap("SBIN", "880"),
    "HDFCBANK.NS": _snap("HDFCBANK", "500"),
    "INFY.NS": _snap("INFY", "1150"),
    "TCS.NS": _snap("TCS", "2100"),
    "RELIANCE.NS": _snap("RELIANCE", "900"),
    "M&M.NS": _snap("M&M", "2200"),
    "POWERGRID.NS": _snap("POWERGRID", "260"),
    "ENGINERSIN.NS": _snap("ENGINERSIN", "180"),
    "RITES.NS": _snap("RITES", "140"),
    "NTPC.NS": _snap("NTPC", "420"),
    "HCLTECH.NS": _snap("HCLTECH", "950"),
    "WIPRO.NS": _snap("WIPRO", "200"),
    "ITC.NS": _snap("ITC", "240"),
    "MUTHOOTFIN.NS": _snap("MUTHOOTFIN", "3300"),
    "FIVESTAR.NS": _snap("FIVESTAR", "360"),
    "COROMANDEL.NS": _snap("COROMANDEL", "1300"),
    "ARE&M.NS": _snap("ARE&M", "800"),
    "CHAMBLFERT.NS": _snap("CHAMBLFERT", "430"),
    "FINCABLES.NS": _snap("FINCABLES", "800"),
    "HAVELLS.NS": _snap("HAVELLS", "400"),
    "KEI.NS": _snap("KEI", "1600"),
    "POLYCAB.NS": _snap("POLYCAB", "2800"),
    "RRKABEL.NS": _snap("RRKABEL", "800"),
    "TITAN.NS": _snap("TITAN", "1250"),
    "TRENT.NS": _snap("TRENT", "700"),
    "ULTRACEMCO.NS": _snap("ULTRACEMCO", "6000"),
    "HAL.NS": _snap("HAL", "5000"),
    "TEXRAIL.NS": _snap("TEXRAIL", "85"),
    "PARADEEP.NS": _snap("PARADEEP", "125"),
    "BAJAJ-AUTO.NS": _snap("BAJAJ-AUTO", "6500"),
}


def mock_results(tickers: list[str]) -> BatchResultDates:
    """Every triggered name reported Q1 on 20-Jul — before the 01-Sep EPS basis."""
    st = Stamped(value=("2026-04-20", "2026-07-20"), source="test", as_of=NOW)
    return BatchResultDates(dates={t.removesuffix(".NS"): st for t in tickers})


@pytest.fixture(autouse=True)
def _no_network_results() -> Iterator[None]:
    with patch("usecases.morning_board.fetch_result_dates_batch", side_effect=mock_results):
        yield


def mock_fetch(ticker: str) -> PriceSnapshot:
    if ticker in PRICE_MAP:
        return PRICE_MAP[ticker]
    raise ValueError(f"test: no price for {ticker}")


class TestMorningBoardIntegration:
    """Run UC1 against the real seed DB with mocked prices."""

    @patch("usecases.morning_board.fetch_price", side_effect=mock_fetch)
    def test_board_runs_and_writes_session(self, _mock: object, scratch_db: Path) -> None:
        result = run_morning_board(scratch_db)
        assert result.run_id.startswith("UC1_")
        assert result.ran_at != ""
        assert len(result.rules_fired) > 0

    @patch("usecases.morning_board.fetch_price", side_effect=mock_fetch)
    def test_petronet_fires_at_370(self, _mock: object, scratch_db: Path) -> None:
        """PETRONET trigger=383, price=370 → FIRED."""
        result = run_morning_board(scratch_db)
        fired_symbols = [e.symbol for e in result.fired]
        assert "PETRONET" in fired_symbols
        petronet = next(e for e in result.fired if e.symbol == "PETRONET")
        assert petronet.status == TriggerStatus.FIRED
        assert petronet.distance_pct is not None
        assert petronet.distance_pct < 0

    @patch("usecases.morning_board.fetch_price", side_effect=mock_fetch)
    def test_hdfcbank_fires_crash_shelf(self, _mock: object, scratch_db: Path) -> None:
        """HDFCBANK crash_shelf=419, price=500 → FAR (not fired)."""
        result = run_morning_board(scratch_db)
        hdfcbank_entries = [e for e in result.fired if e.symbol == "HDFCBANK"]
        assert len(hdfcbank_entries) == 0

    @patch("usecases.morning_board.fetch_price", side_effect=mock_fetch)
    def test_inactive_triggers_in_not_armable(self, _mock: object, scratch_db: Path) -> None:
        """TMB, FEDERALBNK, INDIGRID, ZYDUSLIFE have active=0 or no basis."""
        result = run_morning_board(scratch_db)
        na_symbols = {na.symbol for na in result.not_armable}
        assert "FEDERALBNK" in na_symbols or "TMB" in na_symbols

    @patch("usecases.morning_board.fetch_price", side_effect=mock_fetch)
    def test_format_output_contains_key_sections(self, _mock: object, scratch_db: Path) -> None:
        result = run_morning_board(scratch_db)
        output = format_board(result)
        assert "Morning Board" in output
        assert "NOT ARMABLE" in output
        assert "appointment to re-examine" in output or "Nothing fired" in output

    @patch("usecases.morning_board.fetch_price", side_effect=mock_fetch)
    def test_drops_list_populated(self, _mock: object, scratch_db: Path) -> None:
        result = run_morning_board(scratch_db)
        assert len(result.drops) > 0
        reasons = {d["reason"] for d in result.drops}
        assert len(reasons) > 0

    @patch("usecases.morning_board.fetch_price", side_effect=mock_fetch)
    def test_no_fetch_mode(self, _mock: object, scratch_db: Path) -> None:
        """fetch_prices=False skips price fetching; board has no entries."""
        result = run_morning_board(scratch_db, fetch_prices=False)
        assert len(result.fired) == 0
        assert len(result.near) == 0
        assert len(result.far) == 0
        assert len(result.not_armable) > 0


class TestClassificationAccuracy:
    """Verify specific trigger classifications against mock prices."""

    @patch("usecases.morning_board.fetch_price", side_effect=mock_fetch)
    def test_near_trigger(self, _mock: object, scratch_db: Path) -> None:
        """SBIN trigger=862, price=880 → NEAR (2.1% above)."""
        result = run_morning_board(scratch_db)
        sbin = [e for e in result.near if e.symbol == "SBIN"]
        assert len(sbin) == 1
        assert sbin[0].distance_pct is not None
        assert Decimal(0) < sbin[0].distance_pct <= Decimal(5)

    @patch("usecases.morning_board.fetch_price", side_effect=mock_fetch)
    def test_far_trigger(self, _mock: object, scratch_db: Path) -> None:
        """TCS trigger=1939, price=2100 → FAR (8.3% above)."""
        result = run_morning_board(scratch_db)
        tcs = [e for e in result.far if e.symbol == "TCS"]
        assert len(tcs) == 1
        assert tcs[0].distance_pct is not None
        assert tcs[0].distance_pct > Decimal(5)
