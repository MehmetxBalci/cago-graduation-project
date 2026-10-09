"""Presentation helpers: display-only normalisation, SR wording, cards and evidence-based explanations.

Nothing here feeds back into generation or evaluation. In particular `merge_display_materials` returns a NEW list and never
mutates the candidate that was evaluated.
"""
from __future__ import annotations

import json
from typing import Any

ROLE_ORDER = ("balanced", "sorting_focused", "intent_focused")
ROLE_TITLES = {"balanced": "Balanced", "sorting_focused": "Sorting-focused", "intent_focused": "Intent-focused"}
SR_RULES = {
    "SR1": ("Supported fibre composition", "The readable (outer) composition is a mono- or two-fibre blend that the screening rules list as supported."),
    "SR2": ("Blend complexity", "The readable composition has fewer than three distinct fibres."),
    "SR3": ("Minor-fibre detectability", "Every non-dominant fibre of the readable composition is at least 5%."),
    "SR4": ("Colour screening", "The garment colour is not black (black is used as a screening proxy for detection difficulty)."),
    "SR5": ("Hidden-layer consistency", "Linings / fillings do not contain a material above 5% that is absent from the surface."),
}
ZERO_VIOLATION_TEXT = "No violations detected under the CAGO SR1–SR5 sorting-screening rules."
DISCLAIMER = [
    "CAGO is a graduation-project prototype.",
    "Sorting results refer only to the SR1–SR5 screening rules.",
    "Zero detected violations does not guarantee recyclability or manufacturability.",
    "Plausibility is dataset-relative: it measures support and similarity relative to the TRAIN dataset.",
    "Recommendations are generated from patterns and support found in the TRAIN dataset.",
]
BANNED_CLAIMS = ("recyclability percentage", "sustainability percentage", "guaranteed recyclable", "% recyclable", "ai confidence",
                 "is recyclable", "100% recyclable", "sustainable %", "recyclability %", "manufacturability probability")


def merge_display_materials(materials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """DISPLAY ONLY: merge identical (normalised) material names within one component and sort by percentage.
    Returns a new list; the input (the evaluated candidate) is left untouched."""
    agg: dict[str, float] = {}
    order: list[str] = []
    for m in materials:
        key = str(m["material"]).strip().casefold()
        if key not in agg:
            agg[key] = 0.0
            order.append(key)
        agg[key] += float(m["pct"])
    merged = [{"material": k, "pct": round(agg[k], 6), "merged_slots": sum(str(m["material"]).strip().casefold() == k for m in materials)} for k in order]
    return sorted(merged, key=lambda x: (-x["pct"], x["material"]))


def fmt_pct(p: float) -> str:
    return f"{p:.0f}%" if abs(p - round(p)) < 1e-6 else f"{p:.1f}%"


def composition_lines(components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for c in components:
        merged = merge_display_materials(c["materials"])
        out.append({"component": c["component_name_normalized"].replace("_", " "), "component_class": c["component_class"].replace("_component", ""),
                    "materials": merged, "text": ", ".join(f"{m['material']} {fmt_pct(m['pct'])}" for m in merged),
                    "had_duplicate_slots": any(m["merged_slots"] > 1 for m in merged)})
    return out


def _json_list(v: Any) -> list[dict[str, Any]]:
    if isinstance(v, str):
        try:
            return json.loads(v)
        except ValueError:
            return []
    return list(v or [])


def sr_detail(rule: str, oracle: dict[str, Any], colour: str | None) -> str:
    """Plain-language reason for a VIOLATED rule, built from the Oracle's own outputs."""
    if rule == "SR1":
        reason = {"unsupported_mono": "single fibre outside the supported list", "unsupported_binary": "two-fibre blend outside the supported list",
                  "more_than_two_fibres": "more than two fibres", "no_readable_material": "no readable material"}.get(oracle.get("sr1_reason"), oracle.get("sr1_reason"))
        return f"Readable composition: {reason}."
    if rule == "SR2":
        return f"Readable composition has {oracle.get('sr2_fibre_count')} distinct fibres (3 or more is flagged)."
    if rule == "SR3":
        t = _json_list(oracle.get("sr3_trigger_materials"))
        return "Minor fibre(s) below 5%: " + ", ".join(f"{x['material']} {fmt_pct(x['pct'])}" for x in t) + "." if t else "Minor fibre below 5%."
    if rule == "SR4":
        return f"Colour is '{colour}'. Colour is inherited from the TRAIN template and is not changed by CAGO V1."
    if rule == "SR5":
        t = _json_list(oracle.get("sr5_trigger_materials"))
        where = oracle.get("sr5_hidden_component") or "hidden layer"
        return f"{where.replace('_', ' ')} contains " + ", ".join(f"{x['material']} {fmt_pct(x['pct'])}" for x in t) + " not present on the surface."
    return ""


def sr_status(oracle: dict[str, Any], colour: str | None) -> list[dict[str, Any]]:
    rows = []
    for r, (name, ok_text) in SR_RULES.items():
        v = bool(oracle[f"sr{r[2]}_violation"])
        rows.append({"rule": r, "name": name, "violated": v, "status": "Violation detected" if v else "No violation detected",
                     "detail": sr_detail(r, oracle, colour) if v else ok_text})
    return rows


def sorting_summary_text(vc: int, sr_rows: list[dict[str, Any]]) -> str:
    if vc == 0:
        return ZERO_VIOLATION_TEXT
    flagged = ", ".join(f"{r['rule']} ({r['name'].lower()})" for r in sr_rows if r["violated"])
    return f"{vc} of 5 sorting-screening rules flagged: {flagged}."


def score_label(x: float | None) -> str:
    return "not scored (no scorable preference)" if x is None else f"{x:.0f} / 100"


def contains_banned_claim(text: str) -> list[str]:
    low = text.lower()
    return [b for b in BANNED_CLAIMS if b in low]
