-- db/schema.sql — pattaz.db v1 (2026-09-19). Change only via db/migrations/NNN_*.sql.
PRAGMA foreign_keys = ON;

-- The universe/roster: every name the household tracks, with its standing state.
CREATE TABLE names (
  symbol            TEXT PRIMARY KEY,          -- NSE symbol, e.g. PETRONET
  name              TEXT NOT NULL,
  yf_ticker         TEXT,                      -- yfinance ticker (SYMBOL.NS); NULL = unknown
  ticker_verified   INTEGER NOT NULL DEFAULT 0,-- 1 once tools/prices confirms it resolves
  cell              TEXT,                      -- FK-ish to cells.cell (free text for flexibility)
  sector_class      TEXT,                      -- LENDER | NON_EARNING | INDEX_ETF | CYCLICAL | REGULATED
                                               -- | IT_SERVICES | PHARMA | FMCG | AUTO_OEM | AUTO_ANCILLARY
                                               -- | RETAIL | INSURER | REIT_INVIT | EXCHANGE_DEPOSITORY
                                               -- | DEFENCE | NEW_ECONOMY | DEFAULT ; NULL = classify at runtime (E4)
  classified_on     TEXT,                      -- ISO date; NULL forces runtime classification + flag
  classification_source TEXT,
  status            TEXT NOT NULL CHECK (status IN ('ADD','HOLD','SELL','SOLD','WATCH','NEVER_ADD')),
  bucket            TEXT CHECK (bucket IN ('GBN','GBL','HARD_PASS','OWNED','WATCH_CRASH','WITHDRAWN','BALLAST')),
  verdict_date      TEXT,
  decay_expiry      TEXT,                      -- GBN +30d / GBL +90d from verdict_date (spec osep decay clock)
  p5_status         TEXT,                      -- universe view: BUY | HOLD | AVOID | NOT_IN_UNIVERSE | AGREE_NOTE | DISAGREE_NOTE
  p5_note_ref       TEXT,                      -- e.g. 'ledger §8 note 05-Sep'
  flag_sovereign    INTEGER NOT NULL DEFAULT 0,-- P1: state-directed pricing/capital
  flag_psu          INTEGER NOT NULL DEFAULT 0,-- counts toward the 25% PSU/regulated cap (D36)
  flag_cyclical     INTEGER NOT NULL DEFAULT 0,
  flag_probe_open   INTEGER NOT NULL DEFAULT 0,-- overlay 9: live quality/governance probe
  flag_fraud_tail   INTEGER NOT NULL DEFAULT 0,-- overlay 10
  flag_exit_decided INTEGER NOT NULL DEFAULT 0,-- overlay 7: on the sell list
  notes             TEXT,
  as_of             TEXT NOT NULL,             -- date this row's state was last confirmed
  p_mult_book       REAL,                      -- pattaz-book §4 roster P-mult (interim until holdings sync)
  flag_no_add       INTEGER NOT NULL DEFAULT 0,-- hold-only / museum: builds blocked, first-bite allowed
  nse_sector        TEXT,                      -- NSE's official "Industry" (migration 005); NULL = not in NSE list
  nse_sector_as_of  TEXT,                      -- date of the db/reference/nse_industry_*.csv used
  brand_owned       INTEGER CHECK (brand_owned IN (0, 1)) -- FMCG brand gate (migration 006); NULL = not recorded
);

-- Trigger board. A trigger is ARMABLE only if active=1 AND basis_eps_date is fresh (E3).
CREATE TABLE triggers (
  symbol          TEXT NOT NULL REFERENCES names(symbol),
  kind            TEXT NOT NULL CHECK (kind IN ('BUY','ALERT','CRASH_SHELF','NEXT_BUY')),
  level           REAL NOT NULL,
  basis_eps_date  TEXT,                        -- date of the EPS/book the level was derived from
  derivation      TEXT,                        -- e.g. '14.2x fair on TTM EPS' / 'justified P/B 1.075x'
  set_on          TEXT NOT NULL,
  valid_until     TEXT,                        -- NULL = until next result
  gtt_id          TEXT,                        -- resting Kite GTT, if any (UC3 audit)
  active          INTEGER NOT NULL DEFAULT 1,  -- 0 = NOT ARMABLE (stale basis / withdrawn)
  notes           TEXT,
  PRIMARY KEY (symbol, kind)
);

-- Curated at quarterly results. The engine reads the newest row per symbol.
CREATE TABLE fundamentals (
  symbol          TEXT NOT NULL REFERENCES names(symbol),
  as_of           TEXT NOT NULL,               -- result date the numbers belong to
  eps_ttm         REAL,
  book_value_ps   REAL,
  roe             REAL,                        -- percent
  promoter_pct    REAL,
  pledge_pct      REAL,
  auditor_flag    TEXT,                        -- NULL | text of the concern
  source          TEXT,
  PRIMARY KEY (symbol, as_of)
);

-- Household holdings. PARTIAL until UC2.1 replaces it from Kite (Zerodha) + CSV (Integrated).
CREATE TABLE holdings (
  account         TEXT NOT NULL CHECK (account IN ('ZERODHA_P','INTEGRATED_P','INTEGRATED_V')),
  symbol          TEXT NOT NULL,               -- not FK: ETFs/legacy names may not be in names yet
  qty             INTEGER NOT NULL,
  avg_cost        REAL,
  as_of           TEXT NOT NULL,
  source          TEXT NOT NULL,               -- 'KITE_API' | 'CSV' | 'LEDGER_v4.9' | 'CONFIRMED_FILL'
  PRIMARY KEY (account, symbol, as_of)
);

-- Cell map (spec pattaz-book §5; post-consolidation target D33).
CREATE TABLE cells (
  cell            TEXT PRIMARY KEY,
  members         TEXT NOT NULL,               -- comma-separated symbols
  active_adds     TEXT,                        -- comma-separated symbols allowed to add
  max_adds        INTEGER NOT NULL DEFAULT 2,
  is_full         INTEGER NOT NULL DEFAULT 0,
  notes           TEXT,
  as_of           TEXT NOT NULL
);

-- Policy constants (E2: the ONLY legal home of a number the engine uses).
CREATE TABLE policy (
  key             TEXT PRIMARY KEY,
  value           TEXT NOT NULL,
  unit            TEXT,
  source          TEXT NOT NULL,               -- spec § or ledger D-number
  adopted_on      TEXT NOT NULL
);

-- Results dates verified online where the market-data source is wrong or stale
-- (migration 007). A row replaces the fetched dates until valid_until, then the name
-- fails closed until re-verified (E3/E9).
CREATE TABLE results_verified (
  symbol       TEXT PRIMARY KEY,
  last_result  TEXT NOT NULL,
  valid_until  TEXT NOT NULL,
  source       TEXT NOT NULL,
  verified_on  TEXT NOT NULL
);

-- One-session caps-off waivers from the register (migration 009; D6/D44, e.g. D70).
CREATE TABLE caps_off_waivers (
  symbol    TEXT NOT NULL,
  valid_on  TEXT NOT NULL,
  decision  TEXT NOT NULL,
  note      TEXT,
  PRIMARY KEY (symbol, valid_on)
);

-- Decision register mirror (the ledger's D-register; narrative stays in Drive).
CREATE TABLE decisions (
  d_no            INTEGER PRIMARY KEY,
  decided_on      TEXT,
  title           TEXT NOT NULL,
  detail          TEXT,
  status          TEXT NOT NULL DEFAULT 'CLOSED' CHECK (status IN ('OPEN','CLOSED','SUPERSEDED','INDEX_ONLY'))
);

-- Append-only audit log. Every run writes one row (E8).
CREATE TABLE sessions (
  run_id          TEXT PRIMARY KEY,
  ran_at          TEXT NOT NULL,
  usecase         TEXT NOT NULL,               -- UC1_MORNING_BOARD | UC2_PLATE | UC2_1_SYNC_HOLDINGS
  inputs_json     TEXT NOT NULL,               -- gsec, budget, confirmed liquid, fetch stamps
  outputs_json    TEXT NOT NULL,               -- board / plate
  drops_json      TEXT NOT NULL,               -- [{symbol, reason, detail}]
  rules_fired     TEXT NOT NULL                -- comma-separated rule names
);

-- Optional per-run market snapshot (never a decision input for a later run — E3).
CREATE TABLE market_snapshot (
  run_id          TEXT NOT NULL REFERENCES sessions(run_id),
  symbol          TEXT NOT NULL,
  price           REAL,
  low_52w         REAL,
  high_52w        REAL,
  source          TEXT NOT NULL,
  fetched_at      TEXT NOT NULL,
  PRIMARY KEY (run_id, symbol)
);

CREATE TABLE schema_version (version INTEGER NOT NULL, applied_on TEXT NOT NULL);
INSERT INTO schema_version VALUES (1, '2026-09-19');
