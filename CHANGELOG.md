# Changelog

All notable changes to tiffin-coffee-app. Conventional commits; one concern per PR.

## [Unreleased] — branch `feat/uc2-plate-engine`

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
