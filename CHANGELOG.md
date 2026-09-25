# Changelog

All notable changes to tiffin-coffee-app. Conventional commits; one concern per PR.

## [Unreleased] — branch `feat/uc2-plate-engine`

### 2026-09-25 — Chambal: peak-cycle overlay vs register ADD is an E6

Spec: tiffin-coffee v6 §overlays row 3 ("cyclical AT PEAK MARGINS") · osep v7 E6 ·
ledger v4.9 D59/D61 (Chambal 10sh starter ≤415, tranche-2 gated).

**fix (engine/plate.py)** — `flag_cyclical` alone no longer silently drops a name the
register marks ADD. New `E6_PEAK_CYCLE_CONFLICT`: surfaced as a near-miss and in the
advisory E6 list; the engine takes no action. Cyclicals without an ADD status still drop
`PEAK_CYCLE`. Golden 20-Sep: CHAMBLFERT now reports the conflict instead of PEAK_CYCLE.

Register check (25-Sep): Drive ledger v4.9 §7 trigger board == DB (12-Sep D54 levels).
The 20-Sep chat report's levels (Wipro ~165, HCL ~1200, Muthoot ~2600) were unsourced;
the register stands (D56).

### 2026-09-22 — UC2.1 holdings sync (CSV path) — the register is real

Spec: sync-holdings skill steps 2–5, CLAUDE.md §3, pattaz-book §4.

**feat (tools/csv_import.py)** — parse the household CSV (Kite-P / Int-P / Int-V in one
file) into account rows; tolerant of the older export's P&L columns; refuses a row whose
Total Qty disagrees with the account sum; `as_of` from the filename date.
**feat (usecases/sync_holdings.py)** — `run_sync_holdings_csv`: imports the snapshot,
records exits (absent pairs → qty 0), prints the household view on prices fetched this
run: qty per account, live weight, cap breaches (20%/name, 40%/sector, 25% PSU),
P-board tier, unpriced names. Writes a `UC2_1_SYNC_HOLDINGS` session.
**store** — `load_holdings()` now returns the newest row per (account, symbol); history
via `load_holdings_history()`; `insert_holdings`, `held_pairs`.
**db** — `db/holdings/*.csv` snapshots are imported by the seed (oldest first), so CI
rebuilds the same DB. First snapshot: `household_equity_21sep2026.csv` (81 names,
₹16.38L reported; ₹14.76L priceable — 19 names not in the register / no ticker).
**fix (engine/plate.py)** — build path: a name at the low, owned, gate-passing but blocked
only by cell cap or hold-only now surfaces as `E6_CAPS_OFF_CONFLICT` (Wipro 10-Sep
precedent, pattaz-book §12b) instead of a plain `CELL_FULL`.
**fix (usecases/plate.py)** — WARN when held names cannot be priced (equity understated,
weights conservative). With real holdings the 22-Sep plate is no longer BLOCK-flagged.

### 2026-09-21 — plate audit fixes (fail closed until the register is real)

Spec: tiffin-coffee v5/v6 §first-bite, §overlays, §caps-off · pattaz-book §4, §5, §12b ·
osep v7 E2/E3/E4/E6/E8/E9 · CLAUDE.md §3.

**fix (engine/plate.py)**
- Overlay #5 cell cap no longer blocks a name that already holds an ADD seat
  (`CellInfo.active_adds`). 20-Sep audit: INFY, TCS, NTPC, POWERGRID, MUTHOOT were
  dropped by their own seats.
- `FASTING_NO_FIRST_BITE` split into `NO_TRIGGER` / `NOT_ELIGIBLE` /
  `FIRST_BITE_FAILED`; every `PlateDrop` now carries `what_would_change` (E8) and the
  first-bite drop names each failing condition (a)/(c)/(d) with the gate detail.
- `HOLDINGS_STALE`: a book-owned name with no holdings row and no book P-mult is
  dropped, never guessed (CLAUDE.md §3).
- `NO_ADD_HOLD_ONLY`: hold-only / museum names (`flag_no_add`) cannot build via H;
  a first bite at the low is still allowed ("no-add-beyond-first-bite").
- `E6_CAPS_OFF_CONFLICT`: a first bite that passes every quality gate but is blocked
  only by the cell cap or P=0 is surfaced, not decided (pattaz-book §12b unresolved).
- P-tier from `names.p_mult_book` (pattaz-book §4 roster) when set; `PlateEntry`
  now carries `price` and `p_tier`.
- Quality overlays and the cell overlay are separate functions; quality is never waived.

**fix (usecases/plate.py)**
- `PlateConfig` thresholds, clamps and caps read from the `policy` table (E2).
- Triggers without a `basis_eps_date` are not armed (E3).
- Advisory flags: `BLOCK` on stale holdings (plate is advisory only), `WARN` on
  non-live GoI yield, unclassified names (E4), missing fundamentals, E6 conflicts.
- Session JSON restores per-name gate details and adds advisory flags and
  what-would-change per drop.
- Removed the hard-coded `7.04` emergency yield; no yield → gates fail closed (E9).
- Report-style output: LTP, amount, mode, H, L, band, P-tier, order type; near-miss
  table with "what would change it"; bulk exclusions by rule; guardrails checklist.

**feat (tools/fundamentals.py)**
- ROE derived as EPS/BV when yfinance omits `returnOnEquity` (most NSE names);
  stamped `(roe derived eps/bv)`.

**db (migration 004)**
- `names.p_mult_book` (pattaz-book §4 as-of 06-Sep) and `names.flag_no_add`
  (§5/§6 museum / hold-only: ITC, WIPRO, HCLTECH, HEROMOTOCO, BAJAJ-AUTO, HAL, BEL).
- Policy rows `first_bite_l_max=2`, `first_bite_h_mult_floor=0.25`, `first_bite_qty_max=5`.

**test**
- Golden days: 10-Sep-2026 (HDFC Bank lender gate → qty 0) and 20-Sep-2026
  (audit reconciliation: 7 seat-holders plate; ITC/WIPRO/HCL/HDFC/RELIANCE refused
  for the named reasons). 237 tests, no network.

### 2026-09-20 — UC4 valuation gate engine
- `engine/valuation_gate.py`: fair P/E = 1/GoI yield, justified P/B = (ROE−g)/(r−g),
  sector dispatch (LENDER = P/B only; CYCLICAL, NON_EARNING, INDEX_ETF = never).
- `tools/fundamentals.py`, `store` fundamentals audit rows, GoI yield resolution
  (override → live → policy fallback).
- Migration 003: NTPC conviction override, four missing names, ticker fixes.

### 2026-09-19 — UC2 plate engine, UC1 morning board, seed v4.9
