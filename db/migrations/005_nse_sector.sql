-- Migration 005: NSE official sector per name
-- Date: 2026-09-26
--
-- Why: Praveen asked that the UC5 simulation crash each NSE sector. The register's
-- sector_class is the app's own rule class (LENDER, CYCLICAL, ...); NSE's official
-- "Industry" label (Financial Services, Information Technology, ...) is added beside it.
-- Source: db/reference/nse_industry_2026-09-26.csv = niftyindices.com
-- ind_niftytotalmarket_list.csv (Nifty Total Market, ~750 stocks). Matched on the NSE
-- trading symbol (yfinance ticker stem: REC -> RECLTD).
-- Not in the NSE list (19): CUBEINVIT, EMBASSY, GLOBALSURF, GOLDBEES, HINDOILEXP, IDEAFORGE, INDIGRID, JUNIORBEES, MHRIL, MINDSPACE, NIFTYBEES, NXST, PGINVIT, SILVERBEES, SULA, TATAMOTORS, TEXINFRA, ZUARI, ZUARIIND

ALTER TABLE names ADD COLUMN nse_sector TEXT;
ALTER TABLE names ADD COLUMN nse_sector_as_of TEXT;

UPDATE names SET nse_sector = 'Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'ADANIPORTS';
UPDATE names SET nse_sector = 'Automobile and Auto Components', nse_sector_as_of = '2026-09-26' WHERE symbol = 'ARE&M';
UPDATE names SET nse_sector = 'Capital Goods', nse_sector_as_of = '2026-09-26' WHERE symbol = 'ASHOKLEY';
UPDATE names SET nse_sector = 'Consumer Durables', nse_sector_as_of = '2026-09-26' WHERE symbol = 'ASIANPAINT';
UPDATE names SET nse_sector = 'Automobile and Auto Components', nse_sector_as_of = '2026-09-26' WHERE symbol = 'ATHERENERG';
UPDATE names SET nse_sector = 'Capital Goods', nse_sector_as_of = '2026-09-26' WHERE symbol = 'AVALON';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'AXISBANK';
UPDATE names SET nse_sector = 'Automobile and Auto Components', nse_sector_as_of = '2026-09-26' WHERE symbol = 'BAJAJ-AUTO';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'BAJAJFINSV';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'BAJFINANCE';
UPDATE names SET nse_sector = 'Automobile and Auto Components', nse_sector_as_of = '2026-09-26' WHERE symbol = 'BALKRISIND';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'BANKBARODA';
UPDATE names SET nse_sector = 'Consumer Durables', nse_sector_as_of = '2026-09-26' WHERE symbol = 'BATAINDIA';
UPDATE names SET nse_sector = 'Capital Goods', nse_sector_as_of = '2026-09-26' WHERE symbol = 'BEL';
UPDATE names SET nse_sector = 'Telecommunication', nse_sector_as_of = '2026-09-26' WHERE symbol = 'BHARTIARTL';
UPDATE names SET nse_sector = 'Oil Gas & Consumable Fuels', nse_sector_as_of = '2026-09-26' WHERE symbol = 'BPCL';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'BSE';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'CANBK';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'CDSL';
UPDATE names SET nse_sector = 'Chemicals', nse_sector_as_of = '2026-09-26' WHERE symbol = 'CHAMBLFERT';
UPDATE names SET nse_sector = 'Oil Gas & Consumable Fuels', nse_sector_as_of = '2026-09-26' WHERE symbol = 'CHENNPETRO';
UPDATE names SET nse_sector = 'Healthcare', nse_sector_as_of = '2026-09-26' WHERE symbol = 'CIPLA';
UPDATE names SET nse_sector = 'Oil Gas & Consumable Fuels', nse_sector_as_of = '2026-09-26' WHERE symbol = 'COALINDIA';
UPDATE names SET nse_sector = 'Chemicals', nse_sector_as_of = '2026-09-26' WHERE symbol = 'COROMANDEL';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'CUB';
UPDATE names SET nse_sector = 'Fast Moving Consumer Goods', nse_sector_as_of = '2026-09-26' WHERE symbol = 'DABUR';
UPDATE names SET nse_sector = 'Healthcare', nse_sector_as_of = '2026-09-26' WHERE symbol = 'DIVISLAB';
UPDATE names SET nse_sector = 'Healthcare', nse_sector_as_of = '2026-09-26' WHERE symbol = 'DRREDDY';
UPDATE names SET nse_sector = 'Construction', nse_sector_as_of = '2026-09-26' WHERE symbol = 'ENGINERSIN';
UPDATE names SET nse_sector = 'Automobile and Auto Components', nse_sector_as_of = '2026-09-26' WHERE symbol = 'EXIDEIND';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'FEDERALBNK';
UPDATE names SET nse_sector = 'Capital Goods', nse_sector_as_of = '2026-09-26' WHERE symbol = 'FINCABLES';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'FIVESTAR';
UPDATE names SET nse_sector = 'Oil Gas & Consumable Fuels', nse_sector_as_of = '2026-09-26' WHERE symbol = 'GAIL';
UPDATE names SET nse_sector = 'Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'GESHIP';
UPDATE names SET nse_sector = 'Fast Moving Consumer Goods', nse_sector_as_of = '2026-09-26' WHERE symbol = 'GODREJCP';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'GROWW';
UPDATE names SET nse_sector = 'Capital Goods', nse_sector_as_of = '2026-09-26' WHERE symbol = 'HAL';
UPDATE names SET nse_sector = 'Consumer Durables', nse_sector_as_of = '2026-09-26' WHERE symbol = 'HAVELLS';
UPDATE names SET nse_sector = 'Information Technology', nse_sector_as_of = '2026-09-26' WHERE symbol = 'HCLTECH';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'HDFCBANK';
UPDATE names SET nse_sector = 'Automobile and Auto Components', nse_sector_as_of = '2026-09-26' WHERE symbol = 'HEROMOTOCO';
UPDATE names SET nse_sector = 'Telecommunication', nse_sector_as_of = '2026-09-26' WHERE symbol = 'HFCL';
UPDATE names SET nse_sector = 'Metals & Mining', nse_sector_as_of = '2026-09-26' WHERE symbol = 'HINDALCO';
UPDATE names SET nse_sector = 'Metals & Mining', nse_sector_as_of = '2026-09-26' WHERE symbol = 'HINDCOPPER';
UPDATE names SET nse_sector = 'Oil Gas & Consumable Fuels', nse_sector_as_of = '2026-09-26' WHERE symbol = 'HINDPETRO';
UPDATE names SET nse_sector = 'Fast Moving Consumer Goods', nse_sector_as_of = '2026-09-26' WHERE symbol = 'HINDUNILVR';
UPDATE names SET nse_sector = 'Metals & Mining', nse_sector_as_of = '2026-09-26' WHERE symbol = 'HINDZINC';
UPDATE names SET nse_sector = 'Automobile and Auto Components', nse_sector_as_of = '2026-09-26' WHERE symbol = 'HYUNDAI';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'ICICIBANK';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'ICICIPRULI';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'IDFCFIRSTB';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'IIFL';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'INDUSINDBK';
UPDATE names SET nse_sector = 'Information Technology', nse_sector_as_of = '2026-09-26' WHERE symbol = 'INFY';
UPDATE names SET nse_sector = 'Oil Gas & Consumable Fuels', nse_sector_as_of = '2026-09-26' WHERE symbol = 'IOC';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'IRFC';
UPDATE names SET nse_sector = 'Fast Moving Consumer Goods', nse_sector_as_of = '2026-09-26' WHERE symbol = 'ITC';
UPDATE names SET nse_sector = 'Consumer Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'ITCHOTELS';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'JIOFIN';
UPDATE names SET nse_sector = 'Forest Materials', nse_sector_as_of = '2026-09-26' WHERE symbol = 'JKPAPER';
UPDATE names SET nse_sector = 'Metals & Mining', nse_sector_as_of = '2026-09-26' WHERE symbol = 'JSWSTEEL';
UPDATE names SET nse_sector = 'Fast Moving Consumer Goods', nse_sector_as_of = '2026-09-26' WHERE symbol = 'JYOTHYLAB';
UPDATE names SET nse_sector = 'Consumer Durables', nse_sector_as_of = '2026-09-26' WHERE symbol = 'KALYANKJIL';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'KARURVYSYA';
UPDATE names SET nse_sector = 'Capital Goods', nse_sector_as_of = '2026-09-26' WHERE symbol = 'KEI';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'LICI';
UPDATE names SET nse_sector = 'Construction', nse_sector_as_of = '2026-09-26' WHERE symbol = 'LT';
UPDATE names SET nse_sector = 'Automobile and Auto Components', nse_sector_as_of = '2026-09-26' WHERE symbol = 'M&M';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'MANAPPURAM';
UPDATE names SET nse_sector = 'Healthcare', nse_sector_as_of = '2026-09-26' WHERE symbol = 'MANKIND';
UPDATE names SET nse_sector = 'Automobile and Auto Components', nse_sector_as_of = '2026-09-26' WHERE symbol = 'MARUTI';
UPDATE names SET nse_sector = 'Information Technology', nse_sector_as_of = '2026-09-26' WHERE symbol = 'MASTEK';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'MUTHOOTFIN';
UPDATE names SET nse_sector = 'Healthcare', nse_sector_as_of = '2026-09-26' WHERE symbol = 'NATCOPHARM';
UPDATE names SET nse_sector = 'Fast Moving Consumer Goods', nse_sector_as_of = '2026-09-26' WHERE symbol = 'NESTLEIND';
UPDATE names SET nse_sector = 'Power', nse_sector_as_of = '2026-09-26' WHERE symbol = 'NTPC';
UPDATE names SET nse_sector = 'Oil Gas & Consumable Fuels', nse_sector_as_of = '2026-09-26' WHERE symbol = 'ONGC';
UPDATE names SET nse_sector = 'Chemicals', nse_sector_as_of = '2026-09-26' WHERE symbol = 'PARADEEP';
UPDATE names SET nse_sector = 'Oil Gas & Consumable Fuels', nse_sector_as_of = '2026-09-26' WHERE symbol = 'PETRONET';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'PFC';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'PNB';
UPDATE names SET nse_sector = 'Capital Goods', nse_sector_as_of = '2026-09-26' WHERE symbol = 'POLYCAB';
UPDATE names SET nse_sector = 'Power', nse_sector_as_of = '2026-09-26' WHERE symbol = 'POWERGRID';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'REC';
UPDATE names SET nse_sector = 'Oil Gas & Consumable Fuels', nse_sector_as_of = '2026-09-26' WHERE symbol = 'RELIANCE';
UPDATE names SET nse_sector = 'Construction', nse_sector_as_of = '2026-09-26' WHERE symbol = 'RITES';
UPDATE names SET nse_sector = 'Capital Goods', nse_sector_as_of = '2026-09-26' WHERE symbol = 'RRKABEL';
UPDATE names SET nse_sector = 'Consumer Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'RTNINDIA';
UPDATE names SET nse_sector = 'Metals & Mining', nse_sector_as_of = '2026-09-26' WHERE symbol = 'SAIL';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'SBIN';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'SOUTHBANK';
UPDATE names SET nse_sector = 'Healthcare', nse_sector_as_of = '2026-09-26' WHERE symbol = 'SUNPHARMA';
UPDATE names SET nse_sector = 'Power', nse_sector_as_of = '2026-09-26' WHERE symbol = 'TATAPOWER';
UPDATE names SET nse_sector = 'Metals & Mining', nse_sector_as_of = '2026-09-26' WHERE symbol = 'TATASTEEL';
UPDATE names SET nse_sector = 'Information Technology', nse_sector_as_of = '2026-09-26' WHERE symbol = 'TCS';
UPDATE names SET nse_sector = 'Capital Goods', nse_sector_as_of = '2026-09-26' WHERE symbol = 'TEXRAIL';
UPDATE names SET nse_sector = 'Consumer Durables', nse_sector_as_of = '2026-09-26' WHERE symbol = 'THANGAMAYIL';
UPDATE names SET nse_sector = 'Consumer Durables', nse_sector_as_of = '2026-09-26' WHERE symbol = 'TITAN';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'TMB';
UPDATE names SET nse_sector = 'Capital Goods', nse_sector_as_of = '2026-09-26' WHERE symbol = 'TMCV';
UPDATE names SET nse_sector = 'Consumer Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'TRENT';
UPDATE names SET nse_sector = 'Construction Materials', nse_sector_as_of = '2026-09-26' WHERE symbol = 'ULTRACEMCO';
UPDATE names SET nse_sector = 'Fast Moving Consumer Goods', nse_sector_as_of = '2026-09-26' WHERE symbol = 'VBL';
UPDATE names SET nse_sector = 'Information Technology', nse_sector_as_of = '2026-09-26' WHERE symbol = 'WIPRO';
UPDATE names SET nse_sector = 'Financial Services', nse_sector_as_of = '2026-09-26' WHERE symbol = 'YESBANK';
UPDATE names SET nse_sector = 'Healthcare', nse_sector_as_of = '2026-09-26' WHERE symbol = 'ZYDUSLIFE';
