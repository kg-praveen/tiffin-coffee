"""engine/ranker.py — UC3 plate ranker: legal plate variants, scored, best marked.

Spec: tiffin-coffee v6. The ranker changes NO rule. It only lays out the choices the
spec itself hands to a human, builds each with the real engine (engine/plate.build_plate)
and re-checks each with engine/invariants.check_plate:

  • session amount inside the ticket band — tiffin v4 §TICKET SIZE: "Praveen's ₹5-10K
    band [POLICY]" (policy ticket_band_min / ticket_band_max). The amount Praveen asked
    for is always shown, even outside the band;
  • raise the session / drop the bottom-scoring names — tiffin v6 §BREADTH TARGET:
    "more than 15 means the ticket is too thin (raise the session or drop the
    bottom-scoring names)". Raising never goes past the band top.

Not generated (E6 — the spec does not make it a free choice): "fewer than 8 means the
screen was too tight (loosen to L ≤ 10%)" changes the eligibility rule itself; it stays
a question for Praveen (see usecases/plate.format_plate GUARDRAILS).

Any variant with an invariant VIOLATION is discarded (E9). The rest are ordered
LEXICOGRAPHICALLY by the criteria listed, in order, in policy `ranker_criteria_order`
(E2 — no invented weights). Each criterion cites its spec text on `Criterion`. The
1-10 clamp is not a score: a clamp breach is a QTY_CLAMP VIOLATION and discards the
variant outright. Ties: smaller plan amount (tiffin v4 §TICKET SIZE — ticket x 30 is
the reserve, so the smaller ticket asks less of it), then fewer trimmed names, then
the variant label (stable text order). Pure: no I/O, no clock.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal
from enum import Enum

from engine.invariants import Check, Severity, check_plate
from engine.plate import (
    NameInput,
    PlateConfig,
    PlateDrop,
    PlateDropReason,
    PlateEntry,
    PlateResult,
    build_plate,
)


class Criterion(Enum):
    """One ranking criterion, each traceable to spec text."""

    # tiffin v4 §TICKET SIZE: "Praveen's ₹5-10K band [POLICY] x 30 = ... reserve"
    TICKET_BAND = "ticket_band"
    # Praveen 26-Sep-2026 (engine/plate.size_by_rank): the plan is RAISED only when one
    # share of each ranked name costs more than the session — "shown, never hidden"
    NO_RAISE = "no_raise"
    # tiffin v6 §BREADTH TARGET: "8-15 names per session"
    BREADTH = "breadth"
    # tiffin v6 §formula STEP 6 "residual → BeES Floor": the least money left idle
    RESIDUAL = "residual"


class VariantKind(Enum):
    """Which session amount a variant uses."""

    AS_ASKED = "AS_ASKED"      # the amount Praveen asked for
    BAND_LOW = "BAND_LOW"      # policy ticket_band_min
    BAND_HIGH = "BAND_HIGH"    # policy ticket_band_max ("raise the session", capped)


@dataclass(frozen=True)
class RankerPolicy:
    """Policy rows the ranker needs (E2: all from the policy table)."""

    ticket_band_min: Decimal
    ticket_band_max: Decimal
    breadth_min: int
    breadth_max: int
    criteria: tuple[Criterion, ...]


def parse_criteria(text: str) -> tuple[Criterion, ...]:
    """Policy `ranker_criteria_order` → criteria in order. Unknown, empty or repeated
    names fail closed (E9: no guessed ranking)."""
    names = [t.strip() for t in text.split(",") if t.strip()]
    if not names:
        raise ValueError("ranker_criteria_order is empty")
    if len(set(names)) != len(names):
        raise ValueError(f"ranker_criteria_order repeats a criterion: {text!r}")
    known = {c.value: c for c in Criterion}
    unknown = [n for n in names if n not in known]
    if unknown:
        raise ValueError(f"ranker_criteria_order has unknown criteria: {unknown}")
    return tuple(known[n] for n in names)


def load_ranker_policy(values: Mapping[str, str]) -> RankerPolicy:
    """Build RankerPolicy from policy values (key → value text). A missing key raises
    KeyError — E2: a policy constant is never defaulted in code."""
    return RankerPolicy(
        ticket_band_min=Decimal(values["ticket_band_min"]),
        ticket_band_max=Decimal(values["ticket_band_max"]),
        breadth_min=int(values["breadth_min"]),
        breadth_max=int(values["breadth_max"]),
        criteria=parse_criteria(values["ranker_criteria_order"]),
    )


# ----------------------------------------------------------------- variants ---


@dataclass(frozen=True)
class Variant:
    """One legal-by-construction plate choice, built by build_plate and checked."""

    label: str
    kind: VariantKind
    session_amount: Decimal
    trimmed: tuple[str, ...]
    config: PlateConfig
    result: PlateResult
    checks: tuple[Check, ...]

    @property
    def violations(self) -> list[Check]:
        return [c for c in self.checks if c.severity == Severity.VIOLATION]


def candidate_amounts(asked: Decimal, policy: RankerPolicy) -> list[tuple[VariantKind, Decimal]]:
    """The asked amount, then the band bottom and top (tiffin v4 §TICKET SIZE) —
    each amount once, first kind wins."""
    out: list[tuple[VariantKind, Decimal]] = []
    for kind, amt in ((VariantKind.AS_ASKED, asked),
                      (VariantKind.BAND_LOW, policy.ticket_band_min),
                      (VariantKind.BAND_HIGH, policy.ticket_band_max)):
        if all(a != amt for _, a in out):
            out.append((kind, amt))
    return out


def _label(kind: VariantKind, amount: Decimal, trimmed: tuple[str, ...]) -> str:
    return f"{kind.value}@{amount}" + (f"+TRIM{len(trimmed)}" if trimmed else "")


def _checked(names: Sequence[NameInput], config: PlateConfig, kind: VariantKind,
             result: PlateResult, trimmed: tuple[str, ...],
             policy: RankerPolicy) -> Variant:
    checks = check_plate(list(names), config, result, policy.breadth_min, policy.breadth_max)
    return Variant(_label(kind, config.session_amount, trimmed), kind,
                   config.session_amount, trimmed, config, result, tuple(checks))


def build_variant(names: Sequence[NameInput], config: PlateConfig, kind: VariantKind,
                  amount: Decimal, policy: RankerPolicy) -> Variant:
    """The real plate at `amount` — build_plate unchanged, only the session differs."""
    cfg = replace(config, session_amount=amount)
    return _checked(names, cfg, kind, build_plate(list(names), cfg), (), policy)


def _trim_drop(e: PlateEntry, rank: int, total: int, policy: RankerPolicy) -> PlateDrop:
    return PlateDrop(
        e.symbol, e.name, PlateDropReason.BREADTH_TRIMMED,
        f"score {e.score} ranks #{rank} of {total}; breadth ceiling is {policy.breadth_max}",
        h=e.h, l_pct=e.l_pct,
        what_would_change=f"a score inside the top {policy.breadth_max}, or pick a "
                          f"variant that keeps every ranked name",
    )


def trim_variant(names: Sequence[NameInput], base: Variant,
                 policy: RankerPolicy) -> Variant | None:
    """tiffin v6 §BREADTH TARGET "drop the bottom-scoring names": only when the plate
    is above the ceiling, and only down to the ceiling. Bottom = build_plate's own rank
    order (score, then symbol). Trimmed names are dropped WITH a reason (E8)."""
    entries = base.result.entries
    if len(entries) <= policy.breadth_max:
        return None
    cut = entries[policy.breadth_max:]
    cut_syms = {e.symbol for e in cut}
    kept = [n for n in names if n.symbol not in cut_syms]
    r = build_plate(kept, base.config)
    drops = [_trim_drop(e, policy.breadth_max + i + 1, len(entries), policy)
             for i, e in enumerate(cut)]
    r = replace(r, drops=[*r.drops, *drops],
                rules_fired=[*r.rules_fired, *(f"BREADTH_TRIM:{e.symbol}" for e in cut)])
    return _checked(names, base.config, base.kind, r, tuple(e.symbol for e in cut), policy)


def generate_variants(names: Sequence[NameInput], config: PlateConfig,
                      policy: RankerPolicy) -> list[Variant]:
    """Every variant: each candidate amount, plus its trimmed twin when breadth is
    above the ceiling. config.session_amount is the amount Praveen asked for."""
    out: list[Variant] = []
    for kind, amt in candidate_amounts(config.session_amount, policy):
        v = build_variant(names, config, kind, amt, policy)
        out.append(v)
        t = trim_variant(names, v, policy)
        if t is not None:
            out.append(t)
    return out


# ------------------------------------------------------------------ scoring ---


@dataclass(frozen=True)
class Mark:
    """How one variant stands on one criterion. `sort_value`: lower is better."""

    criterion: Criterion
    ok: bool
    sort_value: Decimal
    detail: str


def _in_band(amount: Decimal, policy: RankerPolicy) -> bool:
    return policy.ticket_band_min <= amount <= policy.ticket_band_max


def mark_ticket_band(v: Variant, policy: RankerPolicy) -> Mark:
    """tiffin v4 §TICKET SIZE: the plan (what is actually spent) sits in the band."""
    plan = v.result.plan_amount
    ok = _in_band(plan, policy)
    return Mark(Criterion.TICKET_BAND, ok, Decimal(not ok),
                f"plan {plan} {'inside' if ok else 'outside'} the "
                f"{policy.ticket_band_min}-{policy.ticket_band_max} ticket band")


def mark_no_raise(v: Variant, policy: RankerPolicy) -> Mark:
    """Praveen 26-Sep-2026: a raised plan means the session could not buy 1 of each."""
    r = v.result
    ok = r.plan_amount == r.session_amount
    return Mark(Criterion.NO_RAISE, ok, Decimal(not ok),
                "spends the session as given" if ok
                else f"needs {r.plan_amount} (session {r.session_amount} too small for 1 each)")


def mark_breadth(v: Variant, policy: RankerPolicy) -> Mark:
    """tiffin v6 §BREADTH TARGET 8-15 (policy breadth_min / breadth_max)."""
    n = len(v.result.entries)
    ok = policy.breadth_min <= n <= policy.breadth_max
    return Mark(Criterion.BREADTH, ok, Decimal(not ok),
                f"{n} names vs target {policy.breadth_min}-{policy.breadth_max}")


def mark_residual(v: Variant, policy: RankerPolicy) -> Mark:
    """tiffin v6 STEP 6: residual → BeES; what is still left after the sweep is idle."""
    res = v.result.residual
    return Mark(Criterion.RESIDUAL, True, res, f"{res} left after stocks + BeES")


_MARKERS = {
    Criterion.TICKET_BAND: mark_ticket_band,
    Criterion.NO_RAISE: mark_no_raise,
    Criterion.BREADTH: mark_breadth,
    Criterion.RESIDUAL: mark_residual,
}


@dataclass(frozen=True)
class ScoredVariant:
    variant: Variant
    marks: tuple[Mark, ...]      # every criterion, in Criterion order (for display)
    key: tuple[Decimal, ...]     # policy order, then the tie-break rule

    def mark(self, c: Criterion) -> Mark:
        return next(m for m in self.marks if m.criterion == c)


def score_variant(v: Variant, policy: RankerPolicy) -> ScoredVariant:
    """Marks on every criterion; the sort key follows the policy order, then ties:
    smaller plan, fewer trimmed names (label breaks the last tie in rank_order)."""
    marks = tuple(_MARKERS[c](v, policy) for c in Criterion)
    by = {m.criterion: m for m in marks}
    key = (*(by[c].sort_value for c in policy.criteria),
           v.result.plan_amount, Decimal(len(v.trimmed)))
    return ScoredVariant(v, marks, key)


@dataclass(frozen=True)
class RankerResult:
    ranked: tuple[ScoredVariant, ...]   # legal variants, best first
    discarded: tuple[Variant, ...]      # a VIOLATION — never ranked (E9)
    best: ScoredVariant | None          # None → NO ACTION
    why: tuple[str, ...]


def _beats(best: ScoredVariant, other: ScoredVariant, policy: RankerPolicy) -> str:
    """The first criterion (policy order) on which best beats other — or the tie rule."""
    for c in policy.criteria:
        b, o = best.mark(c), other.mark(c)
        if b.sort_value != o.sort_value:
            return f"beats {other.variant.label} on {c.value}: {b.detail} vs {o.detail}"
    if best.variant.result.plan_amount != other.variant.result.plan_amount:
        return (f"ties {other.variant.label} on every criterion — smaller plan wins "
                f"({best.variant.result.plan_amount} vs {other.variant.result.plan_amount})")
    return f"ties {other.variant.label} on every criterion — fewer trims / label order"


def score_variants(variants: Sequence[Variant], policy: RankerPolicy) -> RankerResult:
    """Discard any variant with a VIOLATION; order the rest by key, then label."""
    legal = [v for v in variants if not v.violations]
    discarded = tuple(v for v in variants if v.violations)
    ranked = tuple(sorted((score_variant(v, policy) for v in legal),
                          key=lambda s: (s.key, s.variant.label)))
    if not ranked:
        return RankerResult((), discarded, None,
                            ("no legal variant — NO ACTION (E9)",))
    best = ranked[0]
    why = tuple(_beats(best, o, policy) for o in ranked[1:])
    return RankerResult(ranked, discarded, best, why)


def rank_variants(names: Sequence[NameInput], config: PlateConfig,
                  policy: RankerPolicy) -> RankerResult:
    """UC3: generate every legal variant, score, mark the best. Deterministic —
    names are sorted by symbol first so input order never changes the answer."""
    ordered = sorted(names, key=lambda n: n.symbol)
    return score_variants(generate_variants(ordered, config, policy), policy)
