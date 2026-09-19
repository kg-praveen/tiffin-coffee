"""db/seed_build.py — build db/pattaz.db from schema.sql + the ledger v4.9 seed (2026-09-19).

Provenance: ★★★ PATTAZ MASTER LEDGER v4.9 (17-Sep-2026) + the v8 LEDGER APPENDIX.
Every row carries an as_of / set_on date. Numbers here are STATE (ledger-cache with
dates), never live inputs — the engine re-fetches prices every run (spec E2/E3).
Run:  python db/seed_build.py   → overwrites db/pattaz.db and writes db/seed.sql
"""
from __future__ import annotations
import sqlite3, pathlib, datetime as dt

HERE = pathlib.Path(__file__).parent
DB, SCHEMA, DUMP = HERE / "pattaz.db", HERE / "schema.sql", HERE / "seed.sql"
LEDGER = "2026-09-17"      # ledger v4.9 date — default as_of
BOARD = "2026-09-12"       # D54 re-derived trigger board
EPS_BASIS = "2026-09-01"   # fresh-EPS rebuild (Q1 FY27 results basis)
VALID = "2026-11-15"       # re-verify at the Q2 FY27 print (E3)

def exp(verdict: str, days: int) -> str:
    return (dt.date.fromisoformat(verdict) + dt.timedelta(days=days)).isoformat()

# ---------------------------------------------------------------- names ---
# (symbol, name, yf, cell, cls, status, bucket, verdict, decay, p5, p5ref, sov, psu, cyc, probe, fraud, exit, notes)
N: list[tuple] = []
def n(symbol, name, cell, cls, status, bucket=None, verdict=None, decay=None, p5=None, p5ref=None,
      sov=0, psu=0, cyc=0, probe=0, fraud=0, exit_=0, notes=None, yf="", classified=True):
    N.append((symbol, name, (f"{symbol}.NS" if yf == "" else yf), cell, cls,
              LEDGER if (cls and classified) else None, "ledger v4.9 §5/§7" if cls else None,
              status, bucket, verdict, decay, p5, p5ref, sov, psu, cyc, probe, fraud, exit_, notes, LEDGER))

GBN, GBL = exp(BOARD, 30), exp(BOARD, 90)
# --- live board (D54, 12-Sep) ---
n("PETRONET","Petronet LNG","ENERGY_GAS","REGULATED","ADD","GBN",BOARD,GBN,psu=1,notes="Tranches gated on Dahej funding disclosure; re-underwrite if D/E>0.5")
n("NTPC","NTPC","POWER","REGULATED","ADD","GBN",BOARD,GBN,psu=1,notes="Conditional on the Coal India exit (same cell)")
n("INFY","Infosys","IT","IT_SERVICES","ADD","GBN",BOARD,GBN,notes="Gate on USD/CC revenue, never INR PAT")
n("TCS","Tata Consultancy Services","IT","IT_SERVICES","ADD","GBN",BOARD,GBN,notes="Re-verify at Oct Q2")
n("ITC","ITC","FMCG","FMCG","HOLD","OWNED",BOARD,None,"BUY",notes="Hold, no add; crash-shelf 228; income-floor claim withdrawn until dividend prints")
n("ARE&M","Amara Raja Energy & Mobility","ANCILLARY","AUTO_ANCILLARY","ADD","GBL",BOARD,GBL,notes="HALF-PLATE only (EBITDA margin compression); universe veto at reduced weight",yf="ARE&M.NS")
n("RELIANCE","Reliance Industries","ENERGY_GAS",None,"HOLD","OWNED",BOARD,None,"AGREE_NOTE","ledger §8 05-Sep",notes="Conglomerate: classify at runtime (SC edge rule, strictest gate); P5 AGREE = hold",classified=False)
n("WIPRO","Wipro","IT","IT_SERVICES","HOLD","OWNED",BOARD,None,notes="D48 hold-no-add; swap SOURCE (shrinks in USD)")
n("M&M","Mahindra & Mahindra","AUTO_PV_FARM","AUTO_OEM","ADD","GBL",BOARD,GBL,notes="Designated add",yf="M&M.NS")
n("HCLTECH","HCL Technologies","IT","IT_SERVICES","HOLD","OWNED",BOARD,None,notes="Museum (Varshu); no add")
n("ENGINERSIN","Engineers India","CAPGOODS_PSU","DEFAULT","ADD","GBL",BOARD,GBL,psu=1,notes="Prices commercially (regulated≠directed)")
n("RITES","RITES","CAPGOODS_PSU","DEFAULT","ADD","GBL",BOARD,GBL,psu=1)
n("POWERGRID","Power Grid Corp","POWER","REGULATED","ADD","GBL",BOARD,GBL,psu=1,notes="Was ABOVE trigger on 12-Sep — dropped from buy band; trigger stands")
n("SBIN","State Bank of India","LENDING_BANKS","LENDER","ADD","GBL",BOARD,GBL,psu=1,notes="At justified P/B ~1.6x; PSU cap applies")
n("HDFCBANK","HDFC Bank","LENDING_BANKS","LENDER","HOLD","OWNED",BOARD,None,"AGREE_NOTE","ledger §8 05-Sep",notes="P-board BLOCKED (at/over target); crash-shelf ~419 (D47); 10-Sep 5sh = control exception D62")
n("MUTHOOTFIN","Muthoot Finance","GOLD_NBFC","LENDER","ADD","GBN",BOARD,GBN,"DISAGREE_NOTE","ledger §8 05-Sep (approved, unlocked)",notes="Starter only; tripwires: gold −20% · RBI LTV · ROE floor · P/B above his objection")
n("FIVESTAR","Five-Star Business Finance","LENDING_BANKS","LENDER","HOLD","OWNED",BOARD,None,notes="D53 HOLD")
n("CHAMBLFERT","Chambal Fertilisers","AGRI_INPUTS","CYCLICAL","ADD","GBN","2026-09-17",exp("2026-09-17",30),cyc=1,notes="D59/D61 starter 10sh; NEXT BUY 10sh ≤415; tranche-2 gated on FY27 OCF/PAT toward 70%+; kill <~40% with rising borrowings; subsidy rule D60")
n("COROMANDEL","Coromandel International","AGRI_INPUTS","CYCLICAL","WATCH","GBL",BOARD,GBL,cyc=1,notes="Trigger 1,225 (far); subsidy-linked sovereign flag per D60 check")
# --- wires cluster (D42 GBL) ---
for s,nm in [("FINCABLES","Finolex Cables"),("POLYCAB","Polycab India"),("KEI","KEI Industries"),("HAVELLS","Havells India"),("RRKABEL","RR Kabel")]:
    n(s,nm,"WIRES_GBL","DEFAULT","WATCH","GBL","2026-09-08",exp("2026-09-08",90),notes="D42: HARD PASS at price; re-underwrite after 2-3 qtrs of Ultravolt/Adani volume data")
# --- alerts / watch-crash ---
n("ULTRACEMCO","UltraTech Cement","CEMENT","CYCLICAL","WATCH","HARD_PASS","2026-09-08",None,cyc=1,notes="D42 HP; alert 5,820")
n("TRENT","Trent","RETAIL","RETAIL","WATCH","HARD_PASS","2026-09-08",None,notes="D42 HP; alert 679")
n("TITAN","Titan Company","RETAIL","RETAIL","WATCH","WATCH_CRASH",None,None,"AVOID",notes="Diamond needle (75-90x); alert 1,209")
n("HAL","Hindustan Aeronautics","DEFENCE","DEFENCE","HOLD","OWNED",None,None,psu=1,notes="Defence cell FULL; crash-shelf name; working-capital objection logged; 52wk-high marker ~4,900")
n("BEL","Bharat Electronics","DEFENCE","DEFENCE","HOLD","OWNED",None,None,psu=1,notes="Defence cell FULL; crash-shelf")
n("LT","Larsen & Toubro","DEFENCE","DEFAULT","WATCH","WATCH_CRASH",None,None,notes="Crash-shelf only")
n("ADANIPORTS","Adani Ports","PORTS","DEFAULT","WATCH","WATCH_CRASH")
n("NESTLEIND","Nestle India","FMCG","FMCG","WATCH","WATCH_CRASH",None,None,"HOLD",notes="~50x; 'Nifty-50 consider, Sensex no'")
n("KALYANKJIL","Kalyan Jewellers","RETAIL","RETAIL","WATCH","WATCH_CRASH",None,None,notes="FOCO-model risk (gate: own-store vs franchise)")
n("TMCV","Tata Motors CV (post-demerger)","CV","AUTO_OEM","HOLD","OWNED",None,None,notes="D44 museum-no-more; E indeterminate post demerger — classify each entity fresh",yf=None)
n("BAJFINANCE","Bajaj Finance","LENDING_BANKS","LENDER","WATCH","WATCH_CRASH",None,None,"AVOID",notes="5.6x book vs ~1.9x justified")
n("EXIDEIND","Exide Industries","ANCILLARY","AUTO_ANCILLARY","WATCH","WITHDRAWN",None,None,"AVOID",notes="Withdrawn (44x), not lowered")
# --- withdrawn / hard pass / sovereign ---
n("GAIL","GAIL India","ENERGY_GAS","REGULATED","WATCH","WITHDRAWN",None,None,psu=1,notes="Withdrawn")
n("BALKRISIND","Balkrishna Industries","ANCILLARY","AUTO_ANCILLARY","HOLD","OWNED",None,None,notes="Owned; withdrawn at 33x")
n("SUNPHARMA","Sun Pharmaceutical","PHARMA_DOMESTIC","PHARMA","HOLD","OWNED",None,None,notes="Cell FULL; 37x withdrawn")
n("CIPLA","Cipla","PHARMA_DOMESTIC","PHARMA","HOLD","OWNED",None,None,notes="Cell FULL; 34x (Goa plant — trailing overstated, small flag)")
n("MANKIND","Mankind Pharma","PHARMA_DOMESTIC","PHARMA","HOLD","OWNED",None,None,notes="D33d hold")
n("BHARTIARTL","Bharti Airtel","TELECOM","DEFAULT","HOLD","OWNED",None,None,notes="~42x; no add")
n("ONGC","ONGC","ENERGY_GAS","CYCLICAL","NEVER_ADD","HARD_PASS",None,None,sov=1,psu=1,cyc=1,notes="P1 sovereign; cheapest-on-H trap (overlay 2 worked case)")
for s,nm in [("IOC","Indian Oil"),("BPCL","BPCL"),("HINDPETRO","HPCL")]:
    n(s,nm,"ENERGY_GAS","CYCLICAL","NEVER_ADD","HARD_PASS",None,None,sov=1,psu=1,cyc=1,notes="OMC — P1 directed pricing")
n("BANKBARODA","Bank of Baroda","LENDING_BANKS","LENDER","WATCH","WITHDRAWN",None,None,psu=1,fraud=1,notes="0.7x book passes P/B; legacy-fraud tail (overlay 10) + cell block")
n("CANBK","Canara Bank","LENDING_BANKS","LENDER","WATCH","WITHDRAWN",None,None,psu=1,notes="Watch Q2 provisions; PSU cap")
for s,nm in [("PNB","Punjab National Bank"),("PFC","Power Finance Corp"),("REC","REC")]:
    n(s,nm,"LENDING_BANKS","LENDER","NEVER_ADD","HARD_PASS",None,None,sov=1,psu=1,notes="P1 / PSU cap")
n("TATASTEEL","Tata Steel","METALS_CYCLICAL","CYCLICAL","HOLD","OWNED",None,None,"HOLD",cyc=1,exit_=1,notes="NEVER ADD; on-strength harvest list; Tata Sons stake story = a tip (no-tip rule)")
n("HINDZINC","Hindustan Zinc","METALS_CYCLICAL","CYCLICAL","SELL","OWNED",None,None,cyc=1,exit_=1,notes="On-strength sell (green days)")
n("JSWSTEEL","JSW Steel","METALS_CYCLICAL","CYCLICAL","SELL","OWNED",None,None,cyc=1,exit_=1,notes="On-strength sell")
n("SAIL","SAIL","METALS_CYCLICAL","CYCLICAL","SELL","OWNED",None,None,psu=1,cyc=1,exit_=1,notes="On-strength sell")
n("CHENNPETRO","Chennai Petroleum","METALS_CYCLICAL","CYCLICAL","SELL","OWNED",None,None,psu=1,cyc=1,exit_=1,notes="Peak-cycle; on-strength sell")
n("GESHIP","Great Eastern Shipping","METALS_CYCLICAL","CYCLICAL","SELL","OWNED",None,None,cyc=1,exit_=1,notes="Buyback ≤1,530 window closes 11-Dec-2026 (D33f); value on NAV/share")
n("HINDALCO","Hindalco","METALS_CYCLICAL","CYCLICAL","WATCH","HARD_PASS",None,None,cyc=1)
n("HINDCOPPER","Hindustan Copper","METALS_CYCLICAL","CYCLICAL","NEVER_ADD","HARD_PASS",None,None,psu=1,cyc=1,notes="D42: P1 + 44x")
n("MASTEK","Mastek","IT","IT_SERVICES","WATCH","HARD_PASS","2026-08-28","2027-02-28",None,"NOT_IN_UNIVERSE",notes="HP on Stage 1+3; expiry 28-Feb-2027")
# --- Adventz six (D61) ---
n("PARADEEP","Paradeep Phosphates","AGRI_INPUTS","CYCLICAL","WATCH","HARD_PASS","2026-09-17",None,cyc=1,notes="D61 NO (three stops); revisit <~120 + gates")
n("TEXRAIL","Texmaco Rail","WAGONS","CYCLICAL","SELL","OWNED","2026-09-17",None,cyc=1,exit_=1,notes="Confetti sell; revisit ~80")
n("ZUARIIND","Zuari Industries","AGRI_INPUTS",None,"WATCH","HARD_PASS","2026-09-17",None,notes="Catalyst-only; holdco overlay — classify at runtime; cross-holding rule D61",classified=False)
n("TEXINFRA","Texmaco Infrastructure","REALTY","DEFAULT","NEVER_ADD","HARD_PASS","2026-09-17",None,notes="D61 NO (130% NAV premium)")
n("ZUARI","Zuari Agro Chemicals","AGRI_INPUTS","CYCLICAL","NEVER_ADD","HARD_PASS","2026-09-17",None,cyc=1,notes="D61 NO")
# --- banks 7a-class ---
n("FEDERALBNK","Federal Bank","LENDING_BANKS","LENDER","WATCH","GBL",None,None,notes="Trigger 215 @1.2x predates ROE-linked gate — RE-DERIVE justified (~1.0-1.1x) before arming")
n("TMB","Tamilnad Mercantile Bank","LENDING_BANKS","LENDER","WATCH","WITHDRAWN",None,None,notes="Ran away (1.36x vs ~1.1x justified)")
n("KARURVYSYA","Karur Vysya Bank","LENDING_BANKS","LENDER","WATCH","GBL",None,None,notes="#1 swap target for SIB")
n("SOUTHBANK","South Indian Bank","LENDING_BANKS","LENDER","HOLD","OWNED",None,None,notes="Swap SOURCE → KVB (open action)")
n("IDFCFIRSTB","IDFC First Bank","LENDING_BANKS","LENDER","HOLD","OWNED",None,None,notes="Spec starter 10sh @85.94 (≤1% band)")
n("ICICIBANK","ICICI Bank","LENDING_BANKS","LENDER","SOLD","WITHDRAWN",None,None,"AGREE_NOTE","ledger §8 05-Sep",notes="SOLD D33e; GTT 1,300 CANCELLED — never resurrect")
n("AXISBANK","Axis Bank","LENDING_BANKS","LENDER","WATCH","WITHDRAWN",None,None,notes="1.8x vs justified FAIL")
n("CUB","City Union Bank","LENDING_BANKS","LENDER","HOLD","OWNED")
n("BAJAJFINSV","Bajaj Finserv","FIN_OTHER",None,"HOLD","OWNED",None,None,notes="Holdco overlay — classify at runtime",classified=False)
n("GROWW","Groww (Billionbrains)","FIN_OTHER","NEW_ECONOMY","HOLD","OWNED","2026-09-12",None,notes="D53 HOLD-WATCH: promoter 27.14% vs 26% floor; PEG 0.76",yf=None)
# --- income sleeve ---
n("INDIGRID","IndiGrid InvIT","INCOME_SLEEVE","REIT_INVIT","WATCH","GBL",None,None,"AVOID",notes="Approved-unfunded sleeve #1 (D8); entry 165-170 on 04-Jul basis (STALE; NAV 146.93 09-Sep); P5 divergence note OWED",yf=None)
n("MINDSPACE","Mindspace REIT","INCOME_SLEEVE","REIT_INVIT","WATCH","GBL",None,None,"AVOID",notes="Entry rule: ≥15% NAV discount (NAV 527, LTV 24.3%, 04-Jul basis)",yf=None)
n("EMBASSY","Embassy Office Parks REIT","INCOME_SLEEVE","REIT_INVIT","WATCH","GBL",None,None,notes="Sleeve #2",yf=None)
n("NXST","Nexus Select Trust","INCOME_SLEEVE","REIT_INVIT","WATCH","GBL",None,None,notes="Watch",yf=None)
n("PGINVIT","PowerGrid InvIT","INCOME_SLEEVE","REIT_INVIT","NEVER_ADD","HARD_PASS",None,None,"AVOID",notes="Melting DPU — same instrument Anand rejected",yf=None)
n("CUBEINVIT","Cube Highways Trust","INCOME_SLEEVE","REIT_INVIT","NEVER_ADD","HARD_PASS",None,None,notes="50.3% promoter pledge (09-Sep)",yf=None)
# --- standing exclusions ---
n("INDUSINDBK","IndusInd Bank","LENDING_BANKS","LENDER","SELL","OWNED",None,None,exit_=1,notes="Exit path; recovery rule met on P-Int lot")
n("JIOFIN","Jio Financial","FIN_OTHER","LENDER","NEVER_ADD","HARD_PASS",None,None,notes="Standing ban; Zerodha lot SOLD 17-Sep; Varshu 8sh legacy")
n("LICI","LIC of India","INSURANCE","INSURER","NEVER_ADD","HARD_PASS",None,None,"AVOID",notes="Governance; insurer = NOT FOUND sector (default ladder)")
n("YESBANK","Yes Bank","LENDING_BANKS","LENDER","NEVER_ADD","HARD_PASS")
n("MANAPPURAM","Manappuram Finance","GOLD_NBFC","LENDER","HOLD","OWNED",None,None,"BUY",notes="Owned, no adds (cell FULL); defensive leg D10/D53; his 2025 'better' verdict fails today's gate")
n("IDEAFORGE","ideaForge Technology","NEW_ECONOMY","NEW_ECONOMY","NEVER_ADD","HARD_PASS")
n("ATHERENERG","Ather Energy","NEW_ECONOMY","NEW_ECONOMY","NEVER_ADD","HARD_PASS",None,None,"AVOID",notes="'Zero valuation is better than Ather's'")
n("HINDOILEXP","Hindustan Oil Exploration","HARVEST","CYCLICAL","SELL","OWNED",None,None,cyc=1,exit_=1,notes="Promoter 0% — harvest loss THIS FY (open action 0b)")
for s,nm in [("DABUR","Dabur"),("GODREJCP","Godrej Consumer"),("BATAINDIA","Bata India")]:
    n(s,nm,"FMCG","FMCG","NEVER_ADD","HARD_PASS")
n("JYOTHYLAB","Jyothy Labs","FMCG","FMCG","NEVER_ADD","HARD_PASS",None,None,notes="⚠️ E6 CONFLICT: ledger v4.9 §8 = never-add; 19-Sep chat proposed GBL pending underwrite. Register wins until overturned in writing (D56)")
n("MHRIL","Mahindra Holidays","HOTELS","DEFAULT","WATCH","GBL","2026-09-19",exp("2026-09-19",90),notes="19-Sep chat: GBL pending underwrite — NOT in ledger v4.9; verify before any action")
n("IIFL","IIFL Finance","FIN_OTHER","LENDER","NEVER_ADD","HARD_PASS",None,None,notes="Promoter <26%; governance")
n("THANGAMAYIL","Thangamayil Jewellery","RETAIL","RETAIL","NEVER_ADD","HARD_PASS",None,None,"AVOID",notes="55x, 6x book")
n("SULA","Sula Vineyards","FMCG","FMCG","NEVER_ADD","HARD_PASS",None,None,notes="Promoter below 26% kill-switch")
n("DIVISLAB","Divi's Laboratories","PHARMA_US","PHARMA","NEVER_ADD","HARD_PASS",None,None,notes="Valuation")
n("RTNINDIA","RattanIndia Enterprises","HARVEST","DEFAULT","SELL","OWNED",None,None,exit_=1,notes="Harvest loss THIS FY (open action 0b)",yf=None)
n("GLOBALSURF","Global Surfaces","HARVEST","DEFAULT","SELL","OWNED",None,None,exit_=1,notes="Integrated lot; harvest loss THIS FY",yf=None)
n("JKPAPER","JK Paper","HARVEST","CYCLICAL","HOLD","OWNED",None,None,cyc=1,notes="Harvest deferred")
n("COALINDIA","Coal India","POWER","CYCLICAL","SELL","OWNED",None,None,"AVOID",sov=1,psu=1,cyc=1,exit_=1,notes="EXIT CANDIDATE (D1 → NTPC); 27sh household; greed-zone yield = dividend-stripping")
n("IRFC","IRFC","HARVEST","LENDER","SELL","OWNED",None,None,psu=1,exit_=1,notes="D44 SELL (200sh)")
n("HFCL","HFCL","HARVEST","DEFAULT","SELL","OWNED",None,None,exit_=1,notes="Limit 216.90 ABOVE market — revise down")
n("DRREDDY","Dr Reddy's","PHARMA_US","PHARMA","SELL","OWNED",None,None,probe=1,exit_=1,notes="⚠️ E6 CONFLICT: ledger v4.9 = exit decided (D3; 5+23 on sell list) vs 19-Sep chat 'dated hold to Jan-2027'. Register wins until overturned (D56). Semaglutide probe open")
n("NATCOPHARM","Natco Pharma","PHARMA_US","PHARMA","HOLD","OWNED",None,None,"BUY",notes="D7 HOLD; cell FULL")
# --- owned holds ---
n("HEROMOTOCO","Hero MotoCorp","AUTO_2W","AUTO_OEM","HOLD","OWNED",None,None,"HOLD",notes="Hold-only museum; fair ~3,950 (01-Sep basis)")
n("BAJAJ-AUTO","Bajaj Auto","AUTO_2W","AUTO_OEM","HOLD","OWNED",None,None,"AVOID",notes="Legacy hold; his band 'below 20x'",yf="BAJAJ-AUTO.NS")
n("HYUNDAI","Hyundai Motor India","AUTO_PV_FARM","AUTO_OEM","SELL","OWNED",None,None,exit_=1,notes="TRIM to ~3% (D33b)")
n("TATAMOTORS","Tata Motors PV (post-demerger)","AUTO_PV_FARM","AUTO_OEM","HOLD","OWNED",None,None,notes="One line; classify fresh post demerger",yf=None)
n("ASHOKLEY","Ashok Leyland","CV","AUTO_OEM","HOLD","OWNED",None,None,"AGREE_NOTE","ledger §8 05-Sep",notes="80sh household (3 lots incl. bonus); exit CANCELLED 13-Jul; hold no-add")
n("AVALON","Avalon Technologies","EMS","DEFAULT","SELL","OWNED",None,None,exit_=1,notes="TRIM to 10-12% of Integrated")
n("CDSL","CDSL","CAP_MKT_INFRA","EXCHANGE_DEPOSITORY","HOLD","OWNED",None,None,notes="Cell FULL; moat-grantor watch (SEBI admitting more players)")
n("BSE","BSE","CAP_MKT_INFRA","EXCHANGE_DEPOSITORY","SELL","OWNED",None,None,exit_=1,notes="D58 trim 5sh (74x); keep Varshu 4 bonus; WATCH post NSE listing 24-Sep")
n("ITCHOTELS","ITC Hotels","HOTELS","DEFAULT","HOLD","OWNED")
n("VBL","Varun Beverages","FMCG","FMCG","HOLD","OWNED",None,None,"AGREE_NOTE","ledger §8 05-Sep",notes="OPEN-VERIFY owned-or-not (§14 item 2); brand-ownership HARD GATE fails adds either way")
n("ZYDUSLIFE","Zydus Lifesciences","PHARMA_US","PHARMA","WATCH","GBL",None,None,"BUY",notes="Universe BUY + OSEP pass = NO ACTION (anti-tip wall); trigger ~737 provisional, basis unknown → NOT ARMABLE")
n("NIFTYBEES","Nippon Nifty 50 BeES","BALLAST","INDEX_ETF","ADD","BALLAST",None,None,notes="BeES floor — never skip")
n("JUNIORBEES","Nippon Nifty Next 50 BeES","BALLAST","INDEX_ETF","ADD","BALLAST",None,None,notes="BeES floor")
n("GOLDBEES","Nippon Gold BeES","BALLAST","NON_EARNING","ADD","BALLAST",None,None,notes="No valuation gate; thermostat governs (>40% NW gates fresh metal buying)")
n("SILVERBEES","Nippon Silver ETF","SILVER",None,"HOLD","OWNED",None,None,notes="Unclassified → Layer-4; 60u in Praveen's Integrated",classified=False)
n("TATAPOWER","Tata Power","POWER","REGULATED","HOLD","OWNED",None,None,psu=0,notes="Hold; '30 P/E very expensive'")

# ------------------------------------------------------------- triggers ---
# (symbol, kind, level, basis, derivation, set_on, valid_until, gtt, active, notes)
T = [
 ("PETRONET","BUY",383,EPS_BASIS,"14.2x fair on TTM EPS (D54 anchor 7.04%)",BOARD,VALID,None,1,None),
 ("NTPC","BUY",407,EPS_BASIS,"14.2x fair; regulated≠directed",BOARD,VALID,None,1,"Conditional on Coal India exit"),
 ("INFY","BUY",1099,EPS_BASIS,"~15x band; USD/CC guard",BOARD,VALID,None,1,None),
 ("TCS","BUY",1939,EPS_BASIS,"~fair on TTM EPS",BOARD,VALID,None,1,"Re-verify at Oct Q2"),
 ("ITC","CRASH_SHELF",228,EPS_BASIS,"fwd EPS ~12-13 post tax shock",BOARD,VALID,None,1,"Hold-only name: shelf, not an add"),
 ("ARE&M","BUY",790,EPS_BASIS,"re-derived on margin compression",BOARD,VALID,None,1,"HALF-PLATE"),
 ("RELIANCE","BUY",854,EPS_BASIS,"14.2x fair",BOARD,VALID,None,1,"Name status HOLD blocks adds (P5 AGREE)"),
 ("WIPRO","BUY",190,EPS_BASIS,"12.5x",BOARD,VALID,None,1,"Name status HOLD (D48)"),
 ("M&M","BUY",2061,EPS_BASIS,"14.2x fair",BOARD,VALID,None,1,None),
 ("HCLTECH","BUY",915,EPS_BASIS,"14.2x fair",BOARD,VALID,None,1,"Museum: no add"),
 ("ENGINERSIN","BUY",177,EPS_BASIS,"14.2x fair",BOARD,VALID,None,1,None),
 ("RITES","BUY",137,EPS_BASIS,"14.2x fair",BOARD,VALID,None,1,None),
 ("POWERGRID","BUY",250,EPS_BASIS,"14.2x fair",BOARD,VALID,None,1,"Above trigger 12-Sep"),
 ("SBIN","BUY",862,EPS_BASIS,"justified P/B ~1.6x",BOARD,VALID,None,1,"PSU cap"),
 ("HDFCBANK","CRASH_SHELF",419,EPS_BASIS,"justified P/B 1.075x on book ₹390 (D47 corrected)",BOARD,VALID,None,1,"P-board BLOCKED; crash-only"),
 ("MUTHOOTFIN","BUY",3221,EPS_BASIS,"justified P/B (ROE-linked, guard 1)",BOARD,VALID,None,1,"Starter only"),
 ("FIVESTAR","BUY",341,EPS_BASIS,"justified P/B",BOARD,VALID,None,1,"Name status HOLD (D53)"),
 ("CHAMBLFERT","NEXT_BUY",415,"2026-08-15","D61: price 409 on 16-Sep, L 2%; FY26 OCF/PAT 7% = the one fail","2026-09-17",VALID,None,1,"10sh next buy; tranche-2 gated on Q1/Q2 FY27 cash conversion"),
 ("COROMANDEL","BUY",1225,EPS_BASIS,"14.2x fair",BOARD,VALID,None,1,"Far"),
 ("FINCABLES","BUY",760,"2026-09-08","D42 GBL",BOARD,VALID,None,1,None),("FINCABLES","ALERT",1048,"2026-09-08","D42",BOARD,VALID,None,1,None),
 ("POLYCAB","BUY",2700,"2026-09-08","D42 GBL",BOARD,VALID,None,1,None),("POLYCAB","ALERT",3724,"2026-09-08","D42",BOARD,VALID,None,1,None),
 ("KEI","BUY",1510,"2026-09-08","D42 GBL",BOARD,VALID,None,1,None),("KEI","ALERT",2085,"2026-09-08","D42",BOARD,VALID,None,1,None),
 ("HAVELLS","BUY",390,"2026-09-08","D42 GBL",BOARD,VALID,None,1,None),("HAVELLS","ALERT",538,"2026-09-08","D42",BOARD,VALID,None,1,None),
 ("RRKABEL","BUY",776,"2026-09-08","D42 GBL",BOARD,VALID,None,1,None),("RRKABEL","ALERT",1070,"2026-09-08","D42",BOARD,VALID,None,1,None),
 ("ULTRACEMCO","ALERT",5820,"2026-09-08","D42",BOARD,VALID,None,1,None),
 ("TRENT","ALERT",679,"2026-09-08","D42",BOARD,VALID,None,1,None),
 ("TITAN","ALERT",1209,"2026-09-08","D42",BOARD,VALID,None,1,None),
 ("HAL","ALERT",4900,None,"52wk-high marker (watch-crash)","2026-09-01",None,None,1,"Marker, not a buy level"),
 ("FEDERALBNK","BUY",215,"2026-08-01","1.2x book — PREDATES ROE-linked gate","2026-08-01",None,None,0,"NOT ARMABLE: re-derive justified P/B (~1.0-1.1x at ROE ~13%)"),
 ("TMB","BUY",750,"2026-08-01","1.36x vs ~1.1x justified","2026-08-01",None,None,0,"NOT ARMABLE: ran away"),
 ("INDIGRID","BUY",167,"2026-07-04","dip band 165-170 (04-Jul basis)","2026-07-04",None,None,0,"NOT ARMABLE: stale basis; NAV 146.93 09-Sep; sleeve unfunded"),
 ("ZYDUSLIFE","BUY",737,None,"provisional","2026-09-01",None,None,0,"NOT ARMABLE: basis unknown; universe BUY + OSEP pass = NO ACTION"),
 ("PARADEEP","ALERT",120,"2026-09-17","D61 revisit level","2026-09-17",None,None,1,"Revisit only, with gates"),
 ("TEXRAIL","ALERT",80,"2026-09-17","D61 revisit level","2026-09-17",None,None,1,"Revisit only"),
]

# ------------------------------------------------------------- holdings ---
# CONFIRMED with an account only. Everything else awaits UC2.1 (Kite sync / CSV import).
H = [
 ("ZERODHA_P","PETRONET",92,None,"2026-09-10","LEDGER_v4.9"),("ZERODHA_P","NTPC",35,None,"2026-09-10","LEDGER_v4.9"),
 ("ZERODHA_P","MUTHOOTFIN",7,2942.63,"2026-09-09","LEDGER_v4.9"),("ZERODHA_P","NIFTYBEES",112,None,"2026-09-10","LEDGER_v4.9"),
 ("ZERODHA_P","JUNIORBEES",11,None,"2026-09-10","LEDGER_v4.9"),("ZERODHA_P","TCS",5,None,"2026-09-10","LEDGER_v4.9"),
 ("ZERODHA_P","INFY",12,None,"2026-09-10","LEDGER_v4.9"),("ZERODHA_P","IDFCFIRSTB",10,85.94,"2026-09-09","LEDGER_v4.9"),
 ("ZERODHA_P","GOLDBEES",389,None,"2026-09-09","LEDGER_v4.9"),("ZERODHA_P","SBIN",3,1008.50,"2026-09-10","CONFIRMED_FILL"),
 ("ZERODHA_P","ARE&M",5,832.15,"2026-09-10","CONFIRMED_FILL"),("ZERODHA_P","WIPRO",10,167.06,"2026-09-10","CONFIRMED_FILL"),
 ("ZERODHA_P","HDFCBANK",5,687.95,"2026-09-10","CONFIRMED_FILL"),  # the D62 control-exception lot ONLY; rest of household HDFC awaits sync
 ("ZERODHA_P","COALINDIA",15,None,"2026-09-06","LEDGER_v4.9"),("ZERODHA_P","TATASTEEL",82,None,"2026-09-01","LEDGER_v4.9"),
 ("ZERODHA_P","ASHOKLEY",40,113.75,"2026-07-13","LEDGER_v4.9"),("INTEGRATED_P","ASHOKLEY",10,0.01,"2026-07-13","LEDGER_v4.9"),
 ("INTEGRATED_V","ASHOKLEY",30,24.56,"2026-07-13","LEDGER_v4.9"),
 ("INTEGRATED_P","NATCOPHARM",22,None,"2026-09-01","LEDGER_v4.9"),("INTEGRATED_V","NATCOPHARM",4,None,"2026-09-01","LEDGER_v4.9"),
 ("INTEGRATED_P","WIPRO",88,None,"2026-09-01","LEDGER_v4.9"),("INTEGRATED_V","WIPRO",48,None,"2026-09-01","LEDGER_v4.9"),
 ("INTEGRATED_P","TCS",4,None,"2026-09-01","LEDGER_v4.9"),("INTEGRATED_V","TCS",6,None,"2026-09-01","LEDGER_v4.9"),
 ("INTEGRATED_P","INFY",4,None,"2026-09-01","LEDGER_v4.9"),("INTEGRATED_V","INFY",20,None,"2026-09-01","LEDGER_v4.9"),
 ("INTEGRATED_P","SILVERBEES",60,None,"2026-09-01","LEDGER_v4.9"),("INTEGRATED_V","DRREDDY",23,None,"2026-09-01","LEDGER_v4.9"),
 ("INTEGRATED_V","JIOFIN",8,None,"2026-09-01","LEDGER_v4.9"),
]

# ---------------------------------------------------------------- cells ---
C = [
 ("IT","INFY,TCS,WIPRO,HCLTECH","INFY,TCS",2,0,"Wipro hold-no-add (D48); HCL museum"),
 ("ENERGY_GAS","PETRONET,RELIANCE","PETRONET",2,0,"Reliance P5 AGREE = hold"),
 ("POWER","NTPC,POWERGRID,TATAPOWER,COALINDIA","NTPC,POWERGRID",2,0,"Coal India EXIT pending; PSU cap 25% (D36)"),
 ("LENDING_BANKS","SBIN,HDFCBANK,IDFCFIRSTB,CUB,SOUTHBANK,FIVESTAR","SBIN",2,0,"HDFC crash-only; Federal/KVB watch; SIB→KVB swap"),
 ("GOLD_NBFC","MUTHOOTFIN,MANAPPURAM","MUTHOOTFIN",2,1,"FULL — no third name, ever; Muthoot starter only"),
 ("CAP_MKT_INFRA","CDSL,BSE","",2,1,"FULL; moat-grantor watch; BSE trim + NSE-listing watch"),
 ("FIN_OTHER","BAJAJFINSV,GROWW","",2,0,"Holds"),
 ("FMCG","ITC,VBL","",2,0,"OPEN QUESTION: VBL owned-or-not; brand gate fails VBL adds"),
 ("AUTO_2W","HEROMOTOCO,BAJAJ-AUTO","",2,1,"FULL museum"),
 ("AUTO_PV_FARM","HYUNDAI,M&M,TATAMOTORS","M&M",2,0,"Hyundai TRIM"),
 ("CV","ASHOKLEY,TMCV","",2,0,"Ashok Leyland hold; TMCV museum"),
 ("DEFENCE","BEL,HAL,LT","",2,1,"FULL; L&T crash-shelf; working-capital objection logged"),
 ("PHARMA_US","DRREDDY,NATCOPHARM,ZYDUSLIFE","",2,1,"FULL; DRL exit decided"),
 ("PHARMA_DOMESTIC","CIPLA,SUNPHARMA,MANKIND","",2,1,"FULL"),
 ("TELECOM","BHARTIARTL","",2,0,None),("EMS","AVALON","",2,0,"Trim"),
 ("ANCILLARY","ARE&M,BALKRISIND","ARE&M",2,0,"Amara Raja half-plate anchor"),
 ("AGRI_INPUTS","CHAMBLFERT,COROMANDEL","CHAMBLFERT,COROMANDEL",2,0,"2 seats; subsidy rule D60; cross-holding rule D61"),
 ("HOTELS","ITCHOTELS,MHRIL","",2,0,"MHRIL pending underwrite (not in ledger)"),
 ("BALLAST","NIFTYBEES,JUNIORBEES,GOLDBEES","NIFTYBEES,JUNIORBEES,GOLDBEES",3,0,"BeES floor never skipped; gold thermostat"),
 ("METALS_CYCLICAL","TATASTEEL,HINDZINC,JSWSTEEL,SAIL,CHENNPETRO,GESHIP","",0,1,"Harvest/on-strength sell side; never add"),
 ("WIRES_GBL","FINCABLES,POLYCAB,KEI,HAVELLS,RRKABEL","",2,0,"GBL with triggers (D42)"),
 ("INCOME_SLEEVE","INDIGRID,MINDSPACE,EMBASSY,NXST","",2,0,"Approved 04-Jul, NEVER FUNDED; target 5-8%; P5 note owed"),
 ("SILVER","SILVERBEES","",1,0,"Unclassified → Layer-4"),
]

# --------------------------------------------------------------- policy ---
P = [
 ("fair_pe_method","1/gsec_yield","formula","osep v7 §ladder (OSEP formalisation of Anand's earnings-yield rule)",BOARD),
 ("cost_of_equity_spread_over_gsec","6.09","pct","ledger §3 (r=13.13% at G-sec 7.04%, D54)",BOARD),
 ("growth_g","5","pct","osep v7 §BANK justified P/B",BOARD),
 ("lender_first_bite_gate","JUSTIFIED_PB_ONLY","rule","tiffin v6 §(c) — defect-2 fix","2026-09-17"),
 ("cap_name_pct","20","pct of household equity","pattaz-book §4","2026-07-13"),
 ("cap_sector_pct","40","pct of household equity","pattaz-book §4","2026-07-13"),
 ("cap_psu_regulated_pct","25","pct of household equity","ledger D36","2026-09-08"),
 ("band_core","7-10","pct","pattaz-book §4","2026-07-13"),("band_standard","4-6","pct","pattaz-book §4","2026-07-13"),
 ("band_satellite","2-3","pct","pattaz-book §4","2026-07-13"),("band_spec_max","1","pct","pattaz-book §4","2026-07-13"),
 ("cell_max_active_adds","2","count","pattaz-book §5","2026-07-13"),
 ("qty_clamp_min","1","shares","tiffin v6 STEP 5","2026-09-10"),("qty_clamp_max","10","shares","tiffin v6 STEP 5","2026-09-10"),
 ("breadth_min","8","names","tiffin v6 STEP 3","2026-09-10"),("breadth_max","15","names","tiffin v6 STEP 3","2026-09-10"),
 ("eligible_h_min","0.85","ratio","tiffin v6 STEP 1","2026-09-10"),("eligible_l_max","5","pct above 52wk low","tiffin v6 STEP 1","2026-09-10"),
 ("h_band_coffee","0.85-0.95:0.5","H:mult","tiffin v6","2026-09-10"),("h_band_tiffin","0.95-1.05:1.0","H:mult","tiffin v6","2026-09-10"),
 ("h_band_full_meals","1.05-1.15:3.0","H:mult","tiffin v6","2026-09-10"),("h_band_hockey","1.15+","H","tiffin v6","2026-09-10"),
 ("p_mult_missing","1.5","mult","tiffin v6 P-index","2026-09-10"),("p_mult_building","1.0","mult","tiffin v6","2026-09-10"),
 ("p_mult_maint","0.5","mult","tiffin v6","2026-09-10"),("p_mult_blocked","0","mult","tiffin v6","2026-09-10"),
 ("ticket_band_min","5000","INR","tiffin v6 (Praveen's band)","2026-09-10"),("ticket_band_max","10000","INR","tiffin v6","2026-09-10"),
 ("single_deployment_cap_pct","15","pct of surplus","tiffin v4 guardrail","2026-08-03"),
 ("two_pocket_split","60/40","ratio","tiffin v6","2026-09-10"),
 ("decay_gbn_days","30","days","osep v7 decay clock","2026-08-03"),("decay_gbl_days","90","days","osep v7 decay clock","2026-08-03"),
 ("promoter_kill_switch_pct","26","pct","osep Stage 0","2026-08-03"),
 ("gold_thermostat_pct_nw","40","pct of net worth","tiffin thermostat","2026-07-13"),
 ("hockey_reserve_floor","100000","INR","pattaz-book §2 [POLICY]","2026-07-14"),
 ("hockey_rung1_nifty_drawdown_pct","15","pct (D28 accelerate-to-lump)","ledger D37","2026-09-08"),
 ("hockey_rung2_nifty_drawdown_pct","25","pct (reserve + powder)","ledger D37","2026-09-08"),
 ("bees_floor","NEVER_SKIP","rule","tiffin v6","2026-07-13"),
 ("novelty_rule_days","1","days (no same-day buy of fresh underwrites)","tiffin overlays","2026-08-03"),
 ("income_sleeve_target_pct","5-8","pct of household equity","ledger D8","2026-07-04"),
 ("planning_yield_pct","8","pct","pattaz-book §16","2026-08-03"),
 ("cost_basis_is_not_a_reason","TRUE","rule","ledger D35","2026-09-08"),
 ("caps_off_first_bite","WAIVES_CAPS_NEVER_GATES","rule","ledger D6+D44","2026-09-09"),
]

# ------------------------------------------------------------ decisions ---
D = [(1,None,"Coal India → NTPC swap",None,"OPEN"),(3,None,"Dr Reddy's exit (quality-integrity)",None,"OPEN"),
 (6,"2026-07-22","Caps-off first bite","waives caps, never gates (refined D44)","CLOSED"),(7,None,"Natco HOLD",None,"CLOSED"),
 (8,"2026-07-04","Income sleeve approved — unfunded",None,"OPEN"),(10,None,"Manappuram HOLD (defensive leg)",None,"CLOSED"),
 (23,None,"No IPOs (froth rule)",None,"CLOSED"),(28,"2026-09-07","Rs21.16L deployment plan + accelerate-to-lump",None,"CLOSED"),
 (29,"2026-09-07","Axis Small Cap redeem-now (with D38)",None,"OPEN"),(31,"2026-09-07","IKS + Venus Pipes GBL-on-price",None,"CLOSED"),
 (33,"2026-09-08","Consolidation 95→~27 with amendments",None,"CLOSED"),(34,"2026-09-08","Sell-list P/L ~+1.18L",None,"CLOSED"),
 (35,"2026-09-08","Cost basis is not a reason",None,"CLOSED"),(36,"2026-09-08","PSU/regulated cap 25%",None,"CLOSED"),
 (37,"2026-09-08","Hockey ladder resize",None,"CLOSED"),(38,"2026-09-08","Axis redemption; FY27 exemption to Axis",None,"OPEN"),
 (39,"2026-09-08","Sell sequence 6 weeks",None,"OPEN"),(40,"2026-09-08","Ten build names",None,"CLOSED"),
 (41,"2026-09-09","The fear rule",None,"CLOSED"),(42,"2026-09-09","Anand 08-Sep verdicts (wires GBL etc.)",None,"CLOSED"),
 (43,"2026-09-09","Rs30K plate",None,"CLOSED"),(44,"2026-09-09","Caps-off refinement; IRFC SELL; TMCV museum",None,"CLOSED"),
 (45,"2026-09-10","Rs1L plate (two-pocket)",None,"CLOSED"),(46,"2026-09-10","Scan findings",None,"CLOSED"),
 (47,"2026-09-10","HDFC trigger 560→419 (bonus un-processed)",None,"CLOSED"),(48,"2026-09-10","Wipro hold-no-add",None,"CLOSED"),
 (49,"2026-09-10","52wk-low scan",None,"CLOSED"),(50,"2026-09-10","Rs35K plate CONFIRMED fills",None,"CLOSED"),
 (51,"2026-09-10","tiffin v5 quantity-first",None,"CLOSED"),(52,"2026-09-12","Thirteen sells approved",None,"CLOSED"),
 (53,"2026-09-12","Reversals: Groww/Five-Star HOLD; Manappuram+Natco off sell list",None,"CLOSED"),
 (54,"2026-09-12","Anchor 7.04%/14.2x re-derivation",None,"CLOSED"),(55,"2026-09-12","Macro: crude, RBI OMO, IPO froth, NSE→BSE watch",None,"CLOSED"),
 (56,"2026-09-12","Research-vs-register protocol",None,"CLOSED"),(57,"2026-09-17","SELL DAY — Rs1,98,262 raised",None,"CLOSED"),
 (58,"2026-09-17","BSE trim 5sh",None,"OPEN"),(59,"2026-09-17","Chambal starter 10sh (gated)",None,"OPEN"),
 (60,"2026-09-17","Fertiliser/subsidy rule",None,"CLOSED"),(61,"2026-09-17","Adventz six-name: Chambal only",None,"CLOSED"),
 (62,"2026-09-17","Skill engine v8 installed; defects 1/2/3 killed; HDFC control exception",None,"CLOSED"),
 (63,"2026-09-17","Ledger delta-chain incident; v4.9 consolidation; wholesale test",None,"CLOSED"),
 (64,"2026-09-17","Sector gate evidence base; NOT-FOUND fallback sectors",None,"CLOSED"),
]
for k in (2,4,5,9,11,12,13,14,15,16,17,18,19,20,21,22,24,25,26,27,30,32):
    D.append((k,None,f"D{k} — index only; full prose in LEDGER ARCHIVE (04→07-Sep deltas)",None,"INDEX_ONLY"))

def build() -> None:
    if DB.exists(): DB.unlink()
    con = sqlite3.connect(DB); con.executescript(SCHEMA.read_text())
    con.executemany("INSERT INTO names VALUES (?,?,?,0,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", N)
    con.executemany("INSERT INTO triggers VALUES (?,?,?,?,?,?,?,?,?,?)", T)
    con.executemany("INSERT INTO holdings VALUES (?,?,?,?,?,?)", H)
    con.executemany("INSERT INTO cells VALUES (?,?,?,?,?,?,?)", [c + (LEDGER,) for c in C])
    con.executemany("INSERT INTO policy VALUES (?,?,?,?,?)", P)
    con.executemany("INSERT INTO decisions VALUES (?,?,?,?,?)", sorted(D))
    con.commit()
    DUMP.write_text("\n".join(con.iterdump()))
    con.close()

if __name__ == "__main__":
    build(); print(f"built {DB} and {DUMP}")
