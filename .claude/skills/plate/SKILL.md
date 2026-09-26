---
name: plate
description: UC2 — "₹10k plate", "what can I buy today with 25k", "tiffin plate". Builds today's buy list per spec/tiffin-coffee.SKILL.md v6: eligibility (H ≥ 0.85 or L ≤ 5%), all ten overlays, sector-aware first-bite gate (lenders = justified P/B only), score, breadth, hard 1-10 clamp, BeES floor. Proposal only.
---
# Tiffin plate (UC2)
1. Ask for the budget if not given; confirm liquid cash is CONFIRMED by Praveen this session
   (never assume a remembered figure). Ask for his confirmed investable surplus and pass it
   as `confirmed_surplus=` — the 15% single-deployment cap is checked only then; a plate
   over the cap is HALT — NO ACTION (say it first). A cap below 1 NIFTYBEES is an E6
   CONFLICT (tiffin v4 cap vs tiffin v6 BeES NO-SKIP) — NO ACTION, name both rules, ask.
   Read out every "OPEN QUESTION for Praveen:" line — they stay until he rules.
2. Run `usecases/plate.py --budget N`. It requires fresh holdings (UC2.1) for the P-index;
   if holdings are older than the policy window, names drop with reason HOLDINGS_STALE.
   Sizing (Praveen 26-Sep-2026): 1 share of each ranked name first; if that costs more
   than the budget, the report says "needs ₹X" at the top — say it first. The rest is
   spread by rank. A "REVIEW FIRST" name is never bought until analysed and approved.
   HOCKEY lines (Nifty week fall, ladder rung, name day fall, H > 1.15) are detection only:
   say them right after the verdict; any reserve deployment needs Praveen's explicit yes.
3. Output: the plate table (name · qty · ~₹ · why), then EVERY dropped name with its
   DropReason, then the rules fired. If nothing is eligible → BeES floor, never skip.
4. Any E6 CONFLICT row in `names.notes` for a candidate → halt on that name, show both
   sides, ask Praveen. Never resolve it yourself.
5. Written to `sessions`; Praveen executes in Kite. 3-state protocol: PLANNED → ORDERED → CONFIRMED.
