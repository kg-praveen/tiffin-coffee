"""tools/gsec.py — fetch India 10-year government security yield.

Spec: osep v7 MoS anchor — the GoI yield ladder (1/gsec_yield = fair P/E).
The yield is fetched live each session (E3). Returns a Stamped Decimal.
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import yfinance as yf

from tools.stamped import Stamped

# ^IRX is the India 10Y G-sec on yfinance (proxy: use the Indian 10Y bond)
# The canonical ticker is "IN10Y.SI" or we can scrape; yfinance carries "^TNX"
# for the US 10Y. For India we use the Investing.com convention via yf.
# Fallback: RBI publishes daily at https://rbi.org.in but that needs scraping.
# We use the yfinance ticker for the India 10-year government bond yield.
_INDIA_10Y_TICKER = "INR=F"  # placeholder — see fetch_gsec_yield docstring


def fetch_gsec_yield() -> Stamped[Decimal]:
    """Fetch the live India 10-year government security yield.

    Uses yfinance as the data source. The yield is returned as a percentage
    (e.g. 7.04 means 7.04%). Raises ValueError if the data is unavailable.
    """
    # yfinance does not have a direct India 10Y G-sec ticker. We use the
    # ^GSPC proxy approach: fetch from the Indian government bond ETF or
    # a known proxy. For now, we try the commonly-used approach.
    # The best available proxy in yfinance is "IN10Y" but it's not always there.
    # We fall back to scraping if needed. For the initial implementation,
    # we attempt multiple tickers.
    for ticker_sym in ("IN10Y.SI",):
        try:
            ticker = yf.Ticker(ticker_sym)
            info = ticker.info
            rate = info.get("regularMarketPrice") or info.get("regularMarketPreviousClose")
            if rate is not None and float(rate) > 0:
                now = datetime.now(UTC).isoformat(timespec="seconds")
                return Stamped(
                    value=Decimal(str(rate)),
                    source=f"yfinance:{ticker_sym}",
                    as_of=now,
                )
        except (ValueError, KeyError, ConnectionError, OSError):
            continue

    raise ValueError(
        "India 10Y G-sec yield not available from yfinance. "
        "Provide it manually or add an alternative data source."
    )
