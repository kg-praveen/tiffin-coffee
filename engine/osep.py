"""engine/osep.py — UC4: the OSEP verdict, stage by stage. PURE (no I/O, no clock).

Spec: spec/osep-stock-analysis.SKILL.md v7 — E-laws, §SC, §G, MoS ladder, Stage 0-3,
P3 thesis type, P5 veto, verdict decay clock, output format.

What the code decides vs what it only records (CLAUDE.md §9: re-underwriting is a
chat-with-Praveen job; the DB records the outcome):
  * computed from data — promoter <26% kill, P4 net-selling flag, solvency, negative
    cumulative profit, loss-scales-with-volume, the sector valuation gate, Stage-1
    watch signals (cash conversion, stagnant sales), the trigger, the expiry, P5, Stage 3.
  * JUDGMENTS supplied from chat research with a cited source — P1 sovereign/directed,
    P2 verifiability, governance, industry durability, investability, Stage-1 score,
    thesis type, promoter-rule exemption, sector class for a new name (E4, §SC).
A missing judgment is UNKNOWN, and UNKNOWN can never become a buy (E3/E9): the verdict
is INCOMPLETE and names exactly what is missing.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

from engine.valuation_gate import (
    ValuationGateInput,
    ValuationGateResult,
    compute_fair_pe,
    compute_justified_pb,
    compute_valuation_gate,
)


class Status(Enum):
    PASS = "PASS"  # noqa: S105
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    EXEMPT = "EXEMPT"
    FLAG = "FLAG"       # a warning that needs a written note, never a kill (P4, watch)


class Bucket(Enum):
    GOOD_BUY_NOW = "GBN"
    GOOD_BUY_LATER = "GBL"
    HARD_PASS = "HARD_PASS"  # noqa: S105
    INCOMPLETE = "INCOMPLETE"   # E9: a required input is missing → NO ACTION
    NO_ACTION = "NO_ACTION"     # standing exclusion / missing market data


THESIS_TYPES = frozenset({"RE-RATING", "CYCLICAL", "COMPOUNDER", "INCOME", "TURNAROUND"})

# §G: sectors with no earnings-multiple gate → no trigger can be derived
NO_TRIGGER_SECTORS = frozenset({"CYCLICAL", "NON_EARNING", "INDEX_ETF"})
LENDER = "LENDER"
BRAND_SECTORS = frozenset({"FMCG"})


@dataclass(frozen=True)
class Judgment:
    """Answers from chat research, each recorded with its source (osep_judgments)."""

    sovereign_directed: bool | None = None     # P1: state can direct price/capital/dividend
    thesis_verifiable: bool | None = None      # P2: the one thesis variable is public
    governance_clean: bool | None = None       # integrity / red flags / going concern
    industry_durable: bool | None = None       # industry-death check (40 years)
    investable: bool | None = None             # durable LISTED company
    stage1_score: int | None = None            # Fisher-6, out of 50
    thesis_type: str | None = None             # P3
    promoter_exempt: bool | None = None        # bank (RBI) or widely-held blue chip


@dataclass(frozen=True)
class OsepPolicy:
    """All from the policy table (E2)."""

    gsec_yield_pct: Decimal
    coe_spread: Decimal
    growth_g: Decimal
    promoter_kill_pct: Decimal
    promoter_net_sell_flag_pct: Decimal
    stage1_gate: int
    decay_gbn_days: int
    decay_gbl_days: int
    decay_hard_pass_days: int
    cap_name_pct: Decimal
    cap_sector_pct: Decimal


@dataclass(frozen=True)
class OsepInput:
    symbol: str
    today: str
    sector_class: str | None
    price: Decimal | None
    eps_ttm: Decimal | None
    bvps: Decimal | None
    roe_pct: Decimal | None
    pe: Decimal | None
    pb: Decimal | None
    promoter_pct_series: Sequence[Decimal] | None     # oldest → newest, quarterly
    total_debt: Decimal | None
    equity: Decimal | None
    net_income_hist: Sequence[Decimal] | None         # newest first, annual
    revenue_hist: Sequence[Decimal] | None            # newest first, annual
    ocf_hist: Sequence[Decimal] | None                # newest first, annual
    judgment: Judgment = field(default_factory=Judgment)
    standing_exclusion: str | None = None             # register: never-add / sold reason
    brand_owned: bool | None = None
    p5_status: str | None = None
    p5_note_ref: str | None = None
    household_weight_pct: Decimal | None = None
    sector_weight_pct: Decimal | None = None


@dataclass(frozen=True)
class Check:
    stage: str
    rule: str
    status: Status
    detail: str


@dataclass(frozen=True)
class OsepVerdict:
    symbol: str
    bucket: Bucket
    thesis_type: str | None
    trigger: Decimal | None
    trigger_basis: str
    expiry: str | None
    gate: ValuationGateResult | None
    checks: tuple[Check, ...]
    missing: tuple[str, ...]
    what_would_change: tuple[str, ...]
    p5_line: str

    def by_status(self, status: Status) -> list[Check]:
        return [c for c in self.checks if c.status == status]


_CENT = Decimal("0.01")


# ----------------------------------------------------------------- stage 0 ---


def _judged(stage: str, rule: str, value: bool | None, good_when: bool,
            pass_txt: str, fail_txt: str) -> Check:
    if value is None:
        return Check(stage, rule, Status.UNKNOWN, "not yet researched — record a judgment")
    ok = value == good_when
    return Check(stage, rule, Status.PASS if ok else Status.FAIL, pass_txt if ok else fail_txt)


def stage0_checks(inp: OsepInput, pol: OsepPolicy) -> list[Check]:
    """Stage 0 kill switches (any FAIL = HARD PASS). P4 is a FLAG, never a kill."""
    j = inp.judgment
    out = [
        _judged("0", "P1 sovereign control", j.sovereign_directed, False,
                "state cannot direct price, capital or dividend (REGULATED≠DIRECTED)",
                "state can direct price / capital / dividend → P1 kill"),
        _judged("0", "P2 verifiable thesis", j.thesis_verifiable, True,
                "the thesis variable is in public disclosure",
                "thesis variable cannot be verified publicly → P2 kill"),
        _judged("0", "integrity / governance", j.governance_clean, True,
                "no red flag found", "governance red flag → kill"),
        _judged("0", "industry death (40 years)", j.industry_durable, True,
                "industry likely to exist in 40 years", "dying industry → slow pass"),
        _judged("0", "investability", j.investable, True,
                "durable listed company", "no durable listed vehicle"),
    ]
    out.append(_promoter_check(inp, pol))
    out.append(_promoter_selling(inp, pol))
    out.append(_solvency(inp))
    out.append(_cumulative_profit(inp))
    out.append(_loss_scales(inp))
    return out


def _promoter_check(inp: OsepInput, pol: OsepPolicy) -> Check:
    if inp.judgment.promoter_exempt:
        return Check("0", "promoter ≥ 26%", Status.EXEMPT,
                     "exempt: bank (RBI-mandated) or widely-held blue chip (judgment)")
    s = inp.promoter_pct_series
    if not s:
        return Check("0", "promoter ≥ 26%", Status.UNKNOWN, "promoter holding not fetched")
    last = s[-1]
    if last < pol.promoter_kill_pct:
        return Check("0", "promoter ≥ 26%", Status.FAIL,
                     f"promoter {last}% < {pol.promoter_kill_pct}% → kill")
    return Check("0", "promoter ≥ 26%", Status.PASS, f"promoter {last}%")


def _promoter_selling(inp: OsepInput, pol: OsepPolicy) -> Check:
    """P4: promoter net seller of > flag % of equity over trailing 12m → FLAG."""
    s = inp.promoter_pct_series
    if not s or len(s) < 5:
        return Check("0", "P4 promoter net selling", Status.UNKNOWN,
                     "fewer than 5 quarters of promoter data")
    drop = s[-5] - s[-1]
    if drop > pol.promoter_net_sell_flag_pct:
        return Check("0", "P4 promoter net selling", Status.FLAG,
                     f"promoter down {drop:.2f} pts in 12m — written investigation before "
                     f"any plate (PE/VC exits exempt)")
    return Check("0", "P4 promoter net selling", Status.PASS, f"12m change {-drop:+.2f} pts")


def _solvency(inp: OsepInput) -> Check:
    """(Equity+Reserves) < 2x institutional debt → kill. Lenders exempt. Debt excludes
    leases (tools/company_data.py) but cannot split out working-capital lines — a FAIL
    says so, and a regulated utility's tariff-recovered debt is an open E6 (§14 0b)."""
    if inp.sector_class == LENDER:
        return Check("0", "solvency", Status.EXEMPT, "lenders exempt (debt is the product)")
    if inp.equity is None or inp.total_debt is None:
        return Check("0", "solvency", Status.UNKNOWN, "equity or debt not fetched")
    if inp.equity < 2 * inp.total_debt:
        return Check("0", "solvency", Status.FAIL,
                     f"equity {inp.equity:,.0f} < 2 x debt {inp.total_debt:,.0f} "
                     f"(debt ex-leases; working-capital lines not separable — check before acting)")
    return Check("0", "solvency", Status.PASS,
                 f"equity {inp.equity:,.0f} ≥ 2 x debt {inp.total_debt:,.0f}")


def _cumulative_profit(inp: OsepInput) -> Check:
    h = inp.net_income_hist
    if not h:
        return Check("0", "cumulative profit", Status.UNKNOWN, "profit history not fetched")
    total = sum(h, Decimal(0))
    if total < 0:
        return Check("0", "cumulative profit", Status.FAIL,
                     f"{len(h)}-year cumulative profit {total:,.0f} < 0")
    return Check("0", "cumulative profit", Status.PASS, f"{len(h)}-year total {total:,.0f}")


def _loss_scales(inp: OsepInput) -> Check:
    ni, rev = inp.net_income_hist, inp.revenue_hist
    if not ni or not rev or len(ni) < 2 or len(rev) < 2:
        return Check("0", "loss scales with volume", Status.UNKNOWN, "history too short")
    if ni[0] < 0 and ni[1] < 0 and ni[0] < ni[1] and rev[0] > rev[1]:
        return Check("0", "loss scales with volume", Status.FAIL,
                     "losses grew while revenue grew — no operating leverage")
    return Check("0", "loss scales with volume", Status.PASS, "not a growing-loss business")


# ----------------------------------------------------------------- stage 1 ---


def stage1_checks(inp: OsepInput, pol: OsepPolicy) -> list[Check]:
    out: list[Check] = []
    score = inp.judgment.stage1_score
    if score is None:
        out.append(Check("1", "quality score ≥ gate", Status.UNKNOWN,
                         "Fisher-6 score not yet recorded"))
    elif score < pol.stage1_gate:
        out.append(Check("1", "quality score ≥ gate", Status.FAIL,
                         f"{score}/50 < {pol.stage1_gate}"))
    else:
        out.append(Check("1", "quality score ≥ gate", Status.PASS, f"{score}/50"))
    if inp.sector_class in BRAND_SECTORS:
        if inp.brand_owned is None:
            out.append(Check("1", "brand ownership (FMCG)", Status.UNKNOWN,
                             "brand ownership not recorded"))
        else:
            out.append(Check("1", "brand ownership (FMCG)",
                             Status.PASS if inp.brand_owned else Status.FAIL,
                             "owns its brands" if inp.brand_owned
                             else "does not own its brand → hard gate"))
    ni, ocf, rev = inp.net_income_hist, inp.ocf_hist, inp.revenue_hist
    if ni and ocf and len(ni) >= 2 and len(ocf) >= 2 and ni[0] > ni[1] and ocf[0] < ocf[1]:
        out.append(Check("1", "cash conversion (watch)", Status.FLAG,
                         "profit up but operating cash flow down"))
    if rev and len(rev) >= 4 and rev[0] <= rev[3]:
        out.append(Check("1", "sales growth (watch)", Status.FLAG,
                         "sales no higher than three years ago"))
    return out


# ------------------------------------------------------- stage 2 + trigger ---


def valuation_gate(inp: OsepInput, pol: OsepPolicy) -> ValuationGateResult:
    """§G sector gate — the one definition lives in engine/valuation_gate.py (E7)."""
    return compute_valuation_gate(ValuationGateInput(
        symbol=inp.symbol, sector_class=inp.sector_class, pe_trailing=inp.pe,
        pb_ratio=inp.pb, roe_pct=inp.roe_pct, gsec_yield_pct=pol.gsec_yield_pct,
        cost_of_equity_spread=pol.coe_spread, growth_g_pct=pol.growth_g))


def derive_trigger(inp: OsepInput, pol: OsepPolicy) -> tuple[Decimal | None, str]:
    """The buy level from this session's data: fair P/E (1 ÷ GoI) x TTM EPS, or for a
    lender justified P/B x book value per share. No trigger where §G forbids one."""
    if inp.sector_class in NO_TRIGGER_SECTORS:
        return None, f"{inp.sector_class}: no earnings-multiple gate (§G) — no trigger"
    if pol.gsec_yield_pct <= 0:
        return None, "GoI yield unavailable (E9)"
    if inp.sector_class == LENDER:
        r = pol.gsec_yield_pct + pol.coe_spread
        jpb = compute_justified_pb(inp.roe_pct, r, pol.growth_g)
        if jpb is None or inp.bvps is None or inp.bvps <= 0:
            return None, "justified P/B or book value missing"
        return ((jpb * inp.bvps).quantize(_CENT, rounding=ROUND_HALF_UP),
                f"justified P/B {jpb}x x book/share {inp.bvps}")
    if inp.eps_ttm is None or inp.eps_ttm <= 0:
        return None, "no positive TTM EPS — earnings gate cannot price it"
    fair = compute_fair_pe(pol.gsec_yield_pct)
    return ((fair * inp.eps_ttm).quantize(_CENT, rounding=ROUND_HALF_UP),
            f"fair P/E {fair}x (1 ÷ {pol.gsec_yield_pct}%) x TTM EPS {inp.eps_ttm}")


# ----------------------------------------------------------- P5 + stage 3 ---


def p5_line(inp: OsepInput, osep_pass: bool) -> tuple[str, bool]:
    """(text, blocks_plate). Veto only, never a vote (§P5)."""
    s = inp.p5_status
    if s == "AVOID" and inp.p5_note_ref is None:
        return ("Anand universe AVOID — a written disagreement note is required before "
                "any plate"), True
    if s == "BUY" and not osep_pass:
        return "Anand universe BUY but OSEP passes on nothing — NO ACTION (anti-tip wall)", False
    if s in (None, "NOT_IN_UNIVERSE"):
        return "not in Anand's universe — no veto", False
    return f"Anand universe {s}" + (f" (note: {inp.p5_note_ref})" if inp.p5_note_ref else ""), False


def stage3_checks(inp: OsepInput, pol: OsepPolicy) -> list[Check]:
    out: list[Check] = []
    w, sw = inp.household_weight_pct, inp.sector_weight_pct
    if w is not None:
        out.append(Check("3", "≤ 20% per stock", Status.FAIL if w >= pol.cap_name_pct
                         else Status.PASS, f"household weight {w}%"))
    if sw is not None:
        out.append(Check("3", "≤ 40% per sector", Status.FAIL if sw >= pol.cap_sector_pct
                         else Status.PASS, f"sector weight {sw}%"))
    return out


# ------------------------------------------------------------------ verdict ---


def _expiry(today: str, days: int) -> str:
    return (date.fromisoformat(today) + timedelta(days=days)).isoformat()


def analyse(inp: OsepInput, pol: OsepPolicy) -> OsepVerdict:
    """E5 precedence: exclusion → freshness → Stage 0 → Stage 1 → sector gate/Stage 2 →
    P5 → (sizing is tiffin's). A lower stage only tightens."""
    checks: list[Check] = []
    missing: list[str] = []
    wwc: list[str] = []

    def done(bucket: Bucket, trig: Decimal | None = None, basis: str = "",
             gate: ValuationGateResult | None = None, p5: str = "") -> OsepVerdict:
        days = {Bucket.GOOD_BUY_NOW: pol.decay_gbn_days,
                Bucket.GOOD_BUY_LATER: pol.decay_gbl_days,
                Bucket.HARD_PASS: pol.decay_hard_pass_days}.get(bucket)
        return OsepVerdict(inp.symbol, bucket, inp.judgment.thesis_type, trig, basis,
                           _expiry(inp.today, days) if days else None, gate, tuple(checks),
                           tuple(missing), tuple(wwc), p5)

    if inp.standing_exclusion:
        checks.append(Check("E5", "standing exclusion", Status.FAIL, inp.standing_exclusion))
        wwc.append("Praveen changes the register in writing")
        return done(Bucket.NO_ACTION)
    if inp.price is None or inp.price <= 0:
        missing.append("live price")
        return done(Bucket.NO_ACTION)
    if inp.sector_class is None:
        missing.append("sector class (§SC: classify from the business description, cite it)")

    s0 = stage0_checks(inp, pol)
    checks += s0
    if any(c.status == Status.FAIL for c in s0):
        wwc.append("the failing kill switch clears (re-check at expiry — they do clear)")
        return done(Bucket.HARD_PASS)
    s1 = stage1_checks(inp, pol)
    checks += s1
    if any(c.status == Status.FAIL for c in s1):
        wwc.append("quality re-scored above the gate / brand ownership changes")
        return done(Bucket.HARD_PASS)

    missing += [f"{c.rule} ({c.stage})" for c in s0 + s1 if c.status == Status.UNKNOWN]
    if inp.judgment.thesis_type not in THESIS_TYPES:
        missing.append("thesis type (P3: RE-RATING / CYCLICAL / COMPOUNDER / INCOME / "
                       "TURNAROUND)")

    gate = valuation_gate(inp, pol) if inp.sector_class else None
    trig, basis = derive_trigger(inp, pol) if inp.sector_class else (None, "no sector class")
    checks.append(Check("2", "sector valuation gate", Status.UNKNOWN if gate is None else
                        Status.PASS if gate.passed else Status.FAIL,
                        gate.detail if gate else "needs sector class"))
    checks += stage3_checks(inp, pol)
    p5, p5_blocks = p5_line(inp, bool(gate and gate.passed))

    if missing:
        wwc.append("research and record: " + "; ".join(missing))
        return done(Bucket.INCOMPLETE, trig, basis, gate, p5)

    now = gate is not None and gate.passed and trig is not None and inp.price <= trig
    if trig is None:
        wwc.append(basis)
    elif not now:
        wwc.append(f"price ≤ {trig} ({basis})")
    if p5_blocks:
        wwc.append("write the P5 disagreement note")
    return done(Bucket.GOOD_BUY_NOW if now else Bucket.GOOD_BUY_LATER, trig, basis, gate, p5)
