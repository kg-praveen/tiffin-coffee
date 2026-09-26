"""tests/test_ledger_sync.py — UC6 ledger sync on a scratch register, no network.

The v4.10 fixture matches the register (migration 009 caught it up), so it must report
nothing to draft. A synthetic v4.11 (built from the fixture) adds D69-D71, moves two
levels, adds unknown / ambiguous names and flips two cell seats.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import pytest

from usecases.ledger_sync import format_report, main, run_ledger_sync

FIX = Path(__file__).parent / "fixtures" / "ledger"
V410 = FIX / "PATTAZ_MASTER_LEDGER_v4.10_2026-09-26.txt"
MIG = Path(__file__).parent.parent / "db" / "migrations" / "011_ledger_aliases.sql"


def _apply_migration_011(db: Path) -> None:
    """The shared register gets 011 only at integration; apply it to the scratch copy."""
    con = sqlite3.connect(db)
    sql = MIG.read_text()
    has = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ledger_aliases'").fetchone()
    if has:
        sql = re.sub(r"CREATE TABLE \w+ \(.*?\);", "", sql, flags=re.DOTALL)
    con.executescript(sql)
    con.close()


@pytest.fixture
def reg(scratch_db: Path) -> Path:
    _apply_migration_011(scratch_db)
    return scratch_db


def _v411(folder: Path) -> Path:
    t = V410.read_text()
    t = t.replace("v4.10 | 2026-09-26", "v4.11 | 2026-09-28")
    t = t.replace("DECISION REGISTER — D1-D68", "DECISION REGISTER — D1-D71")
    t = t.replace("NTPC 407", "NTPC 400")
    t = t.replace("Polycab 2,700 (3,724)", "Polycab 2,700 (3,800)")
    t = t.replace("TCS 1,939 → HOLD-no-add (D65).",
                  "TCS 1,939 → HOLD-no-add (D65) · Zensar 600 · Tata Motors 900 · Hindalco 700.")
    t = t.replace("M&M add", "M&M hold")
    t = t.replace("Tata Power hold", "Tata Power (add)")
    extra = ("D69 (26-Sep) IT GATE CHANGE — per-share USD operating profit.\n"
             "D70 (26-Sep) WIPRO CAPS-OFF — Mon 28-Sep only.\n"
             "D71 (27-Sep) DR REDDY'S EXIT DONE — Praveen's written \"done\" on both books.\n")
    anchor = "D68 (25-Sep) PLATES"
    i = t.index(anchor)
    j = t.index("\n", i) + 1
    t = t[:j] + extra + t[j:]
    p = folder / "PATTAZ_MASTER_LEDGER_v4.11_2026-09-28.txt"
    p.write_text(t)
    return p


def _sessions(db: Path) -> list[tuple[str, str, str]]:
    con = sqlite3.connect(db)
    rows = con.execute(
        "SELECT usecase, outputs_json, drops_json FROM sessions ORDER BY ran_at").fetchall()
    con.close()
    return rows


# -------------------------------------------------------- v4.10 (in sync) ---

def test_v410_matches_register(reg: Path, tmp_path: Path) -> None:
    rep = run_ledger_sync(reg, file=V410, drafts_dir=tmp_path / "drafts")
    assert rep.error is None
    assert rep.version == "4.10" and rep.ledger_date == "2026-09-26"
    assert rep.new_decisions == []
    assert rep.register_ahead == [69, 70]           # D69/D70 went straight to the register
    assert rep.declared_unread == []                # every D1-D68 number was read
    assert rep.trigger_changes == []
    assert rep.cell_diffs == []
    assert rep.draft_path is None                   # nothing unambiguous to draft
    assert not (tmp_path / "drafts").exists()
    unknown = {u.ledger_name for u in rep.unknown_names}
    assert "Bajaj Housing" in unknown
    compared = {c.symbol for c in rep.compared}
    assert {"SBIN", "ENGINERSIN", "HDFCBANK", "RSYSTEMS", "CHAMBLFERT", "POLYCAB"} <= compared


def test_writes_one_session_row(reg: Path, tmp_path: Path) -> None:
    before = len(_sessions(reg))
    run_ledger_sync(reg, file=V410, drafts_dir=tmp_path)
    rows = _sessions(reg)
    assert len(rows) == before + 1
    usecase, outputs, _drops = rows[-1]
    assert usecase == "UC6_LEDGER_SYNC"
    assert json.loads(outputs)["version"] == "4.10"


# ---------------------------------------------------------- v4.11 (drift) ---

def test_v411_new_decision_and_level_moves(reg: Path, tmp_path: Path) -> None:
    rep = run_ledger_sync(reg, file=_v411(tmp_path), drafts_dir=tmp_path / "drafts")
    assert [d.d_no for d in rep.new_decisions] == [71]
    assert rep.new_decisions[0].decided_on == "2026-09-27"
    assert rep.register_ahead == []
    moves = {(c.symbol, c.kind): (c.register_level, c.ledger_level) for c in rep.trigger_changes}
    assert set(moves) == {("NTPC", "BUY"), ("POLYCAB", "ALERT")}
    assert str(moves[("NTPC", "BUY")][1]) == "400"


def test_v411_review_items_never_drafted(reg: Path, tmp_path: Path) -> None:
    rep = run_ledger_sync(reg, file=_v411(tmp_path), drafts_dir=tmp_path / "drafts")
    review = {r.ledger_name: r for r in rep.trigger_review}
    assert set(review["Tata Motors"].candidates) == {"TATAMOTORS", "TMCV"}
    assert review["Hindalco"].symbol == "HINDALCO"   # in register, but no trigger row
    assert "Zensar" in {u.ledger_name for u in rep.unknown_names}
    assert rep.draft_path is not None
    sql = rep.draft_path.read_text()
    assert "Zensar" not in sql and "TATAMOTORS" not in sql and "HINDALCO" not in sql


def test_v411_cell_seat_differences(reg: Path, tmp_path: Path) -> None:
    rep = run_ledger_sync(reg, file=_v411(tmp_path), drafts_dir=tmp_path / "drafts")
    diffs = {(c.symbol, c.ledger_state, c.register_add) for c in rep.cell_diffs}
    assert diffs == {("M&M", "NOT_ADD", True), ("TATAPOWER", "ADD", False)}
    assert "M&M" not in rep.draft_path.read_text()  # type: ignore[union-attr]


def test_draft_header_path_and_it_applies_cleanly(reg: Path, tmp_path: Path) -> None:
    rep = run_ledger_sync(reg, file=_v411(tmp_path), drafts_dir=tmp_path / "drafts")
    assert rep.draft_path == tmp_path / "drafts" / "ledger_4.11.sql"
    sql = rep.draft_path.read_text()
    assert sql.startswith("-- DRAFT — review before applying")
    assert "DR REDDY''S EXIT DONE" in sql              # quotes escaped
    # the run itself changed nothing but the session log
    con = sqlite3.connect(reg)
    assert con.execute("SELECT level FROM triggers WHERE symbol='NTPC' AND kind='BUY'"
                       ).fetchone()[0] == 407
    assert con.execute("SELECT COUNT(*) FROM decisions WHERE d_no=71").fetchone()[0] == 0
    # applying the draft (Praveen's yes) lands exactly the drafted items
    con.executescript(sql)
    assert con.execute("SELECT level FROM triggers WHERE symbol='NTPC' AND kind='BUY'"
                       ).fetchone()[0] == 400
    assert con.execute("SELECT level FROM triggers WHERE symbol='POLYCAB' AND kind='ALERT'"
                       ).fetchone()[0] == 3800
    assert con.execute("SELECT decided_on FROM decisions WHERE d_no=71").fetchone()[0] == \
        "2026-09-27"
    con.close()


# ------------------------------------------------------------ finder / CLI ---

def test_folder_picks_newest(reg: Path, tmp_path: Path) -> None:
    (tmp_path / V410.name).write_text(V410.read_text())
    _v411(tmp_path)
    rep = run_ledger_sync(reg, folder=tmp_path, drafts_dir=tmp_path / "drafts")
    assert rep.version == "4.11"


def test_no_ledger_fails_closed_and_still_logs(reg: Path, tmp_path: Path) -> None:
    before = len(_sessions(reg))
    rep = run_ledger_sync(reg, folder=tmp_path / "empty", drafts_dir=tmp_path / "drafts")
    assert rep.error is not None and rep.draft_path is None
    assert len(_sessions(reg)) == before + 1
    assert "NO ACTION" in format_report(rep)


def test_works_before_migration_011(scratch_db: Path, tmp_path: Path) -> None:
    """Without the alias table SBI/EIL are unknown names — reported, never guessed."""
    rep = run_ledger_sync(scratch_db, file=V410, drafts_dir=tmp_path)
    assert {"SBI", "EIL"} <= {u.ledger_name for u in rep.unknown_names}
    assert rep.trigger_changes == []


def test_report_is_plain_language(reg: Path, tmp_path: Path) -> None:
    rep = run_ledger_sync(reg, file=_v411(tmp_path), drafts_dir=tmp_path / "drafts")
    text = format_report(rep)
    assert "D71" in text and "NTPC" in text and "407" in text and "400" in text
    assert "Tata Motors" in text and "Zensar" in text
    assert "DRAFT" in text and "nothing was applied" in text.lower()


def test_cli(reg: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["--db", str(reg), "--file", str(_v411(tmp_path)),
               "--drafts-dir", str(tmp_path / "d")])
    assert rc == 0
    assert "D71" in capsys.readouterr().out
    assert (tmp_path / "d" / "ledger_4.11.sql").exists()
    assert main(["--db", str(reg), "--folder", str(tmp_path / "none"),
                 "--drafts-dir", str(tmp_path / "d")]) == 1


def test_migration_011_survives_seed_build_style(tmp_path: Path) -> None:
    """db/seed_build.py runs schema.sql, then migrations >= 007 with CREATE TABLE
    stripped; drafts/ is a sub-folder and must never be picked up by its glob."""
    root = Path(__file__).parent.parent / "db"
    con = sqlite3.connect(tmp_path / "s.db")
    con.executescript((root / "schema.sql").read_text())
    con.executescript(re.sub(r"CREATE TABLE \w+ \(.*?\);", "", MIG.read_text(),
                             flags=re.DOTALL))
    assert con.execute("SELECT symbol FROM ledger_aliases WHERE alias='sbi'"
                       ).fetchone()[0] == "SBIN"
    con.close()
    assert all(p.parent == root / "migrations"
               for p in (root / "migrations").glob("*.sql"))


# ------------------------------------------------- review fixes (fix/ledger-sync) ---

def _variant(folder: Path, *pairs: tuple[str, str]) -> Path:
    """A v4.10 copy with text replacements (each `old` must be present)."""
    t = V410.read_text()
    for old, new in pairs:
        assert old in t, old
        t = t.replace(old, new)
    p = folder / V410.name
    p.write_text(t)
    return p


def test_conflicting_ledger_levels_halt_not_drafted(reg: Path, tmp_path: Path) -> None:
    """E6: the same register trigger row read at two ledger levels -> review, no draft."""
    led = _variant(tmp_path, ("· NTPC 407 ·", "· NTPC 407 · NTPC 400 ·"))
    rep = run_ledger_sync(reg, file=led, drafts_dir=tmp_path / "drafts")
    assert all(c.symbol != "NTPC" for c in rep.trigger_changes)
    assert all(c.symbol != "NTPC" for c in rep.compared)
    conflict = [r for r in rep.trigger_review if r.symbol == "NTPC"]
    assert [r.reason for r in conflict] == ["LEDGER_CONFLICT"]
    assert rep.draft_path is None
    assert "NTPC" in format_report(rep)


def test_repeated_equal_ledger_level_compares_once(reg: Path, tmp_path: Path) -> None:
    led = _variant(tmp_path, ("· NTPC 407 ·", "· NTPC 407 · NTPC 407 ·"))
    rep = run_ledger_sync(reg, file=led, drafts_dir=tmp_path / "drafts")
    assert [c.symbol for c in rep.compared].count("NTPC") == 1
    assert all(r.symbol != "NTPC" for r in rep.trigger_review)


def test_register_row_newer_than_ledger_is_not_reverted(reg: Path, tmp_path: Path) -> None:
    """E3: a register level set after the ledger date is never drafted back to the
    older ledger level — it goes to review instead."""
    con = sqlite3.connect(reg)
    con.execute("UPDATE triggers SET set_on='2026-09-27' WHERE symbol='NTPC' AND kind='BUY'")
    con.commit()
    con.close()
    led = _variant(tmp_path, ("· NTPC 407 ·", "· NTPC 400 ·"))
    rep = run_ledger_sync(reg, file=led, drafts_dir=tmp_path / "drafts")
    assert all(c.symbol != "NTPC" for c in rep.trigger_changes)
    assert [r.reason for r in rep.trigger_review if r.symbol == "NTPC"] == ["REGISTER_NEWER"]
    assert rep.draft_path is None


def test_declared_but_unread_decisions_are_flagged(reg: Path, tmp_path: Path) -> None:
    """A D-number inside the ledger's declared range that the parser could not read is
    shown as unread — never reported as 'register ahead', never 'in step'."""
    led = _variant(tmp_path, ("· D48 WIPRO", "· X48 WIPRO"))
    rep = run_ledger_sync(reg, file=led, drafts_dir=tmp_path / "drafts")
    assert rep.declared_unread == [48]
    assert 48 not in rep.register_ahead
    text = format_report(rep)
    assert "in step" not in text
    assert "D48" in text


def test_explicit_symbol_not_in_register_is_unknown(reg: Path, tmp_path: Path) -> None:
    led = _variant(tmp_path, ("★ R SYSTEMS (RSYSTEMS)", "★ R SYSTEMS (RSYSX)"))
    rep = run_ledger_sync(reg, file=led, drafts_dir=tmp_path / "drafts")
    assert "R SYSTEMS" in {u.ledger_name for u in rep.unknown_names}
    assert all(r.symbol != "RSYSX" for r in rep.trigger_review)


def test_session_row_carries_every_unused_item(reg: Path, tmp_path: Path) -> None:
    """E8: the session row holds the same review / unread lists the report prints."""
    rep = run_ledger_sync(reg, file=_v411(tmp_path), drafts_dir=tmp_path / "drafts")
    _u, outputs, drops = _sessions(reg)[-1]
    out = json.loads(outputs)
    assert out["unparsed"] == rep.unparsed
    assert out["unmatched_mentions"] == rep.unmatched_mentions
    assert out["cell_unclear"] == rep.cell_unclear
    assert out["declared_unread"] == rep.declared_unread
    reasons = {d["reason"] for d in json.loads(drops)}
    assert {"NOT_IN_REGISTER", "AMBIGUOUS_NAME", "NO_REGISTER_TRIGGER"} <= reasons


def test_unreadable_file_fails_closed_and_logs(reg: Path, tmp_path: Path,
                                               monkeypatch: pytest.MonkeyPatch) -> None:
    import usecases.ledger_sync as uc

    def boom(_p: object) -> object:
        raise OSError("permission denied")

    monkeypatch.setattr(uc, "parse_ledger", boom)
    before = len(_sessions(reg))
    rep = run_ledger_sync(reg, file=V410, drafts_dir=tmp_path / "drafts")
    assert rep.error is not None and "permission denied" in rep.error
    assert rep.draft_path is None
    assert len(_sessions(reg)) == before + 1
    assert format_report(rep).splitlines()[1].startswith("NO ACTION")
