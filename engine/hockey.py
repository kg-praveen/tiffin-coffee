"""engine/hockey.py — HOCKEY detection: the market signals the plate could not see.

Spec: tiffin-coffee v6 §H table, HOCKEY row — "> 1.15, or Nifty -5% in a week, or a
name -10% in a day with no Stage-0 cause" → thali (reserve); §TWO-POCKET "LADDER the
surge — ~⅓ at Nifty -15%, ~⅓ at -25%" (ledger D37 rungs); §PROCEDURE step 8 "HOCKEY
MODE: present the pre-committed thali menu FIRST, sized from the reserve, and confirm
before placing"; "Hockey never overrides Stage-0 or a cell cap".

DETECTION ONLY. The spec does not define reserve tranche sizes in rupees (the thali
menu is pre-committed in the ledger, not in the register), so this module never sizes
anything and never changes the plate: it reports what fired, and every reserve move
needs Praveen's yes. Thresholds come from policy (E2). Pure: no I/O, no clock.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

from engine.plate import Mode, NameInput, PlateResult

MARKET = "*"   # symbol used for index-level signals


class HockeyKind(Enum):
    """Which HOCKEY condition fired. Spec cited per member."""

    NIFTY_WEEK = "NIFTY_WEEK"   # tiffin v6 §H: Nifty -5% in a week
    RUNG_1 = "RUNG_1"           # tiffin v6 §TWO-POCKET ladder / ledger D37 rung 1
    RUNG_2 = "RUNG_2"           # tiffin v6 §TWO-POCKET ladder / ledger D37 rung 2
    NAME_DAY = "NAME_DAY"       # tiffin v6 §H: a name -10% in a day (no Stage-0 cause)
    H_ABOVE = "H_ABOVE"         # tiffin v6 §H: H > 1.15 (the plate's HOCKEY mode)


@dataclass(frozen=True)
class HockeyConfig:
    """Policy thresholds, each a positive magnitude of a FALL in %. None = the policy
    row is missing → that check is not run and the report says so (E9)."""

    nifty_week_fall_pct: Decimal | None
    name_day_fall_pct: Decimal | None
    rung1_drawdown_pct: Decimal | None
    rung2_drawdown_pct: Decimal | None


@dataclass(frozen=True)
class IndexInput:
    """Nifty moves for this run (unwrapped from Stamped by the usecase)."""

    week_change_pct: Decimal | None
    drawdown_pct: Decimal | None     # from the 52-week high; ≤ 0


@dataclass(frozen=True)
class HockeySignal:
    kind: HockeyKind
    symbol: str
    move_pct: Decimal | None        # the observed move (None for H_ABOVE)
    threshold_pct: Decimal | None   # the fall it crossed (None for H_ABOVE)
    blocked_by: str | None = None   # the gate that already said no (hockey never overrides)


@dataclass(frozen=True)
class HockeyReport:
    signals: tuple[HockeySignal, ...]
    not_checked: tuple[str, ...]

    def of(self, kind: HockeyKind) -> list[HockeySignal]:
        return [s for s in self.signals if s.kind == kind]

    @property
    def market_hockey(self) -> bool:
        """Index-level hockey (a week fall or a ladder rung) — the reserve question."""
        return any(s.symbol == MARKET for s in self.signals)


def compute_change_pct(now: Decimal, before: Decimal) -> Decimal | None:
    """% change now vs before, to 2 dp (the precision the threshold is read at)."""
    if before <= 0:
        return None
    return ((now - before) / before * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def is_fall_at_least(move_pct: Decimal, fall_pct: Decimal) -> bool:
    """'Nifty -5%' / 'name -10%' read as a fall of that size or more (inclusive)."""
    return move_pct <= -fall_pct


def highest_rung(drawdown_pct: Decimal, cfg: HockeyConfig) -> tuple[HockeyKind, Decimal] | None:
    """tiffin v6 §TWO-POCKET ladder / ledger D37: the deepest rung reached, if any."""
    for kind, rung in ((HockeyKind.RUNG_2, cfg.rung2_drawdown_pct),
                       (HockeyKind.RUNG_1, cfg.rung1_drawdown_pct)):
        if rung is not None and is_fall_at_least(drawdown_pct, rung):
            return kind, rung
    return None


def latest_completed_session(run_date: date) -> date:
    """E3 freshness for market data: the last weekday strictly before the run date.

    Definition used (the spec gives none): data stamped on this day or later is "this
    run's" data (a run on Tuesday accepts Monday's close or Tuesday's live bar; a run on
    Saturday/Sunday/Monday accepts Friday's). NSE holidays are not known to the engine,
    so data before a holiday reads stale — fail-closed (E9), never assumed fresh."""
    d = run_date - timedelta(days=1)
    while d.weekday() >= 5:           # Sat=5, Sun=6
        d -= timedelta(days=1)
    return d


def is_market_data_fresh(as_of: date, run_date: date) -> bool:
    """E3: True when `as_of` is not older than the latest completed session."""
    return as_of >= latest_completed_session(run_date)


def stale_market_data_reason(as_of: date, run_date: date) -> str | None:
    """None when fresh; otherwise the named reason used in the not-checked list."""
    if is_market_data_fresh(as_of, run_date):
        return None
    return (f"stale data: as of {as_of.isoformat()}, older than the latest session "
            f"{latest_completed_session(run_date).isoformat()} for run date "
            f"{run_date.isoformat()}")


def detect_index_hockey(index: IndexInput | None, cfg: HockeyConfig,
                        index_missing_why: str = "no Nifty data this run",
                        ) -> tuple[list[HockeySignal], list[str]]:
    """Nifty -X% in a week (tiffin v6 §H) and the drawdown ladder rungs (D37).

    `index_missing_why` names why `index` is None (e.g. stale index data, E3)."""
    signals: list[HockeySignal] = []
    missing: list[str] = []
    week = index.week_change_pct if index else None
    dd = index.drawdown_pct if index else None
    if cfg.nifty_week_fall_pct is None:
        missing.append("Nifty week fall (policy hockey_nifty_week_fall_pct missing)")
    elif week is None:
        missing.append(f"Nifty week fall ({index_missing_why})")
    elif is_fall_at_least(week, cfg.nifty_week_fall_pct):
        signals.append(HockeySignal(HockeyKind.NIFTY_WEEK, MARKET, week,
                                    cfg.nifty_week_fall_pct))
    if cfg.rung1_drawdown_pct is None and cfg.rung2_drawdown_pct is None:
        missing.append("hockey ladder (policy rung rows missing)")
    elif dd is None:
        missing.append(f"hockey ladder ({index_missing_why})")
    else:
        rung = highest_rung(dd, cfg)
        if rung is not None:
            signals.append(HockeySignal(rung[0], MARKET, dd, rung[1]))
    return signals, missing


def detect_name_day_hockey(names: Sequence[NameInput], result: PlateResult,
                           cfg: HockeyConfig) -> tuple[list[HockeySignal], list[str]]:
    """A name -10% in a day (tiffin v6 §H). The "no Stage-0 cause" half is a headline
    check the code does not do (CLAUDE.md §6) — the signal is a question for Praveen.
    A name the gates already dropped keeps its drop: hockey never overrides them."""
    if cfg.name_day_fall_pct is None:
        return [], ["name day fall (policy hockey_name_day_fall_pct missing)"]
    dropped = {d.symbol: d.reason.name for d in result.drops}
    signals: list[HockeySignal] = []
    unknown = 0
    for n in sorted(names, key=lambda x: x.symbol):
        if n.prev_close is None:
            unknown += 1
            continue
        move = compute_change_pct(n.price, n.prev_close)
        if move is not None and is_fall_at_least(move, cfg.name_day_fall_pct):
            signals.append(HockeySignal(HockeyKind.NAME_DAY, n.symbol, move,
                                        cfg.name_day_fall_pct, dropped.get(n.symbol)))
    missing = ([f"name day fall (no previous close for {unknown} of {len(names)} names)"]
               if unknown else [])
    return signals, missing


def detect_h_hockey(result: PlateResult) -> list[HockeySignal]:
    """H > 1.15 on the plate (tiffin v6 §H — the band lives once, in engine/plate.py)."""
    return [HockeySignal(HockeyKind.H_ABOVE, e.symbol, None, None)
            for e in result.entries if e.mode == Mode.HOCKEY]


def detect_hockey(names: Sequence[NameInput], result: PlateResult,
                  index: IndexInput | None, cfg: HockeyConfig, *,
                  index_missing_why: str = "no Nifty data this run",
                  not_checked_extra: Sequence[str] = ()) -> HockeyReport:
    """Every HOCKEY condition in tiffin v6 §H + the D37 ladder, in a stable order.

    `not_checked_extra`: inputs the caller already dropped with a named reason (E3)."""
    idx_sig, idx_missing = detect_index_hockey(index, cfg, index_missing_why)
    day_sig, day_missing = detect_name_day_hockey(names, result, cfg)
    return HockeyReport(
        signals=tuple([*idx_sig, *day_sig, *detect_h_hockey(result)]),
        not_checked=tuple([*idx_missing, *day_missing, *not_checked_extra]),
    )


def hockey_rules_fired(report: HockeyReport) -> list[str]:
    """E8 "rules fired by name": one label per HOCKEY detection, e.g. HOCKEY:NIFTY_WEEK,
    HOCKEY:RUNG_1, HOCKEY:NAME_DAY:INFY, HOCKEY:H_ABOVE:INFY. Detection only."""
    return [f"HOCKEY:{s.kind.name}" if s.symbol == MARKET
            else f"HOCKEY:{s.kind.name}:{s.symbol}" for s in report.signals]


def parse_two_pocket_split(value: str) -> tuple[Decimal, Decimal]:
    """tiffin v6 §TWO-POCKET CASH RULE: "Equity money splits 60% TIFFIN POCKET / 40%
    HOCKEY RESERVE" (policy two_pocket_split, e.g. "60/40"). Returns (tiffin, reserve).

    Only the split is defined; the pocket balances ("equity money") are not in the
    register, so callers can state the rule but not check a plate against it."""
    left, sep, right = value.partition("/")
    if not sep:
        raise ValueError(f"two_pocket_split {value!r}: expected 'tiffin/reserve'")
    tiffin, reserve = Decimal(left.strip()), Decimal(right.strip())
    if tiffin + reserve != 100:
        raise ValueError(f"two_pocket_split {value!r} does not sum to 100")
    return tiffin, reserve
