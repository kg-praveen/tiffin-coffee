"""engine/plate.py — pure functions for UC2 (tiffin-coffee buy plate).

Spec: tiffin-coffee v6 formula, osep v7 ENGINE CONTRACT E1-E9.
All inputs are typed dataclasses + policy dict.
No I/O, no network, no datetime.now(), no DB.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

# ------------------------------------------------------------------ enums ---


class Mode(Enum):
    """Hunger-index mode. Spec: tiffin-coffee v6 §H table."""

    FASTING = "FASTING"
    COFFEE = "COFFEE"
    TIFFIN = "TIFFIN"
    FULL_MEALS = "FULL_MEALS"
    HOCKEY = "HOCKEY"


class LowBand(Enum):
    """Distance-from-52wk-low band. Spec: tiffin-coffee v5 §L table."""

    AT_THE_LOW = "AT_THE_LOW"
    ON_THE_LOW = "ON_THE_LOW"
    NEAR_THE_LOW = "NEAR_THE_LOW"
    MID_RANGE = "MID_RANGE"
    OFF_THE_LOW = "OFF_THE_LOW"


class PriorityTier(Enum):
    """Portfolio priority tier. Spec: tiffin-coffee v6 §P table."""

    BLOCKED = "BLOCKED"
    MAINTENANCE = "MAINTENANCE"
    BUILDING = "BUILDING"
    MISSING = "MISSING"


class PlateDropReason(Enum):
    """Why a name was excluded from the plate. Spec E8: every drop carries one."""

    NO_TRIGGER = "no armable trigger and not at the low (spec: no trigger cannot plate)"
    NOT_ELIGIBLE = "H below eligibility and L above the low band"
    FIRST_BITE_FAILED = "at the low but first-bite conditions (a)-(d) not all met"
    HOLDINGS_STALE = "book says OWNED but holdings has no row (CLAUDE.md §3)"
    NO_ADD_HOLD_ONLY = "hold-only / museum name — builds blocked, first-bite allowed"
    E6_CAPS_OFF_CONFLICT = "first-bite blocked only by cell/P cap — §12b caps-off unresolved"
    SCORE_ZERO = "score is zero after HxLxP"
    STATUS_BLOCKED = "name status blocks adds"
    EXIT_DECIDED = "on the sell list (overlay #7)"
    NEVER_ADD = "standing never-add (overlay #8)"
    SOVEREIGN = "P1 sovereign — state-owned/directed (overlay #2)"
    PEAK_CYCLE = "peak-cycle cyclical (overlay #3)"
    PSU_CAP = "PSU/regulated cap breached (overlay #4)"
    CELL_FULL = "cell is full or max active adds reached (overlay #5)"
    P5_VETO = "P5 universe AVOID without disagreement note (overlay #6)"
    PROBE_OPEN = "live quality/governance probe (overlay #9)"
    FRAUD_TAIL = "fraud/legacy tail (overlay #10)"
    DECAY_EXPIRED = "verdict expired — re-underwrite before plating"
    NO_PRICE = "price not available"
    PRICE_FETCH_FAILED = "price fetch failed this run"
    P_BLOCKED = "P-tier is BLOCKED (at cap/target)"
    NO_TICKER = "no yf_ticker — cannot fetch price"


# --------------------------------------------------------------- inputs ---


@dataclass(frozen=True)
class CellInfo:
    """Cell occupancy state for overlay #5."""

    is_full: bool
    active_add_count: int
    max_adds: int
    active_adds: frozenset[str] = frozenset()


@dataclass(frozen=True)
class NameInput:
    """All data the plate engine needs for one name. Populated by the usecase."""

    symbol: str
    name: str
    price: Decimal
    low_52w: Decimal
    trigger_level: Decimal | None
    sector_class: str | None
    status: str
    bucket: str | None
    cell: str | None
    flag_sovereign: bool
    flag_psu: bool
    flag_cyclical: bool
    flag_probe_open: bool
    flag_fraud_tail: bool
    flag_exit_decided: bool
    p5_status: str | None
    p5_note_ref: str | None
    decay_expiry: str | None
    qty_held_household: int
    current_weight_pct: Decimal | None
    valuation_gate_passed: bool
    valuation_gate_detail: str = ""
    p_mult_book: Decimal | None = None
    flag_no_add: bool = False
    owned_per_book: bool = False


@dataclass(frozen=True)
class PlateConfig:
    """Session-level configuration for the plate engine."""

    session_amount: Decimal
    today: str
    psu_weight_pct: Decimal
    cells: dict[str, CellInfo]
    bees_price: Decimal | None
    eligible_h_min: Decimal = Decimal("0.85")
    eligible_l_max: Decimal = Decimal(5)
    qty_clamp_min: int = 1
    qty_clamp_max: int = 10
    first_bite_qty_max: int = 5
    first_bite_h_mult_floor: Decimal = Decimal("0.25")
    first_bite_l_max: Decimal = Decimal(2)
    cap_psu_regulated_pct: Decimal = Decimal(25)


# -------------------------------------------------------------- outputs ---


@dataclass(frozen=True)
class PlateEntry:
    """One name on the final plate."""

    symbol: str
    name: str
    price: Decimal
    qty: int
    amount: Decimal
    mode: Mode
    h: Decimal | None
    l_pct: Decimal
    low_band: LowBand
    h_mult: Decimal
    l_mult: Decimal
    p_mult: Decimal
    p_tier: PriorityTier
    score: Decimal
    tilt: Decimal
    budget: Decimal
    is_first_bite: bool


@dataclass(frozen=True)
class PlateDrop:
    """A name that was considered but excluded."""

    symbol: str
    name: str
    reason: PlateDropReason
    detail: str
    h: Decimal | None = None
    l_pct: Decimal | None = None
    what_would_change: str = ""


@dataclass(frozen=True)
class PlateResult:
    """Complete plate output. Spec: E8 output law."""

    entries: list[PlateEntry]
    drops: list[PlateDrop]
    bees_sweep_qty: int
    bees_sweep_amount: Decimal
    total_stock_amount: Decimal
    total_with_sweep: Decimal
    session_amount: Decimal
    residual: Decimal
    rules_fired: list[str] = field(default_factory=list)


# ----------------------------------------- classification functions ---


_H_BANDS: list[tuple[Decimal, Decimal, Mode, Decimal]] = [
    (Decimal("1.15"), Decimal(999), Mode.HOCKEY, Decimal("3.0")),
    (Decimal("1.05"), Decimal("1.15"), Mode.FULL_MEALS, Decimal("3.0")),
    (Decimal("0.95"), Decimal("1.05"), Mode.TIFFIN, Decimal("1.0")),
    (Decimal("0.85"), Decimal("0.95"), Mode.COFFEE, Decimal("0.5")),
]


def classify_mode(h: Decimal) -> tuple[Mode, Decimal]:
    """Spec: tiffin-coffee v6 §H table. Returns (mode, h_mult)."""
    for lo, _hi, mode, mult in _H_BANDS:
        if h >= lo:
            return mode, mult
    return Mode.FASTING, Decimal(0)


_L_BANDS: list[tuple[Decimal, Decimal, LowBand, Decimal]] = [
    (Decimal(0), Decimal(2), LowBand.AT_THE_LOW, Decimal("1.5")),
    (Decimal(2), Decimal(5), LowBand.ON_THE_LOW, Decimal("1.25")),
    (Decimal(5), Decimal(15), LowBand.NEAR_THE_LOW, Decimal("1.0")),
    (Decimal(15), Decimal(30), LowBand.MID_RANGE, Decimal("0.5")),
]


def classify_low_band(l_pct: Decimal) -> tuple[LowBand, Decimal]:
    """Spec: tiffin-coffee v5 §L table. Returns (band, l_mult)."""
    for lo, hi, band, mult in _L_BANDS:
        if l_pct >= lo and l_pct < hi:
            return band, mult
    return LowBand.OFF_THE_LOW, Decimal("0.25")


_BUCKET_MIDPOINTS: dict[str, Decimal] = {
    "core": Decimal("8.5"),
    "standard": Decimal(5),
    "satellite": Decimal("2.5"),
    "spec": Decimal("0.5"),
}


def classify_priority(
    current_weight_pct: Decimal | None,
    bucket: str | None,
) -> tuple[PriorityTier, Decimal]:
    """Spec: tiffin-coffee v6 §P table. Returns (tier, p_mult).

    If current_weight_pct is None (no holdings data), returns MISSING.
    """
    if current_weight_pct is None:
        return PriorityTier.MISSING, Decimal("1.5")

    midpoint = _BUCKET_MIDPOINTS.get(bucket or "", Decimal(5))

    if midpoint == 0:
        fill_pct = Decimal(100) if current_weight_pct > 0 else Decimal(0)
    else:
        fill_pct = (current_weight_pct / midpoint) * 100

    if fill_pct >= Decimal(100):
        return PriorityTier.BLOCKED, Decimal(0)
    if fill_pct >= Decimal(70):
        return PriorityTier.MAINTENANCE, Decimal("0.5")
    if fill_pct >= Decimal(10):
        return PriorityTier.BUILDING, Decimal("1.0")
    return PriorityTier.MISSING, Decimal("1.5")


def priority_from_book(p_mult_book: Decimal) -> tuple[PriorityTier, Decimal]:
    """P-tier from the pattaz-book §4 roster value (interim until holdings sync).

    Spec: tiffin-coffee v6 §P table — the roster carries the multiplier directly.
    """
    if p_mult_book <= 0:
        return PriorityTier.BLOCKED, Decimal(0)
    if p_mult_book < Decimal("1.0"):
        return PriorityTier.MAINTENANCE, p_mult_book
    if p_mult_book < Decimal("1.5"):
        return PriorityTier.BUILDING, p_mult_book
    return PriorityTier.MISSING, p_mult_book


def compute_h(trigger_level: Decimal, price: Decimal) -> Decimal:
    """H = trigger / price. Spec: tiffin-coffee v6 §H."""
    if price == 0:
        return Decimal(0)
    return (trigger_level / price).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def compute_l(price: Decimal, low_52w: Decimal) -> Decimal:
    """L = (price - 52wk low) / 52wk low x 100. Spec: tiffin-coffee v5 §L."""
    if low_52w == 0:
        return Decimal(999)
    return (
        ((price - low_52w) / low_52w * 100)
        .quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )


# ------------------------------------------------------------ overlays ---


def check_quality_overlays(
    n: NameInput,
    config: PlateConfig,
) -> PlateDropReason | None:
    """Quality overlays #1-4, #6-#10 + decay. Spec: tiffin-coffee v5 §overlays.

    These are never waived — "a portfolio-construction waiver, not a quality
    waiver" (tiffin v5 §caps-off). Returns the first failing reason or None.
    """
    if n.flag_probe_open:
        return PlateDropReason.PROBE_OPEN

    if n.flag_sovereign:
        return PlateDropReason.SOVEREIGN

    if n.flag_cyclical:
        return PlateDropReason.PEAK_CYCLE

    if n.flag_psu and config.psu_weight_pct >= config.cap_psu_regulated_pct:
        return PlateDropReason.PSU_CAP

    if n.p5_status == "AVOID" and n.p5_note_ref is None:
        return PlateDropReason.P5_VETO

    if n.flag_exit_decided:
        return PlateDropReason.EXIT_DECIDED

    if n.status == "NEVER_ADD":
        return PlateDropReason.NEVER_ADD

    if n.flag_fraud_tail:
        return PlateDropReason.FRAUD_TAIL

    if n.decay_expiry is not None and n.decay_expiry < config.today:
        return PlateDropReason.DECAY_EXPIRED

    return None


def check_cell_overlay(
    n: NameInput,
    config: PlateConfig,
) -> PlateDropReason | None:
    """Overlay #5: ≤2 active adds per cell. Spec: pattaz-book §5.

    The cap limits how many names hold ADD seats; a name that already holds a
    seat (listed in active_adds) is never blocked by its own seat.
    """
    if not n.cell or n.cell not in config.cells:
        return None
    cell = config.cells[n.cell]
    if n.symbol in cell.active_adds:
        return None
    if cell.is_full or cell.active_add_count >= cell.max_adds:
        return PlateDropReason.CELL_FULL
    return None


def check_overlays(
    n: NameInput,
    config: PlateConfig,
) -> PlateDropReason | None:
    """All 10 overlays (quality then cell). Spec: tiffin-coffee v5 §overlays."""
    return check_quality_overlays(n, config) or check_cell_overlay(n, config)


_OVERLAY_WHAT_WOULD_CHANGE: dict[PlateDropReason, str] = {
    PlateDropReason.PROBE_OPEN: "probe resolved and flag cleared in the register",
    PlateDropReason.SOVEREIGN: "never while state-directed (P1)",
    PlateDropReason.PEAK_CYCLE: "through-cycle test (osep G-CYCLICAL) or flag review",
    PlateDropReason.PSU_CAP: "PSU/regulated weight back under the cap",
    PlateDropReason.CELL_FULL: "a seat in the cell (≤2 active adds, pattaz-book §5)",
    PlateDropReason.P5_VETO: "a written disagreement note logged (overlay #6)",
    PlateDropReason.EXIT_DECIDED: "never — buy and sell never share a session",
    PlateDropReason.NEVER_ADD: "register change (pattaz-book §8)",
    PlateDropReason.FRAUD_TAIL: "legacy tail cleared in the register",
    PlateDropReason.DECAY_EXPIRED: "re-underwrite (GBN 30d / GBL 90d decay)",
}


# ----------------------------------------------------- first-bite check ---


def check_first_bite(
    l_pct: Decimal,
    overlays_passed: bool,
    valuation_gate_passed: bool,
    is_owned: bool,
    sector_class: str | None,
    l_max: Decimal = Decimal(2),
) -> bool:
    """Spec: tiffin-coffee v5 §first-bite-at-the-low. All four conditions required.

    (a) L ≤ 2%
    (b) every exclusion overlay passes
    (c) sector-appropriate valuation gate passes (caller pre-computes)
    (d) already owned
    Non-earning sectors (gold proxies) are never eligible.
    """
    if sector_class == "NON_EARNING":
        return False
    return (
        l_pct <= l_max
        and overlays_passed
        and valuation_gate_passed
        and is_owned
    )


def first_bite_failures(
    n: NameInput,
    l_pct: Decimal,
    is_owned: bool,
    config: PlateConfig,
) -> list[str]:
    """Name each failing first-bite condition (E8: the drop must say why)."""
    failures: list[str] = []
    if n.sector_class == "NON_EARNING":
        failures.append("NON_EARNING: thermostat is the only gate")
    if l_pct > config.first_bite_l_max:
        failures.append(f"(a) L={l_pct}% > {config.first_bite_l_max}%")
    if not n.valuation_gate_passed:
        failures.append(f"(c) gate: {n.valuation_gate_detail or 'FAIL'}")
    if not is_owned:
        failures.append("(d) not owned — a first bite averages, never opens")
    return failures


# ---------------------------------------------------- scoring & sizing ---


def compute_score(h_mult: Decimal, l_mult: Decimal, p_mult: Decimal) -> Decimal:
    """SCORE = H-mult x L-mult x P-mult. Spec: tiffin-coffee v5 §formula step 2."""
    return (h_mult * l_mult * p_mult).quantize(
        Decimal("0.001"), rounding=ROUND_HALF_UP
    )


def assign_tilts(scores: list[Decimal]) -> list[Decimal]:
    """Spec: tiffin-coffee v5 §formula step 4.

    TILT = 1.25 top-third by SCORE, 1.0 middle-third, 0.75 bottom-third.
    """
    n = len(scores)
    if n == 0:
        return []

    indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    third = max(n // 3, 1)

    tilts = [Decimal("1.0")] * n
    for rank, (orig_idx, _score) in enumerate(indexed):
        if rank < third:
            tilts[orig_idx] = Decimal("1.25")
        elif rank >= n - third:
            tilts[orig_idx] = Decimal("0.75")
    return tilts


def compute_qty(
    budget: Decimal,
    price: Decimal,
    clamp_min: int,
    clamp_max: int,
) -> int:
    """QTY = clamp(round(budget/price), min, max). Spec: v5 §formula step 5."""
    if price <= 0:
        return 0
    raw = (budget / price).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return max(clamp_min, min(clamp_max, int(raw)))


def compute_bees_sweep(
    residual: Decimal,
    bees_price: Decimal | None,
) -> tuple[int, Decimal]:
    """Spec: tiffin-coffee v6 §BeES floor — sweep residual into NIFTYBEES."""
    if bees_price is None or bees_price <= 0:
        return 0, Decimal(0)
    qty = int(residual / bees_price)
    return qty, (bees_price * qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# --------------------------------------------------------- main builder ---


def build_plate(
    names: list[NameInput],
    config: PlateConfig,
) -> PlateResult:
    """Build the full buy plate. Spec: tiffin-coffee v6 §procedure steps 4-7.

    Scans ALL names, computes H/L/P, applies overlays, scores, sizes, sweeps.
    """
    drops: list[PlateDrop] = []
    _ScoredRow = tuple[
        NameInput, Decimal | None, Mode, LowBand,
        Decimal, Decimal, Decimal, Decimal, PriorityTier, Decimal, bool,
    ]
    scored: list[_ScoredRow] = []
    rules_fired: list[str] = []

    def _drop(n: NameInput, reason: PlateDropReason, detail: str, wwc: str,
              h: Decimal | None = None, l_pct: Decimal | None = None) -> None:
        drops.append(PlateDrop(n.symbol, n.name, reason, detail, h=h, l_pct=l_pct,
                               what_would_change=wwc))

    for n in names:
        # --- pre-checks ---
        if n.status in ("SOLD", "NEVER_ADD"):
            _drop(n, PlateDropReason.STATUS_BLOCKED, f"status={n.status}",
                  "register status change (pattaz-book §8)")
            continue

        if n.flag_exit_decided:
            _drop(n, PlateDropReason.EXIT_DECIDED, "flag_exit_decided=1",
                  _OVERLAY_WHAT_WOULD_CHANGE[PlateDropReason.EXIT_DECIDED])
            continue

        # --- compute L ---
        l_pct = compute_l(n.price, n.low_52w)
        low_band, l_mult = classify_low_band(l_pct)

        # --- compute H ---
        h: Decimal | None = None
        mode = Mode.FASTING
        h_mult = Decimal(0)
        if n.trigger_level is not None and n.trigger_level > 0:
            h = compute_h(n.trigger_level, n.price)
            mode, h_mult = classify_mode(h)

        # --- eligibility check (step 1) ---
        eligible_via_h = h is not None and h >= config.eligible_h_min
        eligible_via_l = l_pct <= config.eligible_l_max

        if not eligible_via_h and not eligible_via_l:
            if h is None or n.trigger_level is None:
                _drop(n, PlateDropReason.NO_TRIGGER,
                      f"no armable trigger; L={l_pct}% (52wk low {n.low_52w})",
                      f"underwrite and log a trigger, or price within "
                      f"{config.eligible_l_max}% of the 52wk low",
                      h=h, l_pct=l_pct)
            else:
                price_needed = (n.trigger_level / config.eligible_h_min).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP,
                )
                _drop(n, PlateDropReason.NOT_ELIGIBLE,
                      f"H={h} < {config.eligible_h_min}, L={l_pct}% > {config.eligible_l_max}%",
                      f"price ≤ {price_needed} (H ≥ {config.eligible_h_min}) "
                      f"or L ≤ {config.eligible_l_max}%",
                      h=h, l_pct=l_pct)
            continue

        # --- holdings integrity (CLAUDE.md §3: fail closed, never guess P) ---
        if n.owned_per_book and n.qty_held_household == 0 and n.p_mult_book is None:
            _drop(n, PlateDropReason.HOLDINGS_STALE,
                  "book says OWNED/HOLD but holdings has no row — P unknown",
                  "sync holdings (UC2.1) or set p_mult_book from pattaz-book §4",
                  h=h, l_pct=l_pct)
            rules_fired.append(f"HOLDINGS_STALE:{n.symbol}")
            continue

        # --- quality overlays (never waived) ---
        quality_drop = check_quality_overlays(n, config)
        if quality_drop is not None:
            _drop(n, quality_drop, f"H={h}, L={l_pct}%",
                  _OVERLAY_WHAT_WOULD_CHANGE[quality_drop], h=h, l_pct=l_pct)
            rules_fired.append(f"overlay:{quality_drop.name}:{n.symbol}")
            continue

        # --- portfolio-construction inputs (cell seat, P-tier) ---
        cell_drop = check_cell_overlay(n, config)
        is_owned = n.qty_held_household > 0 or (n.owned_per_book and n.p_mult_book is not None)
        if n.p_mult_book is not None:
            p_tier, p_mult = priority_from_book(n.p_mult_book)
        else:
            p_tier, p_mult = classify_priority(n.current_weight_pct, n.bucket)

        is_first_bite = False
        if not eligible_via_h:
            # --- first-bite path (the one exception to FASTING) ---
            failures = first_bite_failures(n, l_pct, is_owned, config)
            passes = check_first_bite(
                l_pct, True, n.valuation_gate_passed, is_owned, n.sector_class,
                l_max=config.first_bite_l_max,
            )
            if failures or not passes:
                _drop(n, PlateDropReason.FIRST_BITE_FAILED, "; ".join(failures),
                      f"all of: L ≤ {config.first_bite_l_max}% · owned · sector gate pass",
                      h=h, l_pct=l_pct)
                continue
            if cell_drop is not None or p_tier == PriorityTier.BLOCKED:
                blocker = "cell cap" if cell_drop is not None else "P=0 (at/over target)"
                _drop(n, PlateDropReason.E6_CAPS_OFF_CONFLICT,
                      f"first-bite passes quality gates but is blocked by {blocker}; "
                      f"caps-off waiver is UNRESOLVED (pattaz-book §12b)",
                      "Praveen rules on §12b caps-off for this name — engine takes no action",
                      h=h, l_pct=l_pct)
                rules_fired.append(f"E6:CAPS_OFF:{n.symbol}")
                continue
            is_first_bite = True
            h_mult = max(h_mult, config.first_bite_h_mult_floor)
            rules_fired.append(f"first_bite:{n.symbol}")
        else:
            # --- build path (eligible via H) ---
            build_blocker = (
                "cell cap" if cell_drop is not None
                else "hold-only/museum" if n.flag_no_add
                else None
            )
            if build_blocker is not None and check_first_bite(
                l_pct, True, n.valuation_gate_passed, is_owned, n.sector_class,
                l_max=config.first_bite_l_max,
            ):
                # Wipro 10-Sep precedent: at the low, owned, gate passes, build blocked
                # only by portfolio construction → the §12b caps-off question.
                _drop(n, PlateDropReason.E6_CAPS_OFF_CONFLICT,
                      f"H={h}, L={l_pct}%, owned, gate PASS — build blocked by {build_blocker}; "
                      f"a first bite here needs the §12b caps-off waiver (UNRESOLVED)",
                      "Praveen rules on §12b caps-off for this name — engine takes no action",
                      h=h, l_pct=l_pct)
                rules_fired.append(f"E6:CAPS_OFF:{n.symbol}")
                continue
            if cell_drop is not None:
                _drop(n, cell_drop, f"H={h}, L={l_pct}% — not a seat-holder in cell {n.cell}",
                      _OVERLAY_WHAT_WOULD_CHANGE[cell_drop], h=h, l_pct=l_pct)
                rules_fired.append(f"overlay:{cell_drop.name}:{n.symbol}")
                continue
            if n.flag_no_add:
                _drop(n, PlateDropReason.NO_ADD_HOLD_ONLY,
                      f"H={h} would build, but name is hold-only/museum per pattaz-book",
                      "register status change; a first bite at the low is still allowed",
                      h=h, l_pct=l_pct)
                continue
            if p_tier == PriorityTier.BLOCKED:
                _drop(n, PlateDropReason.P_BLOCKED,
                      f"P-tier BLOCKED (weight={n.current_weight_pct}%, book={n.p_mult_book})",
                      "household weight back inside the target band",
                      h=h, l_pct=l_pct)
                continue

        # --- score ---
        score = compute_score(h_mult, l_mult, p_mult)
        if score == 0:
            _drop(n, PlateDropReason.SCORE_ZERO,
                  f"H-mult={h_mult} x L-mult={l_mult} x P-mult={p_mult} = 0",
                  "any multiplier above zero", h=h, l_pct=l_pct)
            continue

        scored.append((n, h, mode, low_band, l_pct, h_mult, l_mult, p_mult, p_tier,
                       score, is_first_bite))

    # --- tilt assignment (step 4) ---
    scores_only = [s[9] for s in scored]
    tilts = assign_tilts(scores_only)

    n_eligible = len(scored)
    if n_eligible == 0:
        bees_qty, bees_amount = compute_bees_sweep(config.session_amount, config.bees_price)
        return PlateResult(
            entries=[],
            drops=drops,
            bees_sweep_qty=bees_qty,
            bees_sweep_amount=bees_amount,
            total_stock_amount=Decimal(0),
            total_with_sweep=bees_amount,
            session_amount=config.session_amount,
            residual=config.session_amount - bees_amount,
            rules_fired=rules_fired,
        )

    # --- budget & qty (steps 4-5) ---
    entries: list[PlateEntry] = []
    total_stock = Decimal(0)

    for i, row in enumerate(scored):
        n, h, mode, low_band, l_pct, h_mult, l_mult, p_mult, p_tier, score, is_fb = row
        tilt = tilts[i]
        budget = ((config.session_amount / n_eligible) * tilt).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        qty_max = config.first_bite_qty_max if is_fb else config.qty_clamp_max
        qty = compute_qty(budget, n.price, config.qty_clamp_min, qty_max)
        amount = (n.price * qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_stock += amount

        entries.append(PlateEntry(
            symbol=n.symbol,
            name=n.name,
            price=n.price,
            qty=qty,
            amount=amount,
            mode=mode,
            h=h,
            l_pct=l_pct,
            low_band=low_band,
            h_mult=h_mult,
            l_mult=l_mult,
            p_mult=p_mult,
            p_tier=p_tier,
            score=score,
            tilt=tilt,
            budget=budget,
            is_first_bite=is_fb,
        ))

    entries.sort(key=lambda e: e.score, reverse=True)

    # --- BeES sweep (step 6) ---
    residual = config.session_amount - total_stock
    bees_qty, bees_amount = compute_bees_sweep(max(residual, Decimal(0)), config.bees_price)

    return PlateResult(
        entries=entries,
        drops=drops,
        bees_sweep_qty=bees_qty,
        bees_sweep_amount=bees_amount,
        total_stock_amount=total_stock,
        total_with_sweep=total_stock + bees_amount,
        session_amount=config.session_amount,
        residual=config.session_amount - total_stock - bees_amount,
        rules_fired=rules_fired,
    )
