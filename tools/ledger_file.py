"""tools/ledger_file.py — read the local text export of the Drive master ledger (UC6).

Why local: CLAUDE.md §6 forbids Google Docs/Sheets calls at runtime, so the input is the
"PATTAZ_MASTER_LEDGER_v<x.y>_<date>.txt" file Praveen (or the chat session) saves next
to this repo. The ledger's own POINTER RULE ("read NEWEST") picks the file.

What is parsed (ledger v4.10 layout):
  §10 decision register — D-number, date (when written "(25-Sep)"), title, detail;
      the "D2,D4-5,...: archive" list becomes index-only entries.
  §7  trigger board     — ledger name → level (Stamped), notes such as HOLD-no-add;
      status lists (WATCH-ONLY, WITHDRAWN, HARD PASS, ...) become name mentions.
  §5  cell map          — per cell, each named seat as ADD / NOT_ADD / UNCLEAR.
The text is semi-structured prose. Anything that does not fit a known shape goes to
`unparsed` — this module never guesses (E6/E9: an unmapped line is shown, not used).
Every level carries {value, source=file name, as_of=ledger date} (E2).
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from tools.stamped import Stamped

FILE_RE = re.compile(r"^PATTAZ_MASTER_LEDGER_v(\d+)\.(\d+)_(\d{4}-\d{2}-\d{2})\.txt$")
_HEADER_RE = re.compile(r"PATTAZ MASTER LEDGER\s*[—-]+\s*v(\d+\.\d+)\s*\|\s*(\d{4}-\d{2}-\d{2})")
_SECTION_RE = re.compile(r"^§(\d+)\b")
_MONTHS = {m: i for i, m in enumerate(
    ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}

# §10 shapes
_D_DATED = re.compile(r"^D(\d+) \((\d{1,2})-([A-Za-z]{3})\) (.+)$")
_D_INDEXED = re.compile(r"^D(\d+)(?:/D(\d+))? (.+)$")
_D_ARCHIVE = re.compile(r"^(D\d+(?:-\d+)?(?:,D\d+(?:-\d+)?)*): archive\.?$")
_D_RANGE = re.compile(r"D(\d+)\s*-\s*D(\d+)")

# §7 shapes
_LABEL_RE = re.compile(
    r"(?:^|(?<=\. ))(?P<label>[A-Z][A-Z/\-]+(?: [A-Z/\-]+)*(?: \([^)]*\))?):\s")
_LEVEL_ENTRY = re.compile(
    r"^(?P<name>[A-Za-z][A-Za-z&.'\- ]*?)\s+[~≤]?(?P<level>\d[\d,]*(?:\.\d+)?)(?![\w.%,])"
    r"\s*(?P<rest>.*)$")
_EXPLICIT_SYMBOL = re.compile(
    r"^★\s*(?P<name>[A-Za-z][A-Za-z&.' ]*?) \((?P<sym>[A-Z0-9&\-]+)\).*?\bTrigger "
    r"(?P<level>\d[\d,]*(?:\.\d+)?)")
_LE_LEVEL = re.compile(r"≤\s*(\d[\d,]*(?:\.\d+)?)")
_ALERT_IN_NOTE = re.compile(r"\balert (\d[\d,]*(?:\.\d+)?)")
_BARE_LEVEL = re.compile(r"^(\d[\d,]*(?:\.\d+)?)$")
_LEVEL_SEGMENTS = ("GBN", "WIRES", "BANKS")
_ALERT_SEGMENTS = ("ALERTS",)
_STATUS_SEGMENTS = ("WATCH-ONLY", "WITHDRAWN", "HARD PASS", "HARVEST", "INCOME SLEEVE")
_IGNORED_SEGMENTS = ("ARMABILITY",)

# §5 seat state keywords (a part with none of these inherits the last part's state)
_NOT_ADD_RE = re.compile(
    r"no[- ]adds?|never-add|fails adds|\bholds?\b|museum|\btrim\b|\bexit\b|\bsold\b|legacy|"
    r"crash|one line|\bspec\b|watch|pending", re.IGNORECASE)
_ADD_RE = re.compile(r"\badds?\b", re.IGNORECASE)


@dataclass(frozen=True)
class LedgerDecision:
    """One §10 register entry. `title` is None for archive-only (index) entries."""

    d_no: int
    decided_on: str | None
    title: str | None
    detail: str | None
    index_only: bool


@dataclass(frozen=True)
class LedgerTrigger:
    """One §7 board level. kind: LEVEL (buy / crash-shelf / next-buy) or ALERT."""

    name: str
    symbol_hint: str | None
    kind: str
    level: Stamped[Decimal]
    note: str
    segment: str


@dataclass(frozen=True)
class BoardMention:
    """A name listed in a §7 status list (no level), e.g. WITHDRAWN/ZERO: GAIL."""

    name: str
    segment: str
    note: str


@dataclass(frozen=True)
class CellSeat:
    """A §5 seat: `name` is the raw text before any parenthesis (may carry a status)."""

    cell_label: str
    name: str
    state: str  # ADD | NOT_ADD | UNCLEAR
    text: str


@dataclass(frozen=True)
class ParsedLedger:
    source: str
    version: Stamped[str]
    ledger_date: str
    declared_max_d: int | None
    decisions: list[LedgerDecision] = field(default_factory=list)
    triggers: list[LedgerTrigger] = field(default_factory=list)
    mentions: list[BoardMention] = field(default_factory=list)
    cell_seats: list[CellSeat] = field(default_factory=list)
    unparsed: list[str] = field(default_factory=list)


# ------------------------------------------------------------------ finder ---

def default_ledger_folder(repo_root: Path) -> Path:
    """Default home of the ledger export: ../tiffin-coffee/investing_plans."""
    return repo_root.parent / "tiffin-coffee" / "investing_plans"


def find_newest_ledger(folder: str | Path) -> Path | None:
    """Ledger POINTER RULE: the newest version wins (numeric x.y, then date)."""
    folder = Path(folder)
    if not folder.is_dir():
        return None
    best: tuple[tuple[int, int, str], Path] | None = None
    for p in folder.iterdir():
        m = FILE_RE.match(p.name)
        if not m:
            continue
        key = (int(m.group(1)), int(m.group(2)), m.group(3))
        if best is None or key > best[0]:
            best = (key, p)
    return best[1] if best else None


# ----------------------------------------------------------------- helpers ---

def split_top(text: str, sep: str) -> list[str]:
    """Split on `sep` only outside parentheses; strip and drop empties."""
    out: list[str] = []
    depth, start, i = 0, 0, 0
    while i < len(text):
        c = text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth = max(depth - 1, 0)
        elif depth == 0 and text.startswith(sep, i):
            out.append(text[start:i])
            i += len(sep)
            start = i
            continue
        i += 1
    out.append(text[start:])
    return [s.strip() for s in out if s.strip()]


def _num(s: str) -> Decimal:
    return Decimal(s.replace(",", ""))


def _iso_from_day_month(day: str, mon: str, ledger_date: str) -> str | None:
    """'25-Sep' → ISO date in the ledger's year (previous year if after the ledger date)."""
    month = _MONTHS.get(mon.lower())
    if month is None:
        return None
    ref = dt.date.fromisoformat(ledger_date)
    try:
        d = dt.date(ref.year, month, int(day))
    except ValueError:
        return None
    if d > ref:
        d = d.replace(year=ref.year - 1)
    return d.isoformat()


def _sections(text: str) -> dict[int, list[str]]:
    """Section number → its lines (header line first)."""
    out: dict[int, list[str]] = {}
    cur: int | None = None
    for line in text.splitlines():
        m = _SECTION_RE.match(line)
        if m:
            cur = int(m.group(1))
            out[cur] = [line]
        elif line.startswith("====="):
            cur = None
        elif cur is not None and line.strip():
            out[cur].append(line.strip())
    return out


def _header(text: str, source: str) -> tuple[str, str]:
    m = _HEADER_RE.search(text)
    if m:
        return m.group(1), m.group(2)
    f = FILE_RE.match(Path(source).name)
    if f:
        return f"{f.group(1)}.{f.group(2)}", f.group(3)
    raise ValueError(f"no ledger version/date in header or file name: {source}")


# --------------------------------------------------------------------- §10 ---

def _expand_archive(spec: str) -> list[int]:
    nums: list[int] = []
    for part in spec.split(","):
        a, _, b = part.lstrip("D").partition("-")
        nums.extend(range(int(a), int(b or a) + 1))
    return nums


def _parse_decision_chunk(chunk: str) -> list[LedgerDecision] | None:
    chunk = chunk.strip().rstrip(".")
    arch = _D_ARCHIVE.match(chunk)
    if arch:
        return [LedgerDecision(n, None, None, None, True) for n in _expand_archive(arch.group(1))]
    m = _D_INDEXED.match(chunk)
    if not m:
        return None
    nums = [int(m.group(1))] + ([int(m.group(2))] if m.group(2) else [])
    return [LedgerDecision(n, None, m.group(3).strip(), None, False) for n in nums]


def parse_decisions(lines: list[str], ledger_date: str
                    ) -> tuple[int | None, list[LedgerDecision], list[str]]:
    """§10 DECISION REGISTER → (declared max D, entries, unparsed)."""
    declared = None
    if lines:
        r = _D_RANGE.search(lines[0])
        declared = int(r.group(2)) if r else None
    out: list[LedgerDecision] = []
    unparsed: list[str] = []
    for line in lines[1:]:
        m = _D_DATED.match(line)
        if m:
            title, _, detail = m.group(4).partition(" — ")
            out.append(LedgerDecision(
                int(m.group(1)), _iso_from_day_month(m.group(2), m.group(3), ledger_date),
                title.strip(), detail.strip() or None, False))
            continue
        for chunk in split_top(line, " · "):
            got = _parse_decision_chunk(chunk)
            if got is None:
                unparsed.append(f"§10: {chunk}")
            else:
                out.extend(got)
    return declared, out, unparsed


# ---------------------------------------------------------------------- §7 ---

def _segments(line: str) -> list[tuple[str | None, str]]:
    """Split a board line into (label, body) at 'LABEL:' markers (line start or after '. ')."""
    marks = list(_LABEL_RE.finditer(line))
    if not marks:
        return [(None, line)]
    segs: list[tuple[str | None, str]] = []
    if marks[0].start() > 0:
        segs.append((None, line[:marks[0].start()]))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(line)
        segs.append((m.group("label"), line[m.end():end].strip()))
    return segs


def _clean_label(label: str) -> str:
    return re.sub(r"\s*\([^)]*\)$", "", label).strip()


def _stamped(level: str, stamp: tuple[str, str]) -> Stamped[Decimal]:
    return Stamped(value=_num(level), source=stamp[0], as_of=stamp[1])


def _level_entry(chunk: str, kind: str, seg: str, stamp: tuple[str, str],
                 bare_is_alert: bool) -> list[LedgerTrigger] | None:
    """'Name 1,234 (note)' → a level; '(alert N)' — or a bare '(N)' once the segment
    has used 'alert N' (the wires-cluster column shorthand) — adds an ALERT level."""
    m = _LEVEL_ENTRY.match(chunk.rstrip("."))
    if not m:
        return None
    name, rest = m.group("name").strip(), m.group("rest").strip()
    note = rest.lstrip("→").strip()
    if note.startswith("(") and note.endswith(")"):
        note = note[1:-1].strip()
    out = [LedgerTrigger(name, None, kind, _stamped(m.group("level"), stamp), note, seg)]
    alert = _ALERT_IN_NOTE.search(rest)
    bare = _BARE_LEVEL.match(note) if bare_is_alert else None
    second = alert or bare
    if second and kind == "LEVEL":
        out.append(LedgerTrigger(name, None, "ALERT", _stamped(second.group(1), stamp),
                                 note, seg))
    return out


def _mentions(body: str, seg: str) -> list[BoardMention]:
    out: list[BoardMention] = []
    for chunk in split_top(body, " · "):
        note_m = re.search(r"\(([^)]*)\)", chunk)
        head = re.sub(r"\([^)]*\)", "", chunk).strip().rstrip(".")
        for name in head.split("/"):
            if name.strip():
                out.append(BoardMention(name.strip(), seg, note_m.group(1) if note_m else ""))
    return out


def _level_segment(label: str, seg: str, body: str, stamp: tuple[str, str]
                   ) -> tuple[list[LedgerTrigger], list[str]]:
    """One labelled level segment (GBN/NEAR, WIRES, BANKS, ALERTS, or a NAME: label)."""
    trig: list[LedgerTrigger] = []
    unparsed: list[str] = []
    kind = "ALERT" if seg.startswith(_ALERT_SEGMENTS) else "LEVEL"
    chunks = split_top(body, " · ")
    if not seg.startswith(_LEVEL_SEGMENTS + _ALERT_SEGMENTS):
        le = _LE_LEVEL.search(chunks[0]) if chunks else None
        if le is None:
            return [], [f"§7: {label}: {body}"]
        trig.append(LedgerTrigger(seg, None, "LEVEL", _stamped(le.group(1), stamp),
                                  chunks[0], seg))
        chunks = chunks[1:]
    bare_is_alert = False
    for chunk in chunks:
        got = _level_entry(chunk, kind, seg, stamp, bare_is_alert)
        if got is None:
            unparsed.append(f"§7 {seg}: {chunk}")
            continue
        bare_is_alert = bare_is_alert or bool(_ALERT_IN_NOTE.search(chunk))
        trig.extend(got)
    return trig, unparsed


def parse_board(lines: list[str], stamp: tuple[str, str]
                ) -> tuple[list[LedgerTrigger], list[BoardMention], list[str]]:
    """§7 WATCHLIST + TRIGGERS → (levels, status-list mentions, unparsed)."""
    trig: list[LedgerTrigger] = []
    ment: list[BoardMention] = []
    unparsed: list[str] = []
    for line in lines[1:]:
        ex = _EXPLICIT_SYMBOL.match(line)
        if ex:
            trig.append(LedgerTrigger(ex.group("name").strip(), ex.group("sym"), "LEVEL",
                                      _stamped(ex.group("level"), stamp), line, "EXPLICIT"))
            continue
        for label, body in _segments(line):
            if label is None:
                unparsed.append(f"§7: {body}")
                continue
            seg = _clean_label(label)
            if seg.startswith(_IGNORED_SEGMENTS):
                continue
            if seg.startswith(_STATUS_SEGMENTS):
                ment.extend(_mentions(body, seg))
                continue
            t, u = _level_segment(label, seg, body, stamp)
            trig.extend(t)
            unparsed.extend(u)
    return trig, ment, unparsed


# ---------------------------------------------------------------------- §5 ---

def _state(text: str) -> str | None:
    if _NOT_ADD_RE.search(text):
        return "NOT_ADD"
    if _ADD_RE.search(text):
        return "ADD"
    return None


def _has_name(text: str) -> bool:
    """False when the seat text is only status words (e.g. 'Jyothy = never-add')."""
    left = _ADD_RE.sub("", _NOT_ADD_RE.sub("", text))
    return bool(re.search(r"[A-Za-z&]{2}", left))


def _seats_for_item(cell: str, item: str) -> list[CellSeat]:
    parts = split_top(item, "+")
    states = [_state(p) for p in parts]
    inherited = states[-1] or "UNCLEAR"
    return [CellSeat(cell, p.split("(")[0].strip(), s or inherited, p)
            for p, s in zip(parts, states, strict=True)]


def parse_cells(lines: list[str]) -> tuple[list[CellSeat], list[str]]:
    """§5 CELL MAP → seats (ADD / NOT_ADD / UNCLEAR) and unparsed chunks."""
    seats: list[CellSeat] = []
    unparsed: list[str] = []
    for line in lines[1:]:
        for chunk in split_top(line.rstrip("."), " · "):
            label, eq, members = chunk.partition(" = ")
            if not eq:
                unparsed.append(f"§5: {chunk}")
                continue
            for semi in split_top(members, "; "):
                for item in split_top(semi, ", "):
                    for seat in _seats_for_item(label.strip(), item):
                        if _has_name(seat.name):
                            seats.append(seat)
                        else:
                            unparsed.append(f"§5 {label.strip()}: {item}")
    return seats, unparsed


# ------------------------------------------------------------------- entry ---

def parse_ledger_text(text: str, source: str) -> ParsedLedger:
    """Parse ledger text. Raises ValueError when no version/date can be found (E9)."""
    version, ledger_date = _header(text, source)
    name = Path(source).name
    stamp = (f"ledger v{version} ({name})", ledger_date)
    secs = _sections(text)
    declared, decisions, u10 = parse_decisions(secs.get(10, []), ledger_date)
    triggers, mentions, u7 = parse_board(secs.get(7, []), stamp)
    seats, u5 = parse_cells(secs.get(5, []))
    return ParsedLedger(
        source=str(source),
        version=Stamped(value=version, source=stamp[0], as_of=ledger_date),
        ledger_date=ledger_date,
        declared_max_d=declared,
        decisions=decisions, triggers=triggers, mentions=mentions, cell_seats=seats,
        unparsed=u5 + u7 + u10,
    )


def parse_ledger(path: str | Path) -> ParsedLedger:
    p = Path(path)
    return parse_ledger_text(p.read_text(encoding="utf-8"), source=str(p))
