---
name: plate
description: UC2 — "₹10k plate", "what can I buy today with 25k", "tiffin plate". Builds today's buy list per spec/tiffin-coffee.SKILL.md v6: eligibility (H ≥ 0.85 or L ≤ 5%), all ten overlays, sector-aware first-bite gate (lenders = justified P/B only), score, breadth, hard 1-10 clamp, BeES floor. Proposal only.
---
# Tiffin plate (UC2)
1. Ask for the budget if not given; confirm liquid cash is CONFIRMED by Praveen this session
   (never assume a remembered figure).
2. Run `usecases/plate.py --budget N`. It requires fresh holdings (UC2.1) for the P-index;
   if holdings are older than the policy window, names drop with reason HOLDINGS_STALE.
   Sizing (Praveen 26-Sep-2026): 1 share of each ranked name first; if that costs more
   than the budget, the report says "needs ₹X" at the top — say it first. The rest is
   spread by rank. A "REVIEW FIRST" name is never bought until analysed and approved.
3. Output: the plate table (name · qty · ~₹ · why), then EVERY dropped name with its
   DropReason, then the rules fired. If nothing is eligible → BeES floor, never skip.
4. Any E6 CONFLICT row in `names.notes` for a candidate → halt on that name, show both
   sides, ask Praveen. Never resolve it yourself.
5. Written to `sessions`; Praveen executes in Kite. 3-state protocol: PLANNED → ORDERED → CONFIRMED.
