# Changelog

All notable changes to tiffin-coffee-app. Conventional commits; one concern per PR.

## [Unreleased] — branch `integrate/four-usecases`

### 2026-09-26 — four use cases built in parallel (workflow: build → review → fix → integrate)

- **UC6 ledger sync** (`usecases/ledger_sync.py`, `tools/ledger_file.py`, skill `ledger-sync`,
  migration 011 `ledger_aliases`) — parses the newest local ledger export, diffs it against
  the register (decisions, triggers, names, cells) and writes a DRAFT migration for review
  (never applied). Conflicting ledger levels (E6), register rows newer than the ledger (E3)
  and unreadable D-numbers (E9) go to review. First live run: ledger v4.11 has D71.
- **UC2 plate extras** (migration 012) — single-deployment cap on a confirmed surplus given
  per run (over the cap → NO ACTION; cap below the BeES floor → E6 CONFLICT); HOCKEY
  detection for Nifty −5% in a week, name −10% in a day and the D37 −15% / −25% rungs
  (`tools/index_moves.py`, `engine/hockey.py`) — detection + advisory only, no reserve
  sizing; stale index data is not used (E3); two-pocket 60/40 stated, not checked. Every
  open question prints as "OPEN QUESTION for Praveen".
- **UC2.1 Kite holdings sync** (`tools/kite.py`, `run_sync_holdings_kite`) — read-only
  Zerodha holdings for ZERODHA_P; login URL + request token from Praveen, token cached for
  the day in a git-ignored file; every failure writes a NO ACTION session.
- **UC3 plate ranker** (`engine/ranker.py`, `usecases/ranker.py`, skill `plate-ranker`,
  migration 014) — legal plate variants side by side, each passing every invariant; ranking
  order is PROVISIONAL until Praveen confirms it (policy `ranker_criteria_order`).
Integration: migrations 011/012/014 applied to the register (sessions kept); 634 passed;
UC5 128 runs, 0 violations.

## UC4 OSEP (PR #13)

### 2026-09-26 — UC4 OSEP analyser

Spec: osep v7 (E-laws, §SC, §G, Stages 0-3, P3, P5, decay clock, output format);
CLAUDE.md §9 (re-underwriting is a chat job; the DB records the outcome).
- **engine/osep.py** — the verdict, stage by stage. Computed from data: promoter <26%
  kill, P4 net-selling flag, solvency (debt ex-leases, newest balance sheet), negative
  cumulative profit, loss-scales-with-volume, Stage-1 watch flags, sector valuation gate,
  trigger (fair P/E x EPS; lender justified P/B x book; none for cyclical/gold/ETF), P5,
  Stage 3, expiry (GBN 30 / GBL 90 / HARD PASS 180 days). Judgments (P1, P2, governance,
  industry, investability, Stage-1 score, thesis type, promoter exemption, sector class)
  come from chat research with a source; a missing one → INCOMPLETE, never a buy (E9).
- **tools/company_data.py** — promoter % and company-REPORTED quarterly EPS from
  Screener; debt, equity, profit, revenue, cash flow and business description from Yahoo.
- **usecases/osep.py** — `analyse` (session UC4_OSEP) · `judge` (records a judgment with
  its source) · `apply` (on Praveen's yes: append-only verdict log old → new + reason,
  bucket/expiry/thesis/trigger to the register; status stays his) · `rederive` (every
  active trigger on fresh EPS/book, no writes — the October job). Skill `osep`.
- **db migration 010** — `osep_judgments`, `osep_verdicts`, `names.thesis_type`; policy
  `decay_hard_pass_days` 180, `stage1_gate` 35, `promoter_net_sell_flag_pct` 2.
Findings on first run (26-Sep, not applied): R Systems' ledger trigger 251 uses EPS 17.7
(Screener P/E incl. minority interest); reported 4-quarter EPS is 16.27 → fair 228.59 →
GOOD BUY LATER at 235.62. `rederive` at 7.119%: most triggers move -1% to -11%.

## 2026-09-26 — ledger v4.10 + weekend prices (PR #12)

### 2026-09-26 — register catches up with ledger v4.10 + D69/D70; weekend prices fixed

**fix (tools/prices.py)** — use the last traded price (`regularMarketPrice`) stamped with
its trade time. `regularMarketPreviousClose` is the session before: on Sat 26-Sep it gave
Thursday's close (Infosys 1,014.50 vs Friday's 1,000.20).
**db (migration 009)** — from ledger v4.10 (local copy; Drive returned 403) and the 26-Sep
handoff: decisions D65-D70; R Systems added (IT add #2, trigger 251, spec <=1%); TCS
HOLD-no-add and its trigger retired; IT cell seats INFY + RSYSTEMS; NTPC and Power Grid
NO ACTION until the E6 solvency ruling (§14 0b); Petronet held for the reserve decision
(§14 1(v)); `caps_off_waivers` table with D70 (Wipro, 28-Sep only).
**feat (engine/plate.py)** — `caps_off_waived`: a register waiver for this session lifts
cell cap, hold-only and P=0 (D6/D44) — never quality, valuation, bans or event hold.
**feat (tools/csv_import.py)** — accepts the compact 25-Sep export headers; 25-Sep broker
holdings imported (incl. D67 override buys).
Monday 28-Sep preview (live, Friday closes): Infosys 3 · R Systems 6 · Wipro 5 (D70) ·
Muthoot 1 · Amara Raja 1 · SBI 1 = Rs9,844. 412 passed.

## 2026-09-26 — results-week pause (PR #11)

### 2026-09-26 — results-week pause (event hold)

tiffin-coffee v6 §procedure step 6: "earnings within 5 calendar days → hold that plate
unless Praveen opts in ('event risk, your call')".
- **engine** — a name that would be bought but has results within `event_hold_days`
  (policy, migration 008 = 5) is dropped `EVENT_HOLD`; `event_opt_in` buys it anyway.
  Invariants treat such a name on a plate as a violation.
- **data** — next results date from the results feed (after verified overrides) plus the
  dates Yahoo puts in the quote (`FundamentalsSnapshot.upcoming_results`) — no extra
  download. Unknown next date on a plated stock → WARN, not a block (companies announce
  only days ahead).
- **report** — "RESULTS WEEK" advisory; guardrail line now live.
- **UC5** — new `results_week` scenario (everyone reports in 2 days → nothing bought).
Replay on the 25-Sep recording: 5-Oct holds TCS (results 8-Oct). 408 passed.
seed_build now applies every data migration from 007 on.

## 2026-09-26 — verified facts (PR #10)

### 2026-09-26 — facts looked up online and recorded (migration 007)

Praveen 26-Sep: "find it from online and record them". Sources are in the migration.
- **Brand ownership:** ITC, Dabur, Godrej Consumer, Jyothy, Sula own their brands;
  HUL, Nestle India, Bata India do not (royalties to foreign parents) — never bought.
- **Results dates Yahoo gets wrong/stale:** M&M 30-Jul (Yahoo said 10-Sep), Engineers
  India 13-Aug, RITES 4-Aug, Paradeep 31-Jul, Texmaco 3-Aug. New table
  `results_verified` overrides the feed until 14-Oct, then fails closed until re-checked.
- **New safety check:** a "latest results" date older than 150 days is treated as
  unknown (SEBI LODR Reg 33: results within 45 days of each quarter, 60 for Q4). Policy
  `results_max_age_days`.
M&M's trigger is armed again. UC5: 0 violations.

## 2026-09-26 — brand gate + results date (PR #9)

### 2026-09-26 — FMCG brand-ownership gate; triggers disarm after new results

**1. Brand gate** — osep v7 §G FMCG/CONSUMER-BRAND: "HARD GATE: the company must OWN
its brand" (VBL/Pepsi). `engine/plate.py check_brand_ownership`: FMCG name that does
not own its brand → `BRAND_NOT_OWNED` (never bought); ownership not recorded →
`BRAND_UNVERIFIED` (fail closed, listed as BRAND CHECK for Praveen — E4: never
classified from memory). **db migration 006** `names.brand_owned` (1/0/NULL): only VBL
= 0 is stated; every other FMCG name waits for Praveen. Applied to the live register
(sessions kept). Golden 20-Sep: ITC still refused, now as BRAND_UNVERIFIED.
**2. Results date (E3)** — "armable only on a fresh-EPS basis younger than the last
result". `engine/morning_board.py check_basis_fresh` (used by UC1 and UC2):
basis older than the latest results → `STALE_BASIS`; results date unknown →
`RESULT_DATE_UNKNOWN` (fail closed). `tools/results_dates.py` fetches past and
scheduled results dates (Yahoo). Market recordings now carry them; the 25-Sep
recording was extended (106 stocks; ETFs have none).
UC5: new scenario `results_dates_down`; `clock_+45d` now crosses the October results
and disarms the 1-Sep triggers (0 fire). Acceptance: cases 04 and 16 now pass (19/22).
Live check 26-Sep: M&M disarmed — Yahoo lists M&M results on 10-Sep, after its 1-Sep
basis. Yahoo's M&M dates look irregular; verify before re-deriving.

## 2026-09-26 — sector crashes + NSE sectors (PR #8)

### 2026-09-26 — crash test for every sector; NSE's official sector on every stock

Praveen 26-Sep: "does the simulation take names from each sector recognised by NSE?"
It did not (2 hand-made sector crashes). Now:
**feat (usecases/scenarios.py)** — one −12% crash per sector, generated from the
register: every app sector class (17) and every NSE sector (17). A new sector is
covered automatically. Replaces the hand-made IT and lender crashes.
**db (migration 005)** — `names.nse_sector` + `nse_sector_as_of`: NSE's official
"Industry" from `db/reference/nse_industry_2026-09-26.csv` (NSE Indices, Nifty Total
Market list, ~750 stocks). 107 of 126 names matched on the NSE trading symbol; not in
the list: ETFs, REITs/InvITs, a few small caps, TATAMOTORS (demerged). Applied to the
live register as a migration (session history kept); seed_build loads the same list.
**feat (tools/nse_sectors.py)** — parse + deliberate refresh
(`python -m tools.nse_sectors`).
UC5: 124 runs at Rs10k/Rs40k, 0 violations.

## 2026-09-26 — sizing, bond rate, review first (PR #7)

### 2026-09-26 — new sizing: fit the budget, spread by rank

**Rule change approved by Praveen 26-Sep-2026** (replaces tiffin-coffee v5/v6 §formula
steps 4-5, the thirds tilt; the 1-10 clamp and 5-share first bite stay). The spec file
is not edited by code — Praveen's tiffin-coffee skill needs the same patch.
1. Find and rank the names (unchanged).
2. Give each 1 share. If that costs more than the budget, raise the plan to exactly that
   cost and say so at the top of the report ("needs Rs X, Rs Y more").
3. Spread the money left by rank (#1 gets the most), then one top-up pass by rank.
   Leftover → NIFTYBEES. The plate never spends past the plan.
**engine** — `size_by_rank`, `PlateResult.plan_amount`; `assign_tilts`/`compute_qty`
removed. Invariants: BUDGET (never past plan; plan raised only to the 1-share cost) is a
violation; BUDGET_RAISED is a finding (replaces OVER_SESSION).
Recording 25-Sep: Rs10k now spends Rs9,921 (was Rs13,622); Rs5k → plan Rs8,580, shown.
UC5: 90 runs (Rs5k/10k/40k), 0 violations.

### 2026-09-26 — live bond rate works again; "don't buy" names are raised, not bought

**fix (tools/gsec.py)** — the India 10-year yield now comes from CNBC (`IN10Y-IN`),
with yfinance as backup. yfinance `IN10Y.SI` had been returning 404, so every live
plate was using the 12-Sep stored rate (7.04%). Live on 25-Sep: 7.119%.
**feat (engine/plate.py)** — Praveen 26-Sep: a name the register marks don't-buy
(bucket WITHDRAWN or HARD_PASS) that passes every other gate is dropped as
`REVIEW_FIRST` with the register's reason, and listed at the top of the report.
It is bought only after analysis and Praveen's approval (a register change).
Found by UC5: Canara would have been bought in every falling-market scenario.

## 2026-09-26 — acceptance suite (PR #6)

### 2026-09-26 — the 22-case acceptance suite (spec/MIGRATION-AND-VALIDATION.md)

Spec: MIGRATION-AND-VALIDATION §"Behavioral regression" · CLAUDE.md §5 · E3/E8/E9.

**test (tests/acceptance/)** — one parametrized test per row; every row replays the
approved decision through the real engine. **17/22 pass.** 5 are `xfail(strict=True)`
naming what is missing — they flip to XPASS (and fail the build) when it lands:
- 04 stale basis — armability has no last-quarterly-result date (E3)
- 05 corporate action — no trailing-12m corporate-action input
- 07 conglomerate — no osep §SC classifier (strictest applicable gate)
- 16 VBL — no FMCG brand-ownership gate: an owned VBL at its low would first-bite 5
- 21 Wipro — OPEN E6: table expects first-bite ≤5; engine surfaces §12b caps-off
  (pattaz-book §12b vs ledger v4.9 D44) — Praveen to rule
**fix (usecases/plate.py)** — case 19 / E8: a name with no price this run is now a
named drop (`NO_TICKER` / `PRICE_FETCH_FAILED`, `PlateRunResult.unpriced`, session and
report) instead of silence. Prices and fundamentals are keyed by register symbol —
REC (RECLTD.NS) and THANGAMAYIL (THANGAMAYL.NS) were never considered before.

## UC5 — branch `feat/uc5-simulation` (PR #5)

### 2026-09-26 — UC5 market simulation suite (CI + on demand)

Spec: UC5 (Praveen, 25-Sep) · E1/E2/E3/E8/E9 · tiffin v6 §formula, §first-bite,
§overlays, §BeES floor, §H HOCKEY · osep v7 §3 ladder · ledger §4 D37 hockey rungs ·
CLAUDE.md §4 determinism, §5 no network in CI.

**feat (tools/market_snapshot.py)** — `MarketSnapshot` = prices + fundamentals + GoI yield
of one day, every value Stamped; lossless JSON save/load; `record_snapshot` is the only
network call. First recording: `tests/fixtures/market/market_2026-09-25.json`
(115 prices, 115 fundamentals, G-sec unavailable — see below).
**feat (engine/invariants.py)** — the laws every plate must obey, re-checked on the
output: ACCOUNTING (each name plated or dropped exactly once), DROP_EXPLAINED,
QTY_CLAMP (1-10; first bite ≤5), PRICED_FROM_INPUT, NO_BANNED_ENTRY (exit/sovereign/
probe/fraud/never-add/PSU cap), ELIGIBILITY (H-eligible or a valid first bite — the HDFC
law), TOTALS, FAIL_CLOSED, GATE_MONOTONE. FINDINGS (legal, Praveen's call): BREADTH
outside 8-15, OVER_SESSION (the 1-share floor).
**feat (usecases/scenarios.py)** — pure shocks over a recording (provenance re-stamped
`sim:<tag><-source`; P/E and P/B move with price, EPS/BV/ROE don't) and a 16-scenario
catalog + one flash crash per seat-holder: market −5%/wk, hockey rungs from `policy`,
melt-up, IT and lender sector falls, fresh lows everywhere, G-sec ±50bp, G-sec/price/
partial/fundamentals/BeES outages, clock +45d. `custom_scenario` for what-ifs.
**feat (usecases/simulate.py)** — runs each scenario through the real UC1 + UC2 at each
session size, checks every law, reruns for determinism, cross-checks gate
monotonicity; verdict-first report; one `UC5_SIMULATION` session. CLI `run`, `what-if`,
`record`. Skill `.claude/skills/simulate`.
**refactor (usecases/plate.py, usecases/morning_board.py)** — keyword-only `market=` /
`prices=`, `today=`, `record_session=` for replay; defaults unchanged.
**test** — `tests/sim/` (every scenario × ₹5k/₹10k/₹40k), `tests/test_invariants.py`
(each law shown firing on a corrupted plate), `tests/test_scenarios.py`. 326 pass.

First run (recording 25-Sep): **PASS — 0 violations in 60 runs.** Findings for Praveen:
- At ₹10k the plate spends ₹11-14k in 29 of 30 scenarios (8+ names × 1-share floor).
- Live G-sec fetch is broken (`IN10Y.SI` 404) — every live plate uses the 12-Sep policy
  fallback 7.04% with a WARN.
- HOCKEY on "Nifty −5% wk" / "name −10% day" is not modelled (no index/day-move input).
- **Canara (CANBK)** — ledger §7 "WITHDRAWN/ZERO (P1/PSU cap)", DB bucket WITHDRAWN,
  flag_psu only, 17sh owned — first-bites (qty 5) in every down scenario while household
  PSU weight is under 25%. New FINDING `REGISTER_ZERO_BUCKET`; the gate is unchanged
  pending Praveen's ruling (E6).
- ₹10k is below the spec's own breadth premise ("8-15 names for a Rs25-50k session").

### 2026-09-26 — tests never write to the real register
`tests/conftest.py` `scratch_db` fixture + session guard; UC1 integration and store
session tests moved off `db/pattaz.db` (one appended-then-DELETEd a session row).

## 2026-09-25 — merged to main (#4)

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
