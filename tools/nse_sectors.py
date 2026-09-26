"""tools/nse_sectors.py — NSE's official sector ("Industry") for every listed stock.

Source: NSE Indices, Nifty Total Market constituents
(niftyindices.com/IndexConstituent/ind_niftytotalmarket_list.csv — ~750 stocks, the
same "Industry" labels NSE uses for its sectoral indices: Financial Services,
Information Technology, Healthcare, ...).

This is reference data about the stock, not market data: it is recorded once into
db/reference/nse_industry_<date>.csv (committed) and loaded into names.nse_sector.
`fetch_nse_industry_csv` is the only network call; refresh it deliberately.
"""
from __future__ import annotations

import csv
import io
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

NSE_TOTAL_MARKET_URL = "https://niftyindices.com/IndexConstituent/ind_niftytotalmarket_list.csv"
REFERENCE_DIR = Path(__file__).resolve().parent.parent / "db" / "reference"


def parse_nse_industry_csv(text: str) -> dict[str, str]:
    """NSE symbol → NSE Industry. Rows without both fields are skipped."""
    out: dict[str, str] = {}
    for row in csv.DictReader(io.StringIO(text)):
        sym = (row.get("Symbol") or "").strip()
        ind = (row.get("Industry") or "").strip()
        if sym and ind and ind != "Industry":
            out[sym] = ind
    return out


def newest_reference(folder: Path = REFERENCE_DIR) -> Path | None:
    files = sorted(folder.glob("nse_industry_*.csv"))
    return files[-1] if files else None


def reference_date(path: Path) -> str:
    """nse_industry_2026-09-26.csv → 2026-09-26"""
    return path.stem.removeprefix("nse_industry_")


def nse_symbol(symbol: str, yf_ticker: str | None) -> str:
    """The register keys by its own symbol (REC); NSE by its trading symbol (RECLTD),
    which is the yfinance ticker stem."""
    return yf_ticker.removesuffix(".NS") if yf_ticker else symbol


def fetch_nse_industry_csv() -> str:
    """NETWORK — never in CI."""
    req = urllib.request.Request(NSE_TOTAL_MARKET_URL,
                                 headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        text: str = resp.read().decode("utf-8")
    if not parse_nse_industry_csv(text):
        raise ValueError("NSE Industry list came back empty")
    return text


if __name__ == "__main__":
    out = REFERENCE_DIR / f"nse_industry_{datetime.now(UTC).strftime('%Y-%m-%d')}.csv"
    out.write_text(fetch_nse_industry_csv())
    print(f"saved {out}", file=sys.stderr)
