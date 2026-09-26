-- Migration 009: register catches up with ledger v4.10 (26-Sep) + D69/D70
-- Date: 2026-09-26
--
-- Source: ../tiffin-coffee/investing_plans/PATTAZ_MASTER_LEDGER_v4.10_2026-09-26.txt
-- (Drive upload pending: the Drive connector returned 403) and
-- ../tiffin-coffee/investing_plans/handoff_25sep2026.md §"Decisions 26-Sep" (D69, D70,
-- "go into ledger v4.11"). Holdings: db/holdings/household_equity_25sep2026.csv.

-- ---------------------------------------------------------------- decisions --
INSERT INTO decisions VALUES
 (65,'2026-09-25','IT cell swap: R Systems becomes IT add #2 (GBN 251, spec <=1%); TCS HOLD-no-add',
  'Praveen decision (a). Infosys stays add #1. TCS at fair, flat USD revenue FY26.','CLOSED'),
 (66,'2026-09-25','Trigger source: ledger §7 is authoritative; local board_config.csv is a derivative',
  'Superseded 21-Sep local levels are NOT on the board unless re-proposed and confirmed.','CLOSED'),
 (67,'2026-09-25','One-time overrides: Jyothy 10, Manappuram 5, Natco 4, HDFC Bank 5 — rules stand',
  'Deliberate buys outside the rules; the crossed rules stay in force for future plates.','CLOSED'),
 (68,'2026-09-25','20/22-Sep plates executed; 25-Sep Rs10K plate carried to Mon 28-Sep',
  'Broker exports 25-Sep. Re-price before placing.','CLOSED'),
 (69,'2026-09-26','IT gate change: USD operating profit per share + margin + bookings (not USD revenue)',
  'Rupee drift = upside, never a gate input. osep skill patch queued; engine note only until data exists.','CLOSED'),
 (70,'2026-09-26','Wipro caps-off first bite, Mon 28-Sep ONLY (Anand live consider 20-Sep, D6/D44)',
  'IT two-add cell block waived for one first bite, 1-10 clamp. D48 HOLD stands afterwards; permanent call at Q2 FY27.','CLOSED');

-- -------------------------------------------------------------------- names --
INSERT INTO names (symbol, name, yf_ticker, ticker_verified, cell, sector_class, classified_on,
  classification_source, status, bucket, verdict_date, decay_expiry, p5_status, p5_note_ref,
  flag_sovereign, flag_psu, flag_cyclical, flag_probe_open, flag_fraud_tail, flag_exit_decided,
  notes, as_of, p_mult_book, flag_no_add, nse_sector, nse_sector_as_of, brand_owned)
VALUES ('RSYSTEMS','R Systems International','RSYSTEMS.NS',1,'IT','IT_SERVICES','2026-09-25',
  'ledger v4.10 §5/§7 (D65)','ADD','GBN','2026-09-25','2026-10-25',NULL,NULL,
  0,0,0,0,0,0,
  'D65 IT add #2, spec <=1% household. Blackstone 51.85% promoter (PE sponsor, future OFS overhang). Novigo acquisition inflates growth until Q4 CY26. Solvency passes.',
  '2026-09-26',NULL,0,NULL,NULL,NULL);

UPDATE names SET status = 'HOLD', flag_no_add = 1,
  notes = 'D65 (25-Sep): HOLD-no-add — add slot moved to R Systems. At fair; flat USD revenue FY26.'
  WHERE symbol = 'TCS';
UPDATE names SET notes = 'D48 hold-no-add. D70: one caps-off first bite allowed on Mon 28-Sep only; permanent IT-cell call at Q2 FY27 (needs USD revenue turning, EBIT toward 17%).'
  WHERE symbol = 'WIPRO';
-- ledger v4.10 §14 0b: "Until ruled, both are NO ACTION" (solvency kill-switch on utilities)
UPDATE names SET flag_probe_open = 1,
  notes = 'E6 OPEN (ledger §14 0b): literal osep solvency kill-switch vs tariff-recovered-debt carve-out — NO ACTION until Praveen rules. ' || notes
  WHERE symbol IN ('NTPC','POWERGRID');
-- ledger v4.10 §7 + §14 1(v): hockey-level H = reserve decision (explicit yes) + Dahej funding gate
UPDATE names SET flag_probe_open = 1,
  notes = 'Reserve decision pending (ledger §14 1(v)): H>1.15 is HOCKEY = reserve, not the daily ticket; needs explicit yes + Dahej funding disclosure. ' || notes
  WHERE symbol = 'PETRONET';

-- ----------------------------------------------------------------- triggers --
INSERT INTO triggers (symbol, kind, level, basis_eps_date, derivation, set_on, valid_until,
  gtt_id, active, notes)
VALUES ('RSYSTEMS','BUY',251,'2026-09-24','14.18x fair x TTM EPS ~17.7 (ledger v4.10 §7, D65)',
  '2026-09-25','2026-10-25',NULL,1,'24-Sep price 237, P/E 13.4, 52wk 214-447');
UPDATE triggers SET active = 0, notes = 'D65: TCS HOLD-no-add — no longer a trigger item'
  WHERE symbol = 'TCS';

-- -------------------------------------------------------------------- cells --
UPDATE cells SET members = 'INFY,RSYSTEMS,TCS,WIPRO,HCLTECH', active_adds = 'INFY,RSYSTEMS',
  notes = 'D65: R Systems add #2, TCS hold-no-add; Wipro hold-no-add (D48; D70 one-day waiver); HCL museum'
  WHERE cell = 'IT';

-- ------------------------------------------------------ one-day caps-off waiver --
CREATE TABLE caps_off_waivers (
  symbol    TEXT NOT NULL,
  valid_on  TEXT NOT NULL,       -- the ONE session date the waiver applies to
  decision  TEXT NOT NULL,       -- register reference, e.g. D70
  note      TEXT,
  PRIMARY KEY (symbol, valid_on)
);
INSERT INTO caps_off_waivers VALUES ('WIPRO','2026-09-28','D70',
  'IT two-add cell block + hold-no-add waived for ONE first bite; 1-10 clamp');
