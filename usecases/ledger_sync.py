"""usecases/ledger_sync.py — UC6: is the register behind the Drive ledger?

Why: on 26-Sep the register missed D65-D70 because they lived only in the other
session's ledger. Ledger D66: "§7 of this ledger is authoritative"; ledger §1 / D56:
the register wins until a change is explicitly applied. So this use case only
REPORTS and DRAFTS — it never writes the register (sessions excepted, E8).

Flow: newest local ledger export (tools/ledger_file, POINTER RULE) → diff against the
register (decisions, triggers, names, cells) → plain-language report → a DRAFT SQL file
(db/migrations/drafts/ledger_<version>.sql) holding only the unambiguous items
(new decisions; trigger level changes) → one append-only UC6_LEDGER_SYNC session row.
Ambiguous names, missing trigger rows and cell-seat differences are "needs review"
(E6: never pick silently).

CLI:  python -m usecases.ledger_sync [--folder PATH] [--file PATH] [--db PATH]
"""
from __future__ import annotations

import argparse
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from store.repo import CellRow, NameRow, PattazRepo, TriggerRow
from tools.ledger_file import (
    CellSeat,
    LedgerDecision,
    LedgerTrigger,
    ParsedLedger,
    default_ledger_folder,
    find_newest_ledger,
    parse_ledger,
)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "db" / "pattaz.db"
DEFAULT_DRAFTS = ROOT / "db" / "migrations" / "drafts"
USECASE = "UC6_LEDGER_SYNC"
DRAFT_HEADER = "-- DRAFT — review before applying"
_LEVEL_KINDS = ("BUY", "CRASH_SHELF", "NEXT_BUY")
_RULES = ["LEDGER_POINTER_RULE_NEWEST", "D66_LEDGER_TRIGGERS_AUTHORITATIVE",
          "D56_REGISTER_WINS_UNTIL_APPLIED", "DRAFT_NEVER_AUTO_APPLIED"]


# ------------------------------------------------------------------ models ---

@dataclass(frozen=True)
class Resolution:
    """symbol set when exactly one register name matches; candidates when several."""

    symbol: str | None
    candidates: tuple[str, ...] = ()


@dataclass(frozen=True)
class TriggerCompare:
    ledger_name: str
    symbol: str
    kind: str
    register_level: Decimal
    ledger_level: Decimal
    register_active: bool
    note: str


@dataclass(frozen=True)
class ReviewItem:
    ledger_name: str
    reason: str
    symbol: str | None = None
    candidates: tuple[str, ...] = ()
    detail: str = ""


@dataclass(frozen=True)
class CellDiff:
    symbol: str
    ledger_cell: str
    ledger_state: str       # ADD | NOT_ADD
    register_add: bool
    register_cell: str | None
    text: str


@dataclass
class SyncReport:
    run_id: str
    ran_at: str
    ledger_file: str | None = None
    version: str | None = None
    ledger_date: str | None = None
    declared_max_d: int | None = None
    error: str | None = None
    new_decisions: list[LedgerDecision] = field(default_factory=list)
    new_index_only: list[int] = field(default_factory=list)
    register_ahead: list[int] = field(default_factory=list)
    compared: list[TriggerCompare] = field(default_factory=list)
    trigger_changes: list[TriggerCompare] = field(default_factory=list)
    trigger_review: list[ReviewItem] = field(default_factory=list)
    unknown_names: list[ReviewItem] = field(default_factory=list)
    cell_diffs: list[CellDiff] = field(default_factory=list)
    cell_unclear: list[str] = field(default_factory=list)
    unmatched_mentions: list[str] = field(default_factory=list)
    unparsed: list[str] = field(default_factory=list)
    draft_path: Path | None = None


# -------------------------------------------------------- name resolution ---

class NameResolver:
    """Ledger name → register symbol via names.symbol, names.name, ledger_aliases
    (migration 011), then a whole-word prefix of names.name. Never fuzzy."""

    def __init__(self, names: list[NameRow], aliases: dict[str, str]) -> None:
        self._exact: dict[str, set[str]] = {}
        for n in names:
            self._exact.setdefault(n.symbol.lower(), set()).add(n.symbol)
            self._exact.setdefault(n.name.lower(), set()).add(n.symbol)
        for alias, sym in aliases.items():
            self._exact.setdefault(alias.lower(), set()).add(sym)
        self._names = [(n.name.lower(), n.symbol) for n in names]

    def lookup(self, text: str) -> set[str]:
        k = text.lower().strip(" .,;:~")
        if not k:
            return set()
        if k in self._exact:
            return set(self._exact[k])
        if len(k) < 2:
            return set()
        return {s for nm, s in self._names if nm.startswith(k + " ")}

    def resolve(self, text: str) -> Resolution:
        """The whole text must name one register row (used for §7 board names)."""
        return _to_resolution(self.lookup(text))

    def resolve_in(self, text: str) -> Resolution:
        """Longest word-span that names a register row (used for annotated §5 seats and
        §7 status mentions such as 'Coal India EXIT pending')."""
        tokens = text.split()
        for size in range(len(tokens), 0, -1):
            hits: set[str] = set()
            for start in range(len(tokens) - size + 1):
                hits |= self.lookup(" ".join(tokens[start:start + size]))
            if hits:
                return _to_resolution(hits)
        return Resolution(None)


def _to_resolution(hits: set[str]) -> Resolution:
    if len(hits) == 1:
        return Resolution(next(iter(hits)))
    return Resolution(None, tuple(sorted(hits)))


# ------------------------------------------------------------------- diffs ---

def diff_decisions(led: ParsedLedger, register: set[int]
                   ) -> tuple[list[LedgerDecision], list[int], list[int]]:
    """(new titled decisions, new index-only numbers, register numbers the ledger lacks)."""
    seen: dict[int, LedgerDecision] = {}
    for d in led.decisions:
        if d.d_no not in seen or (seen[d.d_no].title is None and d.title is not None):
            seen[d.d_no] = d
    new = [seen[k] for k in sorted(seen) if k not in register and seen[k].title]
    new_idx = [k for k in sorted(seen) if k not in register and not seen[k].title]
    ahead = sorted(register - set(seen))
    return new, new_idx, ahead


def _register_row(t: LedgerTrigger, rows: list[TriggerRow]) -> list[TriggerRow]:
    kinds = ("ALERT",) if t.kind == "ALERT" else _LEVEL_KINDS
    return [r for r in rows if r.kind in kinds]


def diff_triggers(led: ParsedLedger, resolver: NameResolver, triggers: list[TriggerRow]
                  ) -> tuple[list[TriggerCompare], list[ReviewItem], list[ReviewItem]]:
    """(compared rows, needs-review items, names not in the register) for §7 levels."""
    by_sym: dict[str, list[TriggerRow]] = {}
    for r in triggers:
        by_sym.setdefault(r.symbol, []).append(r)
    compared: list[TriggerCompare] = []
    review: list[ReviewItem] = []
    unknown: list[ReviewItem] = []
    for t in led.triggers:
        res = Resolution(t.symbol_hint) if t.symbol_hint else resolver.resolve(t.name)
        detail = f"ledger {t.kind.lower()} {t.level.value}; {t.note}".strip("; ")
        if res.symbol is None and not res.candidates:
            unknown.append(ReviewItem(t.name, "NOT_IN_REGISTER", detail=detail))
            continue
        if res.symbol is None:
            review.append(ReviewItem(t.name, "AMBIGUOUS_NAME", candidates=res.candidates,
                                     detail=detail))
            continue
        rows = _register_row(t, by_sym.get(res.symbol, []))
        if len(rows) != 1:
            why = "NO_REGISTER_TRIGGER" if not rows else "SEVERAL_REGISTER_TRIGGERS"
            review.append(ReviewItem(t.name, why, symbol=res.symbol,
                                     candidates=tuple(r.kind for r in rows), detail=detail))
            continue
        r = rows[0]
        compared.append(TriggerCompare(t.name, res.symbol, r.kind, r.level, t.level.value,
                                       r.active, t.note))
    return compared, review, unknown


def diff_cells(seats: list[CellSeat], resolver: NameResolver, cells: list[CellRow],
               names: dict[str, NameRow]) -> tuple[list[CellDiff], list[str], list[str]]:
    """(seat differences, unclear seat names, unmatched seat names) — §5 vs cells."""
    adds = {s.strip() for c in cells for s in (c.active_adds or "").split(",") if s.strip()}
    diffs: list[CellDiff] = []
    unclear: list[str] = []
    unmatched: list[str] = []
    for seat in seats:
        for piece in seat.name.split("/"):
            res = resolver.resolve_in(piece)
            if res.symbol is None:
                unmatched.append(f"§5 {seat.cell_label}: {piece.strip()}")
                continue
            if seat.state == "UNCLEAR":
                unclear.append(res.symbol)
                continue
            is_add = res.symbol in adds
            if (seat.state == "ADD") != is_add:
                n = names.get(res.symbol)
                diffs.append(CellDiff(res.symbol, seat.cell_label, seat.state, is_add,
                                      n.cell if n else None, seat.text))
    return diffs, unclear, unmatched


def unmatched_mentions(led: ParsedLedger, resolver: NameResolver) -> list[str]:
    return [f"{m.segment}: {m.name}" for m in led.mentions
            if resolver.resolve_in(m.name).symbol is None]


# ------------------------------------------------------------------- draft ---

def _q(v: str | None) -> str:
    return "NULL" if v is None else "'" + v.replace("'", "''") + "'"


def draft_sql(rep: SyncReport) -> str:
    """The DRAFT file: only new decisions and trigger level changes. Never applied here."""
    L = [DRAFT_HEADER,
         f"-- UC6 ledger sync {rep.run_id} at {rep.ran_at}",
         f"-- Source: {rep.ledger_file} (ledger v{rep.version}, {rep.ledger_date})",
         "-- NEVER auto-applied. Apply only after Praveen says yes; then promote it to a",
         "-- numbered migration in db/migrations/ (seed history is never edited).",
         "-- Covers only unambiguous items; everything else is in the UC6 report.", ""]
    if rep.new_decisions:
        L.append("-- new decisions (status left at the column default, CLOSED — edit if OPEN)")
    # S608: this builds review TEXT for a human, never executed here; values go through _q
    for d in rep.new_decisions:
        L.append("INSERT INTO decisions (d_no, decided_on, title, detail) VALUES "  # noqa: S608
                 f"({d.d_no}, {_q(d.decided_on)}, {_q(d.title)}, {_q(d.detail)});")
    if rep.trigger_changes:
        L += ["", "-- trigger level changes (basis_eps_date / set_on / active NOT touched —"
              " confirm the basis before arming)"]
    for c in rep.trigger_changes:
        note = f"ledger v{rep.version} §7: {c.register_level} -> {c.ledger_level}"
        inactive = "" if c.register_active else "  -- stays inactive (NOT ARMABLE)"
        L.append(f"UPDATE triggers SET level = {c.ledger_level}, notes = "  # noqa: S608
                 f"COALESCE(notes || ' | ', '') || {_q(note)} "
                 f"WHERE symbol = {_q(c.symbol)} AND kind = {_q(c.kind)};{inactive}")
    return "\n".join(L) + "\n"


def write_draft(rep: SyncReport, drafts_dir: Path) -> Path | None:
    if not rep.new_decisions and not rep.trigger_changes:
        return None
    drafts_dir.mkdir(parents=True, exist_ok=True)
    path = drafts_dir / f"ledger_{rep.version}.sql"
    path.write_text(draft_sql(rep), encoding="utf-8")
    return path


# ---------------------------------------------------------------- run ---

def _pick_file(folder: str | Path | None, file: str | Path | None) -> Path | None:
    if file is not None:
        p = Path(file)
        return p if p.is_file() else None
    return find_newest_ledger(folder if folder is not None else default_ledger_folder(ROOT))


def _diff(rep: SyncReport, led: ParsedLedger, repo: PattazRepo) -> None:
    names = repo.load_names()
    resolver = NameResolver(names, repo.load_ledger_aliases())
    register = {d.d_no for d in repo.load_decisions()}
    rep.new_decisions, rep.new_index_only, rep.register_ahead = diff_decisions(led, register)
    rep.compared, rep.trigger_review, rep.unknown_names = diff_triggers(
        led, resolver, repo.load_triggers())
    rep.trigger_changes = [c for c in rep.compared if c.register_level != c.ledger_level]
    rep.cell_diffs, rep.cell_unclear, cell_unmatched = diff_cells(
        led.cell_seats, resolver, repo.load_cells(), {n.symbol: n for n in names})
    rep.unmatched_mentions = cell_unmatched + unmatched_mentions(led, resolver)
    rep.unparsed = list(led.unparsed)


def run_ledger_sync(db_path: str | Path, folder: str | Path | None = None,
                    file: str | Path | None = None,
                    drafts_dir: str | Path = DEFAULT_DRAFTS) -> SyncReport:
    """Diff the newest ledger export against the register. Writes only the draft file
    and one session row; the register itself is never changed (D56)."""
    rep = SyncReport(run_id=f"UC6_{uuid.uuid4().hex[:12]}",
                     ran_at=datetime.now(UTC).isoformat(timespec="seconds"))
    path = _pick_file(folder, file)
    with PattazRepo(db_path) as repo:
        if path is None:
            rep.error = f"no ledger file found ({file or folder or 'default folder'})"
        else:
            try:
                led = parse_ledger(path)
            except ValueError as exc:
                rep.error = str(exc)
            else:
                rep.ledger_file, rep.version = str(path), led.version.value
                rep.ledger_date, rep.declared_max_d = led.ledger_date, led.declared_max_d
                _diff(rep, led, repo)
                rep.draft_path = write_draft(rep, Path(drafts_dir))
        _record(repo, rep)
    return rep


def _record(repo: PattazRepo, rep: SyncReport) -> None:
    """One append-only session row (E8), also when nothing was found."""
    outputs: dict[str, object] = {
        "version": rep.version, "error": rep.error,
        "new_decisions": [d.d_no for d in rep.new_decisions],
        "new_index_only": rep.new_index_only, "register_ahead": rep.register_ahead,
        "trigger_changes": [
            {"symbol": c.symbol, "kind": c.kind, "register": str(c.register_level),
             "ledger": str(c.ledger_level)} for c in rep.trigger_changes],
        "cell_diffs": [asdict(c) for c in rep.cell_diffs],
        "compared": len(rep.compared), "unparsed": len(rep.unparsed),
        "draft_path": str(rep.draft_path) if rep.draft_path else None,
    }
    drops: list[dict[str, object]] = [
        {"symbol": r.symbol or r.ledger_name, "reason": r.reason,
         "detail": f"{r.detail} {list(r.candidates) if r.candidates else ''}".strip()}
        for r in rep.trigger_review + rep.unknown_names]
    repo.append_session(
        rep.run_id, rep.ran_at, USECASE,
        {"ledger_file": rep.ledger_file, "version": rep.version,
         "ledger_date": rep.ledger_date, "declared_max_d": rep.declared_max_d},
        outputs, drops, _RULES)


# ------------------------------------------------------------------ report ---

def _verdict(rep: SyncReport) -> str:
    if rep.error:
        return f"NO ACTION — {rep.error}."
    n_new, n_lvl = len(rep.new_decisions), len(rep.trigger_changes)
    if not n_new and not n_lvl:
        return (f"The register is in step with ledger v{rep.version} on decisions and "
                "trigger levels. Nothing to draft.")
    return (f"The register is BEHIND ledger v{rep.version}: {n_new} new decision(s), "
            f"{n_lvl} trigger level change(s). A DRAFT is ready for review.")


def format_report(rep: SyncReport) -> str:
    """Plain language, verdict first, every review item explained (CLAUDE.md §8)."""
    L = [f"UC6 LEDGER SYNC — {rep.ran_at} ({rep.run_id})", _verdict(rep)]
    if rep.error:
        return "\n".join(L)
    L.append(f"Ledger: {rep.ledger_file} (v{rep.version}, dated {rep.ledger_date}; "
             f"its register runs D1-D{rep.declared_max_d})")
    if rep.new_decisions:
        L += ["", "New decisions (in the ledger, not in the register):"]
        L += [f"  D{d.d_no} ({d.decided_on or 'undated'}) {d.title}" for d in rep.new_decisions]
    if rep.new_index_only:
        L.append(f"Index-only numbers missing from the register: {rep.new_index_only}")
    if rep.register_ahead:
        L.append("Register has decisions the ledger does not list yet: "
                 + ", ".join(f"D{k}" for k in rep.register_ahead)
                 + " (the next ledger release should carry them).")
    if rep.trigger_changes:
        L += ["", "Trigger levels that differ (register -> ledger):"]
        L += [f"  {c.symbol:12s} {c.kind:11s} {c.register_level} -> {c.ledger_level}"
              + ("" if c.register_active else "  (register row is NOT ARMABLE)")
              for c in rep.trigger_changes]
    L.append(f"Trigger rows compared and equal: "
             f"{len(rep.compared) - len(rep.trigger_changes)}")
    if rep.trigger_review:
        L += ["", "Needs your review (not drafted):"]
        L += [f"  {r.ledger_name}: {_why(r)} — {r.detail}" for r in rep.trigger_review]
    if rep.unknown_names:
        L += ["", "Board names not in the register (not drafted — add via OSEP if wanted):"]
        L += [f"  {r.ledger_name} — {r.detail}" for r in rep.unknown_names]
    if rep.cell_diffs:
        L += ["", "Cell seats that differ (not drafted — a seat change is your call):"]
        L += [f"  {c.symbol}: ledger says {'ADD' if c.ledger_state == 'ADD' else 'not an add'}"
              f" ({c.ledger_cell}: {c.text}); register {'has' if c.register_add else 'has no'}"
              f" add seat (cell {c.register_cell})" for c in rep.cell_diffs]
    if rep.unmatched_mentions or rep.unparsed:
        L += ["", f"Could not read {len(rep.unmatched_mentions)} name mention(s) and "
              f"{len(rep.unparsed)} line(s) — shown, never guessed:"]
        L += [f"  ? {u}" for u in rep.unmatched_mentions + rep.unparsed]
    L.append("")
    if rep.draft_path:
        L.append(f"DRAFT written: {rep.draft_path} — nothing was applied. "
                 "Say yes to apply it; it becomes a numbered migration.")
    else:
        L.append("No draft written — nothing was applied.")
    return "\n".join(L)


def _why(r: ReviewItem) -> str:
    if r.reason == "AMBIGUOUS_NAME":
        return f"name matches several register rows {list(r.candidates)}"
    if r.reason == "NO_REGISTER_TRIGGER":
        return f"{r.symbol} is in the register but has no matching trigger row"
    return f"{r.symbol} has several trigger rows {list(r.candidates)}"


# --------------------------------------------------------------------- CLI ---

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m usecases.ledger_sync")
    ap.add_argument("--folder", help="folder holding PATTAZ_MASTER_LEDGER_v*.txt")
    ap.add_argument("--file", help="a specific ledger export (overrides --folder)")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--drafts-dir", default=str(DEFAULT_DRAFTS))
    args = ap.parse_args(argv)
    rep = run_ledger_sync(args.db, folder=args.folder, file=args.file,
                          drafts_dir=args.drafts_dir)
    print(format_report(rep))
    return 1 if rep.error else 0


if __name__ == "__main__":
    sys.exit(main())
