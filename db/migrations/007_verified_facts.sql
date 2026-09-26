-- Migration 007: facts verified online (26-Sep-2026) — brand ownership, results dates
--
-- Praveen 26-Sep: "find it from online and record them". Every value below is cited.
--
-- 1. FMCG brand ownership (osep v7 §G hard gate; migration 006 left these NULL)
--    ITC 1        — Aashirvaad, Sunfeast, Bingo! wholly owned by ITC (ITC annual report; Wikipedia)
--    DABUR 1      — DABUR, HAJMOLA, VATIKA registered to Dabur India Ltd (Justia trademarks)
--    GODREJCP 1   — owns Cinthol, Good Knight, HIT; 7,000+ trademarks (godrejcp.com; Legal500)
--    JYOTHYLAB 1  — owns Ujala, Exo, Maxo, Margo; Henko on lifetime licence; Pril/Fa licences
--                   NOT renewed by Henkel after 31-May-2026 (afaqs; finshots)
--    SULA 1       — owns Sula, RASA, Dindori, The Source, York (company profile)
--    HINDUNILVR 0 — pays Unilever 3.45% of turnover for "Unilever owned trademarks" (hul.co.in 2023)
--    NESTLEIND 0  — pays Nestlé S.A. ~4.5% of sales royalty for trademarks/IP (Swadeshi Index)
--    BATAINDIA 0  — Bata trademark owned by Bata Brands S.A.; Bata India pays royalty (Justia)
-- 2. Results dates where Yahoo is wrong or stale (checked against company/exchange news)
--    M&M 2026-07-30        — Yahoo said 2026-09-10 (mahindra.com "M&M Results Q1 F27")
--    ENGINERSIN 2026-08-13 — Yahoo latest was 2024-10-29 (Investing.com Q1 FY27 slides)
--    RITES 2026-08-04      — Yahoo latest was 2026-05-19 (sahi.com; Whalesbook board notice)
--    PARADEEP 2026-07-31   — Yahoo latest was 2025-02-04 (Investing.com; EquityBulls)
--    TEXRAIL 2026-08-03    — Yahoo latest was 2019-05-13 (Whalesbook; metrorailnews)
--    A verified date replaces Yahoo's list until valid_until (next quarter end + 14 days);
--    after that the name fails closed until re-verified — October results can't slip past.
-- 3. policy results_max_age_days = 150: SEBI LODR Reg 33 — results within 45 days of a
--    quarter end (60 for Q4), so the latest real result is never ~150+ days old. An older
--    "latest" from Yahoo is stale data → unknown → trigger not armed (E3/E9).

UPDATE names SET brand_owned = 1 WHERE symbol IN ('ITC','DABUR','GODREJCP','JYOTHYLAB','SULA');
UPDATE names SET brand_owned = 0 WHERE symbol IN ('HINDUNILVR','NESTLEIND','BATAINDIA');

CREATE TABLE results_verified (
  symbol       TEXT PRIMARY KEY,
  last_result  TEXT NOT NULL,   -- ISO date of the latest results announcement
  valid_until  TEXT NOT NULL,   -- after this the row is ignored and the name fails closed
  source       TEXT NOT NULL,
  verified_on  TEXT NOT NULL
);
INSERT INTO results_verified VALUES
 ('M&M','2026-07-30','2026-10-14','mahindra.com press release M&M Results Q1 F27','2026-09-26'),
 ('ENGINERSIN','2026-08-13','2026-10-14','Investing.com Engineers India Q1 FY27 slides','2026-09-26'),
 ('RITES','2026-08-04','2026-10-14','sahi.com RITES Q1 FY2027; board meeting 4-Aug','2026-09-26'),
 ('PARADEEP','2026-07-31','2026-10-14','Investing.com Paradeep Q1 FY27 slides','2026-09-26'),
 ('TEXRAIL','2026-08-03','2026-10-14','Whalesbook / metrorailnews Texmaco Q1 FY27','2026-09-26');

INSERT INTO policy VALUES ('results_max_age_days','150','days',
 'SEBI LODR Reg 33 (45d quarter / 60d Q4) — migration 007','2026-09-26');
