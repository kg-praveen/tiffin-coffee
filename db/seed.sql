BEGIN TRANSACTION;
CREATE TABLE cells (
  cell            TEXT PRIMARY KEY,
  members         TEXT NOT NULL,               -- comma-separated symbols
  active_adds     TEXT,                        -- comma-separated symbols allowed to add
  max_adds        INTEGER NOT NULL DEFAULT 2,
  is_full         INTEGER NOT NULL DEFAULT 0,
  notes           TEXT,
  as_of           TEXT NOT NULL
);
INSERT INTO "cells" VALUES('IT','INFY,TCS,WIPRO,HCLTECH','INFY,TCS',2,0,'Wipro hold-no-add (D48); HCL museum','2026-09-17');
INSERT INTO "cells" VALUES('ENERGY_GAS','PETRONET,RELIANCE','PETRONET',2,0,'Reliance P5 AGREE = hold','2026-09-17');
INSERT INTO "cells" VALUES('POWER','NTPC,POWERGRID,TATAPOWER,COALINDIA','NTPC,POWERGRID',2,0,'Coal India EXIT pending; PSU cap 25% (D36)','2026-09-17');
INSERT INTO "cells" VALUES('LENDING_BANKS','SBIN,HDFCBANK,IDFCFIRSTB,CUB,SOUTHBANK,FIVESTAR','SBIN',2,0,'HDFC crash-only; Federal/KVB watch; SIB→KVB swap','2026-09-17');
INSERT INTO "cells" VALUES('GOLD_NBFC','MUTHOOTFIN,MANAPPURAM','MUTHOOTFIN',2,1,'FULL — no third name, ever; Muthoot starter only','2026-09-17');
INSERT INTO "cells" VALUES('CAP_MKT_INFRA','CDSL,BSE','',2,1,'FULL; moat-grantor watch; BSE trim + NSE-listing watch','2026-09-17');
INSERT INTO "cells" VALUES('FIN_OTHER','BAJAJFINSV,GROWW','',2,0,'Holds','2026-09-17');
INSERT INTO "cells" VALUES('FMCG','ITC,VBL','',2,0,'OPEN QUESTION: VBL owned-or-not; brand gate fails VBL adds','2026-09-17');
INSERT INTO "cells" VALUES('AUTO_2W','HEROMOTOCO,BAJAJ-AUTO','',2,1,'FULL museum','2026-09-17');
INSERT INTO "cells" VALUES('AUTO_PV_FARM','HYUNDAI,M&M,TATAMOTORS','M&M',2,0,'Hyundai TRIM','2026-09-17');
INSERT INTO "cells" VALUES('CV','ASHOKLEY,TMCV','',2,0,'Ashok Leyland hold; TMCV museum','2026-09-17');
INSERT INTO "cells" VALUES('DEFENCE','BEL,HAL,LT','',2,1,'FULL; L&T crash-shelf; working-capital objection logged','2026-09-17');
INSERT INTO "cells" VALUES('PHARMA_US','DRREDDY,NATCOPHARM,ZYDUSLIFE','',2,1,'FULL; DRL exit decided','2026-09-17');
INSERT INTO "cells" VALUES('PHARMA_DOMESTIC','CIPLA,SUNPHARMA,MANKIND','',2,1,'FULL','2026-09-17');
INSERT INTO "cells" VALUES('TELECOM','BHARTIARTL','',2,0,NULL,'2026-09-17');
INSERT INTO "cells" VALUES('EMS','AVALON','',2,0,'Trim','2026-09-17');
INSERT INTO "cells" VALUES('ANCILLARY','ARE&M,BALKRISIND','ARE&M',2,0,'Amara Raja half-plate anchor','2026-09-17');
INSERT INTO "cells" VALUES('AGRI_INPUTS','CHAMBLFERT,COROMANDEL','CHAMBLFERT,COROMANDEL',2,0,'2 seats; subsidy rule D60; cross-holding rule D61','2026-09-17');
INSERT INTO "cells" VALUES('HOTELS','ITCHOTELS,MHRIL','',2,0,'MHRIL pending underwrite (not in ledger)','2026-09-17');
INSERT INTO "cells" VALUES('BALLAST','NIFTYBEES,JUNIORBEES,GOLDBEES','NIFTYBEES,JUNIORBEES,GOLDBEES',3,0,'BeES floor never skipped; gold thermostat','2026-09-17');
INSERT INTO "cells" VALUES('METALS_CYCLICAL','TATASTEEL,HINDZINC,JSWSTEEL,SAIL,CHENNPETRO,GESHIP','',0,1,'Harvest/on-strength sell side; never add','2026-09-17');
INSERT INTO "cells" VALUES('WIRES_GBL','FINCABLES,POLYCAB,KEI,HAVELLS,RRKABEL','',2,0,'GBL with triggers (D42)','2026-09-17');
INSERT INTO "cells" VALUES('INCOME_SLEEVE','INDIGRID,MINDSPACE,EMBASSY,NXST','',2,0,'Approved 04-Jul, NEVER FUNDED; target 5-8%; P5 note owed','2026-09-17');
INSERT INTO "cells" VALUES('SILVER','SILVERBEES','',1,0,'Unclassified → Layer-4','2026-09-17');
CREATE TABLE decisions (
  d_no            INTEGER PRIMARY KEY,
  decided_on      TEXT,
  title           TEXT NOT NULL,
  detail          TEXT,
  status          TEXT NOT NULL DEFAULT 'CLOSED' CHECK (status IN ('OPEN','CLOSED','SUPERSEDED','INDEX_ONLY'))
);
INSERT INTO "decisions" VALUES(1,NULL,'Coal India → NTPC swap',NULL,'OPEN');
INSERT INTO "decisions" VALUES(2,NULL,'D2 — index only; full prose in LEDGER ARCHIVE (04→07-Sep deltas)',NULL,'INDEX_ONLY');
INSERT INTO "decisions" VALUES(3,NULL,'Dr Reddy''s exit (quality-integrity)',NULL,'OPEN');
INSERT INTO "decisions" VALUES(4,NULL,'D4 — index only; full prose in LEDGER ARCHIVE (04→07-Sep deltas)',NULL,'INDEX_ONLY');
INSERT INTO "decisions" VALUES(5,NULL,'D5 — index only; full prose in LEDGER ARCHIVE (04→07-Sep deltas)',NULL,'INDEX_ONLY');
INSERT INTO "decisions" VALUES(6,'2026-07-22','Caps-off first bite','waives caps, never gates (refined D44)','CLOSED');
INSERT INTO "decisions" VALUES(7,NULL,'Natco HOLD',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(8,'2026-07-04','Income sleeve approved — unfunded',NULL,'OPEN');
INSERT INTO "decisions" VALUES(9,NULL,'D9 — index only; full prose in LEDGER ARCHIVE (04→07-Sep deltas)',NULL,'INDEX_ONLY');
INSERT INTO "decisions" VALUES(10,NULL,'Manappuram HOLD (defensive leg)',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(11,NULL,'D11 — index only; full prose in LEDGER ARCHIVE (04→07-Sep deltas)',NULL,'INDEX_ONLY');
INSERT INTO "decisions" VALUES(12,NULL,'D12 — index only; full prose in LEDGER ARCHIVE (04→07-Sep deltas)',NULL,'INDEX_ONLY');
INSERT INTO "decisions" VALUES(13,NULL,'D13 — index only; full prose in LEDGER ARCHIVE (04→07-Sep deltas)',NULL,'INDEX_ONLY');
INSERT INTO "decisions" VALUES(14,NULL,'D14 — index only; full prose in LEDGER ARCHIVE (04→07-Sep deltas)',NULL,'INDEX_ONLY');
INSERT INTO "decisions" VALUES(15,NULL,'D15 — index only; full prose in LEDGER ARCHIVE (04→07-Sep deltas)',NULL,'INDEX_ONLY');
INSERT INTO "decisions" VALUES(16,NULL,'D16 — index only; full prose in LEDGER ARCHIVE (04→07-Sep deltas)',NULL,'INDEX_ONLY');
INSERT INTO "decisions" VALUES(17,NULL,'D17 — index only; full prose in LEDGER ARCHIVE (04→07-Sep deltas)',NULL,'INDEX_ONLY');
INSERT INTO "decisions" VALUES(18,NULL,'D18 — index only; full prose in LEDGER ARCHIVE (04→07-Sep deltas)',NULL,'INDEX_ONLY');
INSERT INTO "decisions" VALUES(19,NULL,'D19 — index only; full prose in LEDGER ARCHIVE (04→07-Sep deltas)',NULL,'INDEX_ONLY');
INSERT INTO "decisions" VALUES(20,NULL,'D20 — index only; full prose in LEDGER ARCHIVE (04→07-Sep deltas)',NULL,'INDEX_ONLY');
INSERT INTO "decisions" VALUES(21,NULL,'D21 — index only; full prose in LEDGER ARCHIVE (04→07-Sep deltas)',NULL,'INDEX_ONLY');
INSERT INTO "decisions" VALUES(22,NULL,'D22 — index only; full prose in LEDGER ARCHIVE (04→07-Sep deltas)',NULL,'INDEX_ONLY');
INSERT INTO "decisions" VALUES(23,NULL,'No IPOs (froth rule)',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(24,NULL,'D24 — index only; full prose in LEDGER ARCHIVE (04→07-Sep deltas)',NULL,'INDEX_ONLY');
INSERT INTO "decisions" VALUES(25,NULL,'D25 — index only; full prose in LEDGER ARCHIVE (04→07-Sep deltas)',NULL,'INDEX_ONLY');
INSERT INTO "decisions" VALUES(26,NULL,'D26 — index only; full prose in LEDGER ARCHIVE (04→07-Sep deltas)',NULL,'INDEX_ONLY');
INSERT INTO "decisions" VALUES(27,NULL,'D27 — index only; full prose in LEDGER ARCHIVE (04→07-Sep deltas)',NULL,'INDEX_ONLY');
INSERT INTO "decisions" VALUES(28,'2026-09-07','Rs21.16L deployment plan + accelerate-to-lump',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(29,'2026-09-07','Axis Small Cap redeem-now (with D38)',NULL,'OPEN');
INSERT INTO "decisions" VALUES(30,NULL,'D30 — index only; full prose in LEDGER ARCHIVE (04→07-Sep deltas)',NULL,'INDEX_ONLY');
INSERT INTO "decisions" VALUES(31,'2026-09-07','IKS + Venus Pipes GBL-on-price',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(32,NULL,'D32 — index only; full prose in LEDGER ARCHIVE (04→07-Sep deltas)',NULL,'INDEX_ONLY');
INSERT INTO "decisions" VALUES(33,'2026-09-08','Consolidation 95→~27 with amendments',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(34,'2026-09-08','Sell-list P/L ~+1.18L',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(35,'2026-09-08','Cost basis is not a reason',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(36,'2026-09-08','PSU/regulated cap 25%',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(37,'2026-09-08','Hockey ladder resize',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(38,'2026-09-08','Axis redemption; FY27 exemption to Axis',NULL,'OPEN');
INSERT INTO "decisions" VALUES(39,'2026-09-08','Sell sequence 6 weeks',NULL,'OPEN');
INSERT INTO "decisions" VALUES(40,'2026-09-08','Ten build names',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(41,'2026-09-09','The fear rule',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(42,'2026-09-09','Anand 08-Sep verdicts (wires GBL etc.)',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(43,'2026-09-09','Rs30K plate',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(44,'2026-09-09','Caps-off refinement; IRFC SELL; TMCV museum',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(45,'2026-09-10','Rs1L plate (two-pocket)',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(46,'2026-09-10','Scan findings',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(47,'2026-09-10','HDFC trigger 560→419 (bonus un-processed)',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(48,'2026-09-10','Wipro hold-no-add',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(49,'2026-09-10','52wk-low scan',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(50,'2026-09-10','Rs35K plate CONFIRMED fills',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(51,'2026-09-10','tiffin v5 quantity-first',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(52,'2026-09-12','Thirteen sells approved',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(53,'2026-09-12','Reversals: Groww/Five-Star HOLD; Manappuram+Natco off sell list',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(54,'2026-09-12','Anchor 7.04%/14.2x re-derivation',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(55,'2026-09-12','Macro: crude, RBI OMO, IPO froth, NSE→BSE watch',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(56,'2026-09-12','Research-vs-register protocol',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(57,'2026-09-17','SELL DAY — Rs1,98,262 raised',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(58,'2026-09-17','BSE trim 5sh',NULL,'OPEN');
INSERT INTO "decisions" VALUES(59,'2026-09-17','Chambal starter 10sh (gated)',NULL,'OPEN');
INSERT INTO "decisions" VALUES(60,'2026-09-17','Fertiliser/subsidy rule',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(61,'2026-09-17','Adventz six-name: Chambal only',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(62,'2026-09-17','Skill engine v8 installed; defects 1/2/3 killed; HDFC control exception',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(63,'2026-09-17','Ledger delta-chain incident; v4.9 consolidation; wholesale test',NULL,'CLOSED');
INSERT INTO "decisions" VALUES(64,'2026-09-17','Sector gate evidence base; NOT-FOUND fallback sectors',NULL,'CLOSED');
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
CREATE TABLE holdings (
  account         TEXT NOT NULL CHECK (account IN ('ZERODHA_P','INTEGRATED_P','INTEGRATED_V')),
  symbol          TEXT NOT NULL,               -- not FK: ETFs/legacy names may not be in names yet
  qty             INTEGER NOT NULL,
  avg_cost        REAL,
  as_of           TEXT NOT NULL,
  source          TEXT NOT NULL,               -- 'KITE_API' | 'CSV' | 'LEDGER_v4.9' | 'CONFIRMED_FILL'
  PRIMARY KEY (account, symbol, as_of)
);
INSERT INTO "holdings" VALUES('ZERODHA_P','PETRONET',92,NULL,'2026-09-10','LEDGER_v4.9');
INSERT INTO "holdings" VALUES('ZERODHA_P','NTPC',35,NULL,'2026-09-10','LEDGER_v4.9');
INSERT INTO "holdings" VALUES('ZERODHA_P','MUTHOOTFIN',7,2942.63,'2026-09-09','LEDGER_v4.9');
INSERT INTO "holdings" VALUES('ZERODHA_P','NIFTYBEES',112,NULL,'2026-09-10','LEDGER_v4.9');
INSERT INTO "holdings" VALUES('ZERODHA_P','JUNIORBEES',11,NULL,'2026-09-10','LEDGER_v4.9');
INSERT INTO "holdings" VALUES('ZERODHA_P','TCS',5,NULL,'2026-09-10','LEDGER_v4.9');
INSERT INTO "holdings" VALUES('ZERODHA_P','INFY',12,NULL,'2026-09-10','LEDGER_v4.9');
INSERT INTO "holdings" VALUES('ZERODHA_P','IDFCFIRSTB',10,85.94,'2026-09-09','LEDGER_v4.9');
INSERT INTO "holdings" VALUES('ZERODHA_P','GOLDBEES',389,NULL,'2026-09-09','LEDGER_v4.9');
INSERT INTO "holdings" VALUES('ZERODHA_P','SBIN',3,1008.5,'2026-09-10','CONFIRMED_FILL');
INSERT INTO "holdings" VALUES('ZERODHA_P','ARE&M',5,832.15,'2026-09-10','CONFIRMED_FILL');
INSERT INTO "holdings" VALUES('ZERODHA_P','WIPRO',10,167.06,'2026-09-10','CONFIRMED_FILL');
INSERT INTO "holdings" VALUES('ZERODHA_P','HDFCBANK',5,687.95,'2026-09-10','CONFIRMED_FILL');
INSERT INTO "holdings" VALUES('ZERODHA_P','COALINDIA',15,NULL,'2026-09-06','LEDGER_v4.9');
INSERT INTO "holdings" VALUES('ZERODHA_P','TATASTEEL',82,NULL,'2026-09-01','LEDGER_v4.9');
INSERT INTO "holdings" VALUES('ZERODHA_P','ASHOKLEY',40,113.75,'2026-07-13','LEDGER_v4.9');
INSERT INTO "holdings" VALUES('INTEGRATED_P','ASHOKLEY',10,0.01,'2026-07-13','LEDGER_v4.9');
INSERT INTO "holdings" VALUES('INTEGRATED_V','ASHOKLEY',30,24.56,'2026-07-13','LEDGER_v4.9');
INSERT INTO "holdings" VALUES('INTEGRATED_P','NATCOPHARM',22,NULL,'2026-09-01','LEDGER_v4.9');
INSERT INTO "holdings" VALUES('INTEGRATED_V','NATCOPHARM',4,NULL,'2026-09-01','LEDGER_v4.9');
INSERT INTO "holdings" VALUES('INTEGRATED_P','WIPRO',88,NULL,'2026-09-01','LEDGER_v4.9');
INSERT INTO "holdings" VALUES('INTEGRATED_V','WIPRO',48,NULL,'2026-09-01','LEDGER_v4.9');
INSERT INTO "holdings" VALUES('INTEGRATED_P','TCS',4,NULL,'2026-09-01','LEDGER_v4.9');
INSERT INTO "holdings" VALUES('INTEGRATED_V','TCS',6,NULL,'2026-09-01','LEDGER_v4.9');
INSERT INTO "holdings" VALUES('INTEGRATED_P','INFY',4,NULL,'2026-09-01','LEDGER_v4.9');
INSERT INTO "holdings" VALUES('INTEGRATED_V','INFY',20,NULL,'2026-09-01','LEDGER_v4.9');
INSERT INTO "holdings" VALUES('INTEGRATED_P','SILVERBEES',60,NULL,'2026-09-01','LEDGER_v4.9');
INSERT INTO "holdings" VALUES('INTEGRATED_V','DRREDDY',23,NULL,'2026-09-01','LEDGER_v4.9');
INSERT INTO "holdings" VALUES('INTEGRATED_V','JIOFIN',8,NULL,'2026-09-01','LEDGER_v4.9');
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
  as_of             TEXT NOT NULL              -- date this row's state was last confirmed
);
INSERT INTO "names" VALUES('PETRONET','Petronet LNG','PETRONET.NS',0,'ENERGY_GAS','REGULATED','2026-09-17','ledger v4.9 §5/§7','ADD','GBN','2026-09-12','2026-10-12',NULL,NULL,0,1,0,0,0,0,'Tranches gated on Dahej funding disclosure; re-underwrite if D/E>0.5','2026-09-17');
INSERT INTO "names" VALUES('NTPC','NTPC','NTPC.NS',0,'POWER','REGULATED','2026-09-17','ledger v4.9 §5/§7','ADD','GBN','2026-09-12','2026-10-12',NULL,NULL,0,1,0,0,0,0,'CONVICTION-OVERRIDE 2026-09-20: Coal India exit condition waived by Praveen','2026-09-17');
INSERT INTO "names" VALUES('INFY','Infosys','INFY.NS',0,'IT','IT_SERVICES','2026-09-17','ledger v4.9 §5/§7','ADD','GBN','2026-09-12','2026-10-12',NULL,NULL,0,0,0,0,0,0,'Gate on USD/CC revenue, never INR PAT','2026-09-17');
INSERT INTO "names" VALUES('TCS','Tata Consultancy Services','TCS.NS',0,'IT','IT_SERVICES','2026-09-17','ledger v4.9 §5/§7','ADD','GBN','2026-09-12','2026-10-12',NULL,NULL,0,0,0,0,0,0,'Re-verify at Oct Q2','2026-09-17');
INSERT INTO "names" VALUES('ITC','ITC','ITC.NS',0,'FMCG','FMCG','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED','2026-09-12',NULL,'BUY',NULL,0,0,0,0,0,0,'Hold, no add; crash-shelf 228; income-floor claim withdrawn until dividend prints','2026-09-17');
INSERT INTO "names" VALUES('ARE&M','Amara Raja Energy & Mobility','ARE&M.NS',0,'ANCILLARY','AUTO_ANCILLARY','2026-09-17','ledger v4.9 §5/§7','ADD','GBL','2026-09-12','2026-12-11',NULL,NULL,0,0,0,0,0,0,'HALF-PLATE only (EBITDA margin compression); universe veto at reduced weight','2026-09-17');
INSERT INTO "names" VALUES('RELIANCE','Reliance Industries','RELIANCE.NS',0,'ENERGY_GAS',NULL,NULL,NULL,'HOLD','OWNED','2026-09-12',NULL,'AGREE_NOTE','ledger §8 05-Sep',0,0,0,0,0,0,'Conglomerate: classify at runtime (SC edge rule, strictest gate); P5 AGREE = hold','2026-09-17');
INSERT INTO "names" VALUES('WIPRO','Wipro','WIPRO.NS',0,'IT','IT_SERVICES','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED','2026-09-12',NULL,NULL,NULL,0,0,0,0,0,0,'D48 hold-no-add; swap SOURCE (shrinks in USD)','2026-09-17');
INSERT INTO "names" VALUES('M&M','Mahindra & Mahindra','M&M.NS',0,'AUTO_PV_FARM','AUTO_OEM','2026-09-17','ledger v4.9 §5/§7','ADD','GBL','2026-09-12','2026-12-11',NULL,NULL,0,0,0,0,0,0,'Designated add','2026-09-17');
INSERT INTO "names" VALUES('HCLTECH','HCL Technologies','HCLTECH.NS',0,'IT','IT_SERVICES','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED','2026-09-12',NULL,NULL,NULL,0,0,0,0,0,0,'Museum (Varshu); no add','2026-09-17');
INSERT INTO "names" VALUES('ENGINERSIN','Engineers India','ENGINERSIN.NS',0,'CAPGOODS_PSU','DEFAULT','2026-09-17','ledger v4.9 §5/§7','ADD','GBL','2026-09-12','2026-12-11',NULL,NULL,0,1,0,0,0,0,'Prices commercially (regulated≠directed)','2026-09-17');
INSERT INTO "names" VALUES('RITES','RITES','RITES.NS',0,'CAPGOODS_PSU','DEFAULT','2026-09-17','ledger v4.9 §5/§7','ADD','GBL','2026-09-12','2026-12-11',NULL,NULL,0,1,0,0,0,0,NULL,'2026-09-17');
INSERT INTO "names" VALUES('POWERGRID','Power Grid Corp','POWERGRID.NS',0,'POWER','REGULATED','2026-09-17','ledger v4.9 §5/§7','ADD','GBL','2026-09-12','2026-12-11',NULL,NULL,0,1,0,0,0,0,'Was ABOVE trigger on 12-Sep — dropped from buy band; trigger stands','2026-09-17');
INSERT INTO "names" VALUES('SBIN','State Bank of India','SBIN.NS',0,'LENDING_BANKS','LENDER','2026-09-17','ledger v4.9 §5/§7','ADD','GBL','2026-09-12','2026-12-11',NULL,NULL,0,1,0,0,0,0,'At justified P/B ~1.6x; PSU cap applies','2026-09-17');
INSERT INTO "names" VALUES('HDFCBANK','HDFC Bank','HDFCBANK.NS',0,'LENDING_BANKS','LENDER','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED','2026-09-12',NULL,'AGREE_NOTE','ledger §8 05-Sep',0,0,0,0,0,0,'P-board BLOCKED (at/over target); crash-shelf ~419 (D47); 10-Sep 5sh = control exception D62','2026-09-17');
INSERT INTO "names" VALUES('MUTHOOTFIN','Muthoot Finance','MUTHOOTFIN.NS',0,'GOLD_NBFC','LENDER','2026-09-17','ledger v4.9 §5/§7','ADD','GBN','2026-09-12','2026-10-12','DISAGREE_NOTE','ledger §8 05-Sep (approved, unlocked)',0,0,0,0,0,0,'Starter only; tripwires: gold -20% · RBI LTV · ROE floor · P/B above his objection','2026-09-17');
INSERT INTO "names" VALUES('FIVESTAR','Five-Star Business Finance','FIVESTAR.NS',0,'LENDING_BANKS','LENDER','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED','2026-09-12',NULL,NULL,NULL,0,0,0,0,0,0,'D53 HOLD','2026-09-17');
INSERT INTO "names" VALUES('CHAMBLFERT','Chambal Fertilisers','CHAMBLFERT.NS',0,'AGRI_INPUTS','CYCLICAL','2026-09-17','ledger v4.9 §5/§7','ADD','GBN','2026-09-17','2026-10-17',NULL,NULL,0,0,1,0,0,0,'D59/D61 starter 10sh; NEXT BUY 10sh ≤415; tranche-2 gated on FY27 OCF/PAT toward 70%+; kill <~40% with rising borrowings; subsidy rule D60','2026-09-17');
INSERT INTO "names" VALUES('COROMANDEL','Coromandel International','COROMANDEL.NS',0,'AGRI_INPUTS','CYCLICAL','2026-09-17','ledger v4.9 §5/§7','WATCH','GBL','2026-09-12','2026-12-11',NULL,NULL,0,0,1,0,0,0,'Trigger 1,225 (far); subsidy-linked sovereign flag per D60 check','2026-09-17');
INSERT INTO "names" VALUES('FINCABLES','Finolex Cables','FINCABLES.NS',0,'WIRES_GBL','DEFAULT','2026-09-17','ledger v4.9 §5/§7','WATCH','GBL','2026-09-08','2026-12-07',NULL,NULL,0,0,0,0,0,0,'D42: HARD PASS at price; re-underwrite after 2-3 qtrs of Ultravolt/Adani volume data','2026-09-17');
INSERT INTO "names" VALUES('POLYCAB','Polycab India','POLYCAB.NS',0,'WIRES_GBL','DEFAULT','2026-09-17','ledger v4.9 §5/§7','WATCH','GBL','2026-09-08','2026-12-07',NULL,NULL,0,0,0,0,0,0,'D42: HARD PASS at price; re-underwrite after 2-3 qtrs of Ultravolt/Adani volume data','2026-09-17');
INSERT INTO "names" VALUES('KEI','KEI Industries','KEI.NS',0,'WIRES_GBL','DEFAULT','2026-09-17','ledger v4.9 §5/§7','WATCH','GBL','2026-09-08','2026-12-07',NULL,NULL,0,0,0,0,0,0,'D42: HARD PASS at price; re-underwrite after 2-3 qtrs of Ultravolt/Adani volume data','2026-09-17');
INSERT INTO "names" VALUES('HAVELLS','Havells India','HAVELLS.NS',0,'WIRES_GBL','DEFAULT','2026-09-17','ledger v4.9 §5/§7','WATCH','GBL','2026-09-08','2026-12-07',NULL,NULL,0,0,0,0,0,0,'D42: HARD PASS at price; re-underwrite after 2-3 qtrs of Ultravolt/Adani volume data','2026-09-17');
INSERT INTO "names" VALUES('RRKABEL','RR Kabel','RRKABEL.NS',0,'WIRES_GBL','DEFAULT','2026-09-17','ledger v4.9 §5/§7','WATCH','GBL','2026-09-08','2026-12-07',NULL,NULL,0,0,0,0,0,0,'D42: HARD PASS at price; re-underwrite after 2-3 qtrs of Ultravolt/Adani volume data','2026-09-17');
INSERT INTO "names" VALUES('ULTRACEMCO','UltraTech Cement','ULTRACEMCO.NS',0,'CEMENT','CYCLICAL','2026-09-17','ledger v4.9 §5/§7','WATCH','HARD_PASS','2026-09-08',NULL,NULL,NULL,0,0,1,0,0,0,'D42 HP; alert 5,820','2026-09-17');
INSERT INTO "names" VALUES('TRENT','Trent','TRENT.NS',0,'RETAIL','RETAIL','2026-09-17','ledger v4.9 §5/§7','WATCH','HARD_PASS','2026-09-08',NULL,NULL,NULL,0,0,0,0,0,0,'D42 HP; alert 679','2026-09-17');
INSERT INTO "names" VALUES('TITAN','Titan Company','TITAN.NS',0,'RETAIL','RETAIL','2026-09-17','ledger v4.9 §5/§7','WATCH','WATCH_CRASH',NULL,NULL,'AVOID',NULL,0,0,0,0,0,0,'Diamond needle (75-90x); alert 1,209','2026-09-17');
INSERT INTO "names" VALUES('HAL','Hindustan Aeronautics','HAL.NS',0,'DEFENCE','DEFENCE','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED',NULL,NULL,NULL,NULL,0,1,0,0,0,0,'Defence cell FULL; crash-shelf name; working-capital objection logged; 52wk-high marker ~4,900','2026-09-17');
INSERT INTO "names" VALUES('BEL','Bharat Electronics','BEL.NS',0,'DEFENCE','DEFENCE','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED',NULL,NULL,NULL,NULL,0,1,0,0,0,0,'Defence cell FULL; crash-shelf','2026-09-17');
INSERT INTO "names" VALUES('LT','Larsen & Toubro','LT.NS',0,'DEFENCE','DEFAULT','2026-09-17','ledger v4.9 §5/§7','WATCH','WATCH_CRASH',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'Crash-shelf only','2026-09-17');
INSERT INTO "names" VALUES('ADANIPORTS','Adani Ports','ADANIPORTS.NS',0,'PORTS','DEFAULT','2026-09-17','ledger v4.9 §5/§7','WATCH','WATCH_CRASH',NULL,NULL,NULL,NULL,0,0,0,0,0,0,NULL,'2026-09-17');
INSERT INTO "names" VALUES('NESTLEIND','Nestle India','NESTLEIND.NS',0,'FMCG','FMCG','2026-09-17','ledger v4.9 §5/§7','WATCH','WATCH_CRASH',NULL,NULL,'HOLD',NULL,0,0,0,0,0,0,'~50x; ''Nifty-50 consider, Sensex no''','2026-09-17');
INSERT INTO "names" VALUES('KALYANKJIL','Kalyan Jewellers','KALYANKJIL.NS',0,'RETAIL','RETAIL','2026-09-17','ledger v4.9 §5/§7','WATCH','WATCH_CRASH',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'FOCO-model risk (gate: own-store vs franchise)','2026-09-17');
INSERT INTO "names" VALUES('TMCV','Tata Motors CV (post-demerger)',NULL,0,'CV','AUTO_OEM','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'D44 museum-no-more; E indeterminate post demerger — classify each entity fresh','2026-09-17');
INSERT INTO "names" VALUES('BAJFINANCE','Bajaj Finance','BAJFINANCE.NS',0,'LENDING_BANKS','LENDER','2026-09-17','ledger v4.9 §5/§7','WATCH','WATCH_CRASH',NULL,NULL,'AVOID',NULL,0,0,0,0,0,0,'5.6x book vs ~1.9x justified','2026-09-17');
INSERT INTO "names" VALUES('EXIDEIND','Exide Industries','EXIDEIND.NS',0,'ANCILLARY','AUTO_ANCILLARY','2026-09-17','ledger v4.9 §5/§7','WATCH','WITHDRAWN',NULL,NULL,'AVOID',NULL,0,0,0,0,0,0,'Withdrawn (44x), not lowered','2026-09-17');
INSERT INTO "names" VALUES('GAIL','GAIL India','GAIL.NS',0,'ENERGY_GAS','REGULATED','2026-09-17','ledger v4.9 §5/§7','WATCH','WITHDRAWN',NULL,NULL,NULL,NULL,0,1,0,0,0,0,'Withdrawn','2026-09-17');
INSERT INTO "names" VALUES('BALKRISIND','Balkrishna Industries','BALKRISIND.NS',0,'ANCILLARY','AUTO_ANCILLARY','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'Owned; withdrawn at 33x','2026-09-17');
INSERT INTO "names" VALUES('SUNPHARMA','Sun Pharmaceutical','SUNPHARMA.NS',0,'PHARMA_DOMESTIC','PHARMA','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'Cell FULL; 37x withdrawn','2026-09-17');
INSERT INTO "names" VALUES('CIPLA','Cipla','CIPLA.NS',0,'PHARMA_DOMESTIC','PHARMA','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'Cell FULL; 34x (Goa plant — trailing overstated, small flag)','2026-09-17');
INSERT INTO "names" VALUES('MANKIND','Mankind Pharma','MANKIND.NS',0,'PHARMA_DOMESTIC','PHARMA','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'D33d hold','2026-09-17');
INSERT INTO "names" VALUES('BHARTIARTL','Bharti Airtel','BHARTIARTL.NS',0,'TELECOM','DEFAULT','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'~42x; no add','2026-09-17');
INSERT INTO "names" VALUES('ONGC','ONGC','ONGC.NS',0,'ENERGY_GAS','CYCLICAL','2026-09-17','ledger v4.9 §5/§7','NEVER_ADD','HARD_PASS',NULL,NULL,NULL,NULL,1,1,1,0,0,0,'P1 sovereign; cheapest-on-H trap (overlay 2 worked case)','2026-09-17');
INSERT INTO "names" VALUES('IOC','Indian Oil','IOC.NS',0,'ENERGY_GAS','CYCLICAL','2026-09-17','ledger v4.9 §5/§7','NEVER_ADD','HARD_PASS',NULL,NULL,NULL,NULL,1,1,1,0,0,0,'OMC — P1 directed pricing','2026-09-17');
INSERT INTO "names" VALUES('BPCL','BPCL','BPCL.NS',0,'ENERGY_GAS','CYCLICAL','2026-09-17','ledger v4.9 §5/§7','NEVER_ADD','HARD_PASS',NULL,NULL,NULL,NULL,1,1,1,0,0,0,'OMC — P1 directed pricing','2026-09-17');
INSERT INTO "names" VALUES('HINDPETRO','HPCL','HINDPETRO.NS',0,'ENERGY_GAS','CYCLICAL','2026-09-17','ledger v4.9 §5/§7','NEVER_ADD','HARD_PASS',NULL,NULL,NULL,NULL,1,1,1,0,0,0,'OMC — P1 directed pricing','2026-09-17');
INSERT INTO "names" VALUES('BANKBARODA','Bank of Baroda','BANKBARODA.NS',0,'LENDING_BANKS','LENDER','2026-09-17','ledger v4.9 §5/§7','WATCH','WITHDRAWN',NULL,NULL,NULL,NULL,0,1,0,0,1,0,'0.7x book passes P/B; legacy-fraud tail (overlay 10) + cell block','2026-09-17');
INSERT INTO "names" VALUES('CANBK','Canara Bank','CANBK.NS',0,'LENDING_BANKS','LENDER','2026-09-17','ledger v4.9 §5/§7','WATCH','WITHDRAWN',NULL,NULL,NULL,NULL,0,1,0,0,0,0,'Watch Q2 provisions; PSU cap','2026-09-17');
INSERT INTO "names" VALUES('PNB','Punjab National Bank','PNB.NS',0,'LENDING_BANKS','LENDER','2026-09-17','ledger v4.9 §5/§7','NEVER_ADD','HARD_PASS',NULL,NULL,NULL,NULL,1,1,0,0,0,0,'P1 / PSU cap','2026-09-17');
INSERT INTO "names" VALUES('PFC','Power Finance Corp','PFC.NS',0,'LENDING_BANKS','LENDER','2026-09-17','ledger v4.9 §5/§7','NEVER_ADD','HARD_PASS',NULL,NULL,NULL,NULL,1,1,0,0,0,0,'P1 / PSU cap','2026-09-17');
INSERT INTO "names" VALUES('REC','REC','RECLTD.NS',0,'LENDING_BANKS','LENDER','2026-09-17','ledger v4.9 §5/§7','NEVER_ADD','HARD_PASS',NULL,NULL,NULL,NULL,1,1,0,0,0,0,'P1 / PSU cap','2026-09-17');
INSERT INTO "names" VALUES('TATASTEEL','Tata Steel','TATASTEEL.NS',0,'METALS_CYCLICAL','CYCLICAL','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED',NULL,NULL,'HOLD',NULL,0,0,1,0,0,1,'NEVER ADD; on-strength harvest list; Tata Sons stake story = a tip (no-tip rule)','2026-09-17');
INSERT INTO "names" VALUES('HINDZINC','Hindustan Zinc','HINDZINC.NS',0,'METALS_CYCLICAL','CYCLICAL','2026-09-17','ledger v4.9 §5/§7','SELL','OWNED',NULL,NULL,NULL,NULL,0,0,1,0,0,1,'On-strength sell (green days)','2026-09-17');
INSERT INTO "names" VALUES('JSWSTEEL','JSW Steel','JSWSTEEL.NS',0,'METALS_CYCLICAL','CYCLICAL','2026-09-17','ledger v4.9 §5/§7','SELL','OWNED',NULL,NULL,NULL,NULL,0,0,1,0,0,1,'On-strength sell','2026-09-17');
INSERT INTO "names" VALUES('SAIL','SAIL','SAIL.NS',0,'METALS_CYCLICAL','CYCLICAL','2026-09-17','ledger v4.9 §5/§7','SELL','OWNED',NULL,NULL,NULL,NULL,0,1,1,0,0,1,'On-strength sell','2026-09-17');
INSERT INTO "names" VALUES('CHENNPETRO','Chennai Petroleum','CHENNPETRO.NS',0,'METALS_CYCLICAL','CYCLICAL','2026-09-17','ledger v4.9 §5/§7','SELL','OWNED',NULL,NULL,NULL,NULL,0,1,1,0,0,1,'Peak-cycle; on-strength sell','2026-09-17');
INSERT INTO "names" VALUES('GESHIP','Great Eastern Shipping','GESHIP.NS',0,'METALS_CYCLICAL','CYCLICAL','2026-09-17','ledger v4.9 §5/§7','SELL','OWNED',NULL,NULL,NULL,NULL,0,0,1,0,0,1,'Buyback ≤1,530 window closes 11-Dec-2026 (D33f); value on NAV/share','2026-09-17');
INSERT INTO "names" VALUES('HINDALCO','Hindalco','HINDALCO.NS',0,'METALS_CYCLICAL','CYCLICAL','2026-09-17','ledger v4.9 §5/§7','WATCH','HARD_PASS',NULL,NULL,NULL,NULL,0,0,1,0,0,0,NULL,'2026-09-17');
INSERT INTO "names" VALUES('HINDCOPPER','Hindustan Copper','HINDCOPPER.NS',0,'METALS_CYCLICAL','CYCLICAL','2026-09-17','ledger v4.9 §5/§7','NEVER_ADD','HARD_PASS',NULL,NULL,NULL,NULL,0,1,1,0,0,0,'D42: P1 + 44x','2026-09-17');
INSERT INTO "names" VALUES('MASTEK','Mastek','MASTEK.NS',0,'IT','IT_SERVICES','2026-09-17','ledger v4.9 §5/§7','WATCH','HARD_PASS','2026-08-28','2027-02-28',NULL,'NOT_IN_UNIVERSE',0,0,0,0,0,0,'HP on Stage 1+3; expiry 28-Feb-2027','2026-09-17');
INSERT INTO "names" VALUES('PARADEEP','Paradeep Phosphates','PARADEEP.NS',0,'AGRI_INPUTS','CYCLICAL','2026-09-17','ledger v4.9 §5/§7','WATCH','HARD_PASS','2026-09-17',NULL,NULL,NULL,0,0,1,0,0,0,'D61 NO (three stops); revisit <~120 + gates','2026-09-17');
INSERT INTO "names" VALUES('TEXRAIL','Texmaco Rail','TEXRAIL.NS',0,'WAGONS','CYCLICAL','2026-09-17','ledger v4.9 §5/§7','SELL','OWNED','2026-09-17',NULL,NULL,NULL,0,0,1,0,0,1,'Confetti sell; revisit ~80','2026-09-17');
INSERT INTO "names" VALUES('ZUARIIND','Zuari Industries','ZUARIIND.NS',0,'AGRI_INPUTS',NULL,NULL,NULL,'WATCH','HARD_PASS','2026-09-17',NULL,NULL,NULL,0,0,0,0,0,0,'Catalyst-only; holdco overlay — classify at runtime; cross-holding rule D61','2026-09-17');
INSERT INTO "names" VALUES('TEXINFRA','Texmaco Infrastructure','TEXINFRA.NS',0,'REALTY','DEFAULT','2026-09-17','ledger v4.9 §5/§7','NEVER_ADD','HARD_PASS','2026-09-17',NULL,NULL,NULL,0,0,0,0,0,0,'D61 NO (130% NAV premium)','2026-09-17');
INSERT INTO "names" VALUES('ZUARI','Zuari Agro Chemicals','ZUARI.NS',0,'AGRI_INPUTS','CYCLICAL','2026-09-17','ledger v4.9 §5/§7','NEVER_ADD','HARD_PASS','2026-09-17',NULL,NULL,NULL,0,0,1,0,0,0,'D61 NO','2026-09-17');
INSERT INTO "names" VALUES('FEDERALBNK','Federal Bank','FEDERALBNK.NS',0,'LENDING_BANKS','LENDER','2026-09-17','ledger v4.9 §5/§7','WATCH','GBL',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'Trigger 215 @1.2x predates ROE-linked gate — RE-DERIVE justified (~1.0-1.1x) before arming','2026-09-17');
INSERT INTO "names" VALUES('TMB','Tamilnad Mercantile Bank','TMB.NS',0,'LENDING_BANKS','LENDER','2026-09-17','ledger v4.9 §5/§7','WATCH','WITHDRAWN',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'Ran away (1.36x vs ~1.1x justified)','2026-09-17');
INSERT INTO "names" VALUES('KARURVYSYA','Karur Vysya Bank','KARURVYSYA.NS',0,'LENDING_BANKS','LENDER','2026-09-17','ledger v4.9 §5/§7','WATCH','GBL',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'#1 swap target for SIB','2026-09-17');
INSERT INTO "names" VALUES('SOUTHBANK','South Indian Bank','SOUTHBANK.NS',0,'LENDING_BANKS','LENDER','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'Swap SOURCE → KVB (open action)','2026-09-17');
INSERT INTO "names" VALUES('IDFCFIRSTB','IDFC First Bank','IDFCFIRSTB.NS',0,'LENDING_BANKS','LENDER','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'Spec starter 10sh @85.94 (≤1% band)','2026-09-17');
INSERT INTO "names" VALUES('ICICIBANK','ICICI Bank','ICICIBANK.NS',0,'LENDING_BANKS','LENDER','2026-09-17','ledger v4.9 §5/§7','SOLD','WITHDRAWN',NULL,NULL,'AGREE_NOTE','ledger §8 05-Sep',0,0,0,0,0,0,'SOLD D33e; GTT 1,300 CANCELLED — never resurrect','2026-09-17');
INSERT INTO "names" VALUES('AXISBANK','Axis Bank','AXISBANK.NS',0,'LENDING_BANKS','LENDER','2026-09-17','ledger v4.9 §5/§7','WATCH','WITHDRAWN',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'1.8x vs justified FAIL','2026-09-17');
INSERT INTO "names" VALUES('CUB','City Union Bank','CUB.NS',0,'LENDING_BANKS','LENDER','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED',NULL,NULL,NULL,NULL,0,0,0,0,0,0,NULL,'2026-09-17');
INSERT INTO "names" VALUES('BAJAJFINSV','Bajaj Finserv','BAJAJFINSV.NS',0,'FIN_OTHER',NULL,NULL,NULL,'HOLD','OWNED',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'Holdco overlay — classify at runtime','2026-09-17');
INSERT INTO "names" VALUES('GROWW','Groww (Billionbrains)',NULL,0,'FIN_OTHER','NEW_ECONOMY','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED','2026-09-12',NULL,NULL,NULL,0,0,0,0,0,0,'D53 HOLD-WATCH: promoter 27.14% vs 26% floor; PEG 0.76','2026-09-17');
INSERT INTO "names" VALUES('INDIGRID','IndiGrid InvIT',NULL,0,'INCOME_SLEEVE','REIT_INVIT','2026-09-17','ledger v4.9 §5/§7','WATCH','GBL',NULL,NULL,'AVOID',NULL,0,0,0,0,0,0,'Approved-unfunded sleeve #1 (D8); entry 165-170 on 04-Jul basis (STALE; NAV 146.93 09-Sep); P5 divergence note OWED','2026-09-17');
INSERT INTO "names" VALUES('MINDSPACE','Mindspace REIT',NULL,0,'INCOME_SLEEVE','REIT_INVIT','2026-09-17','ledger v4.9 §5/§7','WATCH','GBL',NULL,NULL,'AVOID',NULL,0,0,0,0,0,0,'Entry rule: ≥15% NAV discount (NAV 527, LTV 24.3%, 04-Jul basis)','2026-09-17');
INSERT INTO "names" VALUES('EMBASSY','Embassy Office Parks REIT',NULL,0,'INCOME_SLEEVE','REIT_INVIT','2026-09-17','ledger v4.9 §5/§7','WATCH','GBL',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'Sleeve #2','2026-09-17');
INSERT INTO "names" VALUES('NXST','Nexus Select Trust',NULL,0,'INCOME_SLEEVE','REIT_INVIT','2026-09-17','ledger v4.9 §5/§7','WATCH','GBL',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'Watch','2026-09-17');
INSERT INTO "names" VALUES('PGINVIT','PowerGrid InvIT',NULL,0,'INCOME_SLEEVE','REIT_INVIT','2026-09-17','ledger v4.9 §5/§7','NEVER_ADD','HARD_PASS',NULL,NULL,'AVOID',NULL,0,0,0,0,0,0,'Melting DPU — same instrument Anand rejected','2026-09-17');
INSERT INTO "names" VALUES('CUBEINVIT','Cube Highways Trust',NULL,0,'INCOME_SLEEVE','REIT_INVIT','2026-09-17','ledger v4.9 §5/§7','NEVER_ADD','HARD_PASS',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'50.3% promoter pledge (09-Sep)','2026-09-17');
INSERT INTO "names" VALUES('INDUSINDBK','IndusInd Bank','INDUSINDBK.NS',0,'LENDING_BANKS','LENDER','2026-09-17','ledger v4.9 §5/§7','SELL','OWNED',NULL,NULL,NULL,NULL,0,0,0,0,0,1,'Exit path; recovery rule met on P-Int lot','2026-09-17');
INSERT INTO "names" VALUES('JIOFIN','Jio Financial','JIOFIN.NS',0,'FIN_OTHER','LENDER','2026-09-17','ledger v4.9 §5/§7','NEVER_ADD','HARD_PASS',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'Standing ban; Zerodha lot SOLD 17-Sep; Varshu 8sh legacy','2026-09-17');
INSERT INTO "names" VALUES('LICI','LIC of India','LICI.NS',0,'INSURANCE','INSURER','2026-09-17','ledger v4.9 §5/§7','NEVER_ADD','HARD_PASS',NULL,NULL,'AVOID',NULL,0,0,0,0,0,0,'Governance; insurer = NOT FOUND sector (default ladder)','2026-09-17');
INSERT INTO "names" VALUES('YESBANK','Yes Bank','YESBANK.NS',0,'LENDING_BANKS','LENDER','2026-09-17','ledger v4.9 §5/§7','NEVER_ADD','HARD_PASS',NULL,NULL,NULL,NULL,0,0,0,0,0,0,NULL,'2026-09-17');
INSERT INTO "names" VALUES('MANAPPURAM','Manappuram Finance','MANAPPURAM.NS',0,'GOLD_NBFC','LENDER','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED',NULL,NULL,'BUY',NULL,0,0,0,0,0,0,'Owned, no adds (cell FULL); defensive leg D10/D53; his 2025 ''better'' verdict fails today''s gate','2026-09-17');
INSERT INTO "names" VALUES('IDEAFORGE','ideaForge Technology','IDEAFORGE.NS',0,'NEW_ECONOMY','NEW_ECONOMY','2026-09-17','ledger v4.9 §5/§7','NEVER_ADD','HARD_PASS',NULL,NULL,NULL,NULL,0,0,0,0,0,0,NULL,'2026-09-17');
INSERT INTO "names" VALUES('ATHERENERG','Ather Energy','ATHERENERG.NS',0,'NEW_ECONOMY','NEW_ECONOMY','2026-09-17','ledger v4.9 §5/§7','NEVER_ADD','HARD_PASS',NULL,NULL,'AVOID',NULL,0,0,0,0,0,0,'''Zero valuation is better than Ather''s''','2026-09-17');
INSERT INTO "names" VALUES('HINDOILEXP','Hindustan Oil Exploration','HINDOILEXP.NS',0,'HARVEST','CYCLICAL','2026-09-17','ledger v4.9 §5/§7','SELL','OWNED',NULL,NULL,NULL,NULL,0,0,1,0,0,1,'Promoter 0% — harvest loss THIS FY (open action 0b)','2026-09-17');
INSERT INTO "names" VALUES('DABUR','Dabur','DABUR.NS',0,'FMCG','FMCG','2026-09-17','ledger v4.9 §5/§7','NEVER_ADD','HARD_PASS',NULL,NULL,NULL,NULL,0,0,0,0,0,0,NULL,'2026-09-17');
INSERT INTO "names" VALUES('GODREJCP','Godrej Consumer','GODREJCP.NS',0,'FMCG','FMCG','2026-09-17','ledger v4.9 §5/§7','NEVER_ADD','HARD_PASS',NULL,NULL,NULL,NULL,0,0,0,0,0,0,NULL,'2026-09-17');
INSERT INTO "names" VALUES('BATAINDIA','Bata India','BATAINDIA.NS',0,'FMCG','FMCG','2026-09-17','ledger v4.9 §5/§7','NEVER_ADD','HARD_PASS',NULL,NULL,NULL,NULL,0,0,0,0,0,0,NULL,'2026-09-17');
INSERT INTO "names" VALUES('JYOTHYLAB','Jyothy Labs','JYOTHYLAB.NS',0,'FMCG','FMCG','2026-09-17','ledger v4.9 §5/§7','WATCH','HARD_PASS',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'⚠️ E6 CONFLICT: ledger v4.9 §8 = never-add; 19-Sep chat proposed GBL pending underwrite. Register wins until overturned in writing (D56); Re-evaluation flagged 2026-09-20; was NEVER_ADD','2026-09-17');
INSERT INTO "names" VALUES('MHRIL','Mahindra Holidays','MHRIL.NS',0,'HOTELS','DEFAULT','2026-09-17','ledger v4.9 §5/§7','WATCH','GBL','2026-09-19','2026-12-18',NULL,NULL,0,0,0,0,0,0,'19-Sep chat: GBL pending underwrite — NOT in ledger v4.9; verify before any action','2026-09-17');
INSERT INTO "names" VALUES('IIFL','IIFL Finance','IIFL.NS',0,'FIN_OTHER','LENDER','2026-09-17','ledger v4.9 §5/§7','NEVER_ADD','HARD_PASS',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'Promoter <26%; governance','2026-09-17');
INSERT INTO "names" VALUES('THANGAMAYIL','Thangamayil Jewellery','THANGAMAYL.NS',0,'RETAIL','RETAIL','2026-09-17','ledger v4.9 §5/§7','NEVER_ADD','HARD_PASS',NULL,NULL,'AVOID',NULL,0,0,0,0,0,0,'55x, 6x book','2026-09-17');
INSERT INTO "names" VALUES('SULA','Sula Vineyards','SULA.NS',0,'FMCG','FMCG','2026-09-17','ledger v4.9 §5/§7','NEVER_ADD','HARD_PASS',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'Promoter below 26% kill-switch','2026-09-17');
INSERT INTO "names" VALUES('DIVISLAB','Divi''s Laboratories','DIVISLAB.NS',0,'PHARMA_US','PHARMA','2026-09-17','ledger v4.9 §5/§7','NEVER_ADD','HARD_PASS',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'Valuation','2026-09-17');
INSERT INTO "names" VALUES('RTNINDIA','RattanIndia Enterprises',NULL,0,'HARVEST','DEFAULT','2026-09-17','ledger v4.9 §5/§7','SELL','OWNED',NULL,NULL,NULL,NULL,0,0,0,0,0,1,'Harvest loss THIS FY (open action 0b)','2026-09-17');
INSERT INTO "names" VALUES('GLOBALSURF','Global Surfaces',NULL,0,'HARVEST','DEFAULT','2026-09-17','ledger v4.9 §5/§7','SELL','OWNED',NULL,NULL,NULL,NULL,0,0,0,0,0,1,'Integrated lot; harvest loss THIS FY','2026-09-17');
INSERT INTO "names" VALUES('JKPAPER','JK Paper','JKPAPER.NS',0,'HARVEST','CYCLICAL','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED',NULL,NULL,NULL,NULL,0,0,1,0,0,0,'Harvest deferred','2026-09-17');
INSERT INTO "names" VALUES('COALINDIA','Coal India','COALINDIA.NS',0,'POWER','CYCLICAL','2026-09-17','ledger v4.9 §5/§7','SELL','OWNED',NULL,NULL,'AVOID',NULL,1,1,1,0,0,1,'EXIT CANDIDATE (D1 → NTPC); 27sh household; greed-zone yield = dividend-stripping','2026-09-17');
INSERT INTO "names" VALUES('IRFC','IRFC','IRFC.NS',0,'HARVEST','LENDER','2026-09-17','ledger v4.9 §5/§7','SELL','OWNED',NULL,NULL,NULL,NULL,0,1,0,0,0,1,'D44 SELL (200sh)','2026-09-17');
INSERT INTO "names" VALUES('HFCL','HFCL','HFCL.NS',0,'HARVEST','DEFAULT','2026-09-17','ledger v4.9 §5/§7','SELL','OWNED',NULL,NULL,NULL,NULL,0,0,0,0,0,1,'Limit 216.90 ABOVE market — revise down','2026-09-17');
INSERT INTO "names" VALUES('DRREDDY','Dr Reddy''s','DRREDDY.NS',0,'PHARMA_US','PHARMA','2026-09-17','ledger v4.9 §5/§7','SELL','OWNED',NULL,NULL,NULL,NULL,0,0,0,1,0,1,'⚠️ E6 CONFLICT: ledger v4.9 = exit decided (D3; 5+23 on sell list) vs 19-Sep chat ''dated hold to Jan-2027''. Register wins until overturned (D56). Semaglutide probe open','2026-09-17');
INSERT INTO "names" VALUES('NATCOPHARM','Natco Pharma','NATCOPHARM.NS',0,'PHARMA_US','PHARMA','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED',NULL,NULL,'BUY',NULL,0,0,0,0,0,0,'D7 HOLD; cell FULL','2026-09-17');
INSERT INTO "names" VALUES('HEROMOTOCO','Hero MotoCorp','HEROMOTOCO.NS',0,'AUTO_2W','AUTO_OEM','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED',NULL,NULL,'HOLD',NULL,0,0,0,0,0,0,'Hold-only museum; fair ~3,950 (01-Sep basis)','2026-09-17');
INSERT INTO "names" VALUES('BAJAJ-AUTO','Bajaj Auto','BAJAJ-AUTO.NS',0,'AUTO_2W','AUTO_OEM','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED',NULL,NULL,'AVOID',NULL,0,0,0,0,0,0,'Legacy hold; his band ''below 20x''','2026-09-17');
INSERT INTO "names" VALUES('HYUNDAI','Hyundai Motor India','HYUNDAI.NS',0,'AUTO_PV_FARM','AUTO_OEM','2026-09-17','ledger v4.9 §5/§7','SELL','OWNED',NULL,NULL,NULL,NULL,0,0,0,0,0,1,'TRIM to ~3% (D33b)','2026-09-17');
INSERT INTO "names" VALUES('TATAMOTORS','Tata Motors PV (post-demerger)',NULL,0,'AUTO_PV_FARM','AUTO_OEM','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'One line; classify fresh post demerger','2026-09-17');
INSERT INTO "names" VALUES('ASHOKLEY','Ashok Leyland','ASHOKLEY.NS',0,'CV','AUTO_OEM','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED',NULL,NULL,'AGREE_NOTE','ledger §8 05-Sep',0,0,0,0,0,0,'80sh household (3 lots incl. bonus); exit CANCELLED 13-Jul; hold no-add','2026-09-17');
INSERT INTO "names" VALUES('AVALON','Avalon Technologies','AVALON.NS',0,'EMS','DEFAULT','2026-09-17','ledger v4.9 §5/§7','SELL','OWNED',NULL,NULL,NULL,NULL,0,0,0,0,0,1,'TRIM to 10-12% of Integrated','2026-09-17');
INSERT INTO "names" VALUES('CDSL','CDSL','CDSL.NS',0,'CAP_MKT_INFRA','EXCHANGE_DEPOSITORY','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'Cell FULL; moat-grantor watch (SEBI admitting more players)','2026-09-17');
INSERT INTO "names" VALUES('BSE','BSE','BSE.NS',0,'CAP_MKT_INFRA','EXCHANGE_DEPOSITORY','2026-09-17','ledger v4.9 §5/§7','SELL','OWNED',NULL,NULL,NULL,NULL,0,0,0,0,0,1,'D58 trim 5sh (74x); keep Varshu 4 bonus; WATCH post NSE listing 24-Sep','2026-09-17');
INSERT INTO "names" VALUES('ITCHOTELS','ITC Hotels','ITCHOTELS.NS',0,'HOTELS','DEFAULT','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED',NULL,NULL,NULL,NULL,0,0,0,0,0,0,NULL,'2026-09-17');
INSERT INTO "names" VALUES('VBL','Varun Beverages','VBL.NS',0,'FMCG','FMCG','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED',NULL,NULL,'AGREE_NOTE','ledger §8 05-Sep',0,0,0,0,0,0,'OPEN-VERIFY owned-or-not (§14 item 2); brand-ownership HARD GATE fails adds either way','2026-09-17');
INSERT INTO "names" VALUES('ZYDUSLIFE','Zydus Lifesciences','ZYDUSLIFE.NS',0,'PHARMA_US','PHARMA','2026-09-17','ledger v4.9 §5/§7','WATCH','GBL',NULL,NULL,'BUY',NULL,0,0,0,0,0,0,'Universe BUY + OSEP pass = NO ACTION (anti-tip wall); trigger ~737 provisional, basis unknown → NOT ARMABLE','2026-09-17');
INSERT INTO "names" VALUES('NIFTYBEES','Nippon Nifty 50 BeES','NIFTYBEES.NS',0,'BALLAST','INDEX_ETF','2026-09-17','ledger v4.9 §5/§7','ADD','BALLAST',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'BeES floor — never skip','2026-09-17');
INSERT INTO "names" VALUES('JUNIORBEES','Nippon Nifty Next 50 BeES','JUNIORBEES.NS',0,'BALLAST','INDEX_ETF','2026-09-17','ledger v4.9 §5/§7','ADD','BALLAST',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'BeES floor','2026-09-17');
INSERT INTO "names" VALUES('GOLDBEES','Nippon Gold BeES','GOLDBEES.NS',0,'BALLAST','NON_EARNING','2026-09-17','ledger v4.9 §5/§7','ADD','BALLAST',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'No valuation gate; thermostat governs (>40% NW gates fresh metal buying)','2026-09-17');
INSERT INTO "names" VALUES('SILVERBEES','Nippon Silver ETF','SILVERBEES.NS',0,'SILVER',NULL,NULL,NULL,'HOLD','OWNED',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'Unclassified → Layer-4; 60u in Praveen''s Integrated','2026-09-17');
INSERT INTO "names" VALUES('TATAPOWER','Tata Power','TATAPOWER.NS',0,'POWER','REGULATED','2026-09-17','ledger v4.9 §5/§7','HOLD','OWNED',NULL,NULL,NULL,NULL,0,0,0,0,0,0,'Hold; ''30 P/E very expensive''','2026-09-17');
INSERT INTO "names" VALUES('HINDUNILVR','Hindustan Unilever','HINDUNILVR.NS',0,'FMCG','FMCG','2026-09-17','ledger v4.9 §5/§7','WATCH',NULL,NULL,NULL,NULL,NULL,0,0,0,0,0,0,NULL,'2026-09-17');
INSERT INTO "names" VALUES('ASIANPAINT','Asian Paints','ASIANPAINT.NS',0,'FMCG','DEFAULT','2026-09-17','ledger v4.9 §5/§7','WATCH',NULL,NULL,NULL,NULL,NULL,0,0,0,0,0,0,NULL,'2026-09-17');
INSERT INTO "names" VALUES('MARUTI','Maruti Suzuki','MARUTI.NS',0,'AUTO_PV_FARM','AUTO_OEM','2026-09-17','ledger v4.9 §5/§7','WATCH',NULL,NULL,NULL,NULL,NULL,0,0,0,0,0,0,NULL,'2026-09-17');
INSERT INTO "names" VALUES('ICICIPRULI','ICICI Prudential Life','ICICIPRULI.NS',0,'INSURANCE','INSURER','2026-09-17','ledger v4.9 §5/§7','WATCH',NULL,NULL,NULL,NULL,NULL,0,0,0,0,0,0,NULL,'2026-09-17');
CREATE TABLE policy (
  key             TEXT PRIMARY KEY,
  value           TEXT NOT NULL,
  unit            TEXT,
  source          TEXT NOT NULL,               -- spec § or ledger D-number
  adopted_on      TEXT NOT NULL
);
INSERT INTO "policy" VALUES('fair_pe_method','1/gsec_yield','formula','osep v7 §ladder (OSEP formalisation of Anand''s earnings-yield rule)','2026-09-12');
INSERT INTO "policy" VALUES('cost_of_equity_spread_over_gsec','6.09','pct','ledger §3 (r=13.13% at G-sec 7.04%, D54)','2026-09-12');
INSERT INTO "policy" VALUES('growth_g','5','pct','osep v7 §BANK justified P/B','2026-09-12');
INSERT INTO "policy" VALUES('lender_first_bite_gate','JUSTIFIED_PB_ONLY','rule','tiffin v6 §(c) — defect-2 fix','2026-09-17');
INSERT INTO "policy" VALUES('cap_name_pct','20','pct of household equity','pattaz-book §4','2026-07-13');
INSERT INTO "policy" VALUES('cap_sector_pct','40','pct of household equity','pattaz-book §4','2026-07-13');
INSERT INTO "policy" VALUES('cap_psu_regulated_pct','25','pct of household equity','ledger D36','2026-09-08');
INSERT INTO "policy" VALUES('band_core','7-10','pct','pattaz-book §4','2026-07-13');
INSERT INTO "policy" VALUES('band_standard','4-6','pct','pattaz-book §4','2026-07-13');
INSERT INTO "policy" VALUES('band_satellite','2-3','pct','pattaz-book §4','2026-07-13');
INSERT INTO "policy" VALUES('band_spec_max','1','pct','pattaz-book §4','2026-07-13');
INSERT INTO "policy" VALUES('cell_max_active_adds','2','count','pattaz-book §5','2026-07-13');
INSERT INTO "policy" VALUES('qty_clamp_min','1','shares','tiffin v6 STEP 5','2026-09-10');
INSERT INTO "policy" VALUES('qty_clamp_max','10','shares','tiffin v6 STEP 5','2026-09-10');
INSERT INTO "policy" VALUES('breadth_min','8','names','tiffin v6 STEP 3','2026-09-10');
INSERT INTO "policy" VALUES('breadth_max','15','names','tiffin v6 STEP 3','2026-09-10');
INSERT INTO "policy" VALUES('eligible_h_min','0.85','ratio','tiffin v6 STEP 1','2026-09-10');
INSERT INTO "policy" VALUES('eligible_l_max','5','pct above 52wk low','tiffin v6 STEP 1','2026-09-10');
INSERT INTO "policy" VALUES('h_band_coffee','0.85-0.95:0.5','H:mult','tiffin v6','2026-09-10');
INSERT INTO "policy" VALUES('h_band_tiffin','0.95-1.05:1.0','H:mult','tiffin v6','2026-09-10');
INSERT INTO "policy" VALUES('h_band_full_meals','1.05-1.15:3.0','H:mult','tiffin v6','2026-09-10');
INSERT INTO "policy" VALUES('h_band_hockey','1.15+','H','tiffin v6','2026-09-10');
INSERT INTO "policy" VALUES('p_mult_missing','1.5','mult','tiffin v6 P-index','2026-09-10');
INSERT INTO "policy" VALUES('p_mult_building','1.0','mult','tiffin v6','2026-09-10');
INSERT INTO "policy" VALUES('p_mult_maint','0.5','mult','tiffin v6','2026-09-10');
INSERT INTO "policy" VALUES('p_mult_blocked','0','mult','tiffin v6','2026-09-10');
INSERT INTO "policy" VALUES('ticket_band_min','5000','INR','tiffin v6 (Praveen''s band)','2026-09-10');
INSERT INTO "policy" VALUES('ticket_band_max','10000','INR','tiffin v6','2026-09-10');
INSERT INTO "policy" VALUES('single_deployment_cap_pct','15','pct of surplus','tiffin v4 guardrail','2026-08-03');
INSERT INTO "policy" VALUES('two_pocket_split','60/40','ratio','tiffin v6','2026-09-10');
INSERT INTO "policy" VALUES('decay_gbn_days','30','days','osep v7 decay clock','2026-08-03');
INSERT INTO "policy" VALUES('decay_gbl_days','90','days','osep v7 decay clock','2026-08-03');
INSERT INTO "policy" VALUES('promoter_kill_switch_pct','26','pct','osep Stage 0','2026-08-03');
INSERT INTO "policy" VALUES('gold_thermostat_pct_nw','40','pct of net worth','tiffin thermostat','2026-07-13');
INSERT INTO "policy" VALUES('hockey_reserve_floor','100000','INR','pattaz-book §2 [POLICY]','2026-07-14');
INSERT INTO "policy" VALUES('hockey_rung1_nifty_drawdown_pct','15','pct (D28 accelerate-to-lump)','ledger D37','2026-09-08');
INSERT INTO "policy" VALUES('hockey_rung2_nifty_drawdown_pct','25','pct (reserve + powder)','ledger D37','2026-09-08');
INSERT INTO "policy" VALUES('bees_floor','NEVER_SKIP','rule','tiffin v6','2026-07-13');
INSERT INTO "policy" VALUES('novelty_rule_days','1','days (no same-day buy of fresh underwrites)','tiffin overlays','2026-08-03');
INSERT INTO "policy" VALUES('income_sleeve_target_pct','5-8','pct of household equity','ledger D8','2026-07-04');
INSERT INTO "policy" VALUES('planning_yield_pct','8','pct','pattaz-book §16','2026-08-03');
INSERT INTO "policy" VALUES('cost_basis_is_not_a_reason','TRUE','rule','ledger D35','2026-09-08');
INSERT INTO "policy" VALUES('caps_off_first_bite','WAIVES_CAPS_NEVER_GATES','rule','ledger D6+D44','2026-09-09');
CREATE TABLE schema_version (version INTEGER NOT NULL, applied_on TEXT NOT NULL);
INSERT INTO "schema_version" VALUES(1,'2026-09-19');
CREATE TABLE sessions (
  run_id          TEXT PRIMARY KEY,
  ran_at          TEXT NOT NULL,
  usecase         TEXT NOT NULL,               -- UC1_MORNING_BOARD | UC2_PLATE | UC2_1_SYNC_HOLDINGS
  inputs_json     TEXT NOT NULL,               -- gsec, budget, confirmed liquid, fetch stamps
  outputs_json    TEXT NOT NULL,               -- board / plate
  drops_json      TEXT NOT NULL,               -- [{symbol, reason, detail}]
  rules_fired     TEXT NOT NULL                -- comma-separated rule names
);
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
INSERT INTO "triggers" VALUES('PETRONET','BUY',383.0,'2026-09-01','14.2x fair on TTM EPS (D54 anchor 7.04%)','2026-09-12','2026-11-15',NULL,1,NULL);
INSERT INTO "triggers" VALUES('NTPC','BUY',407.0,'2026-09-01','14.2x fair; regulated≠directed','2026-09-12','2026-11-15',NULL,1,'CONVICTION-OVERRIDE 2026-09-20: Coal India exit condition waived by Praveen');
INSERT INTO "triggers" VALUES('INFY','BUY',1099.0,'2026-09-01','~15x band; USD/CC guard','2026-09-12','2026-11-15',NULL,1,NULL);
INSERT INTO "triggers" VALUES('TCS','BUY',1939.0,'2026-09-01','~fair on TTM EPS','2026-09-12','2026-11-15',NULL,1,'Re-verify at Oct Q2');
INSERT INTO "triggers" VALUES('ITC','CRASH_SHELF',228.0,'2026-09-01','fwd EPS ~12-13 post tax shock','2026-09-12','2026-11-15',NULL,1,'Hold-only name: shelf, not an add');
INSERT INTO "triggers" VALUES('ARE&M','BUY',790.0,'2026-09-01','re-derived on margin compression','2026-09-12','2026-11-15',NULL,1,'HALF-PLATE');
INSERT INTO "triggers" VALUES('RELIANCE','BUY',854.0,'2026-09-01','14.2x fair','2026-09-12','2026-11-15',NULL,1,'Name status HOLD blocks adds (P5 AGREE)');
INSERT INTO "triggers" VALUES('WIPRO','BUY',190.0,'2026-09-01','12.5x','2026-09-12','2026-11-15',NULL,1,'Name status HOLD (D48)');
INSERT INTO "triggers" VALUES('M&M','BUY',2061.0,'2026-09-01','14.2x fair','2026-09-12','2026-11-15',NULL,1,NULL);
INSERT INTO "triggers" VALUES('HCLTECH','BUY',915.0,'2026-09-01','14.2x fair','2026-09-12','2026-11-15',NULL,1,'Museum: no add');
INSERT INTO "triggers" VALUES('ENGINERSIN','BUY',177.0,'2026-09-01','14.2x fair','2026-09-12','2026-11-15',NULL,1,NULL);
INSERT INTO "triggers" VALUES('RITES','BUY',137.0,'2026-09-01','14.2x fair','2026-09-12','2026-11-15',NULL,1,NULL);
INSERT INTO "triggers" VALUES('POWERGRID','BUY',250.0,'2026-09-01','14.2x fair','2026-09-12','2026-11-15',NULL,1,'Above trigger 12-Sep');
INSERT INTO "triggers" VALUES('SBIN','BUY',862.0,'2026-09-01','justified P/B ~1.6x','2026-09-12','2026-11-15',NULL,1,'PSU cap');
INSERT INTO "triggers" VALUES('HDFCBANK','CRASH_SHELF',419.0,'2026-09-01','justified P/B 1.075x on book ₹390 (D47 corrected)','2026-09-12','2026-11-15',NULL,1,'P-board BLOCKED; crash-only');
INSERT INTO "triggers" VALUES('MUTHOOTFIN','BUY',3221.0,'2026-09-01','justified P/B (ROE-linked, guard 1)','2026-09-12','2026-11-15',NULL,1,'Starter only');
INSERT INTO "triggers" VALUES('FIVESTAR','BUY',341.0,'2026-09-01','justified P/B','2026-09-12','2026-11-15',NULL,1,'Name status HOLD (D53)');
INSERT INTO "triggers" VALUES('CHAMBLFERT','NEXT_BUY',415.0,'2026-08-15','D61: price 409 on 16-Sep, L 2%; FY26 OCF/PAT 7% = the one fail','2026-09-17','2026-11-15',NULL,1,'10sh next buy; tranche-2 gated on Q1/Q2 FY27 cash conversion');
INSERT INTO "triggers" VALUES('COROMANDEL','BUY',1225.0,'2026-09-01','14.2x fair','2026-09-12','2026-11-15',NULL,1,'Far');
INSERT INTO "triggers" VALUES('FINCABLES','BUY',760.0,'2026-09-08','D42 GBL','2026-09-12','2026-11-15',NULL,1,NULL);
INSERT INTO "triggers" VALUES('FINCABLES','ALERT',1048.0,'2026-09-08','D42','2026-09-12','2026-11-15',NULL,1,NULL);
INSERT INTO "triggers" VALUES('POLYCAB','BUY',2700.0,'2026-09-08','D42 GBL','2026-09-12','2026-11-15',NULL,1,NULL);
INSERT INTO "triggers" VALUES('POLYCAB','ALERT',3724.0,'2026-09-08','D42','2026-09-12','2026-11-15',NULL,1,NULL);
INSERT INTO "triggers" VALUES('KEI','BUY',1510.0,'2026-09-08','D42 GBL','2026-09-12','2026-11-15',NULL,1,NULL);
INSERT INTO "triggers" VALUES('KEI','ALERT',2085.0,'2026-09-08','D42','2026-09-12','2026-11-15',NULL,1,NULL);
INSERT INTO "triggers" VALUES('HAVELLS','BUY',390.0,'2026-09-08','D42 GBL','2026-09-12','2026-11-15',NULL,1,NULL);
INSERT INTO "triggers" VALUES('HAVELLS','ALERT',538.0,'2026-09-08','D42','2026-09-12','2026-11-15',NULL,1,NULL);
INSERT INTO "triggers" VALUES('RRKABEL','BUY',776.0,'2026-09-08','D42 GBL','2026-09-12','2026-11-15',NULL,1,NULL);
INSERT INTO "triggers" VALUES('RRKABEL','ALERT',1070.0,'2026-09-08','D42','2026-09-12','2026-11-15',NULL,1,NULL);
INSERT INTO "triggers" VALUES('ULTRACEMCO','ALERT',5820.0,'2026-09-08','D42','2026-09-12','2026-11-15',NULL,1,NULL);
INSERT INTO "triggers" VALUES('TRENT','ALERT',679.0,'2026-09-08','D42','2026-09-12','2026-11-15',NULL,1,NULL);
INSERT INTO "triggers" VALUES('TITAN','ALERT',1209.0,'2026-09-08','D42','2026-09-12','2026-11-15',NULL,1,NULL);
INSERT INTO "triggers" VALUES('HAL','ALERT',4900.0,NULL,'52wk-high marker (watch-crash)','2026-09-01',NULL,NULL,1,'Marker, not a buy level');
INSERT INTO "triggers" VALUES('FEDERALBNK','BUY',215.0,'2026-08-01','1.2x book — PREDATES ROE-linked gate','2026-08-01',NULL,NULL,0,'NOT ARMABLE: re-derive justified P/B (~1.0-1.1x at ROE ~13%)');
INSERT INTO "triggers" VALUES('TMB','BUY',750.0,'2026-08-01','1.36x vs ~1.1x justified','2026-08-01',NULL,NULL,0,'NOT ARMABLE: ran away');
INSERT INTO "triggers" VALUES('INDIGRID','BUY',167.0,'2026-07-04','dip band 165-170 (04-Jul basis)','2026-07-04',NULL,NULL,0,'NOT ARMABLE: stale basis; NAV 146.93 09-Sep; sleeve unfunded');
INSERT INTO "triggers" VALUES('ZYDUSLIFE','BUY',737.0,NULL,'provisional','2026-09-01',NULL,NULL,0,'NOT ARMABLE: basis unknown; universe BUY + OSEP pass = NO ACTION');
INSERT INTO "triggers" VALUES('PARADEEP','ALERT',120.0,'2026-09-17','D61 revisit level','2026-09-17',NULL,NULL,1,'Revisit only, with gates');
INSERT INTO "triggers" VALUES('TEXRAIL','ALERT',80.0,'2026-09-17','D61 revisit level','2026-09-17',NULL,NULL,1,'Revisit only');
COMMIT;