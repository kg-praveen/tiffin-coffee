---
name: trigger-check
description: [v2 2026-09-17] Patrol Praveen's live trigger board — pull the newest Pattaz Master Ledger + Finance TODOs from the pattaz_list Drive folder, VALIDATE each trigger's basis (fresh-EPS date + decay clock), fetch fresh prices, classify FIRED/NEAR/FAR, safety-check fired names, and output a ranked action table. Use whenever Praveen says "check on triggers", "trigger check", "scan the board", "anything fired?", "what's near a buy zone", or asks whether any watchlist/GBL name has reached its entry price — even casually.
---

# Trigger Check — the board patrol
**VERSION: v2 (2026-09-17)** — supersedes v1 (05-Jul).
🔴 **v2 KILLS THE SEED BOARD.** v1 carried a hardcoded trigger list (05-Jul) that
went stale and CONFLICTED with the live book (it still carried a CANCELLED ICICI
level and pre-supersession M&M/GAIL levels — details in LEDGER-APPENDIX §D). Per the osep v7 ENGINE CONTRACT (E2/E3):
**no trigger level, price, or valuation number may live in this skill, ever. The
ledger is the ONLY source of triggers; the market is the ONLY source of prices.**
On-demand Layer-2.5 monitoring between tiffin sessions. NEVER auto-buys; outputs a
proposal table. Praveen executes. Zerodha GTTs remain the always-on arm.

## Workflow
1. **LOAD BOARD (ledger only):** Google Drive search_files "PATTAZ MASTER LEDGER"
   and "Finance TODOs" in folder `pattaz_list` (parentId 11rJJfTS0kvFLoTSBm04RpT5LTRkHxp5K);
   read the NEWEST of each. Extract every trigger line WITH its basis: level ·
   fresh-EPS basis date · verdict date · bucket. (Drive tools unload intermittently —
   re-run tool_search "Google Drive search files" first if needed.)
   **No ledger reachable → STOP. Report "board unavailable"; never patrol from
   memory or any skill text (E9).**
2. **VALIDITY GATE (E3) — before any price is fetched:** a trigger is **ARMABLE**
   only if (a) its fresh-EPS basis post-dates the name's last quarterly result,
   (b) its verdict is inside the osep decay clock (GBN 30d / GBL 90d), and (c) no
   corporate action (bonus/split/demerger/buyback, trailing 12m) post-dates the
   basis. Anything else = **⚠️ NOT ARMABLE — report it as "stale basis, re-derive",
   never as FIRED/NEAR, whatever the price says.** Flag any resting broker GTT
   sitting on a not-armable basis for cancellation.
3. **PRICE PASS:** web-search fresh prices for (a) all ARMABLE names, (b) any name
   the ledger last saw within ~10% of trigger, (c) anything Praveen names. Batch
   2-4 names per query. **A price that cannot be fetched fresh = status UNKNOWN —
   never reuse a remembered or ledger price for classification (E3/E9).**
4. **CLASSIFY (armable names only):** 🔴 FIRED = price ≤ trigger | 🟡 NEAR = within
   5% | ⚪ FAR = >5%. Show % distance and the basis date.
5. **FIRED-NAME SAFETY GATE (mandatory):** quick Stage-0 headline scan + Stage-2
   re-score (osep v7 — runtime sector classification §SC applies; a lender is judged
   on justified P/B, never P/E). Distinguish fired on MARKET weakness (buy signal)
   vs COMPANY-SPECIFIC news (re-underwrite first — don't catch the knife).
   **A trigger is an appointment to re-examine, never an order to buy.**
6. **GATES (from the live book + ledger, never memory):** cell caps and P-board
   blocks (pattaz-book §4/§5) · standing exclusions (§8) · sell-list / decided
   exits · swap-gated names · P5 unlogged-AVOID blocks · novelty rule (no same-day
   buy of freshly underwritten names) · caps-off ONLY per §12b (unresolved — E6:
   on collision, HALT and ask).
7. **SIZE [POLICY]:** map each actionable FIRED name to an Opportunity Ladder tier —
   T1 ₹3-5K routine / T2 ₹8-12K real weakness / T3 ₹15-25K panic breadth (index
   −2%+, multiple fires). Whole shares only; tiffin-coffee clamps and the 15%
   single-deployment cap still bind.
8. **OUTPUT:** Name | Trigger (basis date) | Price (fetched now) | Dist | Status |
   Gate | Proposed clip. Lead with FIRED, then NEAR, then a NOT-ARMABLE list with
   what each needs. Nothing fired: one line + the 3 nearest.
9. **LOG:** only on a state CHANGE (newly fired / newly near / newly not-armable),
   append a short dated "Trigger Check — YYYY-MM-DD" note to the ledger. No state
   change = no write. Never create a new fragment file.

## Guardrails
- Proposal only. Fresh data only. **This file contains no market numbers by design —
  finding one here is a defect (osep E2); the never-resurrect register (pattaz-book
  §9) bans the v1 seed board explicitly.**
- During market hours, note the time (ETF legs: avoid open/close spreads;
  10:00-14:30 window).
- 3-STATE PROTOCOL: PLANNED → ORDERED → CONFIRMED (pattaz-book §9).
