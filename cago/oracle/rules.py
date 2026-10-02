"""Baseline SR1-SR5 rules as pure functions. A violation means the rule's barrier is triggered."""
from __future__ import annotations

from typing import Any

from cago.oracle.config import (HIDDEN_CLASSES, HIDDEN_NAMES, SR1_BINARY, SR1_MONO, SR3_THRESHOLD_PCT,
                                SR4_BLACK, SR5_THRESHOLD_PCT)
from cago.oracle.selection import Component, aggregate


def sorted_materials(readable: dict[str, float]) -> list[tuple[str, float]]:
    """Descending pct, ties broken alphabetically (as in the published implementation)."""
    return sorted(readable.items(), key=lambda kv: (-kv[1], kv[0]))


def sr1(readable: dict[str, float]) -> tuple[bool, str]:
    n = len(readable)
    if n == 0:
        return True, "no_readable_material"
    if n == 1:
        return (False, "supported_mono") if next(iter(readable)) in SR1_MONO else (True, "unsupported_mono")
    if n == 2:
        return (False, "supported_binary") if frozenset(readable) in SR1_BINARY else (True, "unsupported_binary")
    return True, "more_than_two_fibres"


def sr2(readable: dict[str, float]) -> tuple[bool, int]:
    n = len(readable)
    return n >= 3, n


def sr3(readable: dict[str, float]) -> tuple[bool, list[dict[str, Any]]]:
    """Non-dominant fibres with pct < 5.0 (exactly 5.0 passes). Dominant fibre is never checked."""
    ordered = sorted_materials(readable)
    trig = [{"material": m, "pct": p} for m, p in ordered[1:] if p < SR3_THRESHOLD_PCT]
    return bool(trig), trig


def sr4(colour_raw: Any) -> tuple[bool, str]:
    """Exact 'black' after str().strip().lower(); no substring matching. None -> ''."""
    norm = str(colour_raw if colour_raw is not None else "").strip().lower()
    return norm == SR4_BLACK, norm


def is_hidden(c: Component) -> bool:
    return c.cls in HIDDEN_CLASSES or c.name in HIDDEN_NAMES


def sr5(comps: list[Component], surface_set: dict[str, float]) -> tuple[bool, Component | None, list[dict[str, Any]]]:
    """First hidden component holding a material with aggregated pct > 5.0 absent from the surface set.

    Returns (violation, triggering hidden component, trigger materials of that component).
    """
    for c in comps:
        if not is_hidden(c):
            continue
        trig = [{"material": m, "pct": p} for m, p in aggregate(c.materials).items()
                if p > SR5_THRESHOLD_PCT and m not in surface_set]
        if trig:
            return True, c, trig
    return False, None, []
