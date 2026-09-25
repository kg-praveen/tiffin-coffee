"""tools/gsec.py — fetch India 10-year government security yield.

Spec: osep v7 MoS anchor — the GoI yield ladder (1/gsec_yield = fair P/E).
The yield is fetched live each session (E3). Returns a Stamped Decimal.

Sources, tried in order (26-Sep-2026: yfinance IN10Y.SI returns 404; CNBC works):
  1. CNBC quote feed, symbol IN10Y-IN (JSON, no key)
  2. yfinance IN10Y.SI (kept in case it comes back)
If both fail → ValueError; the caller falls back to policy and prints a WARN (F2).
"""
from __future__ import annotations

import json
import urllib.request
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import yfinance as yf

from tools.stamped import Stamped

CNBC_URL = (
    "https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol"
    "?symbols=IN10Y-IN&requestMethod=itv&noform=1&partnerId=2&fund=1&exthrs=1&output=json"
)
_TIMEOUT_S = 15
_YF_TICKER = "IN10Y.SI"


def _get_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})  # noqa: S310
    with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:  # noqa: S310
        return json.loads(resp.read())


def parse_cnbc(payload: Any) -> Stamped[Decimal]:
    """Read the yield from a CNBC quote payload. Raises ValueError if it is not there."""
    try:
        q = payload["FormattedQuoteResult"]["FormattedQuote"][0]
        value = Decimal(str(q["last"]).rstrip("%").strip())
    except (KeyError, IndexError, TypeError, InvalidOperation) as exc:
        raise ValueError(f"CNBC IN10Y-IN: unexpected payload ({exc})") from exc
    if value <= 0:
        raise ValueError(f"CNBC IN10Y-IN: non-positive yield {value}")
    as_of = q.get("last_time") or datetime.now(UTC).isoformat(timespec="seconds")
    return Stamped(value=value, source="cnbc:IN10Y-IN", as_of=str(as_of))


def _fetch_cnbc() -> Stamped[Decimal]:
    try:
        return parse_cnbc(_get_json(CNBC_URL))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"CNBC IN10Y-IN unreachable: {exc}") from exc


def _fetch_yfinance() -> Stamped[Decimal]:
    try:
        info = yf.Ticker(_YF_TICKER).info
        rate = info.get("regularMarketPrice") or info.get("regularMarketPreviousClose")
    except (ValueError, KeyError, ConnectionError, OSError) as exc:
        raise ValueError(f"yfinance {_YF_TICKER}: {exc}") from exc
    if rate is None or float(rate) <= 0:
        raise ValueError(f"yfinance {_YF_TICKER}: no yield")
    return Stamped(value=Decimal(str(rate)), source=f"yfinance:{_YF_TICKER}",
                   as_of=datetime.now(UTC).isoformat(timespec="seconds"))


def fetch_gsec_yield() -> Stamped[Decimal]:
    """Fetch the live India 10-year G-sec yield in percent (7.12 means 7.12%).

    Tries each source in order; raises ValueError naming every failure if none work.
    """
    errors: list[str] = []
    for fetch in (_fetch_cnbc, _fetch_yfinance):
        try:
            return fetch()
        except ValueError as exc:
            errors.append(str(exc))
    raise ValueError("India 10Y G-sec yield not available — " + " | ".join(errors))
