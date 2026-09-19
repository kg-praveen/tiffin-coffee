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

from tools.prices import PriceSnapshot, fetch_price
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
        assert snap.price.value == Decimal("1858.30")
        assert snap.low_52w.value == Decimal("1358.35")
        assert snap.high_52w.value == Decimal("2006.45")

    @patch("tools.prices.yf.Ticker")
    def test_hdfcbank_returns_stamped_snapshot(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value = _make_mock_ticker("yf_hdfcbank.json")
        snap = fetch_price("HDFCBANK.NS")

        assert snap.symbol == "HDFCBANK"
        assert snap.price.value == Decimal("1706.85")
        assert snap.low_52w.value == Decimal("1363.55")
        assert snap.high_52w.value == Decimal("1880.00")

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
