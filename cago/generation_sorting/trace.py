"""Structured repair trace (facts only: every field is a measured before/after value; no free-form causality)."""
from __future__ import annotations

from typing import Any

from cago.generation.mutations import replay
from cago.generation_sorting.oracle_view import RULES

STEP_FIELDS = ("step", "targeted_rule", "oracle_reason_before", "operation", "component", "materials_before", "materials_after",
               "oracle_before", "oracle_after", "intent_before", "intent_after", "plausibility_before", "plausibility_after",
               "accepted", "rejection_reason")


def oracle_flags(o: dict[str, Any]) -> dict[str, bool]:
    return {r: bool(o[f"sr{r[2]}_violation"]) for r in RULES}


def make_step(step: int, rule: str, reason_before: Any, operation: str, component: dict[str, Any], mats_before, mats_after,
              o_before: dict[str, Any], o_after: dict[str, Any], intent_before, intent_after, plaus_before, plaus_after,
              accepted: bool, rejection_reason: str | None, entries: list[dict[str, Any]]) -> dict[str, Any]:
    fb, fa = oracle_flags(o_before), oracle_flags(o_after)
    fixed = [r for r in RULES if fb[r] and not fa[r]]
    introduced = [r for r in RULES if fa[r] and not fb[r]]
    return {
        "step": step, "targeted_rule": rule, "oracle_reason_before": reason_before, "operation": operation, "component": component,
        "materials_before": mats_before, "materials_after": mats_after,
        "oracle_before": {"flags": fb, "violation_count": int(o_before["violation_count"])},
        "oracle_after": {"flags": fa, "violation_count": int(o_after["violation_count"])},
        "intent_before": intent_before, "intent_after": intent_after,
        "intent_delta": None if intent_before is None or intent_after is None else round(intent_after - intent_before, 6),
        "plausibility_before": plaus_before, "plausibility_after": plaus_after,
        "plausibility_delta": round(plaus_after - plaus_before, 6),
        "accepted": accepted, "rejection_reason": rejection_reason,
        # a fix is claimed ONLY when the before/after Oracle evaluation confirms the flip True -> False
        "confirmed_fixed_rules": fixed, "claims_targeted_fix": rule in fixed, "introduced_rules": introduced, "entries": entries}


def verify_trace(template_components, pre_repair_components, steps: list[dict[str, Any]], final_components) -> bool:
    """Replaying the ACCEPTED steps' log entries on the pre-repair candidate must reproduce the final candidate exactly,
    and each accepted step's materials_before/after must chain."""
    comps = [dict(c, materials=[dict(m) for m in c["materials"]]) for c in pre_repair_components]
    acc = [s for s in steps if s["accepted"]]
    state = replay(pre_repair_components, [e for s in acc for e in s["entries"]])
    if [[(m["material"], m["pct"]) for m in c["materials"]] for c in state] != \
            [[(m["material"], m["pct"]) for m in c["materials"]] for c in final_components]:
        return False
    cur = comps
    for s in acc:
        ci = s["component"]["index"]
        if [(m, p) for m, p in s["materials_before"]] != [(m["material"], m["pct"]) for m in cur[ci]["materials"]]:
            return False
        cur = replay(cur, s["entries"])
        if [(m, p) for m, p in s["materials_after"]] != [(m["material"], m["pct"]) for m in cur[ci]["materials"]]:
            return False
    return True
