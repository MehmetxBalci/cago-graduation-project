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


# ---------------------------------------------------------------- plain-language wording (display only)
# The frozen evaluation produces technical evidence tokens (e.g. "breathable_fibre_share=0.85"). The functions below turn the
# structured values into readable sentences; they never change a score, a status or the composition. The original technical
# explanation stays available next to the readable sentence.
PREFERENCE_NAMES = {"preferred_dominant_material": "preferred dominant material", "colour": "colour", "fit": "fit", "length_cut": "length",
                    "stretch": "stretch", "thermal_warmth": "thermal warmth", "breathability": "breathability", "durability_wear": "durability",
                    "moisture_wicking": "moisture wicking", "water_repellent": "water repellency"}
_SHARE_TEXT = {
    "breathable_fibre_share": "share of breathable fibres (linen, cotton, lyocell, viscose) in the main fabric",
    "light_fibre_share": "share of light fibres (cotton, linen, lyocell, viscose) in the main fabric",
    "wool_acrylic_share": "share of wool and acrylic in the main fabric",
    "nylon_share": "share of nylon in the main fabric",
    "polyester_nylon_share": "share of polyester and nylon in the main fabric",
    "polyester_filling_share": "share of polyester in the filling",
    "wool_penalty": "deduction for wool in the main fabric",
}
_FLAG_TEXT = {
    "coating_penalty": "a coating layer lowers breathability",
    "filling_penalty": "a filling layer counts against this preference",
    "filling_present": "a filling layer adds warmth",
    "polyester_blend": "a polyester blend adds durability",
    "coating_component": "a coating layer (strong water-repellency evidence)",
    "supporting:synthetic_shell": "a mainly synthetic outer fabric (supporting evidence only, not proof)",
    "strong_evidence_present": "strong water-repellency evidence found",
    "no_strong_evidence (synthetic shell alone is not proof)": "no strong water-repellency evidence (a synthetic outer fabric alone is not proof)",
    "neutral": "neutral request",
}
_STRETCH_BUCKET = {"none": "no elastane (no stretch)", "low": "a low elastane share (low stretch)", "high": "a high elastane share (high stretch)",
                   "out_of_range": "an elastane share outside the supported range"}
_UNSCORABLE_TEXT = {
    "neutral_value": "'standard' is a neutral choice, so it is not scored",
    "no_label_evidence": "the template has no {pref} label in the dataset, so this preference cannot be checked (it is not counted as a miss)",
    "no_primary_component_materials": "the main fabric lists no materials",
    "candidate_colour_unavailable": "the template has no recorded colour",
}


def evidence_phrase(token: str) -> str:
    """One technical evidence token -> readable phrase (unknown tokens are returned unchanged)."""
    if token in _FLAG_TEXT:
        return _FLAG_TEXT[token]
    if token.startswith("text:"):
        return "product text mentions " + token[5:].replace("_", " ").replace(",", ", ")
    if "=" in token:
        key, val = token.split("=", 1)
        if key in _SHARE_TEXT:
            try:
                return f"{_SHARE_TEXT[key]}: {float(val) * 100:.0f}%"
            except ValueError:
                return f"{_SHARE_TEXT[key]}: {val}"
        if key == "elastane":
            return f"elastane share: {val}"
        if key in ("bucket", "stretch_bucket"):
            return "stretch level: " + _STRETCH_BUCKET.get(val, val)
        if key == "primary_component":
            return f"main fabric: {val.replace('_', ' ')}"
        if key == "template_label":
            return f"template label: {val}"
        if key == "candidate_colour":
            return f"colour: {val}"
    return token


def preference_sentence(p: dict[str, Any]) -> str:
    """Readable explanation for one frozen intent entry (keys: preference, requested_value, scorable, satisfaction_0_1,
    evidence, unscorable_reason)."""
    name = PREFERENCE_NAMES.get(p["preference"], p["preference"].replace("_", " "))
    val = p["requested_value"]
    if not p["scorable"]:
        why = _UNSCORABLE_TEXT.get(p.get("unscorable_reason"), str(p.get("unscorable_reason") or "no evidence"))
        return "Not scored: " + why.format(pref=name) + "."
    ev = [str(t) for t in p.get("evidence", [])]
    if p["preference"] == "preferred_dominant_material":
        dom = next((t.split("=", 2) for t in ev if t.startswith("dominant=")), None)
        prim = next((t.split("=", 1)[1] for t in ev if t.startswith("primary_component=")), None)
        where = f"the main fabric ({prim.replace('_', ' ')})" if prim and prim != "main" else "the main fabric"
        if dom and len(dom) == 3:
            return f"The largest material in {where} is {dom[1]} at {dom[2]}" + ("" if dom[1] == val else f", not {val}") + "."
    if p["preference"] in ("fit", "length_cut", "colour"):
        got = next((t.split("=", 1)[1] for t in ev if "=" in t), None)
        src = "inherited from the TRAIN template" if p["preference"] != "colour" else "inherited from the TRAIN template; CAGO does not recolour"
        if got is not None:
            return f"The {name} is '{got}' ({src}); you asked for '{val}'."
    sat = p["satisfaction_0_1"]
    phrases = list(dict.fromkeys(evidence_phrase(t) for t in ev if t != "neutral"))      # de-duplicated, order kept
    if isinstance(val, bool):
        verb = "fully supports" if sat >= 0.99 else "does not support" if sat <= 0.01 else "partly supports"
        head = f"Composition-based estimate: {verb} {name}"
    else:
        verb = "fully meets" if sat >= 0.99 else "does not meet" if sat <= 0.01 else "partly meets"
        head = f"Composition-based estimate: {verb} '{val}' {name}"
    return head + (" — " + "; ".join(phrases) if phrases else "") + ". This is a proxy from the material list, not a measured property."


def _pp(d: float) -> str:
    return f"{d:g} percentage point" + ("" if abs(float(d) - 1) < 1e-9 else "s")


def change_number(step: int) -> int:
    """Generator steps are 0-based; the UI numbers changes from 1 (used consistently for changes and rule attributions)."""
    return int(step) + 1


def change_sentence(e: dict[str, Any]) -> str:
    """Readable description of one mutation-log entry (frozen generator log)."""
    comp = str(e.get("component_name", "component")).replace("_", " ") + " component"
    if e["type"] == "substitution":
        why = " to remove a forbidden material" if e.get("reason") == "forbidden_repair" else ""
        return (f"Change {change_number(e['step'])}: replaced {e['from_material']} with {e['to_material']} in the {comp} "
                f"(that material made up {fmt_pct(float(e['pct']))} of it){why}.")
    b, a = e["pct_before"], e["pct_after"]
    if e["from_material"] == e["to_material"]:
        return (f"Change {change_number(e['step'])}: moved {_pp(e['delta'])} between two {e['from_material']} entries in the {comp} "
                f"(the material total is unchanged).")
    return (f"Change {change_number(e['step'])}: moved {_pp(e['delta'])} from {e['from_material']} to {e['to_material']} in the {comp} "
            f"({e['from_material']} {fmt_pct(float(b[0]))} → {fmt_pct(float(a[0]))}, {e['to_material']} {fmt_pct(float(b[1]))} → {fmt_pct(float(a[1]))}).")


def rule_change_sentence(r: dict[str, Any]) -> str | None:
    """Readable statement for an SR rule whose result differs from the template (frozen ablation evidence)."""
    if r.get("vs_template") not in ("resolved", "introduced"):
        return None
    name = SR_RULES.get(r["rule"], (r["rule"],))[0].lower()
    steps = [change_number(x) for x in (r.get("confirmed_by_mutation_steps") or [])]
    undo = (f"undoing change {steps[0]}" if len(steps) == 1 else
            "undoing any one of changes " + ", ".join(map(str, steps[:-1])) + f" or {steps[-1]}") if steps else ""
    if r["vs_template"] == "resolved":
        head = f"{r['rule']} ({name}) is no longer flagged, while the template was flagged"
        tail = (f"; confirmed: {undo} on its own brings the flag back" if steps
                else "; no single change alone is confirmed as the cause")
    else:
        head = f"{r['rule']} ({name}) is newly flagged compared with the template"
        tail = (f"; confirmed: {undo} on its own removes the flag" if steps
                else "; no single change alone is confirmed as the cause")
    return head + tail + "."


def trade_off_sentence(s: str) -> str:
    """Light wording clean-up of the frozen template-vs-candidate trade-off lines."""
    return (s.replace(" -> ", " → ").replace("Sorting rule violations:", "SR1–SR5 violations:")
            .replace("Intent alignment index:", "Intent alignment:").replace("Dataset-relative plausibility index:", "Dataset-relative plausibility:"))


_CONFLICT_TEXT = {
    frozenset({"fit", "stretch"}): "the chosen fit is rarely combined with the chosen stretch level in the dataset",
    frozenset({"breathability", "water_repellent"}): "water-repellency evidence (coatings, membranes) works against high breathability",
    frozenset({"thermal_warmth", "breathability"}): "heavy warmth (fillings, padding) works against high breathability",
    frozenset({"stretch", "forbidden_materials"}): "stretch is estimated from elastane, but elastane is forbidden",
    frozenset({"moisture_wicking", "forbidden_materials"}): "moisture wicking is estimated from polyester and nylon, but both are forbidden",
    frozenset({"preferred_dominant_material", "stretch"}): "an elastane-dominant material contradicts 'no stretch'",
}


def conflict_text(fields: list[str], fallback: str) -> str:
    return _CONFLICT_TEXT.get(frozenset(fields), fallback)


def invalid_value_text(detail: str) -> str:
    """Remove API-only hints ("use null ...") from frozen validation messages shown in the UI."""
    return (detail.replace(" (use null for no preference)", "; choose one of these or 'No preference'")
            .replace("use true or null", "only true or 'No preference' is allowed"))
