"""Null-safe numeric parsing.

Zero is a valid measurement. Blank, NA, NaN, and non-finite values stay None.
"""

from __future__ import annotations

import math
from typing import Any


def optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text or text.lower() in {"na", "n/a", "nan", "none", "null", "--", "-"}:
            return None
        text = text.replace(",", "").replace("%", "")
        try:
            number = float(text)
        except ValueError:
            return None
    else:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
    if not math.isfinite(number):
        return None
    return number


def optional_int(value: Any) -> int | None:
    number = optional_float(value)
    if number is None or not float(number).is_integer():
        return None
    return int(number)


def utilization_to_percent(value: Any) -> float | None:
    """Normalize utilization to percent points.

    Legacy NetLynx parser contracts often store utilization as a fraction
    (0.95 = 95%). FACT CSV exports and SOC sheets more often use percent.
    Rule: values in [0, 1] → fraction * 100; values > 1 → already percent.
    """

    number = optional_float(value)
    if number is None:
        return None
    if 0.0 <= number <= 1.0:
        return number * 100.0
    return number
