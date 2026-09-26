"""usecases/sync_holdings.py — UC2.1: refresh the holdings register and print the
household view on prices fetched THIS run.

Two paths: Kite Connect (read-only) for ZERODHA_P; the household CSV for the two
Integrated accounts, which have no API. Spec: sync-holdings skill steps 1-5,
CLAUDE.md §3 and §6, pattaz-book §4 (caps at household level, never account level).
Read scope only — nothing here can place an order.

CLI:
  python -m usecases.sync_holdings kite --login-url
  python -m usecases.sync_holdings kite --request-token TOKEN
  python -m usecases.sync_holdings kite            (reuses today's cached token, if any)
  python -m usecases.sync_holdings csv FILE
"""
from __future__ import annotations

import argparse
import logging
import sys
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import tools.kite as kite
from engine.plate import PriorityTier, classify_priority, priority_from_book
from store.repo import NameRow, PattazRepo
from tools.csv_import import (
    HoldingImportRow,
    HouseholdSnapshot,
    parse_household_csv,
    snapshot_with_zeroing,
)
from tools.kite import KITE_SOURCE, ZERODHA_ACCOUNT, KiteHoldingsSnapshot
from tools.prices import BatchPriceResult, fetch_prices_batch

log = logging.getLogger(__name__)
_ACCOUNTS = ("ZERODHA_P", "INTEGRATED_P", "INTEGRATED_V")
_Q2 = Decimal("0.01")
DEFAULT_DB = Path(__file__).resolve().parent.parent / "db" / "pattaz.db"


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
    unknown_symbols: list[str] = field(default_factory=list)   # Kite symbols not in names
    symbol_map: dict[str, str] = field(default_factory=dict)    # Kite → register, if renamed
    possible_renames: list[str] = field(default_factory=list)   # exit + unknown, same sync
    open_questions: list[str] = field(default_factory=list)     # Praveen's calls, surfaced


# Advisory lines — decisions that are Praveen's, not the code's (CLAUDE.md "when the
# spec is ambiguous, STOP and ask"). Behaviour stays as documented until he decides.
OQ_PLEDGED = (
    "OPEN QUESTION for Praveen: pledged/collateral shares (Kite collateral_quantity) are "
    "NOT counted in ZERODHA_P qty (qty = quantity + t1_quantity). Should pledged shares "
    "count as held for household weights and caps? Excluded until you decide."
)
OQ_CSV_ZERODHA = (
    "OPEN QUESTION for Praveen: the household CSV import still writes ZERODHA_P rows even "
    "though Kite is now the Zerodha source. Should the CSV stop writing ZERODHA_P? "
    "Unchanged until you decide; whichever snapshot is newer wins per account+symbol."
)


def _pct(part: Decimal, whole: Decimal) -> Decimal:
    if whole <= 0:
        return Decimal(0)
    return (part / whole * 100).quantize(_Q2, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class _View:
    lines: list[HouseholdLine]
    equity: Decimal
    psu_weight: Decimal
    breaches: list[str]
    unpriced: list[str]
    prices_fetched: int


def _household_view(repo: PattazRepo, fetch_prices: bool) -> _View:
    """Household view on prices fetched THIS run — skill step 4, pattaz-book §4 caps."""
    policy = repo.load_policy()
    cap_name = Decimal(policy["cap_name_pct"].value)
    cap_sector = Decimal(policy["cap_sector_pct"].value)
    cap_psu = Decimal(policy["cap_psu_regulated_pct"].value)
    names_map: dict[str, NameRow] = {n.symbol: n for n in repo.load_names()}

    qty: dict[str, dict[str, int]] = {}
    for h in repo.load_holdings():
        if h.qty > 0:
            qty.setdefault(h.symbol, {})[h.account] = h.qty

    tickers = [t for s in qty if s in names_map and (t := names_map[s].yf_ticker)]
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

    return _View(lines=lines, equity=equity, psu_weight=psu_weight, breaches=breaches,
                 unpriced=sorted(s for s in qty if s not in prices),
                 prices_fetched=len(prices))


def _view_outputs(v: _View) -> dict[str, object]:
    return {"household_equity_priced": str(v.equity), "psu_weight_pct": str(v.psu_weight),
            "cap_breaches": v.breaches, "unpriced": v.unpriced,
            "tiers": {ln.symbol: ln.p_tier for ln in v.lines if ln.p_tier}}


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
        v = _household_view(repo, fetch_prices)
        oqs = [OQ_CSV_ZERODHA] if any(r.account == ZERODHA_ACCOUNT for r in snap.rows) else []

        repo.append_session(
            run_id=run_id, ran_at=now, usecase="UC2_1_SYNC_HOLDINGS",
            inputs={"csv": snap.source, "as_of": snap.as_of, "rows_written": written,
                    "exits_recorded": exits, "prices_fetched": v.prices_fetched,
                    "total_value_reported": str(snap.total_value_reported)},
            outputs={**_view_outputs(v), "open_questions": oqs},
            drops=[], rules_fired=[f"cap:{b}" for b in v.breaches],
        )
        return SyncResult(
            run_id=run_id, ran_at=now, as_of=snap.as_of, source=snap.source,
            rows_written=written, exits_recorded=exits, lines=v.lines,
            household_equity_priced=v.equity, total_value_reported=snap.total_value_reported,
            unpriced_symbols=v.unpriced, psu_weight_pct=v.psu_weight, cap_breaches=v.breaches,
            open_questions=oqs,
        )
    finally:
        repo.close()


# --------------------------------------------------------------- Kite path ---
def map_kite_symbols(
    tradingsymbols: Iterable[str], names: list[NameRow],
) -> tuple[dict[str, str], list[str]]:
    """Kite tradingsymbol → register symbol via the names.yf_ticker stem (RECLTD.NS →
    REC), then an exact symbol match. Unmatched symbols are kept under their Kite
    name and returned as `unknown` so the report names them (never dropped silently).
    """
    by_stem = {n.yf_ticker.split(".")[0].upper(): n.symbol for n in names if n.yf_ticker}
    by_symbol = {n.symbol.upper(): n.symbol for n in names}
    mapping: dict[str, str] = {}
    unknown: list[str] = []
    for ts in tradingsymbols:
        reg = by_stem.get(ts.upper()) or by_symbol.get(ts.upper())
        if reg is None:
            unknown.append(ts)
        mapping[ts] = reg or ts
    return mapping, sorted(set(unknown))


def _kite_import_rows(
    snap: KiteHoldingsSnapshot, mapping: dict[str, str],
) -> list[HoldingImportRow]:
    """One ZERODHA_P row per register symbol; two Kite rows on one symbol are summed
    with a quantity-weighted average cost (Decimal, 2 dp — CLAUDE.md §4)."""
    qty: dict[str, int] = {}
    cost: dict[str, Decimal | None] = {}
    for h in snap.rows:
        sym = mapping[h.tradingsymbol]
        q = h.qty.value
        avg = h.avg_price.value if h.avg_price is not None else None
        if sym in qty:
            prev_q, prev_c = qty[sym], cost[sym]
            cost[sym] = (
                ((prev_c * prev_q + avg * q) / (prev_q + q)).quantize(_Q2, ROUND_HALF_UP)
                if prev_c is not None and avg is not None else None
            )
            qty[sym] = prev_q + q
        else:
            qty[sym], cost[sym] = q, avg
    return [HoldingImportRow(ZERODHA_ACCOUNT, s, qty[s], cost[s]) for s in sorted(qty)]


class KiteSyncRefused(RuntimeError):
    """The Kite sync wrote no holdings (E9). The failure session is already appended;
    `reason` is what was recorded. The original exception, if any, is `__cause__`."""

    def __init__(self, reason: str, run_id: str) -> None:
        super().__init__(reason)
        self.reason = reason
        self.run_id = run_id


def _append_refusal_session(repo: PattazRepo, run_id: str, ran_at: str, reason: str) -> None:
    """CLAUDE.md §3 / E8: a run that wrote nothing still writes a session — source,
    rows_written 0, the refusal reason, and the E9 verdict NO ACTION."""
    repo.append_session(
        run_id=run_id, ran_at=ran_at, usecase="UC2_1_SYNC_HOLDINGS",
        inputs={"source": KITE_SOURCE, "account": ZERODHA_ACCOUNT, "rows_written": 0,
                "exits_recorded": 0},
        outputs={"verdict": "NO ACTION", "refused": reason},
        drops=[], rules_fired=["E9:fail-closed"],
    )


def possible_renames(exited: Iterable[str], unknown: Iterable[str]) -> list[str]:
    """A ZERODHA_P exit and an unknown Kite symbol in the same sync may be ONE name
    renamed/re-listed (e.g. ZOMATO -> ETERNAL), not a sale plus a new buy. The code
    cannot tell which, so it reports the pairing for Praveen to check (never merges)."""
    ex, un = sorted(set(exited)), sorted(set(unknown))
    if not ex or not un:
        return []
    return [f"exit(s) {', '.join(ex)} alongside unknown Kite symbol(s) {', '.join(un)}"]


def run_sync_holdings_kite(
    db_path: str | Path,
    snapshot: KiteHoldingsSnapshot | None = None,
    fetch: Callable[[], KiteHoldingsSnapshot] | None = None,
    fetch_prices: bool = True,
) -> SyncResult:
    """Write the Kite holdings as a full ZERODHA_P snapshot (skill steps 1, 3), then
    print the household view (step 4).

    Snapshot semantics as the CSV path (CLAUDE.md §3): a ZERODHA_P pair held before
    but absent from Kite gets a qty-0 row (recorded exit). INTEGRATED_P/INTEGRATED_V
    are never touched here — they stay CSV-only.

    E9 fail-closed + E8/§3 session law: if the fetch raises (network, expired token)
    or Kite answers empty while the register still shows Zerodha holdings, NO holdings
    are written, a UC2_1_SYNC_HOLDINGS session (rows_written 0, the reason, NO ACTION)
    is appended, and KiteSyncRefused is raised (chained to the original exception).
    """
    if snapshot is None and fetch is None:
        raise ValueError("run_sync_holdings_kite needs a snapshot or a fetch callable")
    now = datetime.now(UTC).isoformat(timespec="seconds")
    run_id = f"UC2_1_{uuid.uuid4().hex[:12]}"

    repo = PattazRepo(db_path)
    try:
        if snapshot is None and fetch is not None:
            try:
                snapshot = fetch()
            except Exception as exc:
                reason = f"Kite fetch failed ({type(exc).__name__}) — nothing written"
                _append_refusal_session(repo, run_id, now, reason)
                raise KiteSyncRefused(reason, run_id) from exc
        held_before = {p for p in repo.held_pairs() if p[0] == ZERODHA_ACCOUNT}
        if not snapshot.rows and held_before:
            reason = (
                f"Kite returned empty holdings but the register shows {len(held_before)} "
                "ZERODHA_P names — refusing to record them all as exits (E9). Re-run, "
                "or import the CSV if the account really is empty."
            )
            _append_refusal_session(repo, run_id, now, reason)
            raise KiteSyncRefused(reason, run_id)
        mapping, unknown = map_kite_symbols(
            [h.tradingsymbol for h in snapshot.rows], repo.load_names(),
        )
        snap = HouseholdSnapshot(as_of=snapshot.as_of, source=KITE_SOURCE,
                                 rows=_kite_import_rows(snapshot, mapping))
        rows = snapshot_with_zeroing(snap, held_before)
        written = repo.insert_holdings(
            [(r.account, r.symbol, r.qty, r.avg_cost) for r in rows], snap.as_of, KITE_SOURCE,
        )
        exited = [r.symbol for r in rows if r.qty == 0]
        renames = possible_renames(exited, unknown)
        oq_pledged = OQ_PLEDGED + (
            f" Rows with collateral/used qty today: {', '.join(snapshot.pledged)}."
            if snapshot.pledged else ""
        )
        oqs = [oq_pledged, OQ_CSV_ZERODHA]
        renamed = {k: v for k, v in mapping.items() if k != v}
        v = _household_view(repo, fetch_prices)

        repo.append_session(
            run_id=run_id, ran_at=now, usecase="UC2_1_SYNC_HOLDINGS",
            inputs={"source": KITE_SOURCE, "account": ZERODHA_ACCOUNT, "as_of": snap.as_of,
                    "rows_written": written, "exits_recorded": len(exited),
                    "prices_fetched": v.prices_fetched, "unknown_symbols": unknown,
                    "symbol_map": renamed, "pledged": snapshot.pledged},
            outputs={**_view_outputs(v), "possible_renames": renames, "open_questions": oqs},
            drops=[], rules_fired=[f"cap:{b}" for b in v.breaches],
        )
        return SyncResult(
            run_id=run_id, ran_at=now, as_of=snap.as_of, source=KITE_SOURCE,
            rows_written=written, exits_recorded=len(exited), lines=v.lines,
            household_equity_priced=v.equity, total_value_reported=None,
            unpriced_symbols=v.unpriced, psu_weight_pct=v.psu_weight, cap_breaches=v.breaches,
            unknown_symbols=unknown, symbol_map=renamed, possible_renames=renames,
            open_questions=oqs,
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
    if r.symbol_map:
        L.append("KITE SYMBOLS MAPPED: "
                 + ", ".join(f"{k} -> {v}" for k, v in sorted(r.symbol_map.items())))
    if r.unknown_symbols:
        L.append(
            f"UNKNOWN KITE SYMBOLS ({len(r.unknown_symbols)}; recorded under the Kite "
            f"name, not in the names register): {', '.join(r.unknown_symbols)}"
        )
    for pr in r.possible_renames:
        L.append(f"POSSIBLE RENAME — check before trusting the exit: {pr}")
    L.extend(r.open_questions)
    return "\n".join(L)


# --------------------------------------------------------------------- CLI ---
_ASK_FOR_LOGIN = (
    "No Kite session for today. Open this URL in your browser, log in, and paste the "
    "request_token from the redirect back to me:\n  {url}\n"
    "Then: python -m usecases.sync_holdings kite --request-token <request_token>"
)


def _run_kite(args: argparse.Namespace) -> int:
    """Skill step 1: print the login URL; take the request token Praveen pastes back.
    Login is never automated; the token is never printed or logged (CLAUDE.md §6)."""
    creds = kite.load_credentials()
    factory = kite._default_factory
    if args.login_url:
        print(kite.login_url(creds.api_key, factory=factory))
        return 0
    today = kite.ist_today()
    if args.request_token:
        token = kite.exchange_request_token(creds, args.request_token, factory=factory,
                                            today=today, token_file=kite.TOKEN_FILE)
    else:
        cached = kite.load_cached_token(today, kite.TOKEN_FILE)
        if cached is None:
            print(_ASK_FOR_LOGIN.format(url=kite.login_url(creds.api_key, factory=factory)))
            return 2
        token = cached
    try:
        r = run_sync_holdings_kite(
            args.db,
            fetch=lambda: kite.fetch_holdings(creds.api_key, token, factory=factory,
                                              today=today),
            fetch_prices=not args.no_prices,
        )
    except KiteSyncRefused as exc:
        print(f"NO ACTION — {exc.reason} (session {exc.run_id} recorded)")
        if exc.__cause__ is not None and kite.is_token_error(exc.__cause__):
            # Kite rejected the token (expired/invalid): forget it, ask for a new login.
            kite.clear_cached_token(kite.TOKEN_FILE)
            print("Kite rejected the access token (expired or invalid); cached token deleted.")
            print(_ASK_FOR_LOGIN.format(url=kite.login_url(creds.api_key, factory=factory)))
            return 2
        raise
    print(format_sync(r))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m usecases.sync_holdings")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    sub = ap.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("kite", help="Zerodha (ZERODHA_P) via Kite Connect, read-only")
    g = k.add_mutually_exclusive_group()
    g.add_argument("--login-url", action="store_true", help="print the Kite login URL")
    g.add_argument("--request-token", help="request_token from the Kite login redirect")
    k.add_argument("--no-prices", action="store_true")
    c = sub.add_parser("csv", help="household CSV snapshot")
    c.add_argument("file")
    c.add_argument("--no-prices", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd == "kite":
        return _run_kite(args)
    print(format_sync(run_sync_holdings_csv(args.db, args.file,
                                            fetch_prices=not args.no_prices)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
