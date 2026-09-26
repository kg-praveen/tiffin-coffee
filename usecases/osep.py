"""usecases/osep.py — UC4: run OSEP on one stock; re-derive the trigger board.

Spec: osep v7 (see engine/osep.py). Flow for a name:
  1. `analyse`  — fetch price, fundamentals, company facts and the GoI yield live
     (E1/E3), add the judgments recorded for the name, run the engine, write a
     UC4_OSEP session (E8). Nothing in the register changes.
  2. `judge`    — record one researched judgment with its source (chat does the
     research; the DB records the outcome — CLAUDE.md §9).
  3. `apply`    — only on Praveen's yes: log old → new verdict with the reason
     (append-only) and write bucket / expiry / thesis / trigger to the register.
  `rederive`    — every active BUY trigger recomputed from this session's EPS / book:
     old vs new, no writes (the October job after Q2 results).
Proposal only; never places an order.
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from engine.osep import (
    Bucket,
    Judgment,
    OsepInput,
    OsepPolicy,
    OsepVerdict,
    Status,
    analyse,
    derive_trigger,
)
from store.repo import NameRow, PattazRepo
from tools.company_data import CompanyFacts, fetch_company_facts
from tools.fundamentals import FundamentalsSnapshot, fetch_fundamentals
from tools.gsec import fetch_gsec_yield
from tools.prices import PriceSnapshot, fetch_price
from tools.stamped import Stamped

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "db" / "pattaz.db"

JUDGMENT_ITEMS = {
    "sovereign_directed": "bool", "thesis_verifiable": "bool", "governance_clean": "bool",
    "industry_durable": "bool", "investable": "bool", "promoter_exempt": "bool",
    "stage1_score": "int", "thesis_type": "str", "sector_class": "str",
}


@dataclass(frozen=True)
class OsepReport:
    run_id: str
    ran_at: str
    symbol: str
    name: str
    yf_ticker: str
    in_register: bool
    old_bucket: str | None
    verdict: OsepVerdict
    inputs: dict[str, str]          # label → "value (source, as_of)"
    judgments: dict[str, tuple[str, str, str]]
    business: str | None


# ---------------------------------------------------------------- helpers ---


def _bool(v: str) -> bool:
    return v.strip().lower() in ("1", "true", "yes", "y")


def _judgment(rows: dict[str, tuple[str, str, str]]) -> Judgment:
    def b(k: str) -> bool | None:
        return _bool(rows[k][0]) if k in rows else None
    return Judgment(
        sovereign_directed=b("sovereign_directed"), thesis_verifiable=b("thesis_verifiable"),
        governance_clean=b("governance_clean"), industry_durable=b("industry_durable"),
        investable=b("investable"), promoter_exempt=b("promoter_exempt"),
        stage1_score=int(rows["stage1_score"][0]) if "stage1_score" in rows else None,
        thesis_type=rows["thesis_type"][0].upper() if "thesis_type" in rows else None,
    )


def _policy(repo: PattazRepo, gsec: Decimal) -> OsepPolicy:
    p = {k: v.value for k, v in repo.load_policy().items()}
    return OsepPolicy(
        gsec_yield_pct=gsec, coe_spread=Decimal(p["cost_of_equity_spread_over_gsec"]),
        growth_g=Decimal(p["growth_g"]), promoter_kill_pct=Decimal(p["promoter_kill_switch_pct"]),
        promoter_net_sell_flag_pct=Decimal(p["promoter_net_sell_flag_pct"]),
        stage1_gate=int(p["stage1_gate"]), decay_gbn_days=int(p["decay_gbn_days"]),
        decay_gbl_days=int(p["decay_gbl_days"]),
        decay_hard_pass_days=int(p["decay_hard_pass_days"]),
        cap_name_pct=Decimal(p["cap_name_pct"]), cap_sector_pct=Decimal(p["cap_sector_pct"]),
    )


def _gsec(repo: PattazRepo, override: Decimal | None) -> Stamped[Decimal]:
    if override is not None:
        return Stamped(value=override, source="override", as_of="this run")
    try:
        return fetch_gsec_yield()
    except ValueError:
        row = repo.load_policy().get("gsec_yield_last_known")
        if row is None:
            return Stamped(value=Decimal(0), source="unavailable", as_of="-")
        return Stamped(value=Decimal(row.value), source="policy fallback (WARN)",
                       as_of=row.adopted_on)


def _fmt(label: str, st: Stamped[object] | None) -> tuple[str, str]:
    if st is None:
        return label, "MISSING"
    return label, f"{st.value} ({st.source}, {st.as_of})"


def _standing_exclusion(n: NameRow | None) -> str | None:
    if n is None:
        return None
    if n.status in ("NEVER_ADD", "SOLD"):
        return f"register status {n.status}" + (f" — {n.notes}" if n.notes else "")
    return None


# ---------------------------------------------------------------- analyse ---


def run_osep(db: str | Path, symbol: str, *, yf_ticker: str | None = None,
             company_name: str | None = None, today: str | None = None,
             price: PriceSnapshot | None = None, fundamentals: FundamentalsSnapshot | None = None,
             facts: CompanyFacts | None = None, gsec_override: Decimal | None = None,
             record_session: bool = True) -> OsepReport:
    now = datetime.now(UTC).isoformat(timespec="seconds")
    today = today or now[:10]
    run_id = f"UC4_{uuid.uuid4().hex[:12]}"
    with PattazRepo(db) as repo:
        n = repo.get_name(symbol)
        ticker = yf_ticker or (n.yf_ticker if n else None) or f"{symbol}.NS"
        stem = ticker.removesuffix(".NS")
        judg_rows = repo.load_judgments(symbol)
        gsec = _gsec(repo, gsec_override)
        pol = _policy(repo, gsec.value)

        price = price or fetch_price(ticker)
        fundamentals = fundamentals or fetch_fundamentals(ticker)
        facts = facts or fetch_company_facts(ticker, stem)

        # one EPS for everything: the company-reported 4-quarter sum when available
        eps = (facts.eps_ttm_reported.value if facts.eps_ttm_reported else
               fundamentals.eps_ttm.value if fundamentals.eps_ttm else None)
        pe = ((price.price.value / eps).quantize(Decimal("0.01")) if eps and eps > 0
              else fundamentals.pe_trailing.value if fundamentals.pe_trailing else None)
        sector = n.sector_class if n and n.sector_class else (
            judg_rows["sector_class"][0] if "sector_class" in judg_rows else None)
        held = sum(h.qty for h in repo.get_holdings_for(symbol))

        inp = OsepInput(
            symbol=symbol, today=today, sector_class=sector,
            price=price.price.value,
            eps_ttm=eps,
            bvps=fundamentals.book_value_ps.value if fundamentals.book_value_ps else None,
            roe_pct=fundamentals.roe_pct.value if fundamentals.roe_pct else None,
            pe=pe,
            pb=fundamentals.pb_ratio.value if fundamentals.pb_ratio else None,
            promoter_pct_series=facts.promoter_pct.value if facts.promoter_pct else None,
            total_debt=facts.total_debt.value if facts.total_debt else None,
            equity=facts.equity.value if facts.equity else None,
            net_income_hist=facts.net_income.value if facts.net_income else None,
            revenue_hist=facts.revenue.value if facts.revenue else None,
            ocf_hist=facts.ocf.value if facts.ocf else None,
            judgment=_judgment(judg_rows),
            standing_exclusion=_standing_exclusion(n),
            brand_owned=n.brand_owned if n else None,
            p5_status=n.p5_status if n else None, p5_note_ref=n.p5_note_ref if n else None,
        )
        verdict = analyse(inp, pol)

        inputs = dict([
            _fmt("price", price.price), _fmt("52-week low", price.low_52w),
            _fmt("TTM EPS (reported, 4 quarters)", facts.eps_ttm_reported),
            _fmt("TTM EPS (Yahoo)", fundamentals.eps_ttm), _fmt("book value/share",
                                                         fundamentals.book_value_ps),
            _fmt("ROE %", fundamentals.roe_pct), _fmt("P/E", fundamentals.pe_trailing),
            _fmt("P/B", fundamentals.pb_ratio), _fmt("GoI 10Y yield %", gsec),
            _fmt("promoter % (quarterly)", facts.promoter_pct),
            _fmt("total debt", facts.total_debt), _fmt("equity", facts.equity),
            _fmt("net income (annual, newest first)", facts.net_income),
            _fmt("revenue (annual, newest first)", facts.revenue),
            _fmt("operating cash flow", facts.ocf),
        ])
        inputs["household holding"] = f"{held} shares (register holdings)"
        report = OsepReport(
            run_id=run_id, ran_at=now, symbol=symbol,
            name=(n.name if n else company_name or symbol), yf_ticker=ticker,
            in_register=n is not None, old_bucket=n.bucket if n else None,
            verdict=verdict, inputs=inputs, judgments=judg_rows,
            business=facts.business.value if facts.business else None)
        if record_session:
            repo.append_session(
                run_id=run_id, ran_at=now, usecase="UC4_OSEP",
                inputs={"symbol": symbol, **inputs,
                        "judgments": {k: list(v) for k, v in judg_rows.items()}},
                outputs=json.loads(json.dumps({
                    "bucket": verdict.bucket.value, "thesis_type": verdict.thesis_type,
                    "trigger": str(verdict.trigger) if verdict.trigger else None,
                    "trigger_basis": verdict.trigger_basis, "expiry": verdict.expiry,
                    "missing": list(verdict.missing), "p5": verdict.p5_line,
                    "what_would_change": list(verdict.what_would_change)})),
                drops=[{"symbol": symbol, "reason": c.rule, "detail": c.detail}
                       for c in verdict.checks if c.status == Status.FAIL],
                rules_fired=[f"{c.stage}:{c.rule}:{c.status.value}" for c in verdict.checks],
            )
        return report


def record_judgment(db: str | Path, symbol: str, item: str, value: str, source: str,
                    today: str | None = None) -> None:
    if item not in JUDGMENT_ITEMS:
        raise ValueError(f"unknown judgment item {item!r}; one of {sorted(JUDGMENT_ITEMS)}")
    if not source.strip():
        raise ValueError("a judgment needs its source (URL, filing, or 'Praveen <date>')")
    kind = JUDGMENT_ITEMS[item]
    if kind == "int":
        int(value)
    if item == "thesis_type" and value.upper() not in (
            "RE-RATING", "CYCLICAL", "COMPOUNDER", "INCOME", "TURNAROUND"):
        raise ValueError("thesis_type must be RE-RATING/CYCLICAL/COMPOUNDER/INCOME/TURNAROUND")
    with PattazRepo(db) as repo:
        repo.save_judgment(symbol, item, value, source,
                           today or datetime.now(UTC).strftime("%Y-%m-%d"))


def apply_report(db: str | Path, report: OsepReport, reason: str) -> None:
    """Praveen said yes: log old → new and write the verdict to the register."""
    v = report.verdict
    if v.bucket not in (Bucket.GOOD_BUY_NOW, Bucket.GOOD_BUY_LATER, Bucket.HARD_PASS):
        raise ValueError(f"{v.bucket.value} is not a verdict that can be recorded "
                         f"(missing: {', '.join(v.missing) or '-'})")
    if not reason.strip():
        raise ValueError("a verdict change needs its reason (osep v7: first-class change)")
    day = report.ran_at[:10]
    sector = report.judgments.get("sector_class", (None,))[0]
    with PattazRepo(db) as repo:
        repo.log_verdict(report.run_id, report.symbol, day, report.old_bucket,
                         v.bucket.value, v.thesis_type, v.trigger, v.expiry, reason)
        repo.apply_verdict(report.symbol, report.name, report.yf_ticker, sector,
                           v.bucket.value, day, v.expiry, v.thesis_type, v.trigger,
                           v.trigger_basis)


# --------------------------------------------------------------- rederive ---


@dataclass(frozen=True)
class RederiveRow:
    symbol: str
    old: Decimal
    new: Decimal | None
    change_pct: Decimal | None
    basis: str


def rederive_board(db: str | Path, *, today: str | None = None,
                   fundamentals: dict[str, FundamentalsSnapshot] | None = None,
                   reported_eps: dict[str, Decimal] | None = None,
                   gsec_override: Decimal | None = None) -> list[RederiveRow]:
    """Every active BUY trigger recomputed on this session's EPS / book. No writes.
    EPS = the company-reported 4-quarter sum (Screener) when available, else Yahoo."""
    today = today or datetime.now(UTC).strftime("%Y-%m-%d")
    out: list[RederiveRow] = []
    with PattazRepo(db) as repo:
        pol = _policy(repo, _gsec(repo, gsec_override).value)
        names = {n.symbol: n for n in repo.load_names()}
        for t in repo.load_triggers(active_only=True):
            if t.kind != "BUY" or t.symbol not in names:
                continue
            n = names[t.symbol]
            ticker = n.yf_ticker or f"{t.symbol}.NS"
            f = (fundamentals or {}).get(t.symbol)
            if f is None and fundamentals is None:
                try:
                    f = fetch_fundamentals(ticker)
                except ValueError:
                    f = None
            if f is None:
                out.append(RederiveRow(t.symbol, t.level, None, None, "fundamentals missing"))
                continue
            eps = (reported_eps or {}).get(t.symbol)
            if eps is None and fundamentals is None:
                try:
                    cf = fetch_company_facts(ticker, ticker.removesuffix(".NS"))
                    eps = cf.eps_ttm_reported.value if cf.eps_ttm_reported else None
                except (ValueError, OSError):
                    eps = None
            if eps is None and f.eps_ttm is not None:
                eps = f.eps_ttm.value
            inp = OsepInput(symbol=t.symbol, today=today, sector_class=n.sector_class,
                            price=None, eps_ttm=eps,
                            bvps=f.book_value_ps.value if f.book_value_ps else None,
                            roe_pct=f.roe_pct.value if f.roe_pct else None, pe=None, pb=None,
                            promoter_pct_series=None, total_debt=None, equity=None,
                            net_income_hist=None, revenue_hist=None, ocf_hist=None)
            new, basis = derive_trigger(inp, pol)
            chg = ((new - t.level) / t.level * 100).quantize(Decimal("0.1")) if new else None
            out.append(RederiveRow(t.symbol, t.level, new, chg, basis))
    return out


# ----------------------------------------------------------------- output ---

_PLAIN = {Bucket.GOOD_BUY_NOW: "GOOD BUY NOW", Bucket.GOOD_BUY_LATER: "GOOD BUY LATER",
          Bucket.HARD_PASS: "HARD PASS", Bucket.INCOMPLETE: "INCOMPLETE — not enough to decide",
          Bucket.NO_ACTION: "NO ACTION"}


def format_report(r: OsepReport) -> str:
    v = r.verdict
    L = [f"OSEP — {r.name} ({r.symbol}) · {r.ran_at[:10]} · run {r.run_id}",
         f"VERDICT: {_PLAIN[v.bucket]}"
         + (f" · thesis {v.thesis_type}" if v.thesis_type else "")
         + (f" · trigger ₹{v.trigger}" if v.trigger else "")
         + (f" · valid until {v.expiry}" if v.expiry else ""),
         f"  was: {r.old_bucket or 'not in register'}", ""]
    if v.missing:
        L += ["MISSING (research these, then re-run):"] + [f"  - {m}" for m in v.missing] + [""]
    for stage in ("E5", "0", "1", "2", "3"):
        rows = [c for c in v.checks if c.stage == stage]
        if rows:
            L.append(f"Stage {stage}:" if stage != "E5" else "Register:")
            L += [f"  [{c.status.value:7s}] {c.rule}: {c.detail}" for c in rows]
    L.append("")
    if v.trigger_basis:
        L.append(f"Trigger: {v.trigger_basis}")
    if v.p5_line:
        L.append(f"Anand: {v.p5_line}")
    L.append("")
    if v.what_would_change:
        L += ["What would change it:"] + [f"  - {w}" for w in v.what_would_change] + [""]
    L.append("Inputs:")
    L += [f"  {k}: {val}" for k, val in r.inputs.items()]
    if r.judgments:
        L.append("Judgments on record:")
        L += [f"  {k} = {val} ({src}, {asof})" for k, (val, src, asof) in r.judgments.items()]
    if r.business:
        L += ["", f"What it does (for §SC): {r.business[:400]}"]
    return "\n".join(L)


def format_rederive(rows: list[RederiveRow]) -> str:
    L = [f"  {'stock':12s} {'old':>10s} {'new':>10s} {'change':>8s}  basis"]
    for r in sorted(rows, key=lambda x: (x.change_pct is None, x.change_pct or 0)):
        new = f"{r.new:,.2f}" if r.new is not None else "-"
        chg = f"{r.change_pct:+}%" if r.change_pct is not None else "-"
        L.append(f"  {r.symbol:12s} {r.old:>10,.2f} {new:>10s} {chg:>8s}  {r.basis}")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m usecases.osep")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyse")
    a.add_argument("symbol")
    a.add_argument("--ticker")
    a.add_argument("--name")
    a.add_argument("--no-session", action="store_true")
    j = sub.add_parser("judge")
    j.add_argument("symbol")
    j.add_argument("item", choices=sorted(JUDGMENT_ITEMS))
    j.add_argument("value")
    j.add_argument("--source", required=True)
    p = sub.add_parser("apply")
    p.add_argument("symbol")
    p.add_argument("--ticker")
    p.add_argument("--name")
    p.add_argument("--reason", required=True)
    sub.add_parser("rederive")
    args = ap.parse_args(argv)

    if args.cmd == "judge":
        record_judgment(args.db, args.symbol, args.item, args.value, args.source)
        print(f"recorded {args.symbol} {args.item} = {args.value} ({args.source})")
        return 0
    if args.cmd == "rederive":
        print(format_rederive(rederive_board(args.db)))
        return 0
    rep = run_osep(args.db, args.symbol, yf_ticker=args.ticker, company_name=args.name,
                   record_session=not getattr(args, "no_session", False))
    print(format_report(rep))
    if args.cmd == "apply":
        apply_report(args.db, rep, args.reason)
        print(f"\nRECORDED in the register: {rep.verdict.bucket.value} ({args.reason})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

