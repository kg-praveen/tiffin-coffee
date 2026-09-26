"""engine/invariants.py — laws every plate must obey, whatever the market does.

Spec: UC5 simulation suite. Each invariant restates a rule that already lives in
engine/plate.py or the spec — it re-checks the OUTPUT, it never re-decides (E7: the
gate is defined once; this module only asserts its consequences).

Two severities:
  VIOLATION — a law is broken; the plate must not be trusted (E9 → NO ACTION).
  FINDING   — legal per spec but Praveen should see it (e.g. breadth outside 8-15,
              the plate spending more than the session because of the 1-share floor).

Pure: no I/O, no clock. Inputs are the NameInputs, config and result of one build.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from engine.plate import (
    BRAND_GATE_SECTORS,
    REVIEW_FIRST_BUCKETS,
    NameInput,
    PlateConfig,
    PlateResult,
    compute_h,
    compute_l,
)


class Severity(Enum):
    VIOLATION = "VIOLATION"
    FINDING = "FINDING"


@dataclass(frozen=True)
class Check:
    """One invariant outcome for one name (or the plate as a whole: symbol='*')."""

    invariant: str
    severity: Severity
    symbol: str
    detail: str


_BANNED_STATUS = frozenset({"SOLD", "NEVER_ADD"})


def inv_accounting(names: list[NameInput], result: PlateResult) -> list[Check]:
    """E8: every name considered is either plated or dropped with a reason — exactly once."""
    out: list[Check] = []
    seen: dict[str, int] = {}
    for sym in [e.symbol for e in result.entries] + [d.symbol for d in result.drops]:
        seen[sym] = seen.get(sym, 0) + 1
    for n in names:
        c = seen.get(n.symbol, 0)
        if c != 1:
            out.append(Check("ACCOUNTING", Severity.VIOLATION, n.symbol,
                             f"appears {c}x across entries+drops (must be exactly 1)"))
    extra = set(seen) - {n.symbol for n in names}
    out.extend(Check("ACCOUNTING", Severity.VIOLATION, s, "plated/dropped but never an input")
               for s in sorted(extra))
    return out


def inv_drops_explained(result: PlateResult) -> list[Check]:
    """E8: every drop names its reason and what would change the verdict."""
    return [Check("DROP_EXPLAINED", Severity.VIOLATION, d.symbol,
                  f"{d.reason.name} has no what-would-change")
            for d in result.drops if not d.what_would_change.strip()]


def inv_qty_clamp(result: PlateResult, config: PlateConfig) -> list[Check]:
    """tiffin v6 §formula step 5: HARD 1-10; a PRICE-BITE is clamped to 5."""
    out: list[Check] = []
    for e in result.entries:
        hi = config.first_bite_qty_max if e.is_first_bite else config.qty_clamp_max
        if not config.qty_clamp_min <= e.qty <= hi:
            out.append(Check("QTY_CLAMP", Severity.VIOLATION, e.symbol,
                             f"qty={e.qty} outside [{config.qty_clamp_min}, {hi}]"))
    return out


def inv_priced_from_input(names: list[NameInput], result: PlateResult) -> list[Check]:
    """E3/E9: no path from missing data to a buy — every entry is priced from this run."""
    by_sym = {n.symbol: n for n in names}
    out: list[Check] = []
    for e in result.entries:
        n = by_sym.get(e.symbol)
        if n is None or n.price <= 0 or e.price != n.price:
            out.append(Check("PRICED_FROM_INPUT", Severity.VIOLATION, e.symbol,
                             f"entry price {e.price} not the input price"))
    return out


def inv_no_banned_entry(names: list[NameInput], result: PlateResult,
                        config: PlateConfig) -> list[Check]:
    """Overlays #2/#7/#8/#9/#10 + status + PSU cap: these names never plate."""
    by_sym = {n.symbol: n for n in names}
    out: list[Check] = []
    for e in result.entries:
        n = by_sym.get(e.symbol)
        if n is None:
            continue
        why = [w for w, bad in (
            ("status " + n.status, n.status in _BANNED_STATUS),
            ("exit decided", n.flag_exit_decided),
            ("sovereign P1", n.flag_sovereign),
            ("probe open", n.flag_probe_open),
            ("fraud tail", n.flag_fraud_tail),
            ("PSU cap breached", n.flag_psu
             and config.psu_weight_pct >= config.cap_psu_regulated_pct),
            (f"register bucket {n.bucket} (review first)", n.bucket in REVIEW_FIRST_BUCKETS),
            ("FMCG brand not owned / not recorded",
             n.sector_class in BRAND_GATE_SECTORS and n.brand_owned is not True),
        ) if bad]
        if why:
            out.append(Check("NO_BANNED_ENTRY", Severity.VIOLATION, e.symbol, ", ".join(why)))
    return out


def inv_eligibility(names: list[NameInput], result: PlateResult,
                    config: PlateConfig) -> list[Check]:
    """tiffin v6 §formula step 1 + §first-bite (a)-(d): a plated name is either
    H-eligible on a live trigger, or a first bite — at the low, owned, gate passed."""
    by_sym = {n.symbol: n for n in names}
    out: list[Check] = []
    for e in result.entries:
        n = by_sym.get(e.symbol)
        if n is None:
            continue
        h_ok = (n.trigger_level is not None
                and compute_h(n.trigger_level, n.price) >= config.eligible_h_min)
        if h_ok and not e.is_first_bite:
            continue
        l_pct = compute_l(n.price, n.low_52w)
        owned = n.qty_held_household > 0 or (n.owned_per_book and n.p_mult_book is not None)
        fails = [w for w, bad in (
            (f"L={l_pct}% > {config.first_bite_l_max}%", l_pct > config.first_bite_l_max),
            ("not owned", not owned),
            ("sector valuation gate failed", not n.valuation_gate_passed),
        ) if bad]
        if fails:
            out.append(Check("ELIGIBILITY", Severity.VIOLATION, e.symbol,
                             "neither H-eligible nor a valid first bite: " + "; ".join(fails)))
    return out


def inv_totals(result: PlateResult) -> list[Check]:
    """Arithmetic closes: stock + sweep + residual = plan amount."""
    out: list[Check] = []
    stock = sum((e.amount for e in result.entries), Decimal(0))
    if stock != result.total_stock_amount:
        out.append(Check("TOTALS", Severity.VIOLATION, "*",
                         f"entries sum {stock} != total_stock {result.total_stock_amount}"))
    if result.total_stock_amount + result.bees_sweep_amount != result.total_with_sweep:
        out.append(Check("TOTALS", Severity.VIOLATION, "*", "stock + sweep != total_with_sweep"))
    if result.plan_amount - result.total_with_sweep != result.residual:
        out.append(Check("TOTALS", Severity.VIOLATION, "*", "plan - total != residual"))
    return out


def inv_budget(result: PlateResult, config: PlateConfig) -> list[Check]:
    """Praveen 26-Sep-2026: the plate never spends more than its plan amount, and the
    plan is the session unless 1 share of each ranked name costs more — then exactly
    that cost, not a rupee more."""
    out: list[Check] = []
    if result.total_with_sweep > result.plan_amount:
        out.append(Check("BUDGET", Severity.VIOLATION, "*",
                         f"spends {result.total_with_sweep} > plan {result.plan_amount}"))
    one_each = sum((e.price * config.qty_clamp_min for e in result.entries), Decimal(0))
    expected = max(result.session_amount, one_each)
    if result.entries and result.plan_amount != expected:
        out.append(Check("BUDGET", Severity.VIOLATION, "*",
                         f"plan {result.plan_amount} but should be {expected} "
                         f"(session {result.session_amount}, 1 each {one_each})"))
    return out


def find_budget_and_breadth(result: PlateResult, breadth_min: int,
                            breadth_max: int) -> list[Check]:
    """FINDINGS (legal, worth Praveen's eye): tiffin v6 §breadth 8-15, and a session
    too small for 1 share of each ranked name (the plan was raised)."""
    out: list[Check] = []
    n = len(result.entries)
    if n and not breadth_min <= n <= breadth_max:
        out.append(Check("BREADTH", Severity.FINDING, "*",
                         f"{n} names vs target {breadth_min}-{breadth_max}"))
    if result.plan_amount > result.session_amount:
        more = result.plan_amount - result.session_amount
        out.append(Check("BUDGET_RAISED", Severity.FINDING, "*",
                         f"session {result.session_amount} too small for 1 share of each "
                         f"— plan raised to {result.plan_amount} (+{more})"))
    return out


def check_plate(names: list[NameInput], config: PlateConfig, result: PlateResult,
                breadth_min: int, breadth_max: int) -> list[Check]:
    """Run every single-plate invariant. Order is stable (deterministic output)."""
    return [
        *inv_accounting(names, result),
        *inv_drops_explained(result),
        *inv_qty_clamp(result, config),
        *inv_priced_from_input(names, result),
        *inv_no_banned_entry(names, result, config),
        *inv_eligibility(names, result, config),
        *inv_totals(result),
        *inv_budget(result, config),
        *find_budget_and_breadth(result, breadth_min, breadth_max),
    ]


def inv_gate_monotone(base: PlateResult, tighter: PlateResult) -> list[Check]:
    """Metamorphic: a higher GoI yield lowers fair P/E and raises r — valuation gates
    only tighten (osep v7 §3 ladder). So a first bite that fails at the lower yield can
    never appear at the higher one, prices unchanged."""
    before = {e.symbol for e in base.entries if e.is_first_bite}
    return [Check("GATE_MONOTONE", Severity.VIOLATION, e.symbol,
                  "first bite appeared only after the yield rose")
            for e in tighter.entries if e.is_first_bite and e.symbol not in before]


def inv_fail_closed(result: PlateResult) -> list[Check]:
    """E9: with no market data at all, the safe output is NO ACTION — no stock, no sweep."""
    if result.entries or result.bees_sweep_qty:
        return [Check("FAIL_CLOSED", Severity.VIOLATION, "*",
                      f"{len(result.entries)} entries / sweep {result.bees_sweep_qty} "
                      f"with no market data")]
    return []


def drop_counts(result: PlateResult) -> dict[str, int]:
    """Drops by reason name, sorted — for reports."""
    counts: dict[str, int] = {}
    for d in result.drops:
        counts[d.reason.name] = counts.get(d.reason.name, 0) + 1
    return dict(sorted(counts.items()))

