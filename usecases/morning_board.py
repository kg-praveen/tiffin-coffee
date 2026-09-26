"""usecases/morning_board.py — UC1 orchestrator: run the morning board.

Spec: trigger-check v2, morning-board skill.
Loads policy + triggers + names from db/pattaz.db, fetches prices via tools/,
classifies FIRED/NEAR/FAR, writes a session record, returns a structured result.
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from engine.morning_board import (
    ArmabilityResult,
    BoardEntry,
    DropReason,
    TriggerStatus,
    build_board,
    check_armability,
    classify_trigger,
    nearest_n,
)
from store.repo import NameRow, PattazRepo, TriggerRow
from tools.prices import PriceSnapshot, fetch_price
from tools.results_dates import BatchResultDates, fetch_result_dates_batch
from tools.stamped import Stamped
from usecases.results import effective_results


def _json_safe(obj: object) -> object:
    """Recursively convert Decimals and enums for JSON serialization."""
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if hasattr(obj, "value") and isinstance(obj, type) is False and hasattr(obj, "name"):
        return obj.value  # type: ignore[union-attr]
    return obj


@dataclass(frozen=True)
class BoardResult:
    """Full output of a morning board run."""
    run_id: str
    ran_at: str
    fired: list[BoardEntry]
    near: list[BoardEntry]
    far: list[BoardEntry]
    not_armable: list[ArmabilityResult]
    unknown: list[BoardEntry]
    drops: list[dict[str, str]]
    rules_fired: list[str]
    gsec_yield: Stamped[Decimal] | None


def run_morning_board(
    db_path: str | Path,
    fetch_prices: bool = True,
    *,
    prices: dict[str, PriceSnapshot] | None = None,
    results: BatchResultDates | None = None,
    today: str | None = None,
    record_session: bool = True,
) -> BoardResult:
    """Execute UC1: the morning trigger board patrol.

    Spec: trigger-check v2 workflow steps 1-9.
    UC5 replay: `prices` (keyed by symbol) replaces the live fetch, `today` pins the
    clock, `record_session=False` keeps a hypothetical board out of the register.
    """
    now = datetime.now(UTC).isoformat(timespec="seconds")
    run_id = f"UC1_{uuid.uuid4().hex[:12]}"
    if today is None:
        today = datetime.now(UTC).strftime("%Y-%m-%d")
    rules_fired: list[str] = []
    drops: list[dict[str, str]] = []

    repo = PattazRepo(db_path)
    try:
        names_map: dict[str, NameRow] = {n.symbol: n for n in repo.load_names()}
        all_triggers: list[TriggerRow] = repo.load_triggers(active_only=False)

        armable_triggers: list[TriggerRow] = []
        not_armable: list[ArmabilityResult] = []

        # E3: latest results dates (replay passes them; a live run fetches them)
        if results is None:
            tickers = sorted({names_map[t.symbol].yf_ticker or "" for t in all_triggers
                              if t.symbol in names_map and names_map[t.symbol].yf_ticker})
            results = (fetch_result_dates_batch(tickers) if fetch_prices and prices is None
                       else BatchResultDates())
        results = effective_results(
            results, repo.load_results_verified(),
            {s: (n.yf_ticker or s).removesuffix(".NS") for s, n in names_map.items()}, today)
        max_age = int(repo.load_policy()["results_max_age_days"].value)

        for t in all_triggers:
            name = names_map.get(t.symbol)
            if name is None:
                drops.append({
                    "symbol": t.symbol,
                    "reason": "NO_NAME_ROW",
                    "detail": f"trigger for {t.symbol} but no names row found",
                })
                continue

            result = check_armability(
                symbol=t.symbol,
                kind=t.kind,
                active=t.active,
                basis_eps_date=t.basis_eps_date,
                decay_expiry=name.decay_expiry,
                today=today,
                yf_ticker=name.yf_ticker,
                name_status=name.status,
                flag_exit_decided=name.flag_exit_decided,
                result_dates=_dates_for(results, name.yf_ticker or t.symbol),
                results_max_age_days=max_age,
            )

            if result.armable:
                armable_triggers.append(t)
                rules_fired.append(f"ARMABLE:{t.symbol}:{t.kind}")
            else:
                not_armable.append(result)
                if result.drop_reason is None:
                    continue
                drops.append({
                    "symbol": t.symbol,
                    "reason": result.drop_reason.name,
                    "detail": result.detail,
                })
                rules_fired.append(f"NOT_ARMABLE:{t.symbol}:{t.kind}:{result.drop_reason.name}")

        entries: list[BoardEntry] = []
        unknown_entries: list[BoardEntry] = []

        if fetch_prices:
            seen_tickers: set[str] = set()
            for t in armable_triggers:
                name = names_map[t.symbol]
                ticker = name.yf_ticker
                if ticker is None:
                    continue
                if ticker in seen_tickers:
                    pass
                seen_tickers.add(ticker)

                snap: PriceSnapshot | None = None
                if prices is not None:
                    snap = prices.get(ticker.removesuffix(".NS"))
                else:
                    try:
                        snap = fetch_price(ticker)
                    except (ValueError, ConnectionError, OSError):
                        snap = None

                if snap is not None and snap.price.value > 0:
                    status, dist = classify_trigger(t.level, snap.price.value)
                    entries.append(BoardEntry(
                        symbol=t.symbol,
                        name=name.name,
                        kind=t.kind,
                        trigger_level=t.level,
                        basis_eps_date=t.basis_eps_date,
                        derivation=t.derivation,
                        price=snap.price.value,
                        price_source=snap.price.source,
                        price_as_of=snap.price.as_of,
                        distance_pct=dist,
                        status=status,
                        notes=t.notes,
                    ))
                    rules_fired.append(f"CLASSIFY:{t.symbol}:{status.value}")
                else:
                    unknown_entries.append(BoardEntry(
                        symbol=t.symbol,
                        name=name.name,
                        kind=t.kind,
                        trigger_level=t.level,
                        basis_eps_date=t.basis_eps_date,
                        derivation=t.derivation,
                        price=None,
                        price_source=None,
                        price_as_of=None,
                        distance_pct=None,
                        status=TriggerStatus.UNKNOWN,
                        notes="price not fetched this run (E3/E9)",
                    ))
                    drops.append({
                        "symbol": t.symbol,
                        "reason": DropReason.PRICE_FETCH_FAILED.name,
                        "detail": f"fetch_price({ticker}) failed or returned 0",
                    })

        fired, near, far = build_board(entries)

        outputs: dict = _json_safe({
            "fired": [asdict(e) for e in fired],
            "near": [asdict(e) for e in near],
            "far_nearest_3": [asdict(e) for e in nearest_n(far)],
            "not_armable_count": len(not_armable),
            "unknown_count": len(unknown_entries),
        })
        inputs: dict = {
            "today": today,
            "triggers_total": len(all_triggers),
            "triggers_armable": len(armable_triggers),
            "fetch_prices": fetch_prices,
        }

        if record_session:
            repo.append_session(
                run_id=run_id,
                ran_at=now,
                usecase="UC1_MORNING_BOARD",
                inputs=inputs,
                outputs=outputs,
                drops=drops,
                rules_fired=rules_fired,
            )

        return BoardResult(
            run_id=run_id,
            ran_at=now,
            fired=fired,
            near=near,
            far=far,
            not_armable=not_armable,
            unknown=unknown_entries,
            drops=drops,
            rules_fired=rules_fired,
            gsec_yield=None,
        )
    finally:
        repo.close()


def _dates_for(results: BatchResultDates, ticker: str) -> tuple[str, ...] | None:
    st = results.dates.get(ticker.removesuffix(".NS"))
    return st.value if st is not None else None


def format_board(result: BoardResult) -> str:
    """Format the board result as plain-language output for Praveen.

    Spec: trigger-check v2 step 8, morning-board skill step 3.
    Verdict first, then tables.
    """
    lines: list[str] = []
    lines.append(f"Morning Board — {result.ran_at}")
    lines.append(f"Run: {result.run_id}")
    lines.append("")

    if result.fired:
        lines.append(
            f"FIRED — {len(result.fired)} trigger(s) at or below entry price:"
        )
        lines.append(_table_header())
        for e in result.fired:
            lines.append(_table_row(e))
        lines.append("")
        lines.append(
            "A fired trigger is an appointment to re-examine, never an order to buy."
        )
        lines.append("")
    else:
        lines.append("Nothing fired.")
        if result.near:
            lines.append("")
        elif result.far:
            lines.append(
                f" Nearest {min(3, len(result.far))}:"
            )
            for e in nearest_n(result.far):
                lines.append(_table_row(e))
            lines.append("")

    if result.near:
        lines.append(f"NEAR — {len(result.near)} within 5% of trigger:")
        lines.append(_table_header())
        for e in result.near:
            lines.append(_table_row(e))
        lines.append("")

    if result.unknown:
        lines.append(f"UNKNOWN — {len(result.unknown)} price not fetched:")
        for e in result.unknown:
            lines.append(f"  {e.symbol:15s} {e.kind:12s} trigger={e.trigger_level}")
        lines.append("")

    if result.not_armable:
        lines.append(
            f"NOT ARMABLE — {len(result.not_armable)} trigger(s) need attention:"
        )
        for na in result.not_armable:
            reason = na.drop_reason.value if na.drop_reason is not None else "unknown"
            lines.append(
                f"  {na.symbol:15s} {na.kind:12s} {reason}"
            )
        lines.append("")

    return "\n".join(lines)


def _table_header() -> str:
    return (
        f"  {'Name':15s} {'Kind':12s} {'Trigger':>10s} {'Price':>10s}"
        f" {'Dist':>7s} {'Basis':10s} {'Notes'}"
    )


def _table_row(e: BoardEntry) -> str:
    price_str = f"{e.price:>10.2f}" if e.price is not None else "     -    "
    dist_str = f"{e.distance_pct:>6.1f}%" if e.distance_pct is not None else "     - "
    basis_str = e.basis_eps_date or "-"
    notes_str = (e.notes or "-")[:40]
    return (
        f"  {e.symbol:15s} {e.kind:12s} {e.trigger_level:>10.2f} {price_str}"
        f" {dist_str} {basis_str:10s} {notes_str}"
    )
