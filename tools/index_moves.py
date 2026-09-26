"""tools/index_moves.py — Nifty 50 moves for the HOCKEY check (^NSEI via yfinance).

Spec: tiffin-coffee v6 §H HOCKEY ("Nifty -5% in a week"), §TWO-POCKET ladder and
ledger D37 (rungs at a Nifty drawdown of -15% / -25%). E1: fetched live every run;
E2: every value Stamped with the index's last session date.

Definitions (data shaping only — the thresholds live in policy, the rule in engine/):
  week change = last close vs the last close on or before 7 calendar days earlier
  drawdown    = last close vs the highest daily high of the past 52 weeks (≤ 0)
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import yfinance as yf

from tools.stamped import Stamped

NIFTY_TICKER = "^NSEI"
_WEEK = timedelta(days=7)
_YEAR = timedelta(days=365)
_CENT = Decimal("0.01")


@dataclass(frozen=True)
class IndexMoves:
    """Index moves for one run. `level` is None when a scenario moved the index without
    a recorded level (the percentages are all the engine reads)."""

    symbol: str
    level: Stamped[Decimal] | None
    week_change_pct: Stamped[Decimal]
    drawdown_pct: Stamped[Decimal]


def _pct(now: Decimal, then: Decimal) -> Decimal:
    return ((now / then - 1) * 100).quantize(_CENT, rounding=ROUND_HALF_UP)


def parse_index_history(rows: Sequence[Mapping[str, Any]], symbol: str,
                        source: str) -> IndexMoves:
    """rows = [{"date": "YYYY-MM-DD", "high": x, "close": y}, ...] (any order).

    Raises ValueError when the history cannot answer both questions (no silent guess)."""
    if not rows:
        raise ValueError(f"{symbol}: empty history")
    hist = sorted((date.fromisoformat(str(r["date"])[:10]), Decimal(str(r["high"])),
                   Decimal(str(r["close"]))) for r in rows)
    last_day, _, last_close = hist[-1]
    week_ago = [c for d, _, c in hist if d <= last_day - _WEEK]
    if not week_ago:
        raise ValueError(f"{symbol}: history has no close a week before {last_day}")
    high = max(h for d, h, _ in hist if d > last_day - _YEAR)
    as_of = last_day.isoformat()

    def st(v: Decimal) -> Stamped[Decimal]:
        return Stamped(value=v, source=source, as_of=as_of)

    return IndexMoves(
        symbol=symbol,
        level=st(last_close),
        week_change_pct=st(_pct(last_close, week_ago[-1])),
        drawdown_pct=st(min(Decimal(0), _pct(last_close, high))),
    )


def fetch_nifty_moves() -> IndexMoves:
    """Fetch one year of ^NSEI daily bars and derive the moves. NETWORK — never in CI.

    Raises ValueError on any failure; the caller reports the hockey check as not run."""
    try:
        frame = yf.Ticker(NIFTY_TICKER).history(period="1y", interval="1d")
        rows = [{"date": str(ix)[:10], "high": float(r["High"]), "close": float(r["Close"])}
                for ix, r in frame.iterrows()]
    except Exception as exc:  # any adapter failure is "no data", never a guess
        raise ValueError(f"{NIFTY_TICKER}: history fetch failed ({exc})") from exc
    return parse_index_history(rows, NIFTY_TICKER, f"yfinance:{NIFTY_TICKER}")
