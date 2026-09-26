"""tools/market_snapshot.py — one market day, recorded once, replayed many times.

Spec: E1 (market data lives nowhere — this is a *recording*, never a decision input
for a live run), E2 (every value stays Stamped), CLAUDE.md §5 (fixtures are refreshed
deliberately, never in CI). UC5 replays a snapshot through UC1/UC2 with shocks applied.

`record_snapshot` is the only function here that touches the network.
"""
from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from tools.fundamentals import (
    BatchFundamentalsResult,
    FundamentalsSnapshot,
    fetch_fundamentals_batch,
)
from tools.gsec import fetch_gsec_yield
from tools.index_moves import IndexMoves, fetch_nifty_moves
from tools.prices import BatchPriceResult, PriceSnapshot, fetch_prices_batch
from tools.results_dates import BatchResultDates, fetch_result_dates_batch
from tools.stamped import Stamped

_FUND_FIELDS = ("pe_trailing", "pb_ratio", "eps_ttm", "book_value_ps", "roe_pct")


@dataclass(frozen=True)
class MarketSnapshot:
    """Everything the plate and board fetch live, frozen at one moment."""

    recorded_at: str  # ISO date of the market day
    prices: BatchPriceResult
    fundamentals: BatchFundamentalsResult
    gsec: Stamped[Decimal] | None
    results: BatchResultDates = field(default_factory=BatchResultDates)
    nifty: IndexMoves | None = None   # tiffin v6 §H HOCKEY inputs (None = not recorded)


# ------------------------------------------------------------ (de)serialise ---


def _st_to_json(s: Stamped[Decimal] | None) -> dict[str, str] | None:
    if s is None:
        return None
    return {"value": str(s.value), "source": s.source, "as_of": s.as_of}


def _st_from_json(d: dict[str, str] | None) -> Stamped[Decimal] | None:
    if d is None:
        return None
    return Stamped(value=Decimal(d["value"]), source=d["source"], as_of=d["as_of"])


def _req(d: dict[str, str]) -> Stamped[Decimal]:
    return Stamped(value=Decimal(d["value"]), source=d["source"], as_of=d["as_of"])


def _price_to_json(p: PriceSnapshot) -> dict[str, Any]:
    d: dict[str, Any] = {"price": _st_to_json(p.price), "low_52w": _st_to_json(p.low_52w),
                         "high_52w": _st_to_json(p.high_52w)}
    if p.prev_close is not None:
        d["prev_close"] = _st_to_json(p.prev_close)
    return d


def _nifty_to_json(m: IndexMoves | None) -> dict[str, Any] | None:
    if m is None:
        return None
    return {"symbol": m.symbol, "level": _st_to_json(m.level),
            "week_change_pct": _st_to_json(m.week_change_pct),
            "drawdown_pct": _st_to_json(m.drawdown_pct)}


def _nifty_from_json(d: dict[str, Any] | None) -> IndexMoves | None:
    if d is None:
        return None
    return IndexMoves(symbol=d["symbol"], level=_st_from_json(d.get("level")),
                      week_change_pct=_req(d["week_change_pct"]),
                      drawdown_pct=_req(d["drawdown_pct"]))


def snapshot_to_json(snap: MarketSnapshot) -> dict[str, Any]:
    out = _snapshot_body_to_json(snap)
    if snap.nifty is not None:          # older recordings have no Nifty: keep them byte-stable
        out["nifty"] = _nifty_to_json(snap.nifty)
    return out


def _snapshot_body_to_json(snap: MarketSnapshot) -> dict[str, Any]:
    return {
        "recorded_at": snap.recorded_at,
        "gsec": _st_to_json(snap.gsec),
        "prices": {sym: _price_to_json(p) for sym, p in sorted(snap.prices.prices.items())},
        "price_failures": dict(sorted(snap.prices.failures.items())),
        "fundamentals": {
            sym: {**{f: _st_to_json(getattr(fs, f)) for f in _FUND_FIELDS},
                  "upcoming_results": (
                      {"value": list(fs.upcoming_results.value),
                       "source": fs.upcoming_results.source,
                       "as_of": fs.upcoming_results.as_of}
                      if fs.upcoming_results else None)}
            for sym, fs in sorted(snap.fundamentals.fundamentals.items())
        },
        "fundamental_failures": dict(sorted(snap.fundamentals.failures.items())),
        "result_dates": {
            sym: {"value": list(st.value), "source": st.source, "as_of": st.as_of}
            for sym, st in sorted(snap.results.dates.items())
        },
        "result_date_failures": dict(sorted(snap.results.failures.items())),
    }


def snapshot_from_json(d: dict[str, Any]) -> MarketSnapshot:
    prices = {
        sym: PriceSnapshot(symbol=sym, price=_req(p["price"]), low_52w=_req(p["low_52w"]),
                           high_52w=_req(p["high_52w"]),
                           prev_close=_st_from_json(p.get("prev_close")))
        for sym, p in d["prices"].items()
    }
    def _upcoming(fd: dict[str, Any]) -> Stamped[tuple[str, ...]] | None:
        u = fd.get("upcoming_results")
        return Stamped(value=tuple(u["value"]), source=u["source"], as_of=u["as_of"]) if u else None

    funds = {
        sym: FundamentalsSnapshot(symbol=sym, **{f: _st_from_json(fd.get(f))
                                                  for f in _FUND_FIELDS},
                                  upcoming_results=_upcoming(fd))
        for sym, fd in d["fundamentals"].items()
    }
    return MarketSnapshot(
        recorded_at=d["recorded_at"],
        prices=BatchPriceResult(prices=prices, failures=dict(d.get("price_failures", {}))),
        fundamentals=BatchFundamentalsResult(
            fundamentals=funds, failures=dict(d.get("fundamental_failures", {}))),
        gsec=_st_from_json(d.get("gsec")),
        results=BatchResultDates(
            dates={sym: Stamped(value=tuple(r["value"]), source=r["source"], as_of=r["as_of"])
                   for sym, r in d.get("result_dates", {}).items()},
            failures=dict(d.get("result_date_failures", {})),
        ),
        nifty=_nifty_from_json(d.get("nifty")),
    )


def save_snapshot(snap: MarketSnapshot, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot_to_json(snap), indent=1, ensure_ascii=False) + "\n")


def load_snapshot(path: Path) -> MarketSnapshot:
    return snapshot_from_json(json.loads(path.read_text()))


def newest_snapshot(folder: Path) -> Path | None:
    """Newest recording by filename (market_YYYY-MM-DD.json sorts by date)."""
    files = sorted(folder.glob("market_*.json"))
    return files[-1] if files else None


# ------------------------------------------------------------------ network ---


def record_snapshot(yf_tickers: Sequence[str]) -> MarketSnapshot:
    """Fetch prices, fundamentals, the GoI yield and Nifty moves live. NETWORK — never
    in CI."""
    try:
        gsec: Stamped[Decimal] | None = fetch_gsec_yield()
    except ValueError:
        gsec = None
    try:
        nifty: IndexMoves | None = fetch_nifty_moves()
    except ValueError:
        nifty = None
    return MarketSnapshot(
        recorded_at=datetime.now(UTC).strftime("%Y-%m-%d"),
        prices=fetch_prices_batch(yf_tickers),
        fundamentals=fetch_fundamentals_batch(yf_tickers),
        gsec=gsec,
        results=fetch_result_dates_batch(yf_tickers),
        nifty=nifty,
    )
