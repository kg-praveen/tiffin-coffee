# First Claude Code session — paste this
Read CLAUDE.md, then spec/tiffin-coffee.SKILL.md, spec/osep-stock-analysis.SKILL.md (the ENGINE CONTRACT
and §SC/§G), and db/README-DATA.md. Do not write engine logic yet.
Task 1 — tools with stamps: implement `tools/stamped.py` (frozen pydantic `Stamped[T]`), `tools/prices.py`
(yfinance: last close, 52-week low/high, as fetched-at), `tools/gsec.py` (India 10Y yield). Each tool has a
recorded-fixture test that runs with no network and a test that fails if a value is returned unstamped.
Task 2 — `store/` repository over db/pattaz.db (read policy, names, triggers, holdings; append sessions).
Task 3 — verify every `names.yf_ticker` resolves via tools/prices; set ticker_verified=1 via a migration;
list the ones that don't for Praveen.
Then stop and show me the test results before UC1.
