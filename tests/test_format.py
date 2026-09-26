"""tests/test_format.py — the shared rupee display helper (usecases/format.inr)."""
from __future__ import annotations

from decimal import Decimal

import pytest

from usecases.format import inr


@pytest.mark.parametrize(("v", "want"), [
    (Decimal(0), "Rs 0"),
    (Decimal("999.49"), "Rs 999"),
    (Decimal("999.5"), "Rs 1,000"),
    (Decimal(347775), "Rs 3,47,775"),
    (Decimal(12345678), "Rs 1,23,45,678"),
    (Decimal(-25000), "-Rs 25,000"),
])
def test_inr_indian_grouping(v: Decimal, want: str) -> None:
    assert inr(v) == want


def test_plate_and_ranker_share_the_public_helper() -> None:
    import usecases.plate as plate_uc
    import usecases.ranker as ranker_uc
    assert not hasattr(plate_uc, "_inr")
    assert plate_uc.inr is inr and ranker_uc.inr is inr
