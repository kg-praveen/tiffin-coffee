"""tools/company_data.py — company facts for an OSEP run (UC4). Network — never in CI.

Spec: osep v7 Stage 0 (promoter, solvency, profit history), Stage 1 watch signals,
§SC (what the company does — cited for classification). Every value is Stamped (E2).

Sources:
  * yfinance statements — total debt, equity, net income, revenue, operating cash flow
    (annual, newest first), business description.
  * screener.in company page — quarterly promoter holding (the NSE shareholding
    pattern, as published). Parsed by `parse_screener_promoters` (pure, tested).
"""
from __future__ import annotations

import re
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import yfinance as yf

from tools.stamped import Stamped

SCREENER_URL = "https://www.screener.in/company/{symbol}/consolidated/"


@dataclass(frozen=True)
class CompanyFacts:
    symbol: str
    promoter_pct: Stamped[tuple[Decimal, ...]] | None       # quarterly, oldest → newest
    promoter_periods: tuple[str, ...]
    total_debt: Stamped[Decimal] | None
    equity: Stamped[Decimal] | None
    net_income: Stamped[tuple[Decimal, ...]] | None         # annual, newest first
    revenue: Stamped[tuple[Decimal, ...]] | None
    ocf: Stamped[tuple[Decimal, ...]] | None
    business: Stamped[str] | None
    # TTM EPS = sum of the last 4 quarterly EPS the company REPORTED (attributable to
    # shareholders). Screener's headline P/E uses profit incl. minority interest — for
    # R Systems that gave 17.7 vs 16.27 reported (26-Sep-2026).
    eps_ttm_reported: Stamped[Decimal] | None = None


def parse_screener_promoters(html: str) -> tuple[tuple[str, ...], tuple[Decimal, ...]]:
    """Quarterly shareholding table → (periods, promoter %). Empty if not found."""
    i = html.find('id="quarterly-shp"')
    if i < 0:
        return (), ()
    seg = html[i:i + 40000]
    row = re.search(r"Promoters.*?</tr>", seg, re.DOTALL)
    head = re.search(r"<thead>.*?</thead>", seg, re.DOTALL)
    if not row or not head:
        return (), ()
    pcts = tuple(Decimal(x) for x in re.findall(r"<td[^>]*>\s*([\d.]+)%\s*</td>", row.group(0)))
    periods = tuple(re.findall(r"<th[^>]*>\s*([A-Z][a-z]{2} \d{4})\s*</th>", head.group(0)))
    n = min(len(pcts), len(periods))
    return periods[-n:], pcts[-n:]


def parse_screener_quarterly_eps(html: str) -> tuple[tuple[str, ...], tuple[Decimal, ...]]:
    """Quarterly results table 'EPS in Rs' row → (periods, EPS), oldest → newest."""
    i = html.find('id="quarters"')
    if i < 0:
        return (), ()
    seg = html[i:i + 80000]
    head = re.search(r"<thead>.*?</thead>", seg, re.DOTALL)
    row = re.search(r"EPS in Rs.*?</tr>", seg, re.DOTALL)
    if not head or not row:
        return (), ()
    periods = tuple(re.findall(r"<th[^>]*>\s*([A-Z][a-z]{2} \d{4})\s*</th>", head.group(0)))
    eps = tuple(Decimal(x.replace(",", ""))
                for x in re.findall(r"<td[^>]*>\s*(-?[\d.,]+)\s*</td>", row.group(0)))
    n = min(len(periods), len(eps))
    return periods[-n:], eps[-n:]


def _row(df: Any, names: tuple[str, ...]) -> tuple[Decimal, ...] | None:
    if df is None or getattr(df, "empty", True):
        return None
    for name in names:
        if name in df.index:
            vals = [v for v in df.loc[name].tolist() if v == v]  # drop NaN
            return tuple(Decimal(str(int(v))) for v in vals) or None
    return None


def newest_balance(annual: Any, quarterly: Any) -> tuple[Decimal | None, Decimal | None, str]:
    """(equity, institutional debt, period) from the NEWEST balance sheet available (E3).

    Debt = Total Debt - Capital Lease Obligations: osep v7 solvency counts institutional
    borrowing, not leases (R Systems Dec-25: 409.8 Cr total, 95.2 Cr leases)."""
    best: tuple[Decimal | None, Decimal | None, str] = (None, None, "")
    for df in (quarterly, annual):
        if df is None or getattr(df, "empty", True):
            continue
        col = df.columns[0]
        eq = _cell(df, ("Stockholders Equity", "Common Stock Equity"), col)
        debt = _cell(df, ("Total Debt",), col)
        lease = _cell(df, ("Capital Lease Obligations",), col) or Decimal(0)
        if eq is None:
            continue
        period = str(col)[:10]
        if period > best[2]:
            inst = (debt - lease) if debt is not None else None
            best = (eq, inst, period)
    return best


def _cell(df: Any, names: tuple[str, ...], col: Any) -> Decimal | None:
    for name in names:
        if name in df.index:
            v = df.loc[name, col]
            if v == v and v is not None:     # not NaN
                return Decimal(str(int(v)))
    return None


def fetch_company_facts(yf_ticker: str, nse_symbol: str) -> CompanyFacts:
    now = datetime.now(UTC).isoformat(timespec="seconds")
    src = f"yfinance:{yf_ticker}"

    def st(v: Any, s: str = src) -> Any:
        return Stamped(value=v, source=s, as_of=now) if v is not None else None

    t = yf.Ticker(yf_ticker)
    eq_v, debt_v, period = newest_balance(t.balance_sheet, t.quarterly_balance_sheet)
    bsrc = f"{src}:balance sheet {period} (debt ex-leases)"
    ni = _row(t.financials, ("Net Income", "Net Income Common Stockholders"))
    rev = _row(t.financials, ("Total Revenue", "Operating Revenue"))
    ocf = _row(t.cashflow, ("Operating Cash Flow",))
    info = t.info or {}
    periods: tuple[str, ...] = ()
    promoters: tuple[Decimal, ...] = ()
    eps_q: tuple[Decimal, ...] = ()
    eps_p: tuple[str, ...] = ()
    try:
        req = urllib.request.Request(SCREENER_URL.format(symbol=nse_symbol),  # noqa: S310
                                     headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=25) as resp:  # noqa: S310
            html = resp.read().decode("utf-8", "ignore")
        periods, promoters = parse_screener_promoters(html)
        eps_p, eps_q = parse_screener_quarterly_eps(html)
    except OSError:
        pass
    eps_ttm = (Stamped(value=sum(eps_q[-4:], Decimal(0)),
                       source=f"screener.in:{nse_symbol}:quarterly EPS {'+'.join(eps_p[-4:])}",
                       as_of=now) if len(eps_q) >= 4 else None)
    return CompanyFacts(
        symbol=nse_symbol,
        promoter_pct=st(promoters or None, f"screener.in:{nse_symbol}:shareholding"),
        promoter_periods=periods,
        total_debt=st(debt_v, bsrc),
        equity=st(eq_v, bsrc),
        net_income=st(ni), revenue=st(rev), ocf=st(ocf),
        business=st(info.get("longBusinessSummary")),
        eps_ttm_reported=eps_ttm,
    )
