"""tests/test_ledger_file.py — parse the local text export of the Drive ledger (UC6).

Fixture: tests/fixtures/ledger/ is a trimmed verbatim copy of ledger v4.10 (26-Sep):
§5 cell map, §7 trigger board, §10 decision register. No network.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from tools.ledger_file import (
    LedgerTrigger,
    find_newest_ledger,
    parse_ledger,
    parse_ledger_text,
    split_top,
)

FIX = Path(__file__).parent / "fixtures" / "ledger"
V410 = FIX / "PATTAZ_MASTER_LEDGER_v4.10_2026-09-26.txt"


@pytest.fixture(scope="module")
def led():  # type: ignore[no-untyped-def]
    return parse_ledger(V410)


def _trig(led, name: str, kind: str = "LEVEL") -> LedgerTrigger:  # type: ignore[no-untyped-def]
    hits = [t for t in led.triggers if t.name == name and t.kind == kind]
    assert len(hits) == 1, (name, kind, hits)
    return hits[0]


# ------------------------------------------------------------------ finder ---

def test_newest_is_numeric_not_lexical(tmp_path: Path) -> None:
    for n in ("PATTAZ_MASTER_LEDGER_v4.9_2026-09-17.txt",
              "PATTAZ_MASTER_LEDGER_v4.10_2026-09-26.txt",
              "PATTAZ_MASTER_LEDGER_v4.11_2026-09-28.txt",
              "PATTAZ_MASTER_LEDGER_v4.2_2026-08-01.txt",
              "notes.txt", "PATTAZ_MASTER_LEDGER_v4.12_draft.txt"):
        (tmp_path / n).write_text("x")
    newest = find_newest_ledger(tmp_path)
    assert newest is not None and newest.name == "PATTAZ_MASTER_LEDGER_v4.11_2026-09-28.txt"


def test_newest_none_when_folder_empty_or_missing(tmp_path: Path) -> None:
    assert find_newest_ledger(tmp_path) is None
    assert find_newest_ledger(tmp_path / "nope") is None


# ------------------------------------------------------------------ header ---

def test_version_and_date_are_stamped(led) -> None:  # type: ignore[no-untyped-def]
    assert led.version.value == "4.10"
    assert led.ledger_date == "2026-09-26"
    assert led.version.as_of == "2026-09-26"
    assert V410.name in led.version.source


def test_no_version_anywhere_fails_closed() -> None:
    with pytest.raises(ValueError):
        parse_ledger_text("just some prose\n§10 DECISION REGISTER\nD1 thing\n", source="x.txt")


def test_version_from_filename_when_header_missing() -> None:
    led = parse_ledger_text("§10 DECISION REGISTER\nD71 (27-Sep) NEW THING — detail\n",
                            source="PATTAZ_MASTER_LEDGER_v4.11_2026-09-28.txt")
    assert led.version.value == "4.11" and led.ledger_date == "2026-09-28"
    assert led.decisions[0].decided_on == "2026-09-27"


# --------------------------------------------------------------- decisions ---

def test_declared_register_range(led) -> None:  # type: ignore[no-untyped-def]
    assert led.declared_max_d == 68


def test_dated_decisions_have_iso_dates_and_titles(led) -> None:  # type: ignore[no-untyped-def]
    by = {d.d_no: d for d in led.decisions}
    assert by[65].decided_on == "2026-09-25"
    assert by[65].title == "IT CELL SWAP"
    assert by[65].detail is not None and "R SYSTEMS" in by[65].detail
    assert by[68].title == "PLATES"
    assert not by[65].index_only


def test_indexed_decisions_paren_aware(led) -> None:  # type: ignore[no-untyped-def]
    by = {d.d_no: d for d in led.decisions}
    assert by[1].title == "Coal India → NTPC swap (exit funds NTPC)"
    assert by[1].decided_on is None
    # " · " inside D33's parentheses must not split the entry
    assert by[33].title is not None and by[33].title.startswith("CONSOLIDATION")
    assert "GE buyback" in by[33].title
    # compound entry names both numbers
    assert by[29].title == by[38].title == "Axis redeem-now"
    assert by[64].title == "SECTOR GATE EVIDENCE BASE filed"


def test_archive_list_is_index_only(led) -> None:  # type: ignore[no-untyped-def]
    by = {d.d_no: d for d in led.decisions}
    for k in (2, 4, 5, 9, 11, 16, 22, 24, 27, 30, 32):
        assert by[k].index_only and by[k].title is None
    assert sorted(by) == list(range(1, 69))


# ---------------------------------------------------------------- triggers ---

def test_gbn_levels_stamped(led) -> None:  # type: ignore[no-untyped-def]
    p = _trig(led, "Petronet")
    assert p.level.value == Decimal(383)
    assert p.level.as_of == "2026-09-26" and V410.name in p.level.source
    assert "HOCKEY" in p.note
    assert _trig(led, "NTPC").level.value == Decimal(407)
    assert _trig(led, "Infosys").level.value == Decimal(1099)
    assert _trig(led, "HDFC").level.value == Decimal(419)


def test_arrow_note_kept(led) -> None:  # type: ignore[no-untyped-def]
    t = _trig(led, "TCS")
    assert t.level.value == Decimal(1939) and "HOLD-no-add" in t.note


def test_explicit_symbol_line(led) -> None:  # type: ignore[no-untyped-def]
    t = _trig(led, "R SYSTEMS")
    assert t.symbol_hint == "RSYSTEMS" and t.level.value == Decimal(251)


def test_name_label_with_le_level(led) -> None:  # type: ignore[no-untyped-def]
    assert _trig(led, "CHAMBAL").level.value == Decimal(415)
    assert _trig(led, "COROMANDEL").level.value == Decimal(1225)


def test_wires_carry_alert_levels(led) -> None:  # type: ignore[no-untyped-def]
    assert _trig(led, "Finolex Cables").level.value == Decimal(760)
    assert _trig(led, "Finolex Cables", "ALERT").level.value == Decimal(1048)
    assert _trig(led, "Polycab", "ALERT").level.value == Decimal(3724)


def test_alerts_segment(led) -> None:  # type: ignore[no-untyped-def]
    assert _trig(led, "HAL", "ALERT").level.value == Decimal(4900)
    assert _trig(led, "UltraTech", "ALERT").level.value == Decimal(5820)


def test_banks_segment_and_share_counts_are_not_levels(led) -> None:  # type: ignore[no-untyped-def]
    assert _trig(led, "Federal").level.value == Decimal(215)
    assert not [t for t in led.triggers if t.name.startswith("IDFC")]
    assert any("IDFC First 10sh" in u for u in led.unparsed)
    assert any("KVB" in u for u in led.unparsed)


def test_status_lists_become_mentions(led) -> None:  # type: ignore[no-untyped-def]
    segs = {m.segment for m in led.mentions}
    assert {"WATCH-ONLY UNTIL A CRASH", "WITHDRAWN/ZERO", "HARVEST BASKET"} <= segs
    assert any(m.name == "Mastek" for m in led.mentions)


# ------------------------------------------------------------------- cells ---

def test_cell_seats(led) -> None:  # type: ignore[no-untyped-def]
    st = {(c.cell_label, c.name): c.state for c in led.cell_seats}
    assert st[("IT", "Infosys")] == "ADD"          # inherits "(adds, D65)"
    assert st[("IT", "R SYSTEMS")] == "ADD"
    assert st[("IT", "TCS HOLD-no-add")] == "NOT_ADD"
    assert st[("Power", "NTPC")] == "ADD"
    assert st[("Power", "Power Grid")] == "ADD"
    assert st[("Energy/gas", "Reliance")] == "NOT_ADD"
    assert st[("Financials", "SBI")] == "ADD"
    assert st[("Ancillary", "Amara Raja")] == "UNCLEAR"


# -------------------------------------------------------------- robustness ---

def test_garbage_lines_go_to_unparsed_never_guessed() -> None:
    text = ("★★★ PATTAZ MASTER LEDGER — v9.1 | 2027-01-02 | x\n"
            "§7 WATCHLIST\nGBN/NEAR (x): Foo 12 · ?? weird ?? · Bar\n"
            "SOMETHING NEW: blah\n§10 DECISION REGISTER\nnot a decision\n")
    led = parse_ledger_text(text, source="t.txt")
    assert [t.name for t in led.triggers] == ["Foo"]
    assert any("weird" in u for u in led.unparsed)
    assert any("SOMETHING NEW" in u for u in led.unparsed)
    assert any("not a decision" in u for u in led.unparsed)


def test_split_top_respects_parentheses() -> None:
    assert split_top("a (b · c) · d", " · ") == ["a (b · c)", "d"]
