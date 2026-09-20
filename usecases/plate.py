"""usecases/plate.py — UC2 orchestrator: build a tiffin-coffee buy plate.

Spec: tiffin-coffee v6 formula, CRITICAL FIX #6 — scans ALL names with tickers,
not just those with active triggers. Names at 52-week lows without triggers
can qualify via the first-bite exception.

Loads state from db/pattaz.db, fetches prices for ALL tickered names via
tools/prices.py, computes H/L/P + overlays via engine/plate.py, writes session.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from engine.plate import (
    CellInfo,
    NameInput,
    PlateConfig,
    PlateResult,
    build_plate,
)
from store.repo import HoldingRow, NameRow, PattazRepo, TriggerRow
from tools.prices import BatchPriceResult, PriceSnapshot, fetch_prices_batch

log = logging.getLogger(__name__)


def _json_safe(obj: object) -> object:
    """Recursively convert Decimals and enums for JSON serialization."""
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if hasattr(obj, "value") and not isinstance(obj, type) and hasattr(obj, "name"):
        return obj.value  # type: ignore[union-attr]
    return obj


@dataclass(frozen=True)
class PlateRunResult:
    """Full output of a plate run."""

    run_id: str
    ran_at: str
    plate: PlateResult
    names_scanned: int
    prices_fetched: int
    prices_failed: int


def _aggregate_holdings(
    holdings: list[HoldingRow],
) -> dict[str, int]:
    """Sum qty across accounts for each symbol."""
    totals: dict[str, int] = {}
    for h in holdings:
        totals[h.symbol] = totals.get(h.symbol, 0) + h.qty
    return totals


def _compute_household_equity(
    holdings_qty: dict[str, int],
    prices: dict[str, PriceSnapshot],
) -> Decimal:
    """Total household equity value = sum(qty * price) for all held names."""
    total = Decimal(0)
    for symbol, qty in holdings_qty.items():
        if symbol in prices:
            total += prices[symbol].price.value * qty
    return total


def _compute_psu_weight(
    names_map: dict[str, NameRow],
    holdings_qty: dict[str, int],
    prices: dict[str, PriceSnapshot],
    household_equity: Decimal,
) -> Decimal:
    """PSU+regulated weight as % of household equity."""
    if household_equity == 0:
        return Decimal(0)
    psu_value = Decimal(0)
    for symbol, qty in holdings_qty.items():
        name = names_map.get(symbol)
        if name and name.flag_psu and symbol in prices:
            psu_value += prices[symbol].price.value * qty
    return ((psu_value / household_equity) * 100).quantize(Decimal("0.01"))


def _build_name_input(
    name: NameRow,
    snap: PriceSnapshot,
    trigger: TriggerRow | None,
    holdings_qty: dict[str, int],
    household_equity: Decimal,
) -> NameInput:
    """Convert store types + price snapshot into a pure engine NameInput."""
    qty_held = holdings_qty.get(name.symbol, 0)

    current_weight_pct: Decimal | None = None
    if household_equity > 0 and name.symbol in holdings_qty:
        value = snap.price.value * qty_held
        current_weight_pct = ((value / household_equity) * 100).quantize(
            Decimal("0.01")
        )

    return NameInput(
        symbol=name.symbol,
        name=name.name,
        price=snap.price.value,
        low_52w=snap.low_52w.value,
        trigger_level=trigger.level if trigger else None,
        sector_class=name.sector_class,
        status=name.status,
        bucket=name.bucket,
        cell=name.cell,
        flag_sovereign=name.flag_sovereign,
        flag_psu=name.flag_psu,
        flag_cyclical=name.flag_cyclical,
        flag_probe_open=name.flag_probe_open,
        flag_fraud_tail=name.flag_fraud_tail,
        flag_exit_decided=name.flag_exit_decided,
        p5_status=name.p5_status,
        p5_note_ref=name.p5_note_ref,
        decay_expiry=name.decay_expiry,
        qty_held_household=qty_held,
        current_weight_pct=current_weight_pct,
        valuation_gate_passed=False,
    )


def run_plate(
    db_path: str | Path,
    session_amount: Decimal,
    fetch_prices: bool = True,
) -> PlateRunResult:
    """Execute UC2: build a tiffin-coffee buy plate.

    CRITICAL FIX #6: scans ALL names with yf_tickers, not just those
    with active triggers. A name at its 52-week low without a trigger
    can still qualify via the first-bite exception.
    """
    now = datetime.now(UTC).isoformat(timespec="seconds")
    run_id = f"UC2_{uuid.uuid4().hex[:12]}"
    today = datetime.now(UTC).strftime("%Y-%m-%d")

    repo = PattazRepo(db_path)
    try:
        all_names = repo.load_names()
        all_triggers = repo.load_triggers(active_only=True)
        all_holdings = repo.load_holdings()
        all_cells = repo.load_cells()

        names_map: dict[str, NameRow] = {n.symbol: n for n in all_names}
        triggers_map: dict[str, TriggerRow] = {}
        for t in all_triggers:
            if t.symbol not in triggers_map:
                triggers_map[t.symbol] = t

        holdings_qty = _aggregate_holdings(all_holdings)

        cells_map: dict[str, CellInfo] = {
            c.cell: CellInfo(
                is_full=c.is_full,
                active_add_count=len(c.active_adds.split(",")) if c.active_adds else 0,
                max_adds=c.max_adds,
            )
            for c in all_cells
        }

        # --- CRITICAL FIX #6: collect ALL tickers, not just triggered ones ---
        tickers_to_fetch: list[str] = []
        symbol_to_ticker: dict[str, str] = {}
        for n in all_names:
            if n.yf_ticker:
                tickers_to_fetch.append(n.yf_ticker)
                symbol_to_ticker[n.symbol] = n.yf_ticker

        log.info(
            "plate scan: %d names total, %d with tickers, %d with triggers",
            len(all_names), len(tickers_to_fetch), len(triggers_map),
        )

        # --- fetch prices for ALL tickered names ---
        batch_result: BatchPriceResult
        if fetch_prices:
            batch_result = fetch_prices_batch(tickers_to_fetch)
        else:
            batch_result = BatchPriceResult()

        prices = batch_result.prices

        # --- compute portfolio-level metrics ---
        household_equity = _compute_household_equity(holdings_qty, prices)
        psu_weight = _compute_psu_weight(
            names_map, holdings_qty, prices, household_equity,
        )

        # --- fetch BeES price ---
        bees_price: Decimal | None = None
        if "NIFTYBEES" in prices:
            bees_price = prices["NIFTYBEES"].price.value

        # --- build NameInputs for ALL names with fetched prices ---
        name_inputs: list[NameInput] = []
        for n in all_names:
            if n.symbol not in prices:
                continue
            snap = prices[n.symbol]
            trigger = triggers_map.get(n.symbol)
            name_inputs.append(
                _build_name_input(n, snap, trigger, holdings_qty, household_equity)
            )

        log.info(
            "plate inputs: %d names with prices, household_equity=%.0f, psu_weight=%.1f%%",
            len(name_inputs), household_equity, psu_weight,
        )

        # --- run the engine ---
        config = PlateConfig(
            session_amount=session_amount,
            today=today,
            psu_weight_pct=psu_weight,
            cells=cells_map,
            bees_price=bees_price,
        )

        plate_result = build_plate(name_inputs, config)

        # --- write session ---
        outputs: dict = _json_safe({
            "entries": [asdict(e) for e in plate_result.entries],
            "bees_sweep_qty": plate_result.bees_sweep_qty,
            "bees_sweep_amount": str(plate_result.bees_sweep_amount),
            "total_stock_amount": str(plate_result.total_stock_amount),
            "total_with_sweep": str(plate_result.total_with_sweep),
            "residual": str(plate_result.residual),
        })
        inputs: dict = {
            "today": today,
            "session_amount": str(session_amount),
            "names_scanned": len(name_inputs),
            "prices_fetched": len(prices),
            "prices_failed": len(batch_result.failures),
            "household_equity": str(household_equity),
            "psu_weight_pct": str(psu_weight),
        }
        drops_json = [
            {"symbol": d.symbol, "reason": d.reason.name, "detail": d.detail}
            for d in plate_result.drops
        ]

        repo.append_session(
            run_id=run_id,
            ran_at=now,
            usecase="UC2_PLATE",
            inputs=inputs,
            outputs=outputs,
            drops=drops_json,
            rules_fired=plate_result.rules_fired,
        )

        return PlateRunResult(
            run_id=run_id,
            ran_at=now,
            plate=plate_result,
            names_scanned=len(name_inputs),
            prices_fetched=len(prices),
            prices_failed=len(batch_result.failures),
        )
    finally:
        repo.close()


def format_plate(result: PlateRunResult) -> str:
    """Format the plate result as plain-language output for Praveen."""
    lines: list[str] = []
    plate = result.plate

    lines.append(f"Buy Plate -- {result.ran_at}")
    lines.append(f"Run: {result.run_id}")
    lines.append(
        f"Session: {plate.session_amount} | "
        f"Scanned: {result.names_scanned} names | "
        f"Prices OK: {result.prices_fetched} | "
        f"Failed: {result.prices_failed}"
    )
    lines.append("")

    if plate.entries:
        lines.append(
            f"PLATE -- {len(plate.entries)} name(s), "
            f"total {plate.total_stock_amount}:"
        )
        lines.append(
            f"  {'Name':15s} {'Qty':>4s} {'Amount':>10s} "
            f"{'Mode':12s} {'H':>6s} {'L%':>6s} {'Score':>7s} {'Tag'}"
        )
        for e in plate.entries:
            h_str = f"{e.h:.3f}" if e.h is not None else "  -   "
            tag = "PRICE-BITE" if e.is_first_bite else ""
            lines.append(
                f"  {e.symbol:15s} {e.qty:>4d} {e.amount:>10.2f} "
                f"{e.mode.value:12s} {h_str:>6s} {e.l_pct:>5.1f}% "
                f"{e.score:>7.3f} {tag}"
            )
        lines.append("")

    if plate.bees_sweep_qty > 0:
        lines.append(
            f"BeES SWEEP: {plate.bees_sweep_qty} NIFTYBEES "
            f"= {plate.bees_sweep_amount}"
        )

    lines.append(
        f"TOTAL: {plate.total_with_sweep} "
        f"(stocks {plate.total_stock_amount} + "
        f"BeES {plate.bees_sweep_amount}) | "
        f"Residual: {plate.residual}"
    )
    lines.append("")

    if plate.drops:
        lines.append(f"DROPS -- {len(plate.drops)} name(s) excluded:")
        for d in plate.drops:
            h_str = f"H={d.h:.3f}" if d.h is not None else "H=-"
            l_str = f"L={d.l_pct:.1f}%" if d.l_pct is not None else "L=-"
            lines.append(
                f"  {d.symbol:15s} {d.reason.name:30s} {h_str} {l_str}"
            )
        lines.append("")

    return "\n".join(lines)
