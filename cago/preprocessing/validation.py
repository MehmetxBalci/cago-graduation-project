"""Independent percentage validation for each component."""
from __future__ import annotations

import math
from typing import Any

from cago.config.settings import PCT_TOLERANCE_HIGH, PCT_TOLERANCE_LOW


def classify_pct(value: Any) -> tuple[float | None, str]:
    """Return (numeric value or None, status in ok|missing|invalid). Bools, NaN/inf, <0, >100 are invalid."""
    if value is None:
        return None, "missing"
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None, "invalid"
    v = float(value)
    if not math.isfinite(v) or v < 0 or v > 100:
        return None, "invalid"
    return v, "ok"


def validate_component(pct_values: list[Any]) -> tuple[float | None, bool, str]:
    """Return (pct_sum_calculated, pct_valid, validation_status).

    pct_sum_calculated sums the valid numeric pcts (None when there are none).
    Priority: invalid_percentage > missing_percentage > zero_sum_component > percentage_out_of_tolerance > valid.
    pct_valid is True only when 99 <= sum <= 101 AND no pct is missing/invalid.
    """
    statuses, nums = [], []
    for raw in pct_values:
        v, st = classify_pct(raw)
        statuses.append(st)
        if v is not None:
            nums.append(v)
    total = math.fsum(nums) if nums else None
    if not pct_values:
        return None, False, "missing_percentage"
    if "invalid" in statuses:
        return total, False, "invalid_percentage"
    if "missing" in statuses:
        return total, False, "missing_percentage"
    if total == 0:
        return total, False, "zero_sum_component"
    if PCT_TOLERANCE_LOW <= total <= PCT_TOLERANCE_HIGH:
        return total, True, "valid"
    return total, False, "percentage_out_of_tolerance"
