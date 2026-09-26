"""usecases/format.py — shared display helpers for the conversational output (E8).

Display only: no rule, no rounding of stored money. Rupee values are rounded to whole
rupees for reading; the Decimal in the register is untouched.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def inr(v: Decimal) -> str:
    """Indian grouping: Rs 3,47,775."""
    q = int(v.quantize(Decimal(1), rounding=ROUND_HALF_UP))
    s = str(abs(q))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts: list[str] = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return ("-" if q < 0 else "") + "Rs " + s
