-- Migration 004: book P-mult roster, hold-only flag, first-bite policy constants
-- Date: 2026-09-21
--
-- Why: the plate audit of 20-Sep showed P-tier running on a partial holdings table
-- and hold-only names (ITC, Wipro, HCL) reaching the plate via H. Until UC2.1
-- syncs holdings, P comes from the pattaz-book §4 roster; hold-only names get a
-- hard flag instead of a note.
--
-- 1. names.p_mult_book — pattaz-book §4 P-BOARD as-of 06-Sep (LEDGER-CACHE)
-- 2. names.flag_no_add — pattaz-book §5/§6 "museum" / "hold-only" / "hold, no add"
-- 3. policy: first-bite constants from tiffin-coffee v5 §first-bite (E2: no bare numbers)

ALTER TABLE names ADD COLUMN p_mult_book REAL;
ALTER TABLE names ADD COLUMN flag_no_add INTEGER NOT NULL DEFAULT 0;

-- 1. pattaz-book §4: "HDFC Bank BLOCKED · ITC 0.5 · Hero 0.5 · Infosys 1.0 ·
--    Muthoot 1.0 · TCS 1.0 · Petronet 1.0 · M&M 1.0"
UPDATE names SET p_mult_book = 0.0 WHERE symbol = 'HDFCBANK';
UPDATE names SET p_mult_book = 0.5 WHERE symbol IN ('ITC', 'HEROMOTOCO');
UPDATE names SET p_mult_book = 1.0 WHERE symbol IN ('INFY', 'MUTHOOTFIN', 'TCS', 'PETRONET', 'M&M');

-- 2. pattaz-book §5/§6: Wipro museum (D48) · HCL museum (Varshu) · ITC "hold, no add" ·
--    Hero "hold-only" · 2W FULL museum (Hero + Bajaj) · HAL/BEL "WATCH-ONLY UNTIL A CRASH"
UPDATE names SET flag_no_add = 1
WHERE symbol IN ('ITC', 'WIPRO', 'HCLTECH', 'HEROMOTOCO', 'BAJAJ-AUTO', 'HAL', 'BEL');

-- 3. first-bite constants (tiffin-coffee v5 §first-bite: L ≤ 2%, H-mult floor 0.25, qty ≤ 5)
INSERT INTO policy (key, value, unit, source, adopted_on) VALUES
  ('first_bite_l_max', '2', 'pct above 52wk low', 'tiffin v5 §first-bite (a)', '2026-09-21'),
  ('first_bite_h_mult_floor', '0.25', 'mult', 'tiffin v5 §first-bite', '2026-09-21'),
  ('first_bite_qty_max', '5', 'shares', 'tiffin v5 §first-bite', '2026-09-21');

INSERT INTO schema_version (version, applied_on) VALUES (4, '2026-09-21');
