---
name: sync-holdings
description: UC2.1 — "sync holdings", "pull my portfolio", "import this CSV". Refreshes the holdings table: Zerodha via the free Kite Connect Personal API (read-only), the two Integrated accounts via CSV drop. Prints the household view. Never places orders.
---
# Sync holdings (UC2.1)
1. Zerodha (ZERODHA_P), read-only Kite Connect:
   - First try today's cached session: `python -m usecases.sync_holdings kite`.
     If it prints "No Kite session for today", continue below.
   - Run `python -m usecases.sync_holdings kite --login-url` and PRINT the URL to Praveen.
     Ask him to log in in his own browser and paste back the `request_token` from the
     redirect URL. NEVER automate the login, never ask for or store his password/TOTP.
   - Run `python -m usecases.sync_holdings kite --request-token <token he pasted>`. It
     exchanges it for today's access token (cached only in the git-ignored
     `.kite_access.token`, expired after the IST day; never printed or logged), reads
     holdings (qty = settled + T1) and writes ZERODHA_P rows only.
   - Kite symbols map to the register via the `names.yf_ticker` stem (RECLTD -> REC).
     Symbols not in `names` are kept under their Kite name and listed as UNKNOWN —
     tell Praveen about each one.
   - If Kite returns an empty book while the register shows Zerodha holdings, nothing
     is written (fail-closed). Say so; do not retry in a loop.
2. Integrated (no API): Praveen drops the household CSV; run
   `python -m usecases.sync_holdings csv <file>`. The Kite path never touches
   INTEGRATED_P / INTEGRATED_V.
3. Rows are written with as_of = the snapshot date and source = KITE_API / CSV; older
   rows are kept (history), the engine reads the newest per account+symbol. A name held
   before and absent from the new snapshot is recorded as an exit (qty 0).
4. Output: household view — qty per account, household weight per name computed on
   prices fetched THIS run, cap breaches (20% / 40% / 25% PSU), and names whose weight
   changed band. Then the P-board status (BLOCKED / MAINT / BUILDING / MISSING).
5. Read scope only. If any code path would call an order or GTT write endpoint, stop.
