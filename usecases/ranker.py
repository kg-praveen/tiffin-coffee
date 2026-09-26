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
from usecases.plate import PlateRunResult, _inr, run_plate

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "db" / "pattaz.db"
MARKET_DIR = ROOT / "tests" / "fixtures" / "market"
_POLICY_KEYS = ("ticket_band_min", "ticket_band_max", "breadth_min", "breadth_max",
                "ranker_criteria_order")


@dataclass(frozen=True)
class RankerRunResult:
    run_id: str
    ran_at: str
    asked: Decimal
    market_source: str
    today: str
    policy: RankerPolicy
    plate_run: PlateRunResult
    ranking: RankerResult


def _load_policy(db_path: str | Path) -> RankerPolicy:
    """E2: every ranker constant from the policy table; a missing row fails closed."""
    with PattazRepo(db_path) as repo:
        rows = repo.load_policy()
    missing = [k for k in _POLICY_KEYS if k not in rows]
    if missing:
        raise ValueError(f"policy rows missing: {', '.join(missing)} — apply migration 014 "
                         f"(db/migrations/014_plate_ranker.sql)")
    return load_ranker_policy({k: rows[k].value for k in _POLICY_KEYS})


def run_ranker(db_path: str | Path, amount: Decimal | None, *,
               market: MarketSnapshot | None, market_source: str,
               today: str | None = None, record_session: bool = True) -> RankerRunResult:
    """UC3. `amount` None → the band top (policy ticket_band_max). `market` None → live
    fetch through the UC2 adapters. The underlying plate run writes no session."""
    policy = _load_policy(db_path)
    asked = policy.ticket_band_max if amount is None else amount
    run = run_plate(db_path, asked, fetch_prices=market is None, market=market,
                    today=today, record_session=False)
    if run.config is None:
        raise RuntimeError("run_plate returned no config — cannot rank")
    ranking = rank_variants(run.name_inputs, run.config, policy)
    result = RankerRunResult(
        run_id=f"UC3_{uuid.uuid4().hex[:12]}",
        ran_at=datetime.now(UTC).isoformat(timespec="seconds"),
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


def _write_session(db_path: str | Path, r: RankerRunResult) -> None:
    """E8: inputs, every variant, the best and why, every drop of the best plate."""
    best = r.ranking.best
    drops: list[dict[str, object]] = []
    if best is not None:
        drops += [{"symbol": d.symbol, "reason": d.reason.name, "detail": d.detail,
                   "what_would_change": d.what_would_change}
                  for d in best.variant.result.drops]
    drops += [{"symbol": d.symbol, "reason": d.reason.name, "detail": d.detail,
               "what_would_change": d.what_would_change} for d in r.plate_run.unpriced]
    drops += [{"symbol": c.symbol, "reason": c.invariant,
               "detail": f"variant {v.label} discarded: {c.detail}"}
              for v in r.ranking.discarded for c in v.violations]
    rules = [f"UC3_ORDER:{'>'.join(c.value for c in r.policy.criteria)}"]
    if best is not None:
        rules += [f"UC3_BEST:{best.variant.label}", *best.variant.result.rules_fired]
    else:
        rules.append("UC3_NO_ACTION")
    with PattazRepo(db_path) as repo:
        repo.append_session(
            run_id=r.run_id, ran_at=r.ran_at, usecase="UC3_RANKER",
            inputs={"asked": str(r.asked), "today": r.today,
                    "market_source": r.market_source,
                    "ticket_band": [str(r.policy.ticket_band_min),
                                    str(r.policy.ticket_band_max)],
                    "breadth": [r.policy.breadth_min, r.policy.breadth_max],
                    "criteria_order": [c.value for c in r.policy.criteria],
                    "gsec_yield_pct": str(r.plate_run.gsec_yield_pct),
                    "gsec_source": r.plate_run.gsec_source},
            outputs={"verdict": "NO_ACTION" if best is None else "BEST_MARKED",
                     "best": best.variant.label if best else None,
                     "why": list(r.ranking.why),
                     "variants": [_variant_json(s) for s in r.ranking.ranked],
                     "discarded": [v.label for v in r.ranking.discarded],
                     "advisory_flags": list(r.plate_run.advisory_flags)},
            drops=drops, rules_fired=rules,
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
    s = f"{_inr(v.session_amount)} {_KIND_WORDS[v.kind]}"
    return s + (f", top {policy.breadth_max} only" if v.trimmed else "")


def _yes(ok: bool) -> str:
    return "yes" if ok else "NO"


def _why_words(r: RankerRunResult) -> list[str]:
    """Plain restatement of engine/ranker._beats for each runner-up."""
    best = r.ranking.best
    if best is None:
        return []
    out: list[str] = []
    for other in r.ranking.ranked[1:]:
        c = next((c for c in r.policy.criteria
                  if best.mark(c).sort_value != other.mark(c).sort_value), None)
        name = _words(other.variant, r.policy)
        if c is None:
            out.append(f"vs {name}: equal on every rule — the smaller ticket wins")
        elif c == Criterion.RESIDUAL:
            out.append(f"vs {name}: leaves {_inr(best.variant.result.residual)} over, "
                       f"not {_inr(other.variant.result.residual)}")
        else:
            out.append(f"vs {name}: that one fails '{_CRITERION_WORDS[c]}' "
                       f"({other.mark(c).detail})")
    return out


def format_ranker(r: RankerRunResult) -> str:
    """Verdict first, then the side-by-side table, what each plate buys, and why."""
    pol, rk = r.policy, r.ranking
    blocked = any(f.startswith("BLOCK") for f in r.plate_run.advisory_flags)
    L = [f"PLATE RANKER (UC3) — market {r.today} ({r.market_source})  |  run {r.run_id}",
         f"You asked for {_inr(r.asked)}. I built {len(rk.ranked) + len(rk.discarded)} "
         f"plates the rules allow and compared them.", ""]
    best = rk.best
    if best is None:
        L.append("VERDICT: NO ACTION — every variant broke a law (E9). Run the simulation.")
    else:
        b = best.variant.result
        L.append(f"BEST: {_words(best.variant, pol)} — {len(b.entries)} stock(s) for "
                 f"{_inr(b.total_stock_amount)} + BeES {_inr(b.bees_sweep_amount)}, "
                 f"{_inr(b.residual)} left over.")
    if blocked:
        L.append("!! Holdings are not synced — advisory only, DO NOT EXECUTE !!")
    L.append("")

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
            f"  {i:>2}{star} {_words(v, pol):32s} {_inr(res.plan_amount):>9s} "
            f"{len(res.entries):>5d} {_inr(res.total_stock_amount):>9s} "
            f"{_inr(res.bees_sweep_amount):>8s} {_inr(res.residual):>7s}  "
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

    if r.plate_run.advisory_flags:
        L.append("ADVISORY (from the plate engine)")
        L += [f"  - {f}" for f in r.plate_run.advisory_flags]
        L.append("")

    L.append("HOW I RANKED — in this order (policy ranker_criteria_order), no weights:")
    L += [f"  {i}. {_CRITERION_WORDS[c]}" for i, c in enumerate(pol.criteria, 1)]
    L.append("  ties → the smaller ticket, then fewer names left off.")
    L.append("  Every plate shown obeyed every law (1-10 clamp, overlays, gates, budget).")
    L.append("  Not offered: loosening the screen to L ≤ 10% when breadth is thin — that "
             "changes a rule; your call.")
    L.append("")
    L.append("Proposal only. Nothing was placed or changed. For the full drop list run "
             "the plate skill at the amount you choose.")
    return "\n".join(L)


# ---------------------------------------------------------------------- CLI ---


def _market(args: argparse.Namespace) -> tuple[MarketSnapshot | None, str]:
    """--live → fetch through the plate adapters (None); else a recording."""
    if args.live:
        return None, "live fetch this run"
    path = newest_snapshot(MARKET_DIR) if args.market == "recording" else Path(args.market)
    if path is None:
        raise SystemExit("no recording found — run `python -m usecases.simulate record`")
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
    snap, src = _market(a)
    r = run_ranker(db, a.amount, market=snap, market_source=src,
                   today=snap.recorded_at if snap is not None else None,
                   record_session=not a.no_session)
    print(format_ranker(r))
    return 0 if r.ranking.best is not None else 1


if __name__ == "__main__":
    sys.exit(main())
