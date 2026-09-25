"""usecases/scenarios.py — UC5 market scenarios: pure shocks over a recorded market day.

Spec: UC5 simulation suite. A scenario never invents a price: it transforms a
RECORDED snapshot (tools/market_snapshot.py) and re-stamps every value it touches as
`sim:<scenario><-<original source>` (E2 provenance kept). Shock sizes are scenario
parameters, cited to the spec that motivates them; hockey rungs come from `policy`.

Valuation ratios move with price (P/E, P/B scale by new/old price); EPS, book value
and ROE do not — a crash makes a name cheaper, it does not change its earnings.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from decimal import ROUND_HALF_UP, Decimal

from tools.fundamentals import BatchFundamentalsResult, FundamentalsSnapshot
from tools.market_snapshot import MarketSnapshot
from tools.prices import BatchPriceResult, PriceSnapshot
from tools.stamped import Stamped

# Shock sizes quoted from the spec (tiffin v6 §H HOCKEY: "Nifty -5% wk / name -10% day").
NIFTY_WEEK_PCT = Decimal(-5)
NAME_DAY_PCT = Decimal(-10)
SECTOR_PCT = Decimal(-12)
MELT_UP_PCT = Decimal(10)
GSEC_STEP_BP = Decimal(50)
CLOCK_STALE_DAYS = 45            # > decay_gbn_days (30): every GBN verdict expires
_NO_MARKET_BETA = frozenset({"NON_EARNING"})   # gold/silver proxies don't follow Nifty

_CENT = Decimal("0.01")


@dataclass(frozen=True)
class SimContext:
    """What a shock may know about the register: sector per symbol, seat-holders."""

    sector_of: Mapping[str, str | None]
    seats: tuple[str, ...]
    policy: Mapping[str, str]


Shock = Callable[[MarketSnapshot, SimContext], MarketSnapshot]


@dataclass(frozen=True)
class Scenario:
    name: str
    title: str
    spec_ref: str
    shock: Shock
    clock_days: int = 0
    expect_fail_closed: bool = False
    tags: tuple[str, ...] = field(default_factory=tuple)


# ----------------------------------------------------------------- shocks ---


def _restamp(s: Stamped[Decimal], value: Decimal, tag: str) -> Stamped[Decimal]:
    return Stamped(value=value, source=f"sim:{tag}<-{s.source}", as_of=s.as_of)


def move_prices(snap: MarketSnapshot, pct_for: Callable[[str], Decimal | None],
                tag: str) -> MarketSnapshot:
    """Move each price by pct_for(symbol)% (None = untouched). The 52-week range
    stretches to include the new price; P/E and P/B scale with price."""
    prices: dict[str, PriceSnapshot] = {}
    ratio: dict[str, Decimal] = {}
    for sym, p in snap.prices.prices.items():
        pct = pct_for(sym)
        if pct is None or pct == 0:
            prices[sym] = p
            continue
        old = p.price.value
        new = (old * (1 + pct / 100)).quantize(_CENT, rounding=ROUND_HALF_UP)
        ratio[sym] = new / old
        prices[sym] = PriceSnapshot(
            symbol=sym,
            price=_restamp(p.price, new, tag),
            low_52w=_restamp(p.low_52w, min(p.low_52w.value, new), tag),
            high_52w=_restamp(p.high_52w, max(p.high_52w.value, new), tag),
        )
    funds: dict[str, FundamentalsSnapshot] = {}
    for sym, f in snap.fundamentals.fundamentals.items():
        r = ratio.get(sym)
        if r is None:
            funds[sym] = f
            continue

        def _scale(s: Stamped[Decimal] | None, r: Decimal = r) -> Stamped[Decimal] | None:
            if s is None:
                return None
            return _restamp(s, (s.value * r).quantize(_CENT, rounding=ROUND_HALF_UP), tag)

        funds[sym] = replace(f, pe_trailing=_scale(f.pe_trailing), pb_ratio=_scale(f.pb_ratio))
    return replace(
        snap,
        prices=BatchPriceResult(prices=prices, failures=dict(snap.prices.failures)),
        fundamentals=BatchFundamentalsResult(
            fundamentals=funds, failures=dict(snap.fundamentals.failures)),
    )


def drop_prices(snap: MarketSnapshot, lose: Callable[[str], bool], tag: str) -> MarketSnapshot:
    """Simulate a feed outage: matching symbols move from prices to failures."""
    kept = {s: p for s, p in snap.prices.prices.items() if not lose(s)}
    failures = dict(snap.prices.failures)
    failures.update({s: f"sim:{tag} — feed down" for s in snap.prices.prices if lose(s)})
    return replace(snap, prices=BatchPriceResult(prices=kept, failures=failures))


def drop_fundamentals(snap: MarketSnapshot, tag: str) -> MarketSnapshot:
    failures = dict(snap.fundamentals.failures)
    failures.update({s: f"sim:{tag} — fundamentals down" for s in snap.fundamentals.fundamentals})
    return replace(snap, fundamentals=BatchFundamentalsResult(fundamentals={}, failures=failures))


def shift_gsec(snap: MarketSnapshot, bp: Decimal | None, tag: str,
               ctx: SimContext | None = None) -> MarketSnapshot:
    """Move the GoI yield by bp basis points; bp=None removes it (feed down).

    A recording without a live yield shifts from the same policy fallback the plate
    would use (F2), stamped as such — never from an invented anchor."""
    if bp is None:
        return replace(snap, gsec=None)
    base = snap.gsec
    if base is None:
        if ctx is None or "gsec_yield_last_known" not in ctx.policy:
            return snap
        base = Stamped(value=Decimal(ctx.policy["gsec_yield_last_known"]),
                       source="policy_fallback:gsec_yield_last_known", as_of=snap.recorded_at)
    return replace(snap, gsec=_restamp(base, base.value + bp / 100, tag))


def reset_lows(snap: MarketSnapshot, tag: str) -> MarketSnapshot:
    """Every name prints a fresh 52-week low at today's price (L = 0 everywhere)."""
    prices = {s: replace(p, low_52w=_restamp(p.low_52w, p.price.value, tag))
              for s, p in snap.prices.prices.items()}
    return replace(snap, prices=BatchPriceResult(prices=prices,
                                                 failures=dict(snap.prices.failures)))


def market_move(pct: Decimal, tag: str) -> Shock:
    """Broad market move: every equity/ETF except non-earning metal proxies."""
    def _shock(snap: MarketSnapshot, ctx: SimContext) -> MarketSnapshot:
        return move_prices(
            snap, lambda s: None if ctx.sector_of.get(s) in _NO_MARKET_BETA else pct, tag)
    return _shock


def sector_move(sector: str, pct: Decimal, tag: str) -> Shock:
    def _shock(snap: MarketSnapshot, ctx: SimContext) -> MarketSnapshot:
        return move_prices(snap, lambda s: pct if ctx.sector_of.get(s) == sector else None, tag)
    return _shock


def name_move(symbol: str, pct: Decimal, tag: str) -> Shock:
    def _shock(snap: MarketSnapshot, _ctx: SimContext) -> MarketSnapshot:
        return move_prices(snap, lambda s: pct if s == symbol else None, tag)
    return _shock


def _identity(snap: MarketSnapshot, _ctx: SimContext) -> MarketSnapshot:
    return snap


def _every_third(snap: MarketSnapshot) -> Callable[[str], bool]:
    lost = set(sorted(snap.prices.prices)[::3])
    return lambda s: s in lost


# ---------------------------------------------------------------- catalog ---


def build_catalog(ctx: SimContext) -> list[Scenario]:
    """The standing CI catalog. Deterministic order; names are stable ids."""
    rung1 = -Decimal(ctx.policy["hockey_rung1_nifty_drawdown_pct"])
    rung2 = -Decimal(ctx.policy["hockey_rung2_nifty_drawdown_pct"])
    cats = [
        Scenario("baseline", "Recorded day, unchanged", "—", _identity),
        Scenario("nifty_week_-5", f"Market {NIFTY_WEEK_PCT}% in a week",
                 "tiffin v6 §H HOCKEY (Nifty -5% wk)", market_move(NIFTY_WEEK_PCT, "nifty-5"),
                 tags=("hockey-gap",)),
        Scenario("hockey_rung1", f"Market {rung1}% (hockey rung 1)", "ledger §4 D37 rung 1",
                 market_move(rung1, "rung1")),
        Scenario("hockey_rung2", f"Market {rung2}% (hockey rung 2)", "ledger §4 D37 rung 2",
                 market_move(rung2, "rung2")),
        Scenario("melt_up_+10", f"Market +{MELT_UP_PCT}%", "E9 — nothing cheap, nothing forced",
                 market_move(MELT_UP_PCT, "meltup")),
        Scenario("it_sector_-12", f"IT services {SECTOR_PCT}%", "tiffin v6 §breadth",
                 sector_move("IT_SERVICES", SECTOR_PCT, "it-12")),
        Scenario("lenders_-12", f"Lenders {SECTOR_PCT}%", "osep G-LENDER (P/B only)",
                 sector_move("LENDER", SECTOR_PCT, "lender-12")),
        Scenario("fresh_lows_everywhere", "Every name at a fresh 52-week low (L=0)",
                 "tiffin v6 §first-bite (a)-(d), clamp to 5", lambda s, _c: reset_lows(s, "lows")),
        Scenario("gsec_+50bp", f"GoI yield +{GSEC_STEP_BP}bp", "osep v7 §3 ladder",
                 lambda s, c: shift_gsec(s, GSEC_STEP_BP, "gsec+50", c)),
        Scenario("gsec_-50bp", f"GoI yield -{GSEC_STEP_BP}bp", "osep v7 §3 ladder",
                 lambda s, c: shift_gsec(s, -GSEC_STEP_BP, "gsec-50", c)),
        Scenario("gsec_feed_down", "GoI yield unavailable → policy fallback",
                 "F2 fallback + WARN", lambda s, _c: shift_gsec(s, None, "gsec-down")),
        Scenario("price_feed_down", "Every price fetch fails", "E3/E9 fail-closed",
                 lambda s, _c: drop_prices(s, lambda _x: True, "prices-down"),
                 expect_fail_closed=True),
        Scenario("partial_outage", "Every third price fetch fails", "E3 drop, never guess",
                 lambda s, _c: drop_prices(s, _every_third(s), "partial")),
        Scenario("fundamentals_down", "No P/E, P/B or ROE for anyone",
                 "E9 — valuation gates fail closed", lambda s, _c: drop_fundamentals(s, "fund")),
        Scenario("bees_missing", "NIFTYBEES unpriced — no floor sweep possible",
                 "tiffin v6 §BeES floor", lambda s, _c: drop_prices(
                     s, lambda x: x == "NIFTYBEES", "bees")),
        Scenario("clock_+45d", f"Same prices, {CLOCK_STALE_DAYS} days later",
                 "osep decay clock (GBN 30d)", _identity, clock_days=CLOCK_STALE_DAYS),
    ]
    cats.extend(
        Scenario(f"flash_{s}_-10", f"{s} {NAME_DAY_PCT}% in a day",
                 "tiffin v6 §H HOCKEY (name -10% day)", name_move(s, NAME_DAY_PCT, f"{s}-10"),
                 tags=("hockey-gap", "flash"))
        for s in ctx.seats
    )
    return cats


def custom_scenario(*, nifty_pct: Decimal | None = None,
                    sector_pcts: Mapping[str, Decimal] | None = None,
                    name_pcts: Mapping[str, Decimal] | None = None,
                    gsec_bp: Decimal | None = None, days: int = 0) -> Scenario:
    """Praveen's on-demand what-if. Moves compose: market, then sector, then name."""
    sector_pcts = dict(sector_pcts or {})
    name_pcts = dict(name_pcts or {})
    parts = []
    if nifty_pct:
        parts.append(f"market {nifty_pct:+}%")
    parts += [f"{k} {v:+}%" for k, v in sector_pcts.items()]
    parts += [f"{k} {v:+}%" for k, v in name_pcts.items()]
    if gsec_bp:
        parts.append(f"G-sec {gsec_bp:+}bp")
    if days:
        parts.append(f"+{days}d")

    def _shock(snap: MarketSnapshot, ctx: SimContext) -> MarketSnapshot:
        if nifty_pct:
            snap = market_move(nifty_pct, "whatif")(snap, ctx)
        for sec, pct in sector_pcts.items():
            snap = sector_move(sec, pct, "whatif")(snap, ctx)
        for sym, pct in name_pcts.items():
            snap = name_move(sym, pct, "whatif")(snap, ctx)
        if gsec_bp:
            snap = shift_gsec(snap, gsec_bp, "whatif", ctx)
        return snap

    return Scenario("what_if", "What if: " + (", ".join(parts) or "no change"),
                    "on-demand", _shock, clock_days=days)
