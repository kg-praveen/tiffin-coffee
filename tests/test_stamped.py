"""tests/test_stamped.py — Stamped[T] contract tests.

Spec: E2 — a bare number crossing a layer boundary is a build failure.
"""
from decimal import Decimal

import pytest
from pydantic import ValidationError

from tools.stamped import Stamped


class TestStampedContract:
    def test_frozen(self) -> None:
        s = Stamped(value=Decimal("100.50"), source="test", as_of="2026-09-19")
        with pytest.raises(ValidationError):
            s.value = Decimal(200)  # type: ignore[misc]

    def test_generic_decimal(self) -> None:
        s = Stamped[Decimal](value=Decimal("7.04"), source="gsec", as_of="2026-09-19")
        assert s.value == Decimal("7.04")
        assert s.source == "gsec"
        assert s.as_of == "2026-09-19"

    def test_generic_str(self) -> None:
        s = Stamped[str](value="LENDER", source="runtime §SC", as_of="2026-09-19")
        assert s.value == "LENDER"

    def test_equality(self) -> None:
        a = Stamped(value=42, source="x", as_of="2026-01-01")
        b = Stamped(value=42, source="x", as_of="2026-01-01")
        assert a == b

    def test_requires_all_fields(self) -> None:
        with pytest.raises(ValidationError):
            Stamped(value=1, source="x")  # type: ignore[call-arg]
        with pytest.raises(ValidationError):
            Stamped(value=1, as_of="x")  # type: ignore[call-arg]
