---
name: plate-ranker
description: UC3 — "which plate is best today", "rank the plates", "5k or 10k today?", "compare plate options", "should I trim the plate". Builds every plate variant the spec lets Praveen choose between (ticket band bottom/top, the asked amount, bottom-scores trim when breadth > 15), checks every law on each, and marks the best with the reason. Proposal only — never places or changes anything.
---
# Plate ranker (UC3)

1. **Amount.** Use the amount Praveen names; if none, the ranker defaults to the ticket
   band top (policy `ticket_band_max`). Confirm liquid cash is CONFIRMED this session
   (tiffin v4: ticket × 30 ≤ confirmed liquid cash) — never a remembered figure.
2. **Run.**
   - Rehearsal on the newest recording: `uv run python -m usecases.ranker --amount N`
     (say the recording's date).
   - Today's market: `uv run python -m usecases.ranker --amount N --live` (network).
   - A specific recording: `--market tests/fixtures/market/market_YYYY-MM-DD.json`.
3. **Answer verdict first:** "Best (provisional): ₹X as you asked / band top / band
   bottom — N stocks, ₹Y left over", then WHY IT WINS in plain words, then the
   side-by-side table, what each plate buys, and the DROPPED list (every name, its
   reason, what would change). If the asked amount is outside the ticket band, say so
   first ("your ₹25k is outside your ₹5-10k band; within the band the best is …") and
   still show the asked-amount plate. If the ranker says NO ACTION — every variant broke
   a law, or a failure (missing policy row, no market data, no config) — quote the
   reason, say "do not trust today's plate" and suggest the `simulate` skill. A NO
   ACTION run still writes its session.
   If ADVISORY holds BLOCK/E6 flags, say "advisory only — do not execute" even though
   every plate passed every invariant check.
4. **Never invent a variant.** Only what the spec hands to a human: an amount inside the
   ₹5-10K band and "drop the bottom-scoring names" when breadth > 15. Loosening the
   screen to L ≤ 10% when breadth < 8 changes a rule — raise it as a question, never run it.
5. Say the ranking order comes from policy `ranker_criteria_order` (ticket band → no
   raised budget → breadth 8-15 → least left over; ties → smaller ticket) and that it
   is **PROVISIONAL**: neither the order nor the tie-break is spec text. Relay the
   "OPEN QUESTION for Praveen" line until he confirms it.
6. One `UC3_RANKER` session is written (`--no-session` to skip). To act, Praveen runs
   the `plate` skill at the chosen amount (that writes the UC2 decision session) and
   executes in Kite himself.
