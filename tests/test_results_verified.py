"""tests/test_results_verified.py — dates verified online override a wrong/stale feed."""
from __future__ import annotations

from pathlib import Path

from store.repo import PattazRepo, VerifiedResult
from tools.results_dates import BatchResultDates
from tools.stamped import Stamped
from usecases.results import effective_results

YAHOO = BatchResultDates(dates={
    "M&M": Stamped(value=("2026-06-03", "2026-09-10"), source="yahoo", as_of="x"),
    "INFY": Stamped(value=("2026-07-23",), source="yahoo", as_of="x"),
})
MM = VerifiedResult("M&M", "2026-07-30", "2026-10-14", "mahindra.com", "2026-09-26")


def test_verified_replaces_wrong_feed_until_valid_until() -> None:
    r = effective_results(YAHOO, [MM], {"M&M": "M&M"}, "2026-09-26")
    assert r.dates["M&M"].value == ("2026-07-30",)
    assert r.dates["M&M"].source.startswith("verified:")
    assert r.dates["INFY"] == YAHOO.dates["INFY"]          # untouched


def test_expired_verification_fails_closed() -> None:
    r = effective_results(YAHOO, [MM], {"M&M": "M&M"}, "2026-10-15")
    assert "M&M" not in r.dates and "re-verify" in r.failures["M&M"]


def test_register_symbol_maps_to_ticker_stem() -> None:
    v = VerifiedResult("REC", "2026-08-01", "2026-10-14", "src", "2026-09-26")
    r = effective_results(BatchResultDates(), [v], {"REC": "RECLTD"}, "2026-09-26")
    assert r.dates["RECLTD"].value == ("2026-08-01",)


def test_register_holds_the_verified_facts(scratch_db: Path) -> None:
    with PattazRepo(scratch_db) as repo:
        got = {v.symbol: v.last_result for v in repo.load_results_verified()}
        brands = {n.symbol: n.brand_owned for n in repo.load_names()
                  if n.sector_class == "FMCG"}
    assert got["M&M"] == "2026-07-30" and got["TEXRAIL"] == "2026-08-03"
    assert brands["ITC"] is True and brands["HINDUNILVR"] is False
    assert brands["VBL"] is False
