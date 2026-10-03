"""Explainable diagnostic template distance (NOT a plausibility score).

Candidates keep the template's component order and material SLOT order, so each candidate slot is compared with the
template slot at the same position: a different material counts as one substitution; |pct difference| is added to the
absolute percentage change. diagnostic_distance = w_sub * n_substitutions + w_pct * abs_pct_change_total / 100.
"""
from __future__ import annotations

from typing import Any

W_SUB = 1.0
W_PCT = 1.0


def topology_preserved(template: list[dict[str, Any]], candidate: list[dict[str, Any]]) -> bool:
    """Same components in the same order with the same ids/class/name and material counts."""
    if len(template) != len(candidate):
        return False
    return all(t["component_id"] == c["component_id"] and t["component_class"] == c["component_class"]
               and t["component_name_normalized"] == c["component_name_normalized"]
               and t["source_component_index"] == c["source_component_index"]
               and len(t["materials"]) == len(c["materials"]) for t, c in zip(template, candidate))


def template_distance(template: list[dict[str, Any]], candidate: list[dict[str, Any]],
                      w_sub: float = W_SUB, w_pct: float = W_PCT) -> dict[str, Any]:
    if not topology_preserved(template, candidate):
        raise ValueError("candidate topology differs from template; distance is undefined")
    per, n_sub, abs_total, n_pct_slots, n_sub_comps = [], 0, 0.0, 0, 0
    for ci, (t, c) in enumerate(zip(template, candidate)):
        subs = sum(tm["material"] != cm["material"] for tm, cm in zip(t["materials"], c["materials"]))
        dpct = sum(abs(cm["pct"] - tm["pct"]) for tm, cm in zip(t["materials"], c["materials"]))
        n_pct_slots += sum(abs(cm["pct"] - tm["pct"]) > 1e-9 for tm, cm in zip(t["materials"], c["materials"]))
        n_sub += subs
        n_sub_comps += subs > 0
        abs_total += dpct
        per.append({"component_index": ci, "component_name": c["component_name_normalized"],
                    "substitutions": subs, "abs_pct_change": round(dpct, 6)})
    return {"n_substitutions": n_sub, "n_substituted_components": n_sub_comps,
            "abs_pct_change_total": round(abs_total, 6), "n_pct_changed_slots": n_pct_slots,
            "diagnostic_distance": round(w_sub * n_sub + w_pct * abs_total / 100.0, 6),
            "formula": f"{w_sub}*n_substitutions + {w_pct}*abs_pct_change_total/100", "per_component": per,
            "note": "diagnostic only; not a plausibility or intent-alignment score"}
