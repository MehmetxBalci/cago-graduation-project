"""Read-only view of the frozen CAGO Oracle for proposal/repair logic.

All rule decisions are made by calling the frozen oracle functions (selection + rules) exactly as
`cago.oracle.engine.evaluate_garment` does; nothing about the Oracle is re-implemented.
"""
from __future__ import annotations

from typing import Any

from cago.oracle import rules as R
from cago.oracle.selection import aggregate, make_component, positive_only, select_readable, select_surface_reference

RULES = ("SR1", "SR2", "SR3", "SR4", "SR5")


def oracle_components(components: list[dict[str, Any]]):
    return [make_component(c["component_id"], c["component_name_normalized"], c["component_class"],
                           [(m["material"], m["pct"]) for m in c["materials"]]) for c in components]


def _index(oc_list, obj) -> int | None:
    return next((i for i, c in enumerate(oc_list) if c is obj), None)


def analyze(components: list[dict[str, Any]], colour: Any, counters=None) -> dict[str, Any]:
    """Rule flags + the Oracle's own explanation inputs (readable component, surface reference, triggers)."""
    if counters is not None:
        counters["fast_rule_evals"] += 1
    oc = oracle_components(components)
    readable_comp, _ = select_readable(oc)
    readable = positive_only(aggregate(readable_comp.materials)) if readable_comp else {}
    v1, reason1 = R.sr1(readable)
    v2, n_fibres = R.sr2(readable)
    v3, t3 = R.sr3(readable)
    v4, _ = R.sr4(colour)
    surf_comp, surf_set, _ = select_surface_reference(oc)
    v5, hid, t5 = R.sr5(oc, surf_set)
    return {"flags": {"SR1": v1, "SR2": v2, "SR3": v3, "SR4": v4, "SR5": v5}, "sr1_reason": reason1, "n_fibres": n_fibres,
            "readable_index": None if readable_comp is None else _index(oc, readable_comp), "readable": readable,
            "sr3_triggers": t3, "surface_index": None if surf_comp is None else _index(oc, surf_comp), "surface_set": set(surf_set),
            "sr5_hidden_index": None if hid is None else _index(oc, hid), "sr5_triggers": t5}


def violation_count(flags: dict[str, bool], rules=RULES) -> int:
    return sum(bool(flags[r]) for r in rules)


def reason_for(rule: str, a: dict[str, Any]) -> Any:
    """Oracle explanation for a violated rule (structured, not free text)."""
    if rule == "SR1":
        return a["sr1_reason"]
    if rule == "SR2":
        return f"n_distinct_fibres={a['n_fibres']}"
    if rule == "SR3":
        return {"minor_fibres_below_5pct": a["sr3_triggers"]}
    if rule == "SR5":
        return {"hidden_component_index": a["sr5_hidden_index"], "absent_from_surface": a["sr5_triggers"],
                "surface_set": sorted(a["surface_set"])}
    return "colour == black (immutable in Generator B V1)" if rule == "SR4" else None
