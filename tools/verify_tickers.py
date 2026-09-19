"""tools/verify_tickers.py — Task 3: verify every names.yf_ticker resolves via yfinance.

Reads names with non-NULL yf_ticker from the DB, attempts to fetch a price for each,
marks verified ones with ticker_verified=1, and reports failures for Praveen.

Run: python -m tools.verify_tickers
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from store.repo import PattazRepo
from tools.prices import fetch_price


def verify_all_tickers(db_path: str | Path) -> tuple[list[str], list[tuple[str, str, str]]]:
    """Verify every unverified yf_ticker in the names table.

    Returns (verified_symbols, failed_list) where failed_list is
    [(symbol, yf_ticker, error_message), ...].
    """
    repo = PattazRepo(db_path)
    to_verify = repo.names_needing_ticker_verification()
    no_ticker = repo.names_without_ticker()

    verified: list[str] = []
    failed: list[tuple[str, str, str]] = []

    print(f"--- Ticker verification: {len(to_verify)} names to check ---")
    print(f"--- {len(no_ticker)} names have no yf_ticker (NULL) ---")
    for n in no_ticker:
        print(f"  NULL ticker: {n.symbol} ({n.name})")
    print()

    for name_row in to_verify:
        ticker = name_row.yf_ticker
        assert ticker is not None
        try:
            snap = fetch_price(ticker)
            repo.set_ticker_verified(name_row.symbol, ticker)
            verified.append(name_row.symbol)
            print(f"  OK  {name_row.symbol:15s} → {ticker:18s}  price={snap.price.value}")
        except (ValueError, Exception) as e:
            failed.append((name_row.symbol, ticker, str(e)))
            print(f"  FAIL {name_row.symbol:15s} → {ticker:18s}  {e}")
        time.sleep(0.3)  # rate-limit

    repo.close()
    return verified, failed


if __name__ == "__main__":
    db = Path("db/pattaz.db")
    if not db.exists():
        print(f"ERROR: {db} not found", file=sys.stderr)
        sys.exit(1)

    verified, failed = verify_all_tickers(db)
    print("\n=== RESULTS ===")
    print(f"Verified: {len(verified)}")
    print(f"Failed:   {len(failed)}")
    if failed:
        print("\nFailed tickers (need Praveen's attention):")
        for sym, tick, err in failed:
            print(f"  {sym:15s} {tick:18s} — {err}")
