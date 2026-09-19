# pattaz.db — what is in it and where it came from (seed 2026-09-19)
Source: ★★★ PATTAZ MASTER LEDGER v4.9 (17-Sep-2026) + the v8 LEDGER APPENDIX. Rebuild any time:
`python db/seed_build.py` (deterministic; edits go in seed_build.py or a migration, never by hand in the .db).
- **names (122)** — the roster with standing state. `sector_class` NULL for RELIANCE, ZUARIIND, BAJAJFINSV,
  SILVERBEES = classify at runtime (E4). Two rows carry a seeded **E6 CONFLICT** note (JYOTHYLAB, DRREDDY):
  ledger v4.9 and the 19-Sep chat disagree; register wins until overturned in writing (D56).
- **triggers (39)** — 12-Sep re-derived board (D54) on the 01-Sep fresh-EPS basis; `valid_until` 15-Nov-2026
  (re-verify at the Q2 FY27 print). Four rows `active=0` = NOT ARMABLE (FEDERALBNK, TMB, INDIGRID, ZYDUSLIFE).
- **holdings (29) — PARTIAL BY DESIGN.** Only lots confirmed with an account. HDFC = the 5-share 10-Sep
  control-exception lot only; household HDFC, IndusInd, IRFC, M&M, Coal India (12sh non-Zerodha) etc. await
  UC2.1. The engine must treat un-synced names as HOLDINGS_STALE, not as zero.
- **cells (24)** — post-consolidation target (D33). **policy (43)** — the only legal home of engine numbers (E2).
- **decisions (64)** — D1-D64 mirror; 22 rows INDEX_ONLY (prose in the Drive LEDGER ARCHIVE).
- `yf_ticker` NULL and `ticker_verified=0` everywhere: **first Claude Code task = verify tickers via tools/prices.**
