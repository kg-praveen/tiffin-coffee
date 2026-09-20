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
from engine.valuation_gate import (
    ValuationGateInput,
    ValuationGateResult,
    compute_valuation_gate,
)
from store.repo import HoldingRow, NameRow, PattazRepo, TriggerRow
from tools.fundamentals import (
    BatchFundamentalsResult,
    FundamentalsSnapshot,
    fetch_fundamentals_batch,
)
from tools.gsec import fetch_gsec_yield
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
    gsec_yield_pct: Decimal
    gsec_source: str
    gate_results: dict[str, ValuationGateResult]


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
    fund: FundamentalsSnapshot | None,
    gsec_yield_pct: Decimal,
    coe_spread: Decimal,
    growth_g: Decimal,
) -> tuple[NameInput, ValuationGateResult]:
    """Convert store types + price snapshot into a pure engine NameInput.

    Returns (NameInput, ValuationGateResult) — the gate result is needed
    for session output enrichment (E8).
    """
    qty_held = holdings_qty.get(name.symbol, 0)

    current_weight_pct: Decimal | None = None
    if household_equity > 0 and name.symbol in holdings_qty:
        value = snap.price.value * qty_held
        current_weight_pct = ((value / household_equity) * 100).quantize(
            Decimal("0.01")
        )

    gate_inp = ValuationGateInput(
        symbol=name.symbol,
        sector_class=name.sector_class,
        pe_trailing=fund.pe_trailing.value if fund and fund.pe_trailing else None,
        pb_ratio=fund.pb_ratio.value if fund and fund.pb_ratio else None,
        roe_pct=fund.roe_pct.value if fund and fund.roe_pct else None,
        gsec_yield_pct=gsec_yield_pct,
        cost_of_equity_spread=coe_spread,
        growth_g_pct=growth_g,
    )
    gate_result = compute_valuation_gate(gate_inp)

    ni = NameInput(
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
        valuation_gate_passed=gate_result.passed,
    )
    return ni, gate_result


def _resolve_gsec_yield(
    policy: dict,
    gsec_yield_override: Decimal | None,
) -> tuple[Decimal, str]:
    """Resolve GoI yield: override → live fetch → policy fallback (F2).

    Returns (yield_pct, source_description).
    """
    if gsec_yield_override is not None:
        return gsec_yield_override, f"override:{gsec_yield_override}"

    try:
        stamped = fetch_gsec_yield()
        return stamped.value, stamped.source
    except ValueError:
        pass

    fallback_row = policy.get("gsec_yield_last_known")
    if fallback_row:
        src = f"policy_fallback:{fallback_row.value} (as_of {fallback_row.adopted_on})"
        return Decimal(fallback_row.value), src

    return Decimal("7.04"), "hardcoded_emergency:7.04"


def run_plate(
    db_path: str | Path,
    session_amount: Decimal,
    fetch_prices: bool = True,
    gsec_yield_override: Decimal | None = None,
) -> PlateRunResult:
    """Execute UC2: build a tiffin-coffee buy plate.

    CRITICAL FIX #6: scans ALL names with tickers, not just those
    with active triggers. Names at 52-week lows without triggers
    can qualify via the first-bite exception.

    UC4: computes valuation gate per name using live fundamentals
    and GoI yield. gsec_yield_override lets Praveen pass the rate manually.
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
        policy = repo.load_policy()

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

        # --- resolve GoI yield (F2: override → live → policy fallback) ---
        gsec_yield_pct, gsec_source = _resolve_gsec_yield(policy, gsec_yield_override)
        coe_spread = Decimal(policy["cost_of_equity_spread_over_gsec"].value)
        growth_g = Decimal(policy["growth_g"].value)
        log.info("GoI yield: %s%% (source: %s)", gsec_yield_pct, gsec_source)

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

        # --- fetch fundamentals for ALL tickered names (UC4) ---
        fund_result: BatchFundamentalsResult
        if fetch_prices:
            fund_result = fetch_fundamentals_batch(tickers_to_fetch)
        else:
            fund_result = BatchFundamentalsResult()

        fund_map = fund_result.fundamentals

        # --- save fundamentals to DB for audit trail (E8) ---
        for sym, fsnap in fund_map.items():
            repo.save_fundamentals(
                symbol=sym,
                as_of=now,
                eps_ttm=fsnap.eps_ttm.value if fsnap.eps_ttm else None,
                book_value_ps=fsnap.book_value_ps.value if fsnap.book_value_ps else None,
                roe=fsnap.roe_pct.value if fsnap.roe_pct else None,
                source=f"yfinance:{symbol_to_ticker.get(sym, sym + '.NS')}",
            )

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
        gate_results: dict[str, ValuationGateResult] = {}
        for n in all_names:
            if n.symbol not in prices:
                continue
            snap = prices[n.symbol]
            trigger = triggers_map.get(n.symbol)
            fund = fund_map.get(n.symbol)
            ni, gate_result = _build_name_input(
                n, snap, trigger, holdings_qty, household_equity,
                fund, gsec_yield_pct, coe_spread, growth_g,
            )
            name_inputs.append(ni)
            gate_results[n.symbol] = gate_result

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
            "fundamentals_fetched": len(fund_map),
            "fundamentals_failed": len(fund_result.failures),
            "household_equity": str(household_equity),
            "psu_weight_pct": str(psu_weight),
            "gsec_yield_pct": str(gsec_yield_pct),
            "gsec_source": gsec_source,
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
            gsec_yield_pct=gsec_yield_pct,
            gsec_source=gsec_source,
            gate_results=gate_results,
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
    lines.append(f"GoI yield: {result.gsec_yield_pct}% (source: {result.gsec_source})")
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
