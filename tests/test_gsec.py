"""tests/test_gsec.py — recorded-fixture tests for tools/gsec.py.

Spec: osep v7 MoS anchor — GoI yield ladder. E2 (Stamped), E3 (fresh each session).
CI runs with NO NETWORK: both sources are patched in every test.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.gsec import fetch_gsec_yield, parse_cnbc
from tools.stamped import Stamped

FIXTURES = Path(__file__).parent / "fixtures"
CNBC = json.loads((FIXTURES / "cnbc_in10y.json").read_text())


def _yf_mock(fixture_file: str) -> MagicMock:
    mock = MagicMock()
    mock.info = json.loads((FIXTURES / fixture_file).read_text())
    return mock


class TestCnbcSource:
    """Primary source since 26-Sep-2026 (yfinance IN10Y.SI returns 404)."""

    @patch("tools.gsec._get_json", return_value=CNBC)
    def test_cnbc_first(self, _m: MagicMock) -> None:
        result = fetch_gsec_yield()
        assert result.value == Decimal("7.119")
        assert result.source == "cnbc:IN10Y-IN"
        assert result.as_of.startswith("2026-09-25")

    def test_parse_rejects_garbage(self) -> None:
        with pytest.raises(ValueError, match="unexpected payload"):
            parse_cnbc({"FormattedQuoteResult": {"FormattedQuote": [{"last": "n/a"}]}})
        with pytest.raises(ValueError, match="unexpected payload"):
            parse_cnbc({})

    @patch("tools.gsec.yf.Ticker")
    @patch("tools.gsec._get_json", side_effect=OSError("offline"))
    def test_falls_back_to_yfinance(self, _m: MagicMock, yf_cls: MagicMock) -> None:
        yf_cls.return_value = _yf_mock("yf_gsec_in10y.json")
        result = fetch_gsec_yield()
        assert result.value == Decimal("6.82") and result.source.startswith("yfinance:")

    @patch("tools.gsec.yf.Ticker")
    @patch("tools.gsec._get_json", side_effect=OSError("offline"))
    def test_both_down_names_each_failure(self, _m: MagicMock, yf_cls: MagicMock) -> None:
        mock = MagicMock()
        mock.info = {"regularMarketPrice": None}
        yf_cls.return_value = mock
        with pytest.raises(ValueError, match=r"not available.*CNBC.*yfinance"):
            fetch_gsec_yield()


class TestGsecStampedEnforcement:
    """E2 contract: yield is never returned as a bare number."""

    @patch("tools.gsec._get_json", return_value=CNBC)
    def test_value_is_stamped_decimal(self, _m: MagicMock) -> None:
        result = fetch_gsec_yield()
        assert isinstance(result, Stamped)
        assert isinstance(result.value, Decimal) and not isinstance(result.value, float)
        assert result.source and result.as_of
