"""tools/csv_import.py — parse a household holdings CSV into account-level rows.

Spec: CLAUDE.md §3 (holdings replaced by UC2.1: Kite for Zerodha, CSV for the two
Integrated accounts), sync-holdings skill step 2. Pure parsing — no DB, no network.
The household CSV carries all three accounts in one file (Kite-P / Int-P / Int-V).
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

_ACCOUNT_COLS: dict[str, str] = {
    "Kite-P Qty": "ZERODHA_P",
    "Int-P Qty": "INTEGRATED_P",
    "Int-V Qty": "INTEGRATED_V",
}
_MONTHS = {m: i for i, m in enumerate(
    ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1,
)}
_DATE_RE = re.compile(r"(\d{1,2})([a-z]{3})(\d{4})", re.IGNORECASE)


@dataclass(frozen=True)
class HoldingImportRow:
    account: str
    symbol: str
    qty: int
    avg_cost: Decimal | None


@dataclass(frozen=True)
class HouseholdSnapshot:
    """One dated snapshot of every account's holdings (E2: as_of + source)."""

    as_of: str
    source: str
    rows: list[HoldingImportRow] = field(default_factory=list)
    total_value_reported: Decimal | None = None


def as_of_from_filename(name: str) -> str | None:
    """household_equity_21sep2026.csv → 2026-09-21."""
    m = _DATE_RE.search(name)
    if not m:
        return None
    day, mon, year = int(m.group(1)), _MONTHS.get(m.group(2).lower()), int(m.group(3))
    if mon is None:
        return None
    return f"{year:04d}-{mon:02d}-{day:02d}"


# Newer exports (25-Sep-2026 onward) use compact headers; map them to the canonical ones.
_HEADER_ALIASES: dict[str, str] = {
    "TotalQty": "Total Qty",
    "KiteP": "Kite-P Qty",
    "IntP": "Int-P Qty",
    "IntV": "Int-V Qty",
    "IntV_20Sep": "Int-V Qty",     # Varshu not re-exported; last confirmed qty carried
    "Value": "Total Value",
}


def _int(raw: str | None) -> int:
    return int(Decimal(raw.strip())) if raw and raw.strip() else 0


def parse_household_csv(path: str | Path, as_of: str | None = None) -> HouseholdSnapshot:
    """Parse the household CSV. Tolerates the extra P&L columns of older exports.

    Raises ValueError on a missing required column or when Total Qty does not
    equal the sum of the account columns (never import numbers that disagree).
    """
    p = Path(path)
    as_of = as_of or as_of_from_filename(p.name)
    if as_of is None:
        raise ValueError(f"{p.name}: no date in filename — pass as_of explicitly")

    with p.open(newline="") as fh:
        reader = csv.DictReader(fh)
        reader.fieldnames = [_HEADER_ALIASES.get(h, h) for h in (reader.fieldnames or [])]
        header = set(reader.fieldnames)
        missing = ({"Stock", "Total Qty"} | set(_ACCOUNT_COLS)) - header
        if missing:
            raise ValueError(f"{p.name}: missing columns {sorted(missing)}")
        has_cost = "Avg Price" in header
        has_value = "Total Value" in header

        rows: list[HoldingImportRow] = []
        total_value = Decimal(0)
        for rec in reader:
            symbol = (rec.get("Stock") or "").strip()
            if not symbol:
                continue
            per_account = {acct: _int(rec.get(col)) for col, acct in _ACCOUNT_COLS.items()}
            declared = _int(rec.get("Total Qty"))
            if declared != sum(per_account.values()):
                raise ValueError(
                    f"{p.name}: {symbol} Total Qty {declared} != account sum "
                    f"{sum(per_account.values())}"
                )
            cost_raw = (rec.get("Avg Price") or "").strip() if has_cost else ""
            avg_cost = Decimal(cost_raw).quantize(Decimal("0.01")) if cost_raw else None
            for acct, qty in per_account.items():
                if qty > 0:
                    rows.append(HoldingImportRow(acct, symbol, qty, avg_cost))
            if has_value and (rec.get("Total Value") or "").strip():
                total_value += Decimal(rec["Total Value"].strip())

    return HouseholdSnapshot(
        as_of=as_of,
        source=f"CSV:{p.name}",
        rows=rows,
        total_value_reported=total_value if has_value else None,
    )


def snapshot_with_zeroing(
    snapshot: HouseholdSnapshot,
    previously_held: set[tuple[str, str]],
) -> list[HoldingImportRow]:
    """A full snapshot means absence = sold: emit qty 0 for (account, symbol) pairs
    that were held before but are missing now, so the newest row per pair is 0."""
    present = {(r.account, r.symbol) for r in snapshot.rows}
    zeroed = [
        HoldingImportRow(acct, sym, 0, None)
        for acct, sym in sorted(previously_held - present)
    ]
    return [*snapshot.rows, *zeroed]
