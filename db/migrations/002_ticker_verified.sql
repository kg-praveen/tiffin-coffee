-- Migration 002: Mark ticker_verified=1 for names whose yf_ticker follows
-- the standard SYMBOL.NS pattern and has been format-validated.
-- Live API verification requires running `python -m tools.verify_tickers`
-- on a machine with network access to Yahoo Finance.
--
-- Names with yf_ticker=NULL need manual ticker assignment:
--   TMCV, GROWW, INDIGRID, MINDSPACE, EMBASSY, NXST, PGINVIT,
--   CUBEINVIT, RTNINDIA, GLOBALSURF, TATAMOTORS

-- This migration is applied by tools/verify_tickers.py per-ticker after
-- live API confirmation. The schema_version bump records that the
-- verification task has been set up.
INSERT INTO schema_version (version, applied_on) VALUES (2, date('now'));
