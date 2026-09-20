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
    """Why a name was excluded from the plate."""

    FASTING_NO_FIRST_BITE = "H<0.85 and first-bite exception does not apply"
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
    cap_psu_regulated_pct: Decimal = Decimal(25)


# -------------------------------------------------------------- outputs ---


@dataclass(frozen=True)
class PlateEntry:
    """One name on the final plate."""

    symbol: str
    name: str
    qty: int
    amount: Decimal
    mode: Mode
    h: Decimal | None
    l_pct: Decimal
    low_band: LowBand
    h_mult: Decimal
    l_mult: Decimal
    p_mult: Decimal
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


def check_overlays(
    n: NameInput,
    config: PlateConfig,
) -> PlateDropReason | None:
    """Run all 10 exclusion overlays. Spec: tiffin-coffee v5 §overlays.

    Returns the first failing overlay's drop reason, or None if all pass.
    Precedence order matches the spec table.
    """
    if n.flag_probe_open:
        return PlateDropReason.PROBE_OPEN

    if n.flag_sovereign:
        return PlateDropReason.SOVEREIGN

    if n.flag_cyclical:
        return PlateDropReason.PEAK_CYCLE

    if n.flag_psu and config.psu_weight_pct >= config.cap_psu_regulated_pct:
        return PlateDropReason.PSU_CAP

    if n.cell and n.cell in config.cells:
        cell = config.cells[n.cell]
        if cell.is_full or cell.active_add_count >= cell.max_adds:
            return PlateDropReason.CELL_FULL

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


# ----------------------------------------------------- first-bite check ---


def check_first_bite(
    l_pct: Decimal,
    overlays_passed: bool,
    valuation_gate_passed: bool,
    is_owned: bool,
    sector_class: str | None,
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
        l_pct <= Decimal(2)
        and overlays_passed
        and valuation_gate_passed
        and is_owned
    )


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
        NameInput, Decimal, Mode, LowBand,
        Decimal, Decimal, Decimal, Decimal, Decimal, bool,
    ]
    scored: list[_ScoredRow] = []
    rules_fired: list[str] = []

    for n in names:
        # --- pre-checks ---
        if n.status in ("SOLD", "NEVER_ADD"):
            drops.append(PlateDrop(n.symbol, n.name, PlateDropReason.STATUS_BLOCKED,
                                   f"status={n.status}"))
            continue

        if n.flag_exit_decided:
            drops.append(PlateDrop(n.symbol, n.name, PlateDropReason.EXIT_DECIDED,
                                   "flag_exit_decided=1"))
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
        is_first_bite = False

        if not eligible_via_h and not eligible_via_l:
            drops.append(PlateDrop(n.symbol, n.name, PlateDropReason.FASTING_NO_FIRST_BITE,
                                   f"H={h}, L={l_pct}% — not eligible",
                                   h=h, l_pct=l_pct))
            continue

        # --- overlays ---
        overlay_drop = check_overlays(n, config)
        overlays_passed = overlay_drop is None

        if not overlays_passed:
            drops.append(PlateDrop(n.symbol, n.name, overlay_drop,
                                   f"H={h}, L={l_pct}%",
                                   h=h, l_pct=l_pct))
            rules_fired.append(f"overlay:{overlay_drop.name}:{n.symbol}")
            continue

        # --- first-bite exception for names eligible via L only ---
        if not eligible_via_h and eligible_via_l:
            is_owned = n.qty_held_household > 0
            is_first_bite = check_first_bite(
                l_pct, overlays_passed, n.valuation_gate_passed, is_owned,
                n.sector_class,
            )
            if not is_first_bite:
                drops.append(PlateDrop(
                    n.symbol, n.name, PlateDropReason.FASTING_NO_FIRST_BITE,
                    f"L={l_pct}% eligible but first-bite conditions not met "
                    f"(owned={is_owned}, gate={n.valuation_gate_passed})",
                    h=h, l_pct=l_pct,
                ))
                continue
            h_mult = max(h_mult, config.first_bite_h_mult_floor)
            rules_fired.append(f"first_bite:{n.symbol}")

        # --- P-tier ---
        p_tier, p_mult = classify_priority(n.current_weight_pct, n.bucket)
        if p_tier == PriorityTier.BLOCKED:
            drops.append(PlateDrop(n.symbol, n.name, PlateDropReason.P_BLOCKED,
                                   f"P-tier BLOCKED (weight={n.current_weight_pct}%)",
                                   h=h, l_pct=l_pct))
            continue

        # --- score ---
        score = compute_score(h_mult, l_mult, p_mult)
        if score == 0:
            drops.append(PlateDrop(n.symbol, n.name, PlateDropReason.SCORE_ZERO,
                                   f"H-mult={h_mult} x L-mult={l_mult} x P-mult={p_mult} = 0",
                                   h=h, l_pct=l_pct))
            continue

        scored.append((n, h, mode, low_band, l_pct, h_mult, l_mult, p_mult, score, is_first_bite))

    # --- tilt assignment (step 4) ---
    scores_only = [s[8] for s in scored]
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

    for i, (n, h, mode, low_band, l_pct, h_mult, l_mult, p_mult, score, is_fb) in enumerate(scored):
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
            qty=qty,
            amount=amount,
            mode=mode,
            h=h,
            l_pct=l_pct,
            low_band=low_band,
            h_mult=h_mult,
            l_mult=l_mult,
            p_mult=p_mult,
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
