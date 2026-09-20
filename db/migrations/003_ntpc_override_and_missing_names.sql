-- Migration 003: NTPC conviction override, add missing names, ticker fixes
-- Date: 2026-09-20
--
-- 1. NTPC: remove Coal India exit condition from trigger (CONVICTION-OVERRIDE)
-- 2. Add 4 missing pattaz names: HUL, Asian Paints, Maruti, ICICI Prudential
-- 3. Jyothy Labs: flag for re-evaluation (NEVER_ADD → WATCH)
-- 4. Fix broken tickers: REC → RECLTD, THANGAMAYIL → THANGAMAYL

-- 1. NTPC trigger: remove Coal India exit condition
UPDATE triggers
SET notes = 'CONVICTION-OVERRIDE 2026-09-20: Coal India exit condition waived by Praveen'
WHERE symbol = 'NTPC' AND kind = 'BUY';

-- 2. Add missing names
INSERT INTO names (symbol, name, yf_ticker, status, bucket, sector_class, classified_on, classification_source, as_of)
VALUES
  ('HINDUNILVR', 'Hindustan Unilever', 'HINDUNILVR.NS', 'WATCH', NULL, 'FMCG', '2026-09-20', 'manual:sector-obvious', '2026-09-20'),
  ('ASIANPAINT', 'Asian Paints', 'ASIANPAINT.NS', 'WATCH', NULL, 'DEFAULT', '2026-09-20', 'manual:sector-obvious', '2026-09-20'),
  ('MARUTI', 'Maruti Suzuki', 'MARUTI.NS', 'WATCH', NULL, 'AUTO_OEM', '2026-09-20', 'manual:sector-obvious', '2026-09-20'),
  ('ICICIPRULI', 'ICICI Prudential Life', 'ICICIPRULI.NS', 'WATCH', NULL, 'INSURER', '2026-09-20', 'manual:sector-obvious', '2026-09-20');

-- 3. Jyothy Labs: re-evaluate (move from NEVER_ADD to WATCH, preserve E6 note)
UPDATE names
SET status = 'WATCH',
    notes = COALESCE(notes, '') || '; Re-evaluation flagged 2026-09-20; was NEVER_ADD',
    as_of = '2026-09-20'
WHERE symbol = 'JYOTHYLAB';

-- 4. Fix broken tickers (both are NEVER_ADD, but data should still be correct)
UPDATE names
SET yf_ticker = 'RECLTD.NS',
    ticker_verified = 0,
    as_of = '2026-09-20'
WHERE symbol = 'REC';

UPDATE names
SET yf_ticker = 'THANGAMAYL.NS',
    ticker_verified = 0,
    as_of = '2026-09-20'
WHERE symbol = 'THANGAMAYIL';
