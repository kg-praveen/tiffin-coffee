"""tools/prices.py — fetch last close, 52-week low/high from yfinance.

Spec: E1 (market data lives nowhere — fetched live every run), E2 (Stamped), E3 (freshness).
Returns Stamped values only. Network failures raise; the caller decides whether to DROP.
"""
from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

import yfinance as yf

from tools.stamped import Stamped

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class PriceSnapshot:
    """All price fields for one ticker, each individually stamped (E2)."""

    symbol: str
    price: Stamped[Decimal]
    low_52w: Stamped[Decimal]
    high_52w: Stamped[Decimal]
    # the session before the last trade (tiffin v6 §H HOCKEY "a name -10% in a day");
    # None when the source did not give it — the day-move check then says it was not run
    prev_close: Stamped[Decimal] | None = None


@dataclass(frozen=True)
class BatchPriceResult:
    """Result of a batch price fetch — successes keyed by symbol, failures with reasons."""

    prices: dict[str, PriceSnapshot] = field(default_factory=dict)
    failures: dict[str, str] = field(default_factory=dict)


def fetch_price(yf_ticker: str) -> PriceSnapshot:
    """Fetch the latest close price and 52-week range for a single NSE ticker.

    Raises ValueError if the ticker does not resolve or data is missing.
    """
    ticker = yf.Ticker(yf_ticker)
    info = ticker.info
    if not info or info.get("regularMarketPrice") is None:
        raise ValueError(f"ticker {yf_ticker!r} did not resolve or returned no price")

    source = f"yfinance:{yf_ticker}"
    # The LAST traded price (Friday's close on a weekend, live LTP in market hours),
    # stamped with the time it traded. regularMarketPreviousClose is the session BEFORE
    # that — on 26-Sep (Sat) it returned Thursday's close (fixed 26-Sep-2026).
    traded = info.get("regularMarketTime")
    now = (datetime.fromtimestamp(int(traded), tz=UTC).isoformat(timespec="seconds")
           if isinstance(traded, (int, float)) and traded > 0
           else datetime.now(UTC).isoformat(timespec="seconds"))

    price_raw = info.get("regularMarketPrice") or info.get("regularMarketPreviousClose")
    low_raw = info.get("fiftyTwoWeekLow")
    high_raw = info.get("fiftyTwoWeekHigh")

    if price_raw is None:
        raise ValueError(f"{yf_ticker}: no price available")
    if low_raw is None or high_raw is None:
        raise ValueError(f"{yf_ticker}: 52-week range not available")
    prev_raw = info.get("regularMarketPreviousClose")

    return PriceSnapshot(
        symbol=yf_ticker.removesuffix(".NS"),
        price=Stamped(value=Decimal(str(price_raw)), source=source, as_of=now),
        low_52w=Stamped(value=Decimal(str(low_raw)), source=source, as_of=now),
        high_52w=Stamped(value=Decimal(str(high_raw)), source=source, as_of=now),
        prev_close=(Stamped(value=Decimal(str(prev_raw)), source=source, as_of=now)
                    if prev_raw is not None else None),
    )


def fetch_prices_batch(yf_tickers: Sequence[str]) -> BatchPriceResult:
    """Fetch prices + 52-week range for multiple tickers. Spec: tiffin-coffee v6 §4.

    Per-ticker failures are captured, not raised — the caller uses
    BatchPriceResult.failures to report drops with DropReason.PRICE_FETCH_FAILED.
    """
    prices: dict[str, PriceSnapshot] = {}
    failures: dict[str, str] = {}

    for yf_ticker in yf_tickers:
        symbol = yf_ticker.removesuffix(".NS")
        try:
            snap = fetch_price(yf_ticker)
            prices[snap.symbol] = snap
        except (ValueError, Exception) as exc:  # noqa: BLE001
            reason = str(exc)
            failures[symbol] = reason
            log.warning("price fetch failed for %s: %s", yf_ticker, reason)

    log.info(
        "batch fetch: %d OK, %d failed out of %d tickers",
        len(prices),
        len(failures),
        len(yf_tickers),
    )
    return BatchPriceResult(prices=prices, failures=failures)
