-- Migration 010: UC4 OSEP analyser — judgments, verdict log, thesis type, policy
-- Date: 2026-09-26
--
-- Why: osep v7 splits into data checks (engine/osep.py) and judgments researched in
-- chat with a cited source (CLAUDE.md §9: re-underwriting is a chat job; the DB records
-- the outcome). "VERDICT CHANGES ARE FIRST-CLASS: log old verdict, new verdict, and
-- REASON. Never silently overwrite." (osep v7 §VERDICT DECAY CLOCK)

CREATE TABLE osep_judgments (
  symbol   TEXT NOT NULL,
  item     TEXT NOT NULL,    -- sovereign_directed | thesis_verifiable | governance_clean |
                             -- industry_durable | investable | stage1_score | thesis_type |
                             -- promoter_exempt | sector_class
  value    TEXT NOT NULL,
  source   TEXT NOT NULL,    -- where the answer came from (URL / filing / Praveen)
  as_of    TEXT NOT NULL,
  PRIMARY KEY (symbol, item)
);

CREATE TABLE osep_verdicts (   -- append-only
  run_id      TEXT NOT NULL,
  symbol      TEXT NOT NULL,
  decided_on  TEXT NOT NULL,
  old_bucket  TEXT,
  new_bucket  TEXT NOT NULL,
  thesis_type TEXT,
  trigger     REAL,
  expiry      TEXT,
  reason      TEXT NOT NULL,
  PRIMARY KEY (run_id, symbol)
);

ALTER TABLE names ADD COLUMN thesis_type TEXT;

INSERT INTO policy VALUES
 ('decay_hard_pass_days','180','days','osep v7 §VERDICT DECAY CLOCK — migration 010','2026-09-26'),
 ('stage1_gate','35','points of 50','osep v7 §STAGE 1 gate — migration 010','2026-09-26'),
 ('promoter_net_sell_flag_pct','2','pct of equity, trailing 12m','osep v7 §STAGE 0 P4 — migration 010','2026-09-26');
