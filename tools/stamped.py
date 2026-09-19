"""tools/stamped.py — Stamped[T]: frozen provenance wrapper for every fetched value.

Spec: E2 (the number law). Every price, valuation ratio, trigger level, rupee value
or cost basis crossing a layer boundary must carry {value, source, as_of}.
A bare number crossing a layer boundary is a build failure.
"""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Stamped(BaseModel, Generic[T], frozen=True):
    """Immutable provenance envelope for a fetched or derived value (E2)."""

    value: T
    source: str
    as_of: str  # ISO-8601 datetime or date string
