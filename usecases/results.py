"""usecases/results.py — combine fetched results dates with dates verified online.

Spec: E3 basis freshness. Yahoo's dates are wrong for some names (M&M) and stale for
others (Engineers India, RITES, Paradeep, Texmaco) — migration 007 records the real
dates with their source. A verified row replaces the fetched list until valid_until;
after that the name has NO dates (fails closed) until someone re-verifies it.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping

from store.repo import VerifiedResult
from tools.results_dates import BatchResultDates
from tools.stamped import Stamped


def effective_results(
    fetched: BatchResultDates,
    verified: Iterable[VerifiedResult],
    stem_of: Mapping[str, str],
    today: str,
) -> BatchResultDates:
    """stem_of maps register symbol → ticker stem (M&M → M&M, REC → RECLTD)."""
    dates = dict(fetched.dates)
    failures = dict(fetched.failures)
    for v in verified:
        stem = stem_of.get(v.symbol, v.symbol)
        if today <= v.valid_until:
            dates[stem] = Stamped(value=(v.last_result,), source=f"verified:{v.source}",
                                  as_of=v.verified_on)
            failures.pop(stem, None)
        else:
            dates.pop(stem, None)
            failures[stem] = (f"verified results date expired on {v.valid_until} — "
                              f"re-verify online")
    return BatchResultDates(dates=dates, failures=failures)
