"""tools/prices.py — fetch last close, 52-week low/high from yfinance.

Spec: E1 (market data lives nowhere — fetched live every run), E2 (Stamped), E3 (freshness).
Returns Stamped values only. Network failures raise; the caller decides whether to DROP.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

import yfinance as yf

from tools.stamped import Stamped


@dataclass(frozen=True)
class PriceSnapshot:
    """All price fields for one ticker, each individually stamped (E2)."""

    symbol: str
    price: Stamped[Decimal]
    low_52w: Stamped[Decimal]
    high_52w: Stamped[Decimal]


def fetch_price(yf_ticker: str) -> PriceSnapshot:
    """Fetch the latest close price and 52-week range for a single NSE ticker.

    Raises ValueError if the ticker does not resolve or data is missing.
    """
    ticker = yf.Ticker(yf_ticker)
    info = ticker.info
    if not info or info.get("regularMarketPrice") is None:
        raise ValueError(f"ticker {yf_ticker!r} did not resolve or returned no price")

    now = datetime.now(UTC).isoformat(timespec="seconds")
    source = f"yfinance:{yf_ticker}"

    price_raw = info.get("regularMarketPreviousClose") or info.get("regularMarketPrice")
    low_raw = info.get("fiftyTwoWeekLow")
    high_raw = info.get("fiftyTwoWeekHigh")

    if price_raw is None:
        raise ValueError(f"{yf_ticker}: no price available")
    if low_raw is None or high_raw is None:
        raise ValueError(f"{yf_ticker}: 52-week range not available")

    return PriceSnapshot(
        symbol=yf_ticker.removesuffix(".NS"),
        price=Stamped(value=Decimal(str(price_raw)), source=source, as_of=now),
        low_52w=Stamped(value=Decimal(str(low_raw)), source=source, as_of=now),
        high_52w=Stamped(value=Decimal(str(high_raw)), source=source, as_of=now),
    )
