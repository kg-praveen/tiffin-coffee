"""usecases/simulate.py — UC5: automated market simulation suite.

Spec: UC5 (Praveen, 25-Sep-2026). Replays a RECORDED market day through the real
UC1 board and UC2 plate under shocks (usecases/scenarios.py) and asserts the laws in
engine/invariants.py on every plate. Two modes:

  CI         — tests/sim replays the committed recording; any VIOLATION fails the build.
  on demand  — `python -m usecases.simulate run|what-if [--live]`; writes ONE
               `UC5_SIMULATION` session. Hypothetical plates are never written as UC2
               sessions — a simulated plate is not a decision (E1, D56).

Proposal only: the simulation never places, stages or suggests an order.
"""
from __future__ import annotations

import argparse
import sys
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from engine.invariants import (
    Check,
    Severity,
    check_plate,
    drop_counts,
    inv_fail_closed,
    inv_gate_monotone,
)
from engine.plate import PlateEntry, PlateResult
from store.repo import PattazRepo
from tools.market_snapshot import (
    MarketSnapshot,
    load_snapshot,
    newest_snapshot,
    record_snapshot,
    save_snapshot,
)
from usecases.morning_board import run_morning_board
from usecases.plate import PlateRunResult, run_plate
from usecases.scenarios import Scenario, SimContext, build_catalog, custom_scenario

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "db" / "pattaz.db"
MARKET_DIR = ROOT / "tests" / "fixtures" / "market"
DEFAULT_AMOUNTS = (Decimal(10000),)


@dataclass(frozen=True)
class ScenarioOutcome:
    scenario: str
    title: str
    spec_ref: str
    amount: Decimal
    today: str
    entries: tuple[PlateEntry, ...]
    plan: Decimal
    stock_amount: Decimal
    sweep_qty: int
    sweep_amount: Decimal
    total: Decimal
    fired: tuple[str, ...]
    near: tuple[str, ...]
    drops_by_reason: dict[str, int]
    advisory: tuple[str, ...]
    checks: tuple[Check, ...]
    tags: tuple[str, ...] = ()

    @property
    def violations(self) -> list[Check]:
        return [c for c in self.checks if c.severity == Severity.VIOLATION]

    @property
    def findings(self) -> list[Check]:
        return [c for c in self.checks if c.severity == Severity.FINDING]


@dataclass(frozen=True)
class SimulationResult:
    run_id: str
    ran_at: str
    market_recorded_at: str
    market_source: str
    outcomes: tuple[ScenarioOutcome, ...]
    cross_checks: tuple[Check, ...] = field(default_factory=tuple)

    @property
    def violations(self) -> list[tuple[str, Check]]:
        out = [(o.scenario, c) for o in self.outcomes for c in o.violations]
        out += [("cross-scenario", c) for c in self.cross_checks
                if c.severity == Severity.VIOLATION]
        return out


# ------------------------------------------------------------------ context ---


def load_context(db_path: Path) -> SimContext:
    with PattazRepo(db_path) as repo:
        names = repo.load_names()
        cells = repo.load_cells()
        policy = repo.load_policy()
    seats = sorted({s.strip() for c in cells if c.active_adds
                    for s in c.active_adds.split(",") if s.strip()})
    # market recordings key by ticker stem (RECLTD), the register by symbol (REC): map both
    keys = [(n, {n.symbol, (n.yf_ticker or n.symbol).removesuffix(".NS")}) for n in names]
    return SimContext(
        sector_of={k: n.sector_class for n, ks in keys for k in ks},
        seats=tuple(seats),
        policy={k: v.value for k, v in policy.items()},
        nse_sector_of={k: n.nse_sector for n, ks in keys for k in ks},
    )


def _shift(day: str, days: int) -> str:
    return (date.fromisoformat(day) + timedelta(days=days)).isoformat()


# ---------------------------------------------------------------------- run ---


def _plate(db: Path, snap: MarketSnapshot, amount: Decimal, today: str) -> PlateRunResult:
    return run_plate(db, amount, market=snap, today=today, record_session=False)


def run_scenario(db: Path, base: MarketSnapshot, sc: Scenario, ctx: SimContext,
                 amount: Decimal) -> tuple[ScenarioOutcome, PlateResult]:
    """One scenario at one session amount: board + plate + every invariant."""
    snap = sc.shock(base, ctx)
    today = _shift(base.recorded_at, sc.clock_days)
    run = _plate(db, snap, amount, today)
    if run.config is None:
        raise RuntimeError("run_plate returned no config — cannot check invariants")
    checks = check_plate(list(run.name_inputs), run.config, run.plate,
                         run.breadth_min, run.breadth_max)
    if sc.expect_fail_closed:
        checks += inv_fail_closed(run.plate)
    # determinism (CLAUDE.md §4): same inputs → same plate
    again = _plate(db, snap, amount, today)
    if again.plate != run.plate:
        checks.append(Check("DETERMINISM", Severity.VIOLATION, "*",
                            "two runs on identical inputs produced different plates"))
    board = run_morning_board(db, prices=snap.prices.prices, results=snap.results,
                              today=today, record_session=False)
    p = run.plate
    return ScenarioOutcome(
        scenario=sc.name, title=sc.title, spec_ref=sc.spec_ref, amount=amount, today=today,
        entries=tuple(p.entries), plan=p.plan_amount, stock_amount=p.total_stock_amount,
        sweep_qty=p.bees_sweep_qty, sweep_amount=p.bees_sweep_amount,
        total=p.total_with_sweep,
        fired=tuple(e.symbol for e in board.fired), near=tuple(e.symbol for e in board.near),
        drops_by_reason=drop_counts(p), advisory=tuple(run.advisory_flags),
        checks=tuple(checks), tags=sc.tags,
    ), p


def run_simulation(db_path: Path, base: MarketSnapshot, scenarios: Sequence[Scenario],
                   amounts: Sequence[Decimal] = DEFAULT_AMOUNTS, *,
                   ctx: SimContext | None = None, market_source: str = "recording",
                   record_session: bool = True) -> SimulationResult:
    ctx = ctx or load_context(db_path)
    outcomes: list[ScenarioOutcome] = []
    plates: dict[tuple[str, Decimal], PlateResult] = {}
    for sc in scenarios:
        for amt in amounts:
            o, p = run_scenario(db_path, base, sc, ctx, amt)
            outcomes.append(o)
            plates[(sc.name, amt)] = p
    cross: list[Check] = []
    for amt in amounts:
        base_p, up_p = plates.get(("baseline", amt)), plates.get(("gsec_+50bp", amt))
        if base_p is not None and up_p is not None:
            cross += inv_gate_monotone(base_p, up_p)
    result = SimulationResult(
        run_id=f"UC5_{uuid.uuid4().hex[:12]}",
        ran_at=datetime.now(UTC).isoformat(timespec="seconds"),
        market_recorded_at=base.recorded_at, market_source=market_source,
        outcomes=tuple(outcomes), cross_checks=tuple(cross),
    )
    if record_session:
        _write_session(db_path, result)
    return result


def _write_session(db_path: Path, r: SimulationResult) -> None:
    """E8: one UC5 row — inputs, per-scenario summary, every violation named."""
    outputs: dict[str, object] = {
        "verdict": "FAIL" if r.violations else "PASS",
        "scenarios": [
            {"scenario": o.scenario, "amount": str(o.amount), "today": o.today,
             "entries": [[e.symbol, e.qty, str(e.amount)] for e in o.entries],
             "total": str(o.total), "fired": list(o.fired),
             "violations": len(o.violations), "findings": [c.detail for c in o.findings]}
            for o in r.outcomes
        ],
    }
    drops: list[dict[str, object]] = [
        {"symbol": c.symbol, "reason": c.invariant, "detail": f"{sc}: {c.detail}"}
        for sc, c in r.violations]
    with PattazRepo(db_path) as repo:
        repo.append_session(
            run_id=r.run_id, ran_at=r.ran_at, usecase="UC5_SIMULATION",
            inputs={"market_recorded_at": r.market_recorded_at,
                    "market_source": r.market_source,
                    "scenarios": sorted({o.scenario for o in r.outcomes}),
                    "amounts": sorted({str(o.amount) for o in r.outcomes})},
            outputs=outputs, drops=drops,
            rules_fired=sorted({c.invariant for o in r.outcomes for c in o.checks}),
        )


# ------------------------------------------------------------------- output ---


def _inr(v: Decimal) -> str:
    return f"Rs{int(v):,}"


def format_simulation(r: SimulationResult) -> str:
    """Verdict first, then the scenario table, then every violation and finding."""
    viol = r.violations
    n = len(r.outcomes)
    lines = [f"UC5 simulation — {r.run_id} · market {r.market_recorded_at} ({r.market_source})"]
    if viol:
        lines.append(f"VERDICT: FAIL — {len(viol)} law violation(s) across {n} runs. "
                     "Do not trust the engine until fixed (E9: NO ACTION).")
    else:
        lines.append(f"VERDICT: PASS — every plate obeyed every law in {n} runs.")
    lines += ["", f"  {'scenario':26s} {'asked':>9s} {'plan':>9s} {'names':>5s} {'1st':>3s} "
                  f"{'stock':>9s} {'sweep':>8s} {'total':>9s} {'fired':>5s}  flags"]
    for o in r.outcomes:
        fb = sum(1 for e in o.entries if e.is_first_bite)
        flags = ",".join(sorted({c.invariant for c in o.checks})) or "-"
        lines.append(
            f"  {o.scenario:26s} {_inr(o.amount):>9s} {_inr(o.plan):>9s} "
            f"{len(o.entries):>5d} {fb:>3d} "
            f"{_inr(o.stock_amount):>9s} {_inr(o.sweep_amount):>8s} {_inr(o.total):>9s} "
            f"{len(o.fired):>5d}  {flags}")
    if viol:
        lines += ["", "VIOLATIONS"]
        lines += [f"  [{sc}] {c.invariant} {c.symbol}: {c.detail}" for sc, c in viol]
    finds = [(o, c) for o in r.outcomes for c in o.findings]
    if finds:
        lines += ["", "FINDINGS (legal per spec — your call)"]
        lines += [f"  [{o.scenario} @ {_inr(o.amount)}] {c.invariant}: {c.detail}"
                  for o, c in finds]
    gaps = sorted({o.scenario for o in r.outcomes if "hockey-gap" in o.tags})
    if gaps:
        lines += ["", "NOT MODELLED: tiffin v6 HOCKEY triggers 'Nifty -5% wk' and "
                      "'name -10% day' — the engine has no index/day-move input, so these "
                      f"scenarios price HOCKEY only via H > 1.15 ({len(gaps)} scenarios)."]
    return "\n".join(lines)


def format_what_if(base: ScenarioOutcome, what: ScenarioOutcome) -> str:
    """On-demand: today's plate vs the what-if plate, name by name."""
    b = {e.symbol: e for e in base.entries}
    w = {e.symbol: e for e in what.entries}
    lines = [what.title, f"Session {_inr(what.amount)} · market {base.today}", ""]
    lines.append(f"  today : {len(b)} names, stock {_inr(base.stock_amount)}, "
                 f"sweep {_inr(base.sweep_amount)}, fired {', '.join(base.fired) or '-'}")
    lines.append(f"  what-if: {len(w)} names, stock {_inr(what.stock_amount)}, "
                 f"sweep {_inr(what.sweep_amount)}, fired {', '.join(what.fired) or '-'}")
    lines += ["", f"  {'name':14s} {'today':>12s} {'what-if':>16s}"]
    for sym in sorted(set(b) | set(w)):
        t = f"{b[sym].qty} @ {b[sym].price}" if sym in b else "-"
        x = w.get(sym)
        s = f"{x.qty} @ {x.price} {x.mode.value}" if x else "-"
        lines.append(f"  {sym:14s} {t:>12s} {s:>16s}")
    v = what.violations
    lines += ["", f"Laws: {'all held' if not v else f'{len(v)} VIOLATION(S) — NO ACTION'}"]
    lines += [f"  {c.invariant} {c.symbol}: {c.detail}" for c in v]
    lines.append("A simulated plate is a rehearsal, never an order.")
    return "\n".join(lines)


# ---------------------------------------------------------------------- CLI ---


def _pairs(items: Sequence[str]) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    for it in items:
        k, _, v = it.rpartition(":")
        out[k] = Decimal(v)
    return out


def _tickers(db: Path) -> list[str]:
    with PattazRepo(db) as repo:
        return [n.yf_ticker for n in repo.load_names() if n.yf_ticker]


def _base_market(args: argparse.Namespace, db: Path) -> tuple[MarketSnapshot, str]:
    if args.live:
        return record_snapshot(_tickers(db)), "live fetch this run"
    path = Path(args.market) if args.market else newest_snapshot(MARKET_DIR)
    if path is None:
        raise SystemExit("no recording found — run `python -m usecases.simulate record`")
    return load_snapshot(path), str(path.relative_to(ROOT) if path.is_absolute() else path)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m usecases.simulate", description=__doc__)
    ap.add_argument("--db", default=str(DEFAULT_DB))
    sub = ap.add_subparsers(dest="cmd", required=True)

    rec = sub.add_parser("record", help="fetch today's market ONCE and save a recording")
    rec.add_argument("--out", default=None)

    for name in ("run", "what-if"):
        p = sub.add_parser(name)
        p.add_argument("--market", default=None, help="recording to replay (default newest)")
        p.add_argument("--live", action="store_true", help="fetch live instead of a recording")
        p.add_argument("--amount", action="append", default=None, type=Decimal)
        p.add_argument("--no-session", action="store_true")
    sub.choices["run"].add_argument("--scenario", action="append", default=None)
    wi = sub.choices["what-if"]
    wi.add_argument("--nifty", type=Decimal, default=None, help="market move %%, e.g. -15")
    wi.add_argument("--sector", action="append", default=[], help="SECTOR_CLASS:-10")
    wi.add_argument("--name", action="append", default=[], help="SYMBOL:-10")
    wi.add_argument("--gsec-bp", type=Decimal, default=None)
    wi.add_argument("--days", type=int, default=0)

    a = ap.parse_args(argv)
    db = Path(a.db)

    if a.cmd == "record":
        snap = record_snapshot(_tickers(db))
        out = Path(a.out) if a.out else MARKET_DIR / f"market_{snap.recorded_at}.json"
        save_snapshot(snap, out)
        print(f"recorded {len(snap.prices.prices)} prices "
              f"({len(snap.prices.failures)} failed), "
              f"{len(snap.fundamentals.fundamentals)} fundamentals, "
              f"gsec={snap.gsec.value if snap.gsec else 'unavailable'} → {out}")
        return 0

    base, src = _base_market(a, db)
    amounts = tuple(a.amount or DEFAULT_AMOUNTS)
    ctx = load_context(db)

    if a.cmd == "run":
        cat = build_catalog(ctx)
        if a.scenario:
            cat = [s for s in cat if s.name in set(a.scenario)]
        r = run_simulation(db, base, cat, amounts, ctx=ctx, market_source=src,
                           record_session=not a.no_session)
        print(format_simulation(r))
        return 1 if r.violations else 0

    what = custom_scenario(nifty_pct=a.nifty, sector_pcts=_pairs(a.sector),
                           name_pcts=_pairs(a.name), gsec_bp=a.gsec_bp, days=a.days)
    baseline = next(s for s in build_catalog(ctx) if s.name == "baseline")
    r = run_simulation(db, base, [baseline, what], amounts[:1], ctx=ctx, market_source=src,
                       record_session=not a.no_session)
    print(format_what_if(r.outcomes[0], r.outcomes[1]))
    return 1 if r.violations else 0


if __name__ == "__main__":
    sys.exit(main())
