-- Migration 014: UC3 plate ranker — criteria order
-- Date: 2026-09-26
--
-- Why: the ranker (engine/ranker.py) orders legal plate variants LEXICOGRAPHICALLY by
-- criteria that each trace to spec text — no weights. E2: the order is policy, not code.
--   ticket_band  tiffin v4 §TICKET SIZE ("Praveen's ₹5-10K band [POLICY]")
--   no_raise     Praveen 26-Sep-2026 sizing (plan raised only when 1 share each costs more)
--   breadth      tiffin v6 §BREADTH TARGET ("8-15 names per session")
--   residual     tiffin v6 §formula STEP 6 ("residual → BeES Floor")
-- Ticket band and breadth bounds reuse the existing policy rows ticket_band_min/max and
-- breadth_min/max. Order proposed by the build; Praveen to confirm (open question).

INSERT OR IGNORE INTO policy VALUES ('ranker_criteria_order','ticket_band,no_raise,breadth,residual',
 'criteria, best first','UC3 ranker — tiffin v4 §TICKET SIZE, v6 §BREADTH TARGET, v6 STEP 6 — migration 014',
 '2026-09-26');
