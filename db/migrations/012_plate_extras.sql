-- Migration 012: plate extras — HOCKEY market triggers the engine could not see
-- Date: 2026-09-26
--
-- Why: tiffin-coffee v6 §H table, HOCKEY row: ">1.15, or Nifty −5% in a week, or a
-- name −10% in a day with no Stage-0 cause". The H>1.15 part was already in code; the
-- two market thresholds were not in `policy` (E2: no bare numbers in engine/).
-- The ladder rungs (hockey_rung1/2_nifty_drawdown_pct, ledger D37), the reserve floor,
-- single_deployment_cap_pct and two_pocket_split already exist — not repeated here.
-- Values are stored as positive magnitudes of a FALL, like the rung rows.

INSERT INTO policy VALUES
 ('hockey_nifty_week_fall_pct','5','pct fall of Nifty over a week','tiffin v6 §H HOCKEY row — migration 012','2026-09-26'),
 ('hockey_name_day_fall_pct','10','pct fall of one name in a day','tiffin v6 §H HOCKEY row — migration 012','2026-09-26');
