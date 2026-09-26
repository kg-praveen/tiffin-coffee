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
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from engine.morning_board import check_basis_fresh
from engine.plate import (
    CellInfo,
    NameInput,
    PlateConfig,
    PlateDrop,
    PlateDropReason,
    PlateResult,
    build_plate,
)
from engine.valuation_gate import (
    ValuationGateInput,
    ValuationGateResult,
    compute_fair_pe,
    compute_valuation_gate,
)
from store.repo import HoldingRow, NameRow, PattazRepo, TriggerRow
from tools.fundamentals import (
    BatchFundamentalsResult,
    FundamentalsSnapshot,
    fetch_fundamentals_batch,
)
from tools.gsec import fetch_gsec_yield
from tools.market_snapshot import MarketSnapshot
from tools.prices import BatchPriceResult, PriceSnapshot, fetch_prices_batch
from tools.results_dates import BatchResultDates, fetch_result_dates_batch
from tools.stamped import Stamped
from usecases.results import effective_results

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
    fair_pe: Decimal
    household_equity: Decimal
    fundamentals_fetched: int
    fundamentals_failed: int
    advisory_flags: list[str]
    breadth_min: int
    breadth_max: int
    name_inputs: tuple[NameInput, ...] = ()
    config: PlateConfig | None = None
    unpriced: tuple[PlateDrop, ...] = ()


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
    next_result_date: str | None = None,
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
        valuation_gate_detail=gate_result.detail,
        p_mult_book=name.p_mult_book,
        flag_no_add=name.flag_no_add,
        owned_per_book=(name.bucket == "OWNED" or name.status == "HOLD"),
        register_note=name.notes or "",
        brand_owned=name.brand_owned,
        next_result_date=next_result_date,
    )
    return ni, gate_result


def _by_register_symbol[V](
    by_stem: dict[str, V],
    symbol_to_ticker: dict[str, str],
) -> dict[str, V]:
    """Map adapter results (keyed by ticker stem) onto register symbols."""
    return {sym: by_stem[t.removesuffix(".NS")] for sym, t in symbol_to_ticker.items()
            if t.removesuffix(".NS") in by_stem}


def _next_result(
    dates: Stamped[tuple[str, ...]] | None,
    fund: FundamentalsSnapshot | None,
    today: str,
) -> str | None:
    """Earliest results date on or after today, from the results feed (after verified
    overrides) and the dates Yahoo lists in the quote."""
    pool = set(dates.value) if dates else set()
    if fund is not None and fund.upcoming_results is not None:
        pool |= set(fund.upcoming_results.value)
    future = sorted(d for d in pool if d >= today)
    return future[0] if future else None


def _unpriced_drops(
    names: list[NameRow],
    prices: dict[str, PriceSnapshot],
    failures: dict[str, str],
) -> list[PlateDrop]:
    """E8 + E9 (MIGRATION-AND-VALIDATION case 19): a name with no price this run is
    NO ACTION naming the missing input — "not found" is not a result, and it is not
    silence either. These never reach the engine (there is nothing to score)."""
    out: list[PlateDrop] = []
    for n in names:
        if n.symbol in prices:
            continue
        if not n.yf_ticker:
            out.append(PlateDrop(n.symbol, n.name, PlateDropReason.NO_TICKER,
                                 "no yf_ticker in the register",
                                 what_would_change="assign + verify a ticker "
                                                   "(tools/verify_tickers.py)"))
        else:
            why = failures.get(n.yf_ticker.removesuffix(".NS"), "not fetched this run")
            out.append(PlateDrop(n.symbol, n.name, PlateDropReason.PRICE_FETCH_FAILED,
                                 f"{n.yf_ticker}: {why}",
                                 what_would_change="a price fetched this run (E3)"))
    return out


def _policy_decimal(policy: dict, key: str) -> Decimal:
    """E2: policy constants come from the policy table — a missing key is a failure."""
    return Decimal(policy[key].value)


def _resolve_gsec_yield(
    policy: dict,
    gsec_yield_override: Decimal | None,
    market: MarketSnapshot | None = None,
) -> tuple[Decimal, str]:
    """Resolve GoI yield: override → live fetch (or the replayed snapshot) → policy
    fallback (F2). A replay never touches the network.

    Returns (yield_pct, source_description).
    """
    if gsec_yield_override is not None:
        return gsec_yield_override, f"override:{gsec_yield_override}"

    if market is not None:
        if market.gsec is not None:
            return market.gsec.value, market.gsec.source
    else:
        try:
            stamped = fetch_gsec_yield()
            return stamped.value, stamped.source
        except ValueError:
            pass

    fallback_row = policy.get("gsec_yield_last_known")
    if fallback_row:
        src = f"policy_fallback:{fallback_row.value} (as_of {fallback_row.adopted_on})"
        return Decimal(fallback_row.value), src

    # E9: no yield → every valuation gate fails closed; the H path is unaffected.
    return Decimal(0), "unavailable"


def run_plate(
    db_path: str | Path,
    session_amount: Decimal,
    fetch_prices: bool = True,
    gsec_yield_override: Decimal | None = None,
    *,
    market: MarketSnapshot | None = None,
    today: str | None = None,
    record_session: bool = True,
    event_opt_in: frozenset[str] = frozenset(),
) -> PlateRunResult:
    """Execute UC2: build a tiffin-coffee buy plate.

    CRITICAL FIX #6: scans ALL names with tickers, not just those
    with active triggers. Names at 52-week lows without triggers
    can qualify via the first-bite exception.

    UC4: computes valuation gate per name using live fundamentals
    and GoI yield. gsec_yield_override lets Praveen pass the rate manually.

    UC5 replay: `market` replaces every live fetch, `today` pins the clock, and
    `record_session=False` keeps a hypothetical plate out of the register (the
    simulation writes its own UC5 session instead).

    `event_opt_in`: names Praveen buys despite results inside the event-hold window
    (tiffin v6 §procedure step 6 — "event risk, your call").
    """
    now = datetime.now(UTC).isoformat(timespec="seconds")
    run_id = f"UC2_{uuid.uuid4().hex[:12]}"
    if today is None:
        today = datetime.now(UTC).strftime("%Y-%m-%d")

    repo = PattazRepo(db_path)
    try:
        all_names = repo.load_names()
        all_triggers = repo.load_triggers(active_only=True)
        all_holdings = repo.load_holdings()
        all_cells = repo.load_cells()
        policy = repo.load_policy()

        names_map: dict[str, NameRow] = {n.symbol: n for n in all_names}

        # --- latest results dates for triggered names (E3 basis check) ---
        trig_tickers = sorted({names_map[t.symbol].yf_ticker or "" for t in all_triggers
                               if t.symbol in names_map and names_map[t.symbol].yf_ticker})
        results: BatchResultDates
        if market is not None:
            results = market.results
        elif fetch_prices:
            results = fetch_result_dates_batch(trig_tickers)
        else:
            results = BatchResultDates()
        results = effective_results(
            results, repo.load_results_verified(),
            {n.symbol: (n.yf_ticker or n.symbol).removesuffix(".NS") for n in all_names}, today)
        max_age = int(_policy_decimal(policy, "results_max_age_days"))

        # E3: a trigger is armable only on a dated basis not older than the latest results
        triggers_map: dict[str, TriggerRow] = {}
        unarmable: list[str] = []
        for t in all_triggers:
            if t.basis_eps_date is None:
                unarmable.append(f"{t.symbol} (no basis date)")
                continue
            nm = names_map.get(t.symbol)
            stem = (nm.yf_ticker or t.symbol).removesuffix(".NS") if nm else t.symbol
            dates = results.dates.get(stem)
            stale, why = check_basis_fresh(t.basis_eps_date,
                                           dates.value if dates else None, today, max_age)
            if stale is not None:
                unarmable.append(f"{t.symbol} ({why})")
                continue
            if t.symbol not in triggers_map:
                triggers_map[t.symbol] = t

        holdings_qty = _aggregate_holdings(all_holdings)

        cells_map: dict[str, CellInfo] = {}
        for c in all_cells:
            seats = frozenset(s.strip() for s in c.active_adds.split(",") if s.strip()) \
                if c.active_adds else frozenset()
            cells_map[c.cell] = CellInfo(
                is_full=c.is_full,
                active_add_count=len(seats),
                max_adds=c.max_adds,
                active_adds=seats,
            )

        # --- resolve GoI yield (F2: override → live → policy fallback) ---
        gsec_yield_pct, gsec_source = _resolve_gsec_yield(
            policy, gsec_yield_override, market)
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
        if market is not None:
            batch_result = market.prices
        elif fetch_prices:
            batch_result = fetch_prices_batch(tickers_to_fetch)
        else:
            batch_result = BatchPriceResult()

        # adapters key by ticker stem (RECLTD.NS → RECLTD); the register keys by symbol
        # (REC). Re-key once so a name whose ticker differs is never silently unpriced.
        prices = _by_register_symbol(batch_result.prices, symbol_to_ticker)

        # --- fetch fundamentals for ALL tickered names (UC4) ---
        fund_result: BatchFundamentalsResult
        if market is not None:
            fund_result = market.fundamentals
        elif fetch_prices:
            fund_result = fetch_fundamentals_batch(tickers_to_fetch)
        else:
            fund_result = BatchFundamentalsResult()

        fund_map = _by_register_symbol(fund_result.fundamentals, symbol_to_ticker)

        # --- save fundamentals to DB for audit trail (E8) ---
        for sym, fsnap in (fund_map.items() if record_session else ()):
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
            stem = symbol_to_ticker[n.symbol].removesuffix(".NS")
            ni, gate_result = _build_name_input(
                n, snap, trigger, holdings_qty, household_equity,
                fund, gsec_yield_pct, coe_spread, growth_g,
                next_result_date=_next_result(results.dates.get(stem), fund, today),
            )
            name_inputs.append(ni)
            gate_results[n.symbol] = gate_result

        # --- E8/E9: a name that could not be priced is a named drop, never silence ---
        unpriced = _unpriced_drops(all_names, prices, batch_result.failures)

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
            eligible_h_min=_policy_decimal(policy, "eligible_h_min"),
            eligible_l_max=_policy_decimal(policy, "eligible_l_max"),
            qty_clamp_min=int(_policy_decimal(policy, "qty_clamp_min")),
            qty_clamp_max=int(_policy_decimal(policy, "qty_clamp_max")),
            first_bite_qty_max=int(_policy_decimal(policy, "first_bite_qty_max")),
            first_bite_h_mult_floor=_policy_decimal(policy, "first_bite_h_mult_floor"),
            first_bite_l_max=_policy_decimal(policy, "first_bite_l_max"),
            cap_psu_regulated_pct=_policy_decimal(policy, "cap_psu_regulated_pct"),
            event_hold_days=int(_policy_decimal(policy, "event_hold_days")),
            event_opt_in=event_opt_in,
        )

        plate_result = build_plate(name_inputs, config)

        # --- advisory flags (E9: a plate on flagged inputs is NO ACTION) ---
        stale = [d.symbol for d in plate_result.drops
                 if d.reason == PlateDropReason.HOLDINGS_STALE]
        e6 = [d.symbol for d in plate_result.drops
              if d.reason in (PlateDropReason.E6_CAPS_OFF_CONFLICT,
                              PlateDropReason.E6_PEAK_CYCLE_CONFLICT)]
        unclassified = [n.symbol for n in all_names
                        if n.symbol in prices and n.classified_on is None]
        advisory: list[str] = []
        if stale:
            advisory.append(
                f"BLOCK: {len(stale)} owned names have no holdings row — household equity, "
                f"P-tiers and caps are unreliable (sync UC2.1): {', '.join(sorted(stale))}"
            )
        if unarmable:
            advisory.append(
                f"WARN: triggers not armed (E3 — re-derive on fresh EPS): {', '.join(unarmable)}"
            )
        if not gsec_source.startswith(("cnbc", "yfinance")):
            advisory.append(f"WARN: GoI yield not live — {gsec_source}")
        if unclassified:
            advisory.append(
                f"WARN: E4 unclassified (default ladder used): {', '.join(unclassified)}"
            )
        if fund_result.failures:
            advisory.append(f"WARN: fundamentals missing for {len(fund_result.failures)} names")
        unpriced_held = sorted(s for s, q in holdings_qty.items() if q > 0 and s not in prices)
        if unpriced_held:
            advisory.append(
                f"WARN: {len(unpriced_held)} held names unpriced (not in register / no ticker) — "
                f"household equity understated, weights conservative: {', '.join(unpriced_held)}"
            )
        if e6:
            advisory.append(f"WARN: E6 caps-off conflict — needs your ruling: {', '.join(e6)}")
        if plate_result.plan_amount > session_amount:
            more = plate_result.plan_amount - session_amount
            advisory.insert(0,
                f"BUDGET: {_inr(session_amount)} is not enough for 1 share of each of the "
                f"{len(plate_result.entries)} ranked stocks — this plate needs "
                f"{_inr(plate_result.plan_amount)} ({_inr(more)} more)")
        brand = sorted(d.symbol for d in plate_result.drops
                       if d.reason == PlateDropReason.BRAND_UNVERIFIED)
        if brand:
            advisory.append(
                f"BRAND CHECK: FMCG names eligible today but brand ownership not recorded "
                f"— confirm who owns the brand: {', '.join(brand)}")
        held = sorted(d.symbol for d in plate_result.drops
                      if d.reason == PlateDropReason.EVENT_HOLD)
        if held:
            advisory.append(
                f"RESULTS WEEK: held — results within {config.event_hold_days} days "
                f"(buy anyway only if you opt in): {', '.join(held)}")
        by_sym = {n.symbol: n for n in name_inputs}
        no_date = sorted(e.symbol for e in plate_result.entries
                         if by_sym[e.symbol].next_result_date is None
                         and by_sym[e.symbol].sector_class not in ("INDEX_ETF", "NON_EARNING"))
        if no_date:
            advisory.append(
                f"WARN: next results date unknown — check none is due this week: "
                f"{', '.join(no_date)}")
        review = sorted(d.symbol for d in plate_result.drops
                        if d.reason == PlateDropReason.REVIEW_FIRST)
        if review:
            advisory.append(
                f"REVIEW FIRST: marked don't-buy but passing every gate — analyse before "
                f"buying: {', '.join(review)}")

        # --- write session ---
        gate_details = {
            sym: {"passed": gr.passed, "gate": gr.gate_name, "detail": gr.detail,
                  "fair_pe": gr.fair_pe, "justified_pb": gr.justified_pb}
            for sym, gr in gate_results.items()
        }
        outputs: dict = _json_safe({
            "entries": [asdict(e) for e in plate_result.entries],
            "bees_sweep_qty": plate_result.bees_sweep_qty,
            "bees_sweep_amount": str(plate_result.bees_sweep_amount),
            "total_stock_amount": str(plate_result.total_stock_amount),
            "total_with_sweep": str(plate_result.total_with_sweep),
            "plan_amount": str(plate_result.plan_amount),
            "residual": str(plate_result.residual),
            "advisory_flags": advisory,
            "gate_details": gate_details,
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
            "triggers_unarmable": unarmable,
        }
        drops_json = [
            {"symbol": d.symbol, "reason": d.reason.name, "detail": d.detail,
             "what_would_change": d.what_would_change,
             "h": str(d.h) if d.h is not None else None,
             "l_pct": str(d.l_pct) if d.l_pct is not None else None}
            for d in [*plate_result.drops, *unpriced]
        ]

        if record_session:
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
            fair_pe=compute_fair_pe(gsec_yield_pct),
            household_equity=household_equity,
            fundamentals_fetched=len(fund_map),
            fundamentals_failed=len(fund_result.failures),
            advisory_flags=advisory,
            breadth_min=int(_policy_decimal(policy, "breadth_min")),
            breadth_max=int(_policy_decimal(policy, "breadth_max")),
            name_inputs=tuple(name_inputs),
            config=config,
            unpriced=tuple(unpriced),
        )
    finally:
        repo.close()


# ------------------------------------------------------------- output ---


def _inr(v: Decimal) -> str:
    """Indian grouping: 3,47,775."""
    q = int(v.quantize(Decimal(1), rounding=ROUND_HALF_UP))
    s = str(abs(q))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts: list[str] = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return ("-" if q < 0 else "") + "Rs " + s


_NEAR_MISS_ALWAYS = frozenset({
    PlateDropReason.HOLDINGS_STALE,
    PlateDropReason.FIRST_BITE_FAILED,
    PlateDropReason.E6_CAPS_OFF_CONFLICT,
    PlateDropReason.E6_PEAK_CYCLE_CONFLICT,
    PlateDropReason.REVIEW_FIRST,
    PlateDropReason.BRAND_UNVERIFIED,
    PlateDropReason.EVENT_HOLD,
    PlateDropReason.DECAY_EXPIRED,
    PlateDropReason.P_BLOCKED,
    PlateDropReason.NO_ADD_HOLD_ONLY,
    PlateDropReason.SCORE_ZERO,
})
_NEAR_MISS_IF_H_ELIGIBLE = frozenset({
    PlateDropReason.CELL_FULL,
    PlateDropReason.PEAK_CYCLE,
    PlateDropReason.PSU_CAP,
    PlateDropReason.P5_VETO,
})
_BULK_ORDER = [
    PlateDropReason.NO_TRIGGER, PlateDropReason.NOT_ELIGIBLE,
    PlateDropReason.CELL_FULL, PlateDropReason.STATUS_BLOCKED,
    PlateDropReason.EXIT_DECIDED, PlateDropReason.NEVER_ADD,
]


def _is_near_miss(d: PlateDrop, h_min: Decimal, l_max: Decimal) -> bool:
    """Display cut-off only (not a rule): a drop worth reading, not just counting."""
    if d.reason in _NEAR_MISS_ALWAYS:
        return True
    if d.reason == PlateDropReason.NOT_ELIGIBLE:
        return (d.h is not None and d.h >= h_min - Decimal("0.10")) or (
            d.l_pct is not None and d.l_pct <= l_max * 2
        )
    if d.reason == PlateDropReason.NO_TRIGGER:
        return d.l_pct is not None and d.l_pct <= l_max
    if d.reason in _NEAR_MISS_IF_H_ELIGIBLE:
        return d.h is not None and d.h >= h_min
    return False


def format_plate(result: PlateRunResult) -> str:
    """Report for Praveen. Spec E8: inputs with stamps · rules fired · the plate ·
    every drop with its reason · what would change the verdict."""
    p = result.plate
    L: list[str] = []
    blocked = any(f.startswith("BLOCK") for f in result.advisory_flags)
    h_min = Decimal("0.85")
    l_max = Decimal(5)

    L.append(f"TIFFIN COFFEE PLATE — {result.ran_at[:10]}  |  run {result.run_id}")
    L.append(
        f"Ticket {_inr(p.session_amount)}"
        + (f" → plan {_inr(p.plan_amount)}" if p.plan_amount > p.session_amount else "")
        + f"  |  GoI {result.gsec_yield_pct}% "
        f"({result.gsec_source}) → fair P/E {result.fair_pe}x  |  "
        f"Household equity {_inr(result.household_equity)}"
        + ("  [PHANTOM — holdings partial]" if blocked else "")
    )
    L.append(
        f"Scanned {result.names_scanned}  |  prices {result.prices_fetched} ok / "
        f"{result.prices_failed} failed  |  fundamentals {result.fundamentals_fetched} ok / "
        f"{result.fundamentals_failed} failed"
    )
    L.append("")

    if result.advisory_flags:
        L.append("!! ADVISORY — DO NOT EXECUTE !!" if blocked else "ADVISORY")
        for f in result.advisory_flags:
            L.append(f"  - {f}")
        L.append("")

    # --- the plate ---
    if p.entries:
        L.append(f"PLATE — {len(p.entries)} name(s) · {_inr(p.total_stock_amount)}")
        L.append(
            f"  {'#':>2} {'Name':12s} {'Qty':>3} {'LTP':>9} {'Amount':>10} "
            f"{'Mode':10s} {'H':>6} {'L%':>6} {'Band':12s} {'P-tier':11s} "
            f"{'Score':>6} {'Order'}"
        )
        for i, e in enumerate(p.entries, 1):
            h_str = f"{e.h:.3f}" if e.h is not None else "-"
            order = "TIGHT LIMIT (first bite, max 5)" if e.is_first_bite else "TIGHT LIMIT"
            L.append(
                f"  {i:>2} {e.symbol:12s} {e.qty:>3} {e.price:>9.2f} {e.amount:>10.2f} "
                f"{e.mode.value:10s} {h_str:>6} {e.l_pct:>5.1f}% {e.low_band.value:12s} "
                f"{e.p_tier.value:11s} {e.score:>6.3f} {order}"
            )
    else:
        L.append("PLATE — no stock qualifies today; BeES floor applies")
    if p.bees_sweep_qty > 0:
        L.append(f"   ↳ NIFTYBEES sweep {p.bees_sweep_qty} = {_inr(p.bees_sweep_amount)}")
    L.append(
        f"  TOTAL {_inr(p.total_with_sweep)} = stocks {_inr(p.total_stock_amount)} "
        f"+ BeES {_inr(p.bees_sweep_amount)}  |  residual {_inr(p.residual)}"
    )
    L.append("")

    # --- what would change the verdict ---
    near = [d for d in p.drops if _is_near_miss(d, h_min, l_max)]
    if near:
        L.append("WHAT WOULD CHANGE THE VERDICT — near misses")
        L.append(f"  {'Name':12s} {'Reason':22s} {'H':>6} {'L%':>6}  Why → what would change it")
        for d in sorted(near, key=lambda x: (x.reason.name, x.symbol)):
            h_str = f"{d.h:.3f}" if d.h is not None else "-"
            l_str = f"{d.l_pct:.1f}%" if d.l_pct is not None else "-"
            L.append(
                f"  {d.symbol:12s} {d.reason.name:22s} {h_str:>6} {l_str:>6}  "
                f"{d.detail} → {d.what_would_change}"
            )
        L.append("")

    # --- the rest, by rule ---
    near_syms = {d.symbol for d in near}
    bulk: dict[PlateDropReason, list[str]] = {}
    for d in p.drops:
        if d.symbol not in near_syms:
            bulk.setdefault(d.reason, []).append(d.symbol)
    if bulk:
        L.append("EXCLUDED BY RULE")
        ordered = _BULK_ORDER + [r for r in bulk if r not in _BULK_ORDER]
        for r in ordered:
            if r in bulk:
                L.append(f"  {r.name} ({len(bulk[r])}): {', '.join(sorted(bulk[r]))}")
        L.append("")

    if result.unpriced:
        by: dict[PlateDropReason, list[str]] = {}
        for d in result.unpriced:
            by.setdefault(d.reason, []).append(d.symbol)
        L.append("NOT PRICED THIS RUN — no action on these (E3/E9)")
        for r, syms in by.items():
            L.append(f"  {r.name} ({len(syms)}): {', '.join(sorted(syms))}")
        L.append("")

    # --- guardrails ---
    n = len(p.entries)
    breadth_ok = result.breadth_min <= n <= result.breadth_max
    L.append("GUARDRAILS")
    L.append("  [x] READ-ONLY — code proposes, Praveen executes in Kite")
    L.append("  [x] qty clamp 1-10 on every name (first bite ≤ 5)")
    if breadth_ok:
        breadth_note = ""
    elif n < result.breadth_min:
        breadth_note = " — BELOW floor; spec says loosen L ≤ 10% — NOT auto-applied (ask)"
    else:
        breadth_note = " — ABOVE ceiling; raise the ticket or drop bottom scores"
    L.append(
        f"  [{'x' if breadth_ok else ' '}] breadth "
        f"{result.breadth_min}-{result.breadth_max}: {n}{breadth_note}"
    )
    L.append("  [x] BeES floor NEVER_SKIP — residual swept")
    L.append("  [x] no buy+sell in one session (EXIT_DECIDED enforced)")
    L.append("  [ ] single-deployment cap 15% of surplus — surplus not in the register yet")
    held = [d.symbol for d in p.drops if d.reason == PlateDropReason.EVENT_HOLD]
    L.append(f"  [x] results-week pause — held: {', '.join(held) if held else 'none'}")
    if blocked:
        L.append("  [ ] holdings synced — NO (this plate is advisory only)")
    return "\n".join(L)
