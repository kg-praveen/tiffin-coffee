"""tests/test_prices.py — recorded-fixture tests for tools/prices.py.

Spec: E2 (every value Stamped), E3 (freshness — fetched this run). CI runs with
NO NETWORK — tests use recorded fixtures (VCR-style JSON).
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.prices import BatchPriceResult, PriceSnapshot, fetch_price, fetch_prices_batch
from tools.stamped import Stamped

FIXTURES = Path(__file__).parent / "fixtures"


def _make_mock_ticker(fixture_file: str) -> MagicMock:
    """Build a mock yfinance.Ticker whose .info returns the recorded fixture."""
    data = json.loads((FIXTURES / fixture_file).read_text())
    mock = MagicMock()
    mock.info = data
    return mock


class TestFetchPriceFromFixture:
    """Tests that run against recorded fixtures — no network."""

    @patch("tools.prices.yf.Ticker")
    def test_infy_returns_stamped_snapshot(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value = _make_mock_ticker("yf_infy.json")
        snap = fetch_price("INFY.NS")

        assert isinstance(snap, PriceSnapshot)
        assert snap.symbol == "INFY"
        assert isinstance(snap.price, Stamped)
        assert isinstance(snap.low_52w, Stamped)
        assert isinstance(snap.high_52w, Stamped)
        assert snap.price.value == Decimal("1862.45")   # last traded, not previous close
        assert snap.low_52w.value == Decimal("1358.35")
        assert snap.high_52w.value == Decimal("2006.45")

    @patch("tools.prices.yf.Ticker")
    def test_hdfcbank_returns_stamped_snapshot(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value = _make_mock_ticker("yf_hdfcbank.json")
        snap = fetch_price("HDFCBANK.NS")

        assert snap.symbol == "HDFCBANK"
        assert snap.price.value == Decimal("1712.50")
        assert snap.low_52w.value == Decimal("1363.55")
        assert snap.high_52w.value == Decimal("1880.00")

    @patch("tools.prices.yf.Ticker")
    def test_weekend_uses_last_close_and_its_time(self, mock_ticker_cls: MagicMock) -> None:
        """26-Sep-2026 (Sat): Infosys closed 1000.20 on Friday; previousClose 1014.50 is
        Thursday. The plate must use Friday's close, stamped with Friday's time."""
        mock = MagicMock()
        mock.info = {"regularMarketPrice": 1000.2, "regularMarketPreviousClose": 1014.5,
                     "regularMarketTime": 1790329500, "marketState": "CLOSED",
                     "fiftyTwoWeekLow": 982.4, "fiftyTwoWeekHigh": 1700.0}
        mock_ticker_cls.return_value = mock
        snap = fetch_price("INFY.NS")
        assert snap.price.value == Decimal("1000.2")
        assert snap.price.as_of.startswith("2026-09-25")

    @patch("tools.prices.yf.Ticker")
    def test_missing_ticker_raises(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value = _make_mock_ticker("yf_missing.json")
        with pytest.raises(ValueError, match="did not resolve"):
            fetch_price("DOESNOTEXIST.NS")


class TestStampedEnforcement:
    """E2 contract: no value returned unstamped."""

    @patch("tools.prices.yf.Ticker")
    def test_price_is_stamped(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value = _make_mock_ticker("yf_infy.json")
        snap = fetch_price("INFY.NS")
        assert hasattr(snap.price, "value")
        assert hasattr(snap.price, "source")
        assert hasattr(snap.price, "as_of")
        assert snap.price.source.startswith("yfinance:")

    @patch("tools.prices.yf.Ticker")
    def test_52w_low_is_stamped(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value = _make_mock_ticker("yf_infy.json")
        snap = fetch_price("INFY.NS")
        assert isinstance(snap.low_52w, Stamped)
        assert snap.low_52w.as_of  # non-empty

    @patch("tools.prices.yf.Ticker")
    def test_52w_high_is_stamped(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value = _make_mock_ticker("yf_infy.json")
        snap = fetch_price("INFY.NS")
        assert isinstance(snap.high_52w, Stamped)
        assert snap.high_52w.as_of  # non-empty

    @patch("tools.prices.yf.Ticker")
    def test_values_are_decimal_not_float(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value = _make_mock_ticker("yf_infy.json")
        snap = fetch_price("INFY.NS")
        assert isinstance(snap.price.value, Decimal)
        assert isinstance(snap.low_52w.value, Decimal)
        assert isinstance(snap.high_52w.value, Decimal)

    @patch("tools.prices.yf.Ticker")
    def test_prev_close_is_stamped_for_the_day_move(self, mock_ticker_cls: MagicMock) -> None:
        """tiffin v6 §H HOCKEY 'name -10% in a day' needs the previous session's close."""
        mock_ticker_cls.return_value = _make_mock_ticker("yf_infy.json")
        snap = fetch_price("INFY.NS")
        assert snap.prev_close is not None
        assert snap.prev_close.value == Decimal("1858.30")
        assert snap.prev_close.source == "yfinance:INFY.NS"

    @patch("tools.prices.yf.Ticker")
    def test_prev_close_missing_is_none_not_a_guess(self, mock_ticker_cls: MagicMock) -> None:
        mock = MagicMock()
        mock.info = {"regularMarketPrice": 100.0, "fiftyTwoWeekLow": 90.0,
                     "fiftyTwoWeekHigh": 120.0}
        mock_ticker_cls.return_value = mock
        assert fetch_price("X.NS").prev_close is None


class TestFetchPricesBatch:
    """Tests for batch price fetching — spec: tiffin-coffee v6 §4 full sweep."""

    @patch("tools.prices.yf.Ticker")
    def test_batch_returns_all_successes(self, mock_ticker_cls: MagicMock) -> None:
        fixtures = {"INFY.NS": "yf_infy.json", "HDFCBANK.NS": "yf_hdfcbank.json"}
        mock_ticker_cls.side_effect = lambda t: _make_mock_ticker(fixtures[t])

        result = fetch_prices_batch(["INFY.NS", "HDFCBANK.NS"])

        assert isinstance(result, BatchPriceResult)
        assert len(result.prices) == 2
        assert "INFY" in result.prices
        assert "HDFCBANK" in result.prices
        assert len(result.failures) == 0

    @patch("tools.prices.yf.Ticker")
    def test_batch_captures_failures_without_raising(self, mock_ticker_cls: MagicMock) -> None:
        def _side_effect(ticker: str) -> MagicMock:
            if ticker == "INFY.NS":
                return _make_mock_ticker("yf_infy.json")
            return _make_mock_ticker("yf_missing.json")

        mock_ticker_cls.side_effect = _side_effect

        result = fetch_prices_batch(["INFY.NS", "DOESNOTEXIST.NS"])

        assert len(result.prices) == 1
        assert "INFY" in result.prices
        assert len(result.failures) == 1
        assert "DOESNOTEXIST" in result.failures

    @patch("tools.prices.yf.Ticker")
    def test_batch_empty_input(self, mock_ticker_cls: MagicMock) -> None:
        result = fetch_prices_batch([])
        assert len(result.prices) == 0
        assert len(result.failures) == 0

    @patch("tools.prices.yf.Ticker")
    def test_batch_all_failures(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value = _make_mock_ticker("yf_missing.json")

        result = fetch_prices_batch(["BAD1.NS", "BAD2.NS"])

        assert len(result.prices) == 0
        assert len(result.failures) == 2

    @patch("tools.prices.yf.Ticker")
    def test_batch_preserves_stamped_values(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value = _make_mock_ticker("yf_infy.json")

        result = fetch_prices_batch(["INFY.NS"])

        snap = result.prices["INFY"]
        assert isinstance(snap.price, Stamped)
        assert isinstance(snap.price.value, Decimal)
        assert snap.price.source.startswith("yfinance:")
