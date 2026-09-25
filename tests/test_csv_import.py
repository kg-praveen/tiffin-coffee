"""tests/test_csv_import.py — household CSV parser (UC2.1). No DB, no network."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from tools.csv_import import (
    HoldingImportRow,
    HouseholdSnapshot,
    as_of_from_filename,
    parse_household_csv,
    snapshot_with_zeroing,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestAsOfFromFilename:
    def test_standard_name(self) -> None:
        assert as_of_from_filename("household_equity_21sep2026.csv") == "2026-09-21"

    def test_single_digit_day(self) -> None:
        assert as_of_from_filename("household_equity_5sep2026.csv") == "2026-09-05"

    def test_no_date(self) -> None:
        assert as_of_from_filename("holdings.csv") is None


class TestParseHouseholdCsv:
    def test_splits_rows_per_account(self) -> None:
        snap = parse_household_csv(FIXTURES / "household_equity_05sep2026.csv")
        assert snap.as_of == "2026-09-05"
        assert snap.source == "CSV:household_equity_05sep2026.csv"
        by = {(r.account, r.symbol): r.qty for r in snap.rows}
        assert by[("ZERODHA_P", "HDFCBANK")] == 126
        assert by[("INTEGRATED_P", "HDFCBANK")] == 29
        assert by[("INTEGRATED_V", "HDFCBANK")] == 29
        assert by[("ZERODHA_P", "RELIANCE")] == 41
        assert ("INTEGRATED_P", "RELIANCE") not in by  # zero-qty accounts are skipped
        assert by[("INTEGRATED_P", "AGARIND")] == 100

    def test_total_value_reported(self) -> None:
        snap = parse_household_csv(FIXTURES / "household_equity_05sep2026.csv")
        assert snap.total_value_reported == Decimal("273745.90")

    def test_no_avg_cost_in_new_export(self) -> None:
        snap = parse_household_csv(FIXTURES / "household_equity_05sep2026.csv")
        assert all(r.avg_cost is None for r in snap.rows)

    def test_legacy_header_with_avg_price(self) -> None:
        snap = parse_household_csv(FIXTURES / "household_equity_legacy_04sep2026.csv")
        rows = {r.symbol: r for r in snap.rows}
        assert rows["MUTHOOTFIN"].avg_cost == Decimal("2942.63")
        assert rows["MUTHOOTFIN"].account == "ZERODHA_P"
        assert snap.as_of == "2026-09-04"

    def test_missing_column_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "household_equity_01sep2026.csv"
        f.write_text("Stock,Total Qty,Kite-P Qty\nX,1,1\n")
        with pytest.raises(ValueError, match="missing columns"):
            parse_household_csv(f)

    def test_total_mismatch_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "household_equity_01sep2026.csv"
        f.write_text("Stock,Total Qty,Kite-P Qty,Int-P Qty,Int-V Qty\nX,5,1,1,1\n")
        with pytest.raises(ValueError, match="Total Qty 5 != account sum 3"):
            parse_household_csv(f)

    def test_undated_filename_needs_explicit_as_of(self, tmp_path: Path) -> None:
        f = tmp_path / "holdings.csv"
        f.write_text("Stock,Total Qty,Kite-P Qty,Int-P Qty,Int-V Qty\nX,1,1,0,0\n")
        with pytest.raises(ValueError, match="no date in filename"):
            parse_household_csv(f)
        assert parse_household_csv(f, as_of="2026-09-01").as_of == "2026-09-01"


class TestSnapshotWithZeroing:
    def test_absent_pairs_get_zero_rows(self) -> None:
        snap = HouseholdSnapshot(as_of="2026-09-21", source="CSV:x",
                                 rows=[HoldingImportRow("ZERODHA_P", "INFY", 9, None)])
        rows = snapshot_with_zeroing(snap, {("ZERODHA_P", "INFY"), ("INTEGRATED_V", "JIOFIN")})
        assert HoldingImportRow("INTEGRATED_V", "JIOFIN", 0, None) in rows
        assert HoldingImportRow("ZERODHA_P", "INFY", 9, None) in rows
        assert len(rows) == 2

    def test_nothing_to_zero(self) -> None:
        snap = HouseholdSnapshot(as_of="2026-09-21", source="CSV:x",
                                 rows=[HoldingImportRow("ZERODHA_P", "INFY", 9, None)])
        assert snapshot_with_zeroing(snap, set()) == snap.rows
