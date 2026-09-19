---
name: morning-board
description: UC1 — "run the morning board", "anything fired?", "what's near a trigger". Fetches live prices + G-sec, checks every trigger's armability (fresh-EPS basis + decay clock), and prints FIRED / NEAR / FAR plus the NOT-ARMABLE list with reasons. Proposal only.
---
# Morning board (UC1)
1. Run `usecases/morning_board.py` (it loads policy + triggers + names from db/pattaz.db,
   fetches prices and the 10Y G-sec via tools/, re-derives fair P/E = 1/yield).
2. Never quote a number that was not fetched in this run (E3). If the fetch fails for a
   name, it appears under "UNKNOWN — price not fetched", never as FAR.
3. Output, verdict first, in plain language:
   - FIRED (price ≤ trigger) → then NEAR (within 5%) → then FAR
   - NOT ARMABLE (active=0 or stale basis) with what each needs
   - resting-GTT mismatches if the Kite GTT list is available (UC3 later)
4. A fired trigger is an appointment to re-examine, never an order. Say so.
5. The run is written to `sessions` before you reply. If it wasn't, say the board is unverified.
