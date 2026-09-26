"""tests/test_engine_morning_board.py — pure engine tests for UC1.

Spec: trigger-check v2, ENGINE CONTRACT E1-E9.
No network, no DB — tests exercise pure functions only.
"""
from __future__ import annotations

from decimal import Decimal

from engine.morning_board import (
    BoardEntry,
    DropReason,
    TriggerStatus,
    build_board,
    check_armability,
    classify_trigger,
    nearest_n,
)


class TestBasisVersusResults:
    """E3: armable only on a basis not older than the latest results (26-Sep-2026)."""

    def _arm(self, basis: str, dates: tuple[str, ...] | None, today: str = "2026-09-26"):  # type: ignore[no-untyped-def]
        return check_armability(
            symbol="INFY", kind="BUY", active=True, basis_eps_date=basis,
            decay_expiry=None, today=today, yf_ticker="INFY.NS", name_status="ADD",
            flag_exit_decided=False, result_dates=dates)

    def test_basis_after_results_is_armable(self) -> None:
        assert self._arm("2026-09-01", ("2026-07-23", "2026-10-23")).armable

    def test_results_after_basis_disarm(self) -> None:
        r = self._arm("2026-09-01", ("2026-07-23", "2026-10-23"), today="2026-10-24")
        assert r.drop_reason == DropReason.STALE_BASIS and "2026-10-23" in r.detail

    def test_same_day_basis_is_fresh(self) -> None:
        assert self._arm("2026-07-23", ("2026-07-23",)).armable

    def test_unknown_dates_fail_closed(self) -> None:
        assert self._arm("2026-09-01", None).drop_reason == DropReason.RESULT_DATE_UNKNOWN
        assert self._arm("2026-09-01", ("2026-10-23",)).drop_reason == \
            DropReason.RESULT_DATE_UNKNOWN          # nothing reported yet in the window


class TestCheckArmability:
    """Spec: trigger-check v2 step 2 (VALIDITY GATE, E3)."""

    def test_fully_armable(self) -> None:
        r = check_armability(
            symbol="PETRONET", kind="BUY", active=True,
            basis_eps_date="2026-09-01", decay_expiry="2026-10-01",
            today="2026-09-19", yf_ticker="PETRONET.NS",
            name_status="ADD", flag_exit_decided=False,
            result_dates=("2026-07-20",),
        )
        assert r.armable is True
        assert r.drop_reason is None

    def test_inactive_trigger(self) -> None:
        r = check_armability(
            symbol="TMB", kind="BUY", active=False,
            basis_eps_date="2026-08-01", decay_expiry="2026-11-01",
            today="2026-09-19", yf_ticker="TMB.NS",
            name_status="ADD", flag_exit_decided=False,
            result_dates=("2026-07-20",),
        )
        assert r.armable is False
        assert r.drop_reason == DropReason.INACTIVE

    def test_no_basis_eps(self) -> None:
        r = check_armability(
            symbol="ZYDUSLIFE", kind="BUY", active=True,
            basis_eps_date=None, decay_expiry="2026-12-01",
            today="2026-09-19", yf_ticker="ZYDUSLIFE.NS",
            name_status="ADD", flag_exit_decided=False,
            result_dates=("2026-07-20",),
        )
        assert r.armable is False
        assert r.drop_reason == DropReason.NO_BASIS_EPS

    def test_decay_expired(self) -> None:
        r = check_armability(
            symbol="TEST", kind="BUY", active=True,
            basis_eps_date="2026-06-01", decay_expiry="2026-08-31",
            today="2026-09-19", yf_ticker="TEST.NS",
            name_status="ADD", flag_exit_decided=False,
            result_dates=("2026-04-20",),
        )
        assert r.armable is False
        assert r.drop_reason == DropReason.DECAY_EXPIRED

    def test_no_ticker(self) -> None:
        r = check_armability(
            symbol="GROWW", kind="BUY", active=True,
            basis_eps_date="2026-09-01", decay_expiry="2026-10-01",
            today="2026-09-19", yf_ticker=None,
            name_status="ADD", flag_exit_decided=False,
            result_dates=("2026-07-20",),
        )
        assert r.armable is False
        assert r.drop_reason == DropReason.NO_TICKER

    def test_status_sold(self) -> None:
        r = check_armability(
            symbol="TEST", kind="BUY", active=True,
            basis_eps_date="2026-09-01", decay_expiry="2026-10-01",
            today="2026-09-19", yf_ticker="TEST.NS",
            name_status="SOLD", flag_exit_decided=False,
            result_dates=("2026-07-20",),
        )
        assert r.armable is False
        assert r.drop_reason == DropReason.STATUS_BLOCKED

    def test_exit_decided(self) -> None:
        r = check_armability(
            symbol="TEST", kind="BUY", active=True,
            basis_eps_date="2026-09-01", decay_expiry="2026-10-01",
            today="2026-09-19", yf_ticker="TEST.NS",
            name_status="ADD", flag_exit_decided=True,
            result_dates=("2026-07-20",),
        )
        assert r.armable is False
        assert r.drop_reason == DropReason.EXIT_DECIDED

    def test_decay_expiry_none_is_armable(self) -> None:
        """decay_expiry=NULL means no expiry set — trigger is armable."""
        r = check_armability(
            symbol="TEST", kind="BUY", active=True,
            basis_eps_date="2026-09-01", decay_expiry=None,
            today="2026-09-19", yf_ticker="TEST.NS",
            name_status="ADD", flag_exit_decided=False,
            result_dates=("2026-07-20",),
        )
        assert r.armable is True

    def test_precedence_exit_before_basis(self) -> None:
        """E5: exit decided takes precedence over missing basis."""
        r = check_armability(
            symbol="TEST", kind="BUY", active=True,
            basis_eps_date=None, decay_expiry=None,
            today="2026-09-19", yf_ticker="TEST.NS",
            name_status="ADD", flag_exit_decided=True,
            result_dates=("2026-07-20",),
        )
        assert r.drop_reason == DropReason.EXIT_DECIDED


class TestClassifyTrigger:
    """Spec: trigger-check v2 step 4."""

    def test_fired_at_trigger(self) -> None:
        status, dist = classify_trigger(Decimal(383), Decimal(383))
        assert status == TriggerStatus.FIRED
        assert dist == Decimal("0.00")

    def test_fired_below_trigger(self) -> None:
        status, dist = classify_trigger(Decimal(383), Decimal(370))
        assert status == TriggerStatus.FIRED
        assert dist < 0

    def test_near_within_5pct(self) -> None:
        status, dist = classify_trigger(Decimal(383), Decimal(400))
        assert status == TriggerStatus.NEAR
        assert Decimal(0) < dist <= Decimal(5)

    def test_far_above_5pct(self) -> None:
        status, dist = classify_trigger(Decimal(383), Decimal(450))
        assert status == TriggerStatus.FAR
        assert dist > Decimal(5)

    def test_boundary_exactly_5pct(self) -> None:
        trigger = Decimal(100)
        price = Decimal(105)
        status, dist = classify_trigger(trigger, price)
        assert status == TriggerStatus.NEAR
        assert dist == Decimal("5.00")

    def test_boundary_just_over_5pct(self) -> None:
        trigger = Decimal(100)
        price = Decimal("105.01")
        status, _dist = classify_trigger(trigger, price)
        assert status == TriggerStatus.FAR


class TestBuildBoard:
    """Spec: trigger-check v2 step 8 — output ordering."""

    def _entry(
        self, symbol: str, status: TriggerStatus, dist: Decimal
    ) -> BoardEntry:
        return BoardEntry(
            symbol=symbol, name=symbol, kind="BUY",
            trigger_level=Decimal(100), basis_eps_date="2026-09-01",
            derivation=None, price=Decimal(100) + dist,
            price_source="test", price_as_of="2026-09-19",
            distance_pct=dist, status=status, notes=None,
        )

    def test_sorts_fired_near_far(self) -> None:
        entries = [
            self._entry("FAR1", TriggerStatus.FAR, Decimal(10)),
            self._entry("FIRED1", TriggerStatus.FIRED, Decimal(-5)),
            self._entry("NEAR1", TriggerStatus.NEAR, Decimal(3)),
            self._entry("FIRED2", TriggerStatus.FIRED, Decimal(-2)),
        ]
        fired, near, far = build_board(entries)
        assert [e.symbol for e in fired] == ["FIRED1", "FIRED2"]
        assert [e.symbol for e in near] == ["NEAR1"]
        assert [e.symbol for e in far] == ["FAR1"]

    def test_nearest_n(self) -> None:
        far = [
            self._entry("A", TriggerStatus.FAR, Decimal(6)),
            self._entry("B", TriggerStatus.FAR, Decimal(15)),
            self._entry("C", TriggerStatus.FAR, Decimal(8)),
            self._entry("D", TriggerStatus.FAR, Decimal(20)),
        ]
        _, _, sorted_far = build_board(far)
        top3 = nearest_n(sorted_far, 3)
        assert [e.symbol for e in top3] == ["A", "C", "B"]
