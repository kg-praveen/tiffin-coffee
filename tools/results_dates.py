"""tools/results_dates.py — quarterly results announcement dates per stock.

Spec: E3 (osep v7 ENGINE CONTRACT) — "triggers = armable only on a fresh-EPS basis
younger than the last result". The engine needs the date of the latest results; this
adapter fetches ALL recent announcement dates (past and scheduled) so a replay can
ask "what was the latest result on day X" for any X (UC5 clock scenarios).

Source: yfinance `get_earnings_dates` (Yahoo). Stamped (E2). Network — never in CI.
"""
from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

import yfinance as yf

from tools.stamped import Stamped

log = logging.getLogger(__name__)
_LIMIT = 8   # two years of quarters: enough for any replay window


@dataclass(frozen=True)
class BatchResultDates:
    """symbol → Stamped tuple of ISO dates (sorted, past and scheduled)."""

    dates: dict[str, Stamped[tuple[str, ...]]] = field(default_factory=dict)
    failures: dict[str, str] = field(default_factory=dict)


def fetch_result_dates(yf_ticker: str) -> Stamped[tuple[str, ...]]:
    """All recent results announcement dates for one ticker. Raises ValueError if none."""
    try:
        df = yf.Ticker(yf_ticker).get_earnings_dates(limit=_LIMIT)
    except Exception as exc:
        raise ValueError(f"{yf_ticker}: earnings dates unavailable ({exc})") from exc
    if df is None or len(df.index) == 0:
        raise ValueError(f"{yf_ticker}: no earnings dates")
    dates = tuple(sorted({str(ts)[:10] for ts in df.index}))
    return Stamped(value=dates, source=f"yfinance:{yf_ticker}:earnings_dates",
                   as_of=datetime.now(UTC).isoformat(timespec="seconds"))


def fetch_result_dates_batch(yf_tickers: Sequence[str]) -> BatchResultDates:
    """Per-ticker failures are captured, not raised (the engine then fails closed)."""
    out: dict[str, Stamped[tuple[str, ...]]] = {}
    failures: dict[str, str] = {}
    for t in yf_tickers:
        sym = t.removesuffix(".NS")
        try:
            out[sym] = fetch_result_dates(t)
        except ValueError as exc:
            failures[sym] = str(exc)
            log.warning("result dates failed for %s: %s", t, exc)
    return BatchResultDates(dates=out, failures=failures)
