-- Migration 008: results-week pause (event hold)
-- Date: 2026-09-26
--
-- Why: tiffin-coffee v6 §procedure step 6 — "EVENT HOLD: earnings within 5 calendar
-- days → hold that plate unless Praveen opts in ('event risk, your call')".
-- E2: the 5 lives in policy, not in code.

INSERT INTO policy VALUES ('event_hold_days','5','days',
 'tiffin-coffee v6 §procedure step 6 — migration 008','2026-09-26');
