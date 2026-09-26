-- Migration 011: ledger_aliases — short names the Drive ledger uses for register symbols
-- Date: 2026-09-26
--
-- UC6 ledger sync maps a ledger name ("SBI 862", "EIL 177") to a register symbol by
-- names.symbol / names.name first; this table covers only the abbreviations the ledger
-- uses that neither matches. Each row is a plain reading of ledger v4.10 usage
-- (§5 cell map, §7 board, §10 register). Anything not listed here and not matching a
-- register name is reported as "needs review" — never guessed.

CREATE TABLE ledger_aliases (
  alias    TEXT PRIMARY KEY COLLATE NOCASE,  -- as written in the ledger
  symbol   TEXT NOT NULL,                    -- register symbol (names.symbol)
  source   TEXT NOT NULL,                    -- where the ledger uses it
  set_on   TEXT NOT NULL
);

INSERT OR IGNORE INTO ledger_aliases VALUES
 ('SBI','SBIN','ledger v4.10 §5 "SBI (add)", §7 "SBI 862"','2026-09-26'),
 ('EIL','ENGINERSIN','ledger v4.10 §7 "EIL 177" (Engineers India)','2026-09-26'),
 ('DRL','DRREDDY','ledger v4.10 §5 "DRL(exit)", §6 "DRL GUARDRAIL-block"','2026-09-26'),
 ('L&T','LT','ledger v4.10 §5 "L&T crash-shelf", §4 crash shelf','2026-09-26'),
 ('KVB','KARURVYSYA','ledger v4.10 §7 "KVB #1 swap for SIB"','2026-09-26'),
 ('SIB','SOUTHBANK','ledger v4.10 §7 "KVB #1 swap for SIB"','2026-09-26'),
 ('HZL','HINDZINC','ledger v4.10 §7 peak-cycle metals list','2026-09-26'),
 ('BoB','BANKBARODA','ledger v4.10 §7 "BoB (fraud tail)"','2026-09-26'),
 ('GE Shipping','GESHIP','ledger v4.10 §2/§7 "GE Shipping"','2026-09-26'),
 ('ICICI','ICICIBANK','ledger v4.10 §5 "ICICI SOLD (D33e)"','2026-09-26'),
 ('HOEC','HINDOILEXP','ledger v4.10 §2/§7 "HOEC (promoter 0% — sell)"','2026-09-26'),
 ('Hind Copper','HINDCOPPER','ledger v4.10 §7 "Hind Copper (P1+44x)"','2026-09-26'),
 ('Texmaco Infra','TEXINFRA','ledger v4.10 §5/§7 "Texmaco Infra"','2026-09-26');
