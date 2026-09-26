---
name: ledger-sync
description: UC6 — "sync the ledger", "anything new in the ledger?", "is the register behind the ledger?". Reads the newest local text export of the PATTAZ MASTER LEDGER, diffs it against the register (decisions, triggers, names, cells) and writes a DRAFT migration for review. Never applies anything without Praveen's yes.
---
# Ledger sync (UC6)

Why: the Drive ledger and the register drift (26-Sep: D65-D70 were only in the other
session's ledger). No Google Drive calls at runtime (CLAUDE.md §6) — the input is the
local file `PATTAZ_MASTER_LEDGER_v<x.y>_<date>.txt`, by default in
`../tiffin-coffee/investing_plans/` (newest version wins — ledger POINTER RULE).

1. **Run it:** `uv run python -m usecases.ledger_sync`
   (another folder: `--folder PATH`; one exact file: `--file PATH`).
   It writes one `UC6_LEDGER_SYNC` session row and, only if something unambiguous
   differs, `db/migrations/drafts/ledger_<version>.sql` with the header
   "DRAFT — review before applying".
2. **Tell Praveen in plain words, verdict first:** "the register is in step" or "the
   register is behind by N decisions and M trigger levels". Then:
   - each new decision (D-number, date, one line);
   - each trigger level that moved (name, old → new);
   - the review list — names that match several register rows, names with no trigger
     row, board names not in the register, cell seats that differ — and say plainly
     that these were NOT drafted because they need his call;
   - the lines it could not read (shown, never guessed).
   If the register has decisions the ledger lacks (e.g. D69/D70), say the next ledger
   release should carry them.
3. **Never apply without his yes.** The draft is never auto-applied. On a clear yes,
   promote the draft to the next numbered migration in `db/migrations/` (seed history
   is never edited) and apply that. New names go through OSEP (UC4), not this draft.
4. If no ledger file is found, the answer is NO ACTION — ask Praveen to save the
   ledger export locally.
