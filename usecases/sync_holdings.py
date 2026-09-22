"""usecases/sync_holdings.py — UC2.1 (CSV path): import a household snapshot and print
the household view on prices fetched THIS run.

Spec: sync-holdings skill steps 2-5, CLAUDE.md §3, pattaz-book §4 (caps at household
level, never account level). Read scope only — nothing here can place an order.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from engine.plate import PriorityTier, classify_priority, priority_from_book
from store.repo import NameRow, PattazRepo
from tools.csv_import import parse_household_csv, snapshot_with_zeroing
from tools.prices import BatchPriceResult, fetch_prices_batch

log = logging.getLogger(__name__)
_ACCOUNTS = ("ZERODHA_P", "INTEGRATED_P", "INTEGRATED_V")
_Q2 = Decimal("0.01")


@dataclass(frozen=True)
class HouseholdLine:
    symbol: str
    qty: dict[str, int]
    qty_total: int
    price: Decimal | None
    value: Decimal | None
    weight_pct: Decimal | None
    p_tier: str | None
    in_register: bool
    cell: str | None
    flag_psu: bool


@dataclass(frozen=True)
class SyncResult:
    run_id: str
    ran_at: str
    as_of: str
    source: str
    rows_written: int
    exits_recorded: int
    lines: list[HouseholdLine]
    household_equity_priced: Decimal
    total_value_reported: Decimal | None
    unpriced_symbols: list[str]
    psu_weight_pct: Decimal
    cap_breaches: list[str]


def _pct(part: Decimal, whole: Decimal) -> Decimal:
    if whole <= 0:
        return Decimal(0)
    return (part / whole * 100).quantize(_Q2, rounding=ROUND_HALF_UP)


def run_sync_holdings_csv(
    db_path: str | Path,
    csv_path: str | Path,
    fetch_prices: bool = True,
) -> SyncResult:
    """Import the CSV as a full household snapshot, then build the household view."""
    now = datetime.now(UTC).isoformat(timespec="seconds")
    run_id = f"UC2_1_{uuid.uuid4().hex[:12]}"
    snap = parse_household_csv(csv_path)

    repo = PattazRepo(db_path)
    try:
        rows = snapshot_with_zeroing(snap, repo.held_pairs())
        written = repo.insert_holdings(
            [(r.account, r.symbol, r.qty, r.avg_cost) for r in rows], snap.as_of, snap.source,
        )
        exits = sum(1 for r in rows if r.qty == 0)

        policy = repo.load_policy()
        cap_name = Decimal(policy["cap_name_pct"].value)
        cap_sector = Decimal(policy["cap_sector_pct"].value)
        cap_psu = Decimal(policy["cap_psu_regulated_pct"].value)
        names_map: dict[str, NameRow] = {n.symbol: n for n in repo.load_names()}

        qty: dict[str, dict[str, int]] = {}
        for h in repo.load_holdings():
            if h.qty > 0:
                qty.setdefault(h.symbol, {})[h.account] = h.qty

        tickers = [names_map[s].yf_ticker for s in qty
                   if s in names_map and names_map[s].yf_ticker]
        batch = fetch_prices_batch(tickers) if fetch_prices else BatchPriceResult()
        prices = {s: p.price.value for s, p in batch.prices.items()}

        values = {s: prices[s] * sum(q.values()) for s, q in qty.items() if s in prices}
        equity = sum(values.values(), Decimal(0))
        psu_value = sum(
            (v for s, v in values.items() if s in names_map and names_map[s].flag_psu), Decimal(0),
        )
        psu_weight = _pct(psu_value, equity)

        lines: list[HouseholdLine] = []
        cell_value: dict[str, Decimal] = {}
        for sym, per_acct in qty.items():
            n = names_map.get(sym)
            value = values.get(sym)
            weight = _pct(value, equity) if value is not None else None
            tier: str | None = None
            if n is not None:
                if n.p_mult_book is not None:
                    tier = priority_from_book(n.p_mult_book)[0].value
                elif weight is not None:
                    tier = classify_priority(weight, n.bucket)[0].value
            if n is not None and n.cell and value is not None:
                cell_value[n.cell] = cell_value.get(n.cell, Decimal(0)) + value
            lines.append(HouseholdLine(
                symbol=sym, qty=per_acct, qty_total=sum(per_acct.values()),
                price=prices.get(sym), value=value, weight_pct=weight, p_tier=tier,
                in_register=n is not None, cell=n.cell if n else None,
                flag_psu=bool(n and n.flag_psu),
            ))
        lines.sort(key=lambda x: (x.value is None, -(x.value or 0)))

        breaches: list[str] = []
        for ln in lines:
            if ln.weight_pct is not None and ln.weight_pct > cap_name:
                breaches.append(f"{ln.symbol} {ln.weight_pct}% > {cap_name}%/name")
        for cell, v in cell_value.items():
            w = _pct(v, equity)
            if w > cap_sector:
                breaches.append(f"cell {cell} {w}% > {cap_sector}%/sector")
        if psu_weight > cap_psu:
            breaches.append(f"PSU/regulated {psu_weight}% > {cap_psu}%")

        unpriced = sorted(s for s in qty if s not in prices)

        repo.append_session(
            run_id=run_id, ran_at=now, usecase="UC2_1_SYNC_HOLDINGS",
            inputs={"csv": snap.source, "as_of": snap.as_of, "rows_written": written,
                    "exits_recorded": exits, "prices_fetched": len(prices),
                    "total_value_reported": str(snap.total_value_reported)},
            outputs={"household_equity_priced": str(equity), "psu_weight_pct": str(psu_weight),
                     "cap_breaches": breaches, "unpriced": unpriced,
                     "tiers": {ln.symbol: ln.p_tier for ln in lines if ln.p_tier}},
            drops=[], rules_fired=[f"cap:{b}" for b in breaches],
        )
        return SyncResult(
            run_id=run_id, ran_at=now, as_of=snap.as_of, source=snap.source,
            rows_written=written, exits_recorded=exits, lines=lines,
            household_equity_priced=equity, total_value_reported=snap.total_value_reported,
            unpriced_symbols=unpriced, psu_weight_pct=psu_weight, cap_breaches=breaches,
        )
    finally:
        repo.close()


def format_sync(r: SyncResult) -> str:
    """Household view — sync-holdings skill step 4."""
    L: list[str] = []
    L.append(f"HOUSEHOLD HOLDINGS — snapshot {r.as_of} ({r.source})  |  run {r.run_id}")
    L.append(
        f"Rows written {r.rows_written} (exits recorded {r.exits_recorded})  |  "
        f"equity on live prices Rs {r.household_equity_priced:,.0f}"
        + (f"  |  CSV reported Rs {r.total_value_reported:,.0f}" if r.total_value_reported else "")
    )
    L.append(f"PSU/regulated weight {r.psu_weight_pct}%")
    L.append("")
    L.append(
        f"  {'Name':12s} {'K':>5} {'IP':>5} {'IV':>5} {'Total':>6} {'LTP':>9} "
        f"{'Value':>11} {'Wt%':>6} {'P-tier':11s} {'Cell'}"
    )
    for ln in r.lines:
        price = f"{ln.price:.2f}" if ln.price is not None else "-"
        value = f"{ln.value:,.0f}" if ln.value is not None else "-"
        wt = f"{ln.weight_pct:.2f}" if ln.weight_pct is not None else "-"
        tier = ln.p_tier or ("not in register" if not ln.in_register else "-")
        L.append(
            f"  {ln.symbol:12s} {ln.qty.get('ZERODHA_P', 0):>5} {ln.qty.get('INTEGRATED_P', 0):>5} "
            f"{ln.qty.get('INTEGRATED_V', 0):>5} {ln.qty_total:>6} {price:>9} {value:>11} "
            f"{wt:>6} {tier:11s} {ln.cell or ''}"
        )
    L.append("")
    if r.cap_breaches:
        L.append("CAP BREACHES (pattaz-book §4, household level)")
        for b in r.cap_breaches:
            L.append(f"  - {b}")
    else:
        L.append("CAP BREACHES: none")
    if r.unpriced_symbols:
        L.append(
            f"UNPRICED ({len(r.unpriced_symbols)}; not in register or no ticker — equity "
            f"understated, weights conservative): {', '.join(r.unpriced_symbols)}"
        )
    blocked = [ln.symbol for ln in r.lines if ln.p_tier == PriorityTier.BLOCKED.value]
    if blocked:
        L.append(f"P-BOARD BLOCKED (at/over target): {', '.join(blocked)}")
    return "\n".join(L)
