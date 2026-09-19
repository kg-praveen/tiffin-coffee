"""tests/test_gsec.py — recorded-fixture tests for tools/gsec.py.

Spec: osep v7 MoS anchor — GoI yield ladder. E2 (Stamped), E3 (fresh each session).
CI runs with NO NETWORK.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.gsec import fetch_gsec_yield
from tools.stamped import Stamped

FIXTURES = Path(__file__).parent / "fixtures"


def _make_gsec_mock(fixture_file: str) -> MagicMock:
    data = json.loads((FIXTURES / fixture_file).read_text())
    mock = MagicMock()
    mock.info = data
    return mock


class TestFetchGsecYield:
    @patch("tools.gsec.yf.Ticker")
    def test_returns_stamped_yield(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value = _make_gsec_mock("yf_gsec_in10y.json")
        result = fetch_gsec_yield()

        assert isinstance(result, Stamped)
        assert isinstance(result.value, Decimal)
        assert result.value == Decimal("6.82")
        assert result.source.startswith("yfinance:")
        assert result.as_of  # non-empty

    @patch("tools.gsec.yf.Ticker")
    def test_yield_is_positive(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value = _make_gsec_mock("yf_gsec_in10y.json")
        result = fetch_gsec_yield()
        assert result.value > 0

    @patch("tools.gsec.yf.Ticker")
    def test_missing_data_raises(self, mock_ticker_cls: MagicMock) -> None:
        mock = MagicMock()
        mock.info = {"regularMarketPrice": None}
        mock_ticker_cls.return_value = mock
        with pytest.raises(ValueError, match="not available"):
            fetch_gsec_yield()


class TestGsecStampedEnforcement:
    """E2 contract: yield is never returned as a bare number."""

    @patch("tools.gsec.yf.Ticker")
    def test_value_has_source_and_as_of(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value = _make_gsec_mock("yf_gsec_in10y.json")
        result = fetch_gsec_yield()
        assert hasattr(result, "value")
        assert hasattr(result, "source")
        assert hasattr(result, "as_of")

    @patch("tools.gsec.yf.Ticker")
    def test_value_is_decimal_not_float(self, mock_ticker_cls: MagicMock) -> None:
        mock_ticker_cls.return_value = _make_gsec_mock("yf_gsec_in10y.json")
        result = fetch_gsec_yield()
        assert isinstance(result.value, Decimal)
        assert not isinstance(result.value, float)
