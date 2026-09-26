"""usecases/ranker.py — UC3: show the plates the rules allow, side by side, best marked.

Spec: tiffin-coffee v6 (engine/ranker.py carries every citation). Runs the real UC2
plate once for its inputs (live, or a recorded market day), then the pure ranker builds
each variant — the ticket band bottom/top, the asked amount, and the bottom-scores trim
when breadth is above the ceiling — checks every law on each, and marks the best.

Writes ONE `UC3_RANKER` session (E8). Never writes a UC2 session: a variant is a choice
for Praveen, not a decision. Proposal only — never places, stages or changes anything.

    python -m usecases.ranker [--amount N] [--market recording|PATH] [--live]
"""
from __future__ import annotations

import argparse
import sys
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from engine.plate import PlateDrop
from engine.ranker import (
    Criterion,
    RankerPolicy,
    RankerResult,
    ScoredVariant,
    Variant,
    VariantKind,
    load_ranker_policy,
    rank_variants,
)
from store.repo import PattazRepo
from tools.market_snapshot import MarketSnapshot, load_snapshot, newest_snapshot
from usecases.format import inr
from usecases.plate import PlateRunResult, run_plate

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "db" / "pattaz.db"
MARKET_DIR = ROOT / "tests" / "fixtures" / "market"
_POLICY_KEYS = ("ticket_band_min", "ticket_band_max", "breadth_min", "breadth_max",
                "ranker_criteria_order")


# The criteria order and the "smaller plan wins" tie-break are NOT spec text: the build
# proposed them (migration 014). Until Praveen confirms, every output marks the ranking
# PROVISIONAL and carries the open question. Flip only on his word (and say so in the PR).
RANKING_PROVISIONAL = True


def ranking_open_question(policy: RankerPolicy | None) -> str:
    """The advisory line shown until Praveen confirms the ranking (CLAUDE.md §7)."""
    order = (" > ".join(c.value for c in policy.criteria) if policy is not None
             else "ticket_band > no_raise > breadth > residual")
    return (f"OPEN QUESTION for Praveen: confirm ranking order {order} and the "
            f"'smaller plan wins' tie-break — neither is spec text (policy "
            f"ranker_criteria_order, migration 014); until you confirm, BEST is provisional.")


@dataclass(frozen=True)
class RankerRunResult:
    """One UC3 run. `no_action_reason` set → the run failed closed (E9): policy, plate
    run and ranking may be missing, and the verdict is NO ACTION."""

    run_id: str
    ran_at: str
    asked: Decimal | None
    market_source: str
    today: str | None
    policy: RankerPolicy | None
    plate_run: PlateRunResult | None
    ranking: RankerResult | None
    no_action_reason: str | None = None

    @property
    def best(self) -> ScoredVariant | None:
        return self.ranking.best if self.ranking is not None else None


def _load_policy(db_path: str | Path) -> RankerPolicy:
    """E2: every ranker constant from the policy table; a missing row fails closed."""
    with PattazRepo(db_path) as repo:
        rows = repo.load_policy()
    missing = [k for k in _POLICY_KEYS if k not in rows]
    if missing:
        raise ValueError(f"policy rows missing: {', '.join(missing)} — apply migration 014 "
                         f"(db/migrations/014_plate_ranker.sql)")
    return load_ranker_policy({k: rows[k].value for k in _POLICY_KEYS})


def _new_ids() -> tuple[str, str]:
    return (f"UC3_{uuid.uuid4().hex[:12]}",
            datetime.now(UTC).isoformat(timespec="seconds"))


def no_action(db_path: str | Path, reason: str, *, asked: Decimal | None,
              market_source: str, today: str | None, policy: RankerPolicy | None = None,
              plate_run: PlateRunResult | None = None,
              record_session: bool = True) -> RankerRunResult:
    """CLAUDE.md §3 / E9: a failed run is NO ACTION with a named reason, and it still
    writes its UC3_RANKER session (verdict NO_ACTION)."""
    run_id, ran_at = _new_ids()
    result = RankerRunResult(run_id=run_id, ran_at=ran_at, asked=asked,
                             market_source=market_source, today=today, policy=policy,
                             plate_run=plate_run, ranking=None, no_action_reason=reason)
    if record_session:
        _write_session(db_path, result)
    return result


def run_ranker(db_path: str | Path, amount: Decimal | None, *,
               market: MarketSnapshot | None, market_source: str,
               today: str | None = None, record_session: bool = True) -> RankerRunResult:
    """UC3. `amount` None → the band top (policy ticket_band_max). `market` None → live
    fetch through the UC2 adapters. The underlying plate run writes no session. A
    missing/invalid policy row or a plate run without a config → NO ACTION (E9)."""
    try:
        policy = _load_policy(db_path)
    except (ValueError, KeyError, ArithmeticError) as exc:
        return no_action(db_path, f"ranker policy unusable: {exc}", asked=amount,
                         market_source=market_source, today=today,
                         record_session=record_session)
    asked = policy.ticket_band_max if amount is None else amount
    run = run_plate(db_path, asked, fetch_prices=market is None, market=market,
                    today=today, record_session=False)
    if run.config is None:
        return no_action(db_path, "the plate run returned no config — nothing to rank",
                         asked=asked, market_source=market_source, today=today,
                         policy=policy, plate_run=run, record_session=record_session)
    ranking = rank_variants(run.name_inputs, run.config, policy)
    run_id, ran_at = _new_ids()
    result = RankerRunResult(
        run_id=run_id, ran_at=ran_at,
        asked=asked, market_source=market_source, today=run.config.today,
        policy=policy, plate_run=run, ranking=ranking,
    )
    if record_session:
        _write_session(db_path, result)
    return result


# ------------------------------------------------------------------ session ---


def _variant_json(s: ScoredVariant) -> dict[str, object]:
    r = s.variant.result
    return {
        "label": s.variant.label, "session": str(s.variant.session_amount),
        "plan": str(r.plan_amount), "names": len(r.entries),
        "stock": str(r.total_stock_amount), "bees": str(r.bees_sweep_amount),
        "residual": str(r.residual), "trimmed": list(s.variant.trimmed),
        "entries": [[e.symbol, e.qty, str(e.amount)] for e in r.entries],
        "marks": {m.criterion.value: {"ok": m.ok, "detail": m.detail} for m in s.marks},
        "findings": [c.detail for c in s.variant.checks],
    }


def shown_variant(r: RankerRunResult) -> Variant | None:
    """The variant whose drops are listed (E8): the best, else the as-asked plate."""
    if r.ranking is None:
        return None
    if r.ranking.best is not None:
        return r.ranking.best.variant
    every = [*(s.variant for s in r.ranking.ranked), *r.ranking.discarded]
    return next((v for v in every if v.kind == VariantKind.AS_ASKED),
                every[0] if every else None)


def shown_drops(r: RankerRunResult) -> list[PlateDrop]:
    """Every dropped name the output must explain (E8): the shown variant's drops,
    then the names that could not be priced this run."""
    v = shown_variant(r)
    drops = list(v.result.drops) if v is not None else []
    if r.plate_run is not None:
        drops += list(r.plate_run.unpriced)
    return drops


def holding_flags(r: RankerRunResult) -> list[str]:
    """Advisory flags that hold the plate: BLOCK (holdings) and E6 (needs a ruling)."""
    flags = r.plate_run.advisory_flags if r.plate_run is not None else []
    return [f for f in flags if f.startswith("BLOCK") or "E6" in f]


def _write_session(db_path: str | Path, r: RankerRunResult) -> None:
    """E8: inputs, every variant, the best and why, every drop of the shown plate.
    A NO ACTION run still writes one (CLAUDE.md §3)."""
    best = r.best
    drops: list[dict[str, object]] = [
        {"symbol": d.symbol, "reason": d.reason.name, "detail": d.detail,
         "what_would_change": d.what_would_change} for d in shown_drops(r)]
    if r.ranking is not None:
        drops += [{"symbol": c.symbol, "reason": c.invariant,
                   "detail": f"variant {v.label} discarded: {c.detail}"}
                  for v in r.ranking.discarded for c in v.violations]
    rules: list[str] = []
    if r.policy is not None:
        rules.append(f"UC3_ORDER:{'>'.join(c.value for c in r.policy.criteria)}")
    if best is not None:
        rules += [f"UC3_BEST:{best.variant.label}", *best.variant.result.rules_fired]
    else:
        rules.append("UC3_NO_ACTION")
    pr, pol = r.plate_run, r.policy
    inputs: dict[str, object] = {
        "asked": str(r.asked) if r.asked is not None else None, "today": r.today,
        "market_source": r.market_source,
        "gsec_yield_pct": str(pr.gsec_yield_pct) if pr is not None else None,
        "gsec_source": pr.gsec_source if pr is not None else None,
    }
    if pol is not None:
        inputs |= {"ticket_band": [str(pol.ticket_band_min), str(pol.ticket_band_max)],
                   "breadth": [pol.breadth_min, pol.breadth_max],
                   "criteria_order": [c.value for c in pol.criteria]}
    rk = r.ranking
    outputs: dict[str, object] = {
        "verdict": "NO_ACTION" if best is None else "BEST_MARKED",
        "no_action_reason": r.no_action_reason,
        "best": best.variant.label if best else None,
        "ranking_status": "PROVISIONAL" if RANKING_PROVISIONAL else "CONFIRMED",
        "open_questions": [ranking_open_question(pol)] if RANKING_PROVISIONAL else [],
        "why": list(rk.why) if rk is not None else [],
        "variants": [_variant_json(s) for s in rk.ranked] if rk is not None else [],
        "discarded": [v.label for v in rk.discarded] if rk is not None else [],
        "advisory_flags": list(pr.advisory_flags) if pr is not None else [],
    }
    with PattazRepo(db_path) as repo:
        repo.append_session(
            run_id=r.run_id, ran_at=r.ran_at, usecase="UC3_RANKER",
            inputs=inputs, outputs=outputs, drops=drops, rules_fired=rules,
        )


# ------------------------------------------------------------------- output ---

_KIND_WORDS = {
    VariantKind.AS_ASKED: "as you asked",
    VariantKind.BAND_LOW: "band bottom",
    VariantKind.BAND_HIGH: "band top",
}
_CRITERION_WORDS = {
    Criterion.TICKET_BAND: "what it spends stays inside your ticket band "
                           "[tiffin v4 §TICKET SIZE]",
    Criterion.NO_RAISE: "the session is enough for 1 share of each — no raised budget "
                        "[Praveen 26-Sep-2026 sizing]",
    Criterion.BREADTH: "breadth inside the target [tiffin v6 §BREADTH TARGET]",
    Criterion.RESIDUAL: "least money left over after stocks + BeES [tiffin v6 STEP 6]",
}


def _words(v: Variant, policy: RankerPolicy) -> str:
    s = f"{inr(v.session_amount)} {_KIND_WORDS[v.kind]}"
    return s + (f", top {policy.breadth_max} only" if v.trimmed else "")


def _yes(ok: bool) -> str:
    return "yes" if ok else "NO"


def _in_band(amount: Decimal, pol: RankerPolicy) -> bool:
    """tiffin v4 §TICKET SIZE band (policy ticket_band_min / ticket_band_max)."""
    return pol.ticket_band_min <= amount <= pol.ticket_band_max


def _band(pol: RankerPolicy) -> str:
    return f"{inr(pol.ticket_band_min)}-{inr(pol.ticket_band_max)}"


def _summary(v: Variant) -> str:
    b = v.result
    return (f"{len(b.entries)} stock(s) for {inr(b.total_stock_amount)} + BeES "
            f"{inr(b.bees_sweep_amount)}, {inr(b.residual)} left over")


def _why_words(r: RankerRunResult) -> list[str]:
    """Plain restatement of engine/ranker._beats for each runner-up."""
    best, pol, rk = r.best, r.policy, r.ranking
    if best is None or pol is None or rk is None:
        return []
    out: list[str] = []
    for other in rk.ranked[1:]:
        c = next((c for c in pol.criteria
                  if best.mark(c).sort_value != other.mark(c).sort_value), None)
        name = _words(other.variant, pol)
        if c is None:
            out.append(f"vs {name}: equal on every rule — the smaller ticket wins "
                       f"(provisional tie-break)")
        elif c == Criterion.RESIDUAL:
            out.append(f"vs {name}: leaves {inr(best.variant.result.residual)} over, "
                       f"not {inr(other.variant.result.residual)}")
        else:
            out.append(f"vs {name}: that one fails '{_CRITERION_WORDS[c]}' "
                       f"({other.mark(c).detail})")
    return out


def _inputs_line(r: RankerRunResult) -> str:
    """E8: the inputs with their as-of stamps and sources."""
    parts = [f"market as of {r.today or 'n/a'} ({r.market_source})"]
    pr = r.plate_run
    if pr is not None:
        parts.append(f"prices {pr.prices_fetched} fetched / {pr.prices_failed} failed "
                     f"of {pr.names_scanned} scanned")
        parts.append(f"GoI 10y {pr.gsec_yield_pct}% ({pr.gsec_source})")
        parts.append(f"fundamentals {pr.fundamentals_fetched} fetched / "
                     f"{pr.fundamentals_failed} failed")
    else:
        parts.append("GoI 10y n/a (no plate run)")
    if r.policy is not None:
        parts.append(f"policy band {_band(r.policy)}, breadth "
                     f"{r.policy.breadth_min}-{r.policy.breadth_max}")
    return "INPUTS: " + " · ".join(parts)


def _drop_lines(r: RankerRunResult) -> list[str]:
    """E8: every dropped name with its reason and what would change the verdict."""
    drops = shown_drops(r)
    if not drops:
        return []
    v = shown_variant(r)
    which = (f"the {_words(v, r.policy)} plate" if v is not None and r.policy is not None
             else "this run")
    out = [f"DROPPED — {len(drops)} name(s) from {which} and the unpriced, each with "
           f"its reason"]
    for d in drops:
        out.append(f"  - {d.symbol}: {d.reason.name} — {d.detail}")
        out.append(f"      what would change: {d.what_would_change or 'n/a'}")
    return out


def _advisory_lines(r: RankerRunResult) -> list[str]:
    flags = r.plate_run.advisory_flags if r.plate_run is not None else []
    if not flags:
        return []
    return ["ADVISORY (from the plate engine)", *(f"  - {f}" for f in flags), ""]


def _format_no_action(r: RankerRunResult) -> str:
    """E9: the fail-closed output — the reason first, then what was known."""
    L = [f"PLATE RANKER (UC3) — market {r.today or 'n/a'} ({r.market_source})  |  "
         f"run {r.run_id}",
         f"NO ACTION — {r.no_action_reason or 'nothing to rank'}", "",
         _inputs_line(r), ""]
    L += _advisory_lines(r)
    if RANKING_PROVISIONAL:
        L += [ranking_open_question(r.policy), ""]
    L += ["Safe output is NO ACTION (E9). Fix the cause above and run again.",
          "Proposal only. Nothing was placed or changed."]
    return "\n".join(L)


def _verdict_lines(r: RankerRunResult, pol: RankerPolicy, rk: RankerResult,
                   asked: Decimal) -> list[str]:
    L: list[str] = []
    best = rk.best
    if not _in_band(asked, pol):
        in_band = next((s for s in rk.ranked if _in_band(s.variant.session_amount, pol)),
                       None)
        head = f"VERDICT: your {inr(asked)} is outside your {_band(pol)} ticket band; "
        L.append(head + (f"within the band the best is {_words(in_band.variant, pol)} — "
                         f"{_summary(in_band.variant)}." if in_band is not None
                         else "no plate inside the band passed every law."))
        every = [*(s.variant for s in rk.ranked), *rk.discarded]
        as_asked = next((v for v in every if v.kind == VariantKind.AS_ASKED), None)
        if as_asked is not None:
            tail = "THROWN OUT (broke a law)" if as_asked.violations else _summary(as_asked)
            L.append(f"AS ASKED ({inr(asked)}, outside the band): {tail}.")
    if best is None:
        L.append("VERDICT: NO ACTION — every variant broke a law (E9). Run the simulation.")
    else:
        tag = "BEST (provisional ranking)" if RANKING_PROVISIONAL else "BEST"
        L.append(f"{tag}: {_words(best.variant, pol)} — {_summary(best.variant)}.")
    if holding_flags(r):
        L.append("!! Held by ADVISORY flag(s) (BLOCK/E6) — advisory only, DO NOT EXECUTE !!")
    if RANKING_PROVISIONAL:
        L.append(ranking_open_question(pol))
    return L


def format_ranker(r: RankerRunResult) -> str:
    """Verdict first, then inputs, why, the side-by-side table, what each plate buys,
    and every drop with what would change it (E8)."""
    pol, rk, asked = r.policy, r.ranking, r.asked
    if r.no_action_reason is not None or pol is None or rk is None or asked is None:
        return _format_no_action(r)
    best = rk.best
    holds = holding_flags(r)
    L = [f"PLATE RANKER (UC3) — market {r.today} ({r.market_source})  |  run {r.run_id}",
         f"You asked for {inr(asked)}. I built {len(rk.ranked) + len(rk.discarded)} "
         f"plates the rules allow and compared them.", ""]
    L += _verdict_lines(r, pol, rk, asked)
    L += ["", _inputs_line(r), ""]

    if best is not None and rk.why:
        L.append("WHY IT WINS")
        L += [f"  - {w}" for w in _why_words(r)]
        L.append("")

    L.append("SIDE BY SIDE")
    L.append(f"  {'#':>2}  {'plate':32s} {'plan':>9s} {'names':>5s} {'stocks':>9s} "
             f"{'BeES':>8s} {'left':>7s}  {'in band':7s} {'1 each':6s} breadth")
    for i, s in enumerate(rk.ranked, 1):
        v, res = s.variant, s.variant.result
        star = "*" if s is best else " "
        L.append(
            f"  {i:>2}{star} {_words(v, pol):32s} {inr(res.plan_amount):>9s} "
            f"{len(res.entries):>5d} {inr(res.total_stock_amount):>9s} "
            f"{inr(res.bees_sweep_amount):>8s} {inr(res.residual):>7s}  "
            f"{_yes(s.mark(Criterion.TICKET_BAND).ok):7s} "
            f"{_yes(s.mark(Criterion.NO_RAISE).ok):6s} "
            f"{_yes(s.mark(Criterion.BREADTH).ok)} ({len(res.entries)} vs "
            f"{pol.breadth_min}-{pol.breadth_max})")
    L.append("")

    L.append("WHAT EACH PLATE BUYS")
    for i, s in enumerate(rk.ranked, 1):
        v = s.variant
        buys = " · ".join(f"{e.symbol} {e.qty}" for e in v.result.entries) or "no stock"
        sweep = f" · NIFTYBEES {v.result.bees_sweep_qty}" if v.result.bees_sweep_qty else ""
        L.append(f"  {i:>2}{'*' if s is best else ' '} {_words(v, pol)}: {buys}{sweep}")
        if v.trimmed:
            L.append(f"      left off (bottom scores): {', '.join(v.trimmed)}")
    L.append("")

    if rk.discarded:
        L.append("THROWN OUT — broke a law, never an option (E9)")
        for v in rk.discarded:
            L.append(f"  {_words(v, pol)}: " + "; ".join(
                f"{c.invariant} {c.symbol} {c.detail}" for c in v.violations))
        L.append("")

    L += _advisory_lines(r)
    drop_lines = _drop_lines(r)
    if drop_lines:
        L += [*drop_lines, ""]

    status = ("PROVISIONAL — awaiting your confirmation" if RANKING_PROVISIONAL
              else "confirmed")
    L.append(f"HOW I RANKED ({status}) — in this order (policy ranker_criteria_order), "
             f"no weights:")
    L += [f"  {i}. {_CRITERION_WORDS[c]}" for i, c in enumerate(pol.criteria, 1)]
    L.append("  ties → the smaller ticket, then fewer names left off.")
    closing = ("  Every plate shown passed every invariant check (engine/invariants) — "
               "1-10 clamp, overlays, gates, budget.")
    if holds:
        closing += (f" But {len(holds)} ADVISORY flag(s) (BLOCK/E6) hold it — see "
                    f"ADVISORY above; do not execute until resolved.")
    L.append(closing)
    L.append("  Not offered: loosening the screen to L ≤ 10% when breadth is thin — that "
             "changes a rule; your call.")
    L.append("")
    L.append("Proposal only. Nothing was placed or changed. To act, run the plate skill "
             "at the amount you choose.")
    return "\n".join(L)


# ---------------------------------------------------------------------- CLI ---


def _market(args: argparse.Namespace) -> tuple[MarketSnapshot | None, str]:
    """--live → fetch through the plate adapters (None); else a recording."""
    if args.live:
        return None, "live fetch this run"
    path = newest_snapshot(MARKET_DIR) if args.market == "recording" else Path(args.market)
    if path is None:
        raise FileNotFoundError("no recording found — run "
                                "`python -m usecases.simulate record`")
    return load_snapshot(path), f"recording {path.name}"


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m usecases.ranker", description=__doc__)
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--amount", type=Decimal, default=None,
                    help="session amount (default: policy ticket_band_max)")
    ap.add_argument("--market", default="recording",
                    help="'recording' (newest in tests/fixtures/market) or a recording path")
    ap.add_argument("--live", action="store_true", help="fetch today's market instead")
    ap.add_argument("--no-session", action="store_true")
    a = ap.parse_args(argv)
    db = Path(a.db)
    try:
        snap, src = _market(a)
    except (OSError, ValueError, KeyError) as exc:
        r = no_action(db, f"no market data: {exc}", asked=a.amount,
                      market_source=str(a.market), today=None,
                      record_session=not a.no_session)
    else:
        r = run_ranker(db, a.amount, market=snap, market_source=src,
                       today=snap.recorded_at if snap is not None else None,
                       record_session=not a.no_session)
    print(format_ranker(r))
    return 0 if r.best is not None else 1


if __name__ == "__main__":
    sys.exit(main())
