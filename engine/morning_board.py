"""engine/morning_board.py — pure functions for UC1 (morning board / trigger patrol).

Spec: trigger-check v2, osep v7 ENGINE CONTRACT E1-E9.
All inputs are typed dataclasses or Stamped values + policy dict.
No I/O, no network, no datetime.now(), no DB.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class TriggerStatus(Enum):
    """Spec trigger-check v2 step 4."""
    FIRED = "FIRED"
    NEAR = "NEAR"
    FAR = "FAR"
    UNKNOWN = "UNKNOWN"


class DropReason(Enum):
    """Why a trigger was excluded from the board."""
    INACTIVE = "trigger active=0 in DB"
    NO_BASIS_EPS = "no basis_eps_date — cannot verify freshness (E3)"
    DECAY_EXPIRED = "verdict expired (osep decay clock)"
    NO_TICKER = "no yf_ticker — price cannot be fetched"
    STATUS_BLOCKED = "name status blocks adds"
    PRICE_FETCH_FAILED = "price not fetched this run (E3/E9)"
    EXIT_DECIDED = "on the sell list (flag_exit_decided)"


@dataclass(frozen=True)
class ArmabilityResult:
    """Result of checking whether a trigger can fire."""
    symbol: str
    kind: str
    armable: bool
    drop_reason: DropReason | None
    detail: str


@dataclass(frozen=True)
class BoardEntry:
    """One row in the morning board output (spec step 8)."""
    symbol: str
    name: str
    kind: str
    trigger_level: Decimal
    basis_eps_date: str | None
    derivation: str | None
    price: Decimal | None
    price_source: str | None
    price_as_of: str | None
    distance_pct: Decimal | None
    status: TriggerStatus
    notes: str | None


NEAR_THRESHOLD_PCT = Decimal(5)


def check_armability(
    symbol: str,
    kind: str,
    active: bool,
    basis_eps_date: str | None,
    decay_expiry: str | None,
    today: str,
    yf_ticker: str | None,
    name_status: str,
    flag_exit_decided: bool,
) -> ArmabilityResult:
    """Spec: trigger-check v2 step 2 (VALIDITY GATE, E3).

    A trigger is ARMABLE only if:
    (a) active=1 in DB
    (b) basis_eps_date is not NULL (fresh-EPS basis exists)
    (c) verdict is inside the decay clock (decay_expiry >= today)
    (d) has a fetchable ticker
    (e) name status allows adds
    (f) not on the exit/sell list

    Returns ArmabilityResult with armable=True or the drop reason.
    """
    if not active:
        return ArmabilityResult(symbol, kind, False, DropReason.INACTIVE, "trigger deactivated")

    if flag_exit_decided:
        return ArmabilityResult(
            symbol, kind, False, DropReason.EXIT_DECIDED, "flag_exit_decided=1"
        )

    if name_status in ("SOLD", "NEVER_ADD"):
        return ArmabilityResult(
            symbol, kind, False, DropReason.STATUS_BLOCKED,
            f"status={name_status}"
        )

    if basis_eps_date is None:
        return ArmabilityResult(
            symbol, kind, False, DropReason.NO_BASIS_EPS,
            "basis_eps_date is NULL — re-derive trigger from fresh EPS"
        )

    if decay_expiry is not None and decay_expiry < today:
        return ArmabilityResult(
            symbol, kind, False, DropReason.DECAY_EXPIRED,
            f"decay_expiry={decay_expiry} < today={today}"
        )

    if yf_ticker is None:
        return ArmabilityResult(
            symbol, kind, False, DropReason.NO_TICKER,
            "no yf_ticker assigned"
        )

    return ArmabilityResult(symbol, kind, True, None, "armable")


def classify_trigger(
    trigger_level: Decimal,
    current_price: Decimal,
) -> tuple[TriggerStatus, Decimal]:
    """Spec: trigger-check v2 step 4.

    Returns (status, distance_pct) where distance_pct is how far the
    price is above the trigger, as a percentage.
    FIRED = price <= trigger (distance <= 0)
    NEAR = within 5% above trigger
    FAR = > 5% above trigger
    """
    if trigger_level == 0:
        return TriggerStatus.FAR, Decimal(999)

    distance_pct = ((current_price - trigger_level) / trigger_level * 100).quantize(
        Decimal("0.01")
    )

    if current_price <= trigger_level:
        return TriggerStatus.FIRED, distance_pct
    if distance_pct <= NEAR_THRESHOLD_PCT:
        return TriggerStatus.NEAR, distance_pct
    return TriggerStatus.FAR, distance_pct


def build_board(
    entries: list[BoardEntry],
) -> tuple[list[BoardEntry], list[BoardEntry], list[BoardEntry]]:
    """Sort entries into FIRED, NEAR, FAR lists, each sorted by distance.

    Spec: trigger-check v2 step 8 — lead with FIRED, then NEAR, then FAR.
    """
    fired = sorted(
        [e for e in entries if e.status == TriggerStatus.FIRED],
        key=lambda e: e.distance_pct or Decimal(0),
    )
    near = sorted(
        [e for e in entries if e.status == TriggerStatus.NEAR],
        key=lambda e: e.distance_pct or Decimal(0),
    )
    far = sorted(
        [e for e in entries if e.status == TriggerStatus.FAR],
        key=lambda e: e.distance_pct or Decimal(999),
    )
    return fired, near, far


def nearest_n(far_entries: list[BoardEntry], n: int = 3) -> list[BoardEntry]:
    """Spec: trigger-check v2 step 8 — if nothing fired, show the 3 nearest."""
    return far_entries[:n]
