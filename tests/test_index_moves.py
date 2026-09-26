"""tests/test_index_moves.py — tools/index_moves.py against a recorded ^NSEI history.

Spec: tiffin-coffee v6 §H HOCKEY ("Nifty -5% in a week"), ledger D37 hockey ladder
(Nifty drawdown rungs). E2: every value Stamped. No network — the fixture was recorded
once on 26-Sep-2026 (last session 25-Sep).
"""
from __future__ import annotations

import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from tools.index_moves import IndexMoves, fetch_nifty_moves, parse_index_history

FIXTURE = Path(__file__).parent / "fixtures" / "yf_nsei_history.json"
ROWS: list[dict[str, object]] = json.loads(FIXTURE.read_text())["rows"]


def _pct(now: str, then: str) -> Decimal:
    return ((Decimal(now) / Decimal(then) - 1) * 100).quantize(Decimal("0.01"),
                                                               rounding=ROUND_HALF_UP)


class TestParse:
    def test_week_change_is_last_close_vs_close_seven_days_earlier(self) -> None:
        m = parse_index_history(ROWS, "^NSEI", "yfinance:^NSEI")
        # 25-Sep close 23140.5 vs 18-Sep close 23346.4
        assert m.week_change_pct.value == _pct("23140.5", "23346.4")

    def test_drawdown_is_from_the_52_week_high(self) -> None:
        m = parse_index_history(ROWS, "^NSEI", "yfinance:^NSEI")
        high = max(Decimal(str(r["high"])) for r in ROWS)
        assert m.drawdown_pct.value == _pct("23140.5", str(high))
        assert m.drawdown_pct.value < 0

    def test_every_value_is_stamped_with_the_last_session(self) -> None:
        m = parse_index_history(ROWS, "^NSEI", "yfinance:^NSEI")
        assert isinstance(m, IndexMoves)
        for st in (m.level, m.week_change_pct, m.drawdown_pct):
            assert st is not None
            assert st.source == "yfinance:^NSEI" and st.as_of == "2026-09-25"
        assert m.level is not None and m.level.value == Decimal("23140.5")

    def test_drawdown_never_positive(self) -> None:
        rows = [{"date": "2026-09-01", "high": 100, "close": 100},
                {"date": "2026-09-10", "high": 110, "close": 110}]
        m = parse_index_history(rows, "^NSEI", "t")
        assert m.drawdown_pct.value == 0
        assert m.week_change_pct.value == Decimal("10.00")

    def test_too_short_history_raises(self) -> None:
        with pytest.raises(ValueError, match="week"):
            parse_index_history(ROWS[-3:], "^NSEI", "t")

    def test_empty_history_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_index_history([], "^NSEI", "t")


class TestFetch:
    @patch("tools.index_moves.yf.Ticker")
    def test_fetch_reads_history_frame(self, ticker: MagicMock) -> None:
        idx = pd.DatetimeIndex([pd.Timestamp(str(r["date"])).tz_localize("Asia/Kolkata")
                                for r in ROWS])
        frame = pd.DataFrame({"High": [r["high"] for r in ROWS],
                              "Close": [r["close"] for r in ROWS]}, index=idx)
        ticker.return_value.history.return_value = frame
        m = fetch_nifty_moves()
        assert m.symbol == "^NSEI"
        assert m.week_change_pct.value == _pct("23140.5", "23346.4")
        assert m.week_change_pct.source == "yfinance:^NSEI"

    @patch("tools.index_moves.yf.Ticker")
    def test_empty_frame_is_value_error(self, ticker: MagicMock) -> None:
        ticker.return_value.history.return_value = pd.DataFrame({"High": [], "Close": []})
        with pytest.raises(ValueError):
            fetch_nifty_moves()

    @patch("tools.index_moves.yf.Ticker")
    def test_network_error_is_value_error(self, ticker: MagicMock) -> None:
        ticker.return_value.history.side_effect = OSError("down")
        with pytest.raises(ValueError, match="down"):
            fetch_nifty_moves()
