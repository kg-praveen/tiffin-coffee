---
name: sync-holdings
description: UC2.1 — "sync holdings", "pull my portfolio", "import this CSV". Refreshes the holdings table: Zerodha via the free Kite Connect Personal API (read-only), the two Integrated accounts via CSV drop. Prints the household view. Never places orders.
---
# Sync holdings (UC2.1)
1. Zerodha: run `tools/kite.py login` → it prints the Kite login URL. Praveen logs in in his
   browser and pastes the `request_token` back; the tool exchanges it for today's access
   token (expires daily; never stored beyond the session; never automate login).
   Then `usecases/sync_holdings.py --account ZERODHA_P` reads holdings, positions, funds.
2. Integrated (no API): Praveen drops a Console/NSDL CSV; run
   `usecases/sync_holdings.py --account INTEGRATED_P --csv <file>` (same for INTEGRATED_V).
3. Rows are written with as_of = now and source = KITE_API / CSV; older rows are kept
   (history), the engine reads the newest per account+symbol.
4. Output: household view — qty per account, household weight per name computed on
   prices fetched THIS run, cap breaches (20% / 40% / 25% PSU), and names whose weight
   changed band. Then the P-board status (BLOCKED / MAINT / BUILDING / MISSING).
5. Read scope only. If any code path would call an order or GTT-place endpoint, stop.
