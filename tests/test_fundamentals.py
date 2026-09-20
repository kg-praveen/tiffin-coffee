"""tests/test_fundamentals.py — recorded-fixture tests for tools/fundamentals.py.

Spec: E2 (every value Stamped), E3 (freshness). CI runs with NO NETWORK.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.fundamentals import (
    BatchFundamentalsResult,
    FundamentalsSnapshot,
    fetch_fundamentals,
    fetch_fundamentals_batch,
)
from tools.stamped import Stamped

FIXTURES = Path(__file__).parent / "fixtures"


def _make_mock_ticker(fixture_file: str) -> MagicMock:
    data = json.loads((FIXTURES / fixture_file).read_text())
    mock = MagicMock()
    mock.info = data
    return mock


class TestFetchFundamentals:
    @patch("tools.fundamentals.yf.Ticker")
    def test_hdfcbank_returns_all_fields(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value = _make_mock_ticker("yf_hdfcbank_full.json")
        snap = fetch_fundamentals("HDFCBANK.NS")

        assert isinstance(snap, FundamentalsSnapshot)
        assert snap.symbol == "HDFCBANK"
        assert snap.pe_trailing is not None
        assert snap.pe_trailing.value == Decimal("13.1")
        assert snap.pb_ratio is not None
        assert snap.pb_ratio.value == Decimal("1.8")
        assert snap.eps_ttm is not None
        assert snap.eps_ttm.value == Decimal("130.3")
        assert snap.book_value_ps is not None
        assert snap.book_value_ps.value == Decimal("948.25")

    @patch("tools.fundamentals.yf.Ticker")
    def test_roe_converted_from_ratio_to_pct(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value = _make_mock_ticker("yf_hdfcbank_full.json")
        snap = fetch_fundamentals("HDFCBANK.NS")
        assert snap.roe_pct is not None
        assert snap.roe_pct.value == Decimal("13.8")

    @patch("tools.fundamentals.yf.Ticker")
    def test_sbin_roe(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value = _make_mock_ticker("yf_sbin_full.json")
        snap = fetch_fundamentals("SBIN.NS")
        assert snap.roe_pct is not None
        assert snap.roe_pct.value == Decimal("18.0")

    @patch("tools.fundamentals.yf.Ticker")
    def test_values_are_stamped(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value = _make_mock_ticker("yf_infy_full.json")
        snap = fetch_fundamentals("INFY.NS")
        assert isinstance(snap.pe_trailing, Stamped)
        assert snap.pe_trailing.source == "yfinance:INFY.NS"
        assert snap.pe_trailing.as_of  # non-empty

    @patch("tools.fundamentals.yf.Ticker")
    def test_values_are_decimal(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value = _make_mock_ticker("yf_infy_full.json")
        snap = fetch_fundamentals("INFY.NS")
        fields = [snap.pe_trailing, snap.pb_ratio, snap.eps_ttm, snap.book_value_ps, snap.roe_pct]
        for field in fields:
            assert field is not None
            assert isinstance(field.value, Decimal)

    @patch("tools.fundamentals.yf.Ticker")
    def test_missing_ticker_raises(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value = _make_mock_ticker("yf_missing.json")
        with pytest.raises(ValueError, match="did not resolve"):
            fetch_fundamentals("DOESNOTEXIST.NS")

    @patch("tools.fundamentals.yf.Ticker")
    def test_partial_data_returns_none_fields(self, mock_cls: MagicMock) -> None:
        mock = MagicMock()
        mock.info = {"regularMarketPrice": 100.0}
        mock_cls.return_value = mock
        snap = fetch_fundamentals("PARTIAL.NS")
        assert snap.pe_trailing is None
        assert snap.pb_ratio is None
        assert snap.roe_pct is None


class TestFetchFundamentalsBatch:
    @patch("tools.fundamentals.yf.Ticker")
    def test_batch_successes(self, mock_cls: MagicMock) -> None:
        fixtures = {"HDFCBANK.NS": "yf_hdfcbank_full.json", "SBIN.NS": "yf_sbin_full.json"}
        mock_cls.side_effect = lambda t: _make_mock_ticker(fixtures[t])

        result = fetch_fundamentals_batch(["HDFCBANK.NS", "SBIN.NS"])
        assert isinstance(result, BatchFundamentalsResult)
        assert len(result.fundamentals) == 2
        assert "HDFCBANK" in result.fundamentals
        assert "SBIN" in result.fundamentals
        assert len(result.failures) == 0

    @patch("tools.fundamentals.yf.Ticker")
    def test_batch_captures_failures(self, mock_cls: MagicMock) -> None:
        def _side(t: str) -> MagicMock:
            if t == "INFY.NS":
                return _make_mock_ticker("yf_infy_full.json")
            return _make_mock_ticker("yf_missing.json")

        mock_cls.side_effect = _side
        result = fetch_fundamentals_batch(["INFY.NS", "BAD.NS"])
        assert len(result.fundamentals) == 1
        assert len(result.failures) == 1
        assert "BAD" in result.failures

    @patch("tools.fundamentals.yf.Ticker")
    def test_batch_empty(self, mock_cls: MagicMock) -> None:
        result = fetch_fundamentals_batch([])
        assert len(result.fundamentals) == 0
        assert len(result.failures) == 0
