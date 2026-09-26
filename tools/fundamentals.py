"""tools/fundamentals.py — fetch trailing P/E, P/B, EPS, book value, ROE from yfinance.

Spec: E1 (market data fetched live), E2 (Stamped), E3 (freshness).
Separate adapter from prices.py — single-concern (plan design decision #2).
"""
from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import yfinance as yf

from tools.stamped import Stamped

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class FundamentalsSnapshot:
    """Fundamental valuation fields for one ticker, each individually stamped (E2).

    Any field may be None — not all stocks have all data (e.g. loss-making → no P/E).
    """

    symbol: str
    pe_trailing: Stamped[Decimal] | None
    pb_ratio: Stamped[Decimal] | None
    eps_ttm: Stamped[Decimal] | None
    book_value_ps: Stamped[Decimal] | None
    roe_pct: Stamped[Decimal] | None
    # results announcement dates Yahoo lists in the quote (IST dates) — no extra call
    upcoming_results: Stamped[tuple[str, ...]] | None = None


@dataclass(frozen=True)
class BatchFundamentalsResult:
    """Result of a batch fundamentals fetch."""

    fundamentals: dict[str, FundamentalsSnapshot] = field(default_factory=dict)
    failures: dict[str, str] = field(default_factory=dict)


def _decimal_or_none(raw: object) -> Decimal | None:
    if raw is None:
        return None
    return Decimal(str(raw))


def fetch_fundamentals(yf_ticker: str) -> FundamentalsSnapshot:
    """Fetch fundamental valuation data for a single NSE ticker.

    Spec: E2 (Stamped). ROE is converted from ratio (0.138) to percent (13.8).
    Raises ValueError if the ticker does not resolve at all.
    """
    ticker = yf.Ticker(yf_ticker)
    info = ticker.info
    if not info or info.get("regularMarketPrice") is None:
        raise ValueError(f"ticker {yf_ticker!r} did not resolve or returned no data")

    now = datetime.now(UTC).isoformat(timespec="seconds")
    source = f"yfinance:{yf_ticker}"
    symbol = yf_ticker.removesuffix(".NS")

    def _stamp(val: Decimal | None) -> Stamped[Decimal] | None:
        if val is None:
            return None
        return Stamped(value=val, source=source, as_of=now)

    pe_raw = _decimal_or_none(info.get("trailingPE"))
    pb_raw = _decimal_or_none(info.get("priceToBook"))
    eps_raw = _decimal_or_none(info.get("trailingEps"))
    bv_raw = _decimal_or_none(info.get("bookValue"))

    roe_ratio = info.get("returnOnEquity")
    roe_stamped: Stamped[Decimal] | None
    if roe_ratio is not None:
        roe_stamped = _stamp(Decimal(str(roe_ratio)) * 100)
    elif eps_raw is not None and bv_raw is not None and bv_raw > 0:
        # yfinance omits ROE for most NSE names; EPS/BV on ending equity is the
        # conservative (understated) derivation — stamped so the audit shows it.
        derived = (eps_raw / bv_raw * 100).quantize(Decimal("0.01"))
        roe_stamped = Stamped(value=derived, source=f"{source} (roe derived eps/bv)", as_of=now)
    else:
        roe_stamped = None

    ist = timezone(timedelta(hours=5, minutes=30))
    stamps = [info.get(k) for k in ("earningsTimestamp", "earningsTimestampStart",
                                    "earningsTimestampEnd")]
    days = tuple(sorted({datetime.fromtimestamp(int(t), tz=ist).date().isoformat()
                         for t in stamps if isinstance(t, (int, float)) and t > 0}))

    return FundamentalsSnapshot(
        symbol=symbol,
        pe_trailing=_stamp(pe_raw),
        pb_ratio=_stamp(pb_raw),
        eps_ttm=_stamp(eps_raw),
        book_value_ps=_stamp(bv_raw),
        roe_pct=roe_stamped,
        upcoming_results=(Stamped(value=days, source=f"{source}:earningsTimestamp", as_of=now)
                          if days else None),
    )


def fetch_fundamentals_batch(
    yf_tickers: Sequence[str],
) -> BatchFundamentalsResult:
    """Fetch fundamentals for multiple tickers. Per-ticker failures captured, not raised."""
    fundamentals: dict[str, FundamentalsSnapshot] = {}
    failures: dict[str, str] = {}

    for yf_ticker in yf_tickers:
        symbol = yf_ticker.removesuffix(".NS")
        try:
            snap = fetch_fundamentals(yf_ticker)
            fundamentals[snap.symbol] = snap
        except (ValueError, Exception) as exc:  # noqa: BLE001
            reason = str(exc)
            failures[symbol] = reason
            log.warning("fundamentals fetch failed for %s: %s", yf_ticker, reason)

    log.info(
        "fundamentals batch: %d OK, %d failed out of %d tickers",
        len(fundamentals),
        len(failures),
        len(yf_tickers),
    )
    return BatchFundamentalsResult(fundamentals=fundamentals, failures=failures)
