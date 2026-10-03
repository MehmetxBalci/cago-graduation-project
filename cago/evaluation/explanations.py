"""Structured, fact-backed explanations. Every statement derives from a computed value or a before/after comparison.

Causal wording is used ONLY when confirmed: a rule whose flag differs between template and candidate is attributed to a
mutation step only if replaying the mutation log WITHOUT that step reverts the flag (single-step ablation).
"""
from __future__ import annotations

from typing import Any

from cago.evaluation.config import EvaluationConfig
from cago.evaluation.candidate import RULES
from cago.generation.baseline import oracle_eval, public_components
from cago.generation.mutations import replay
from cago.generation.template_selector import Template

DISCLAIMER = ("Indices are computed from composition/label data only (preference alignment, rule satisfaction, similarity to "
              "the TRAIN distribution). They are not measures of physical performance, environmental impact or production feasibility.")


def describe_mutation(e: dict[str, Any]) -> str:
    if e["type"] == "substitution":
        tag = " (forbidden-material repair)" if e.get("reason") == "forbidden_repair" else ""
        return (f"Substituted {e['from_material']} with {e['to_material']} in component '{e['component_name']}' "
                f"(slot at {e['pct']:g}%){tag}")
    return (f"Moved {e['delta']:g} percentage points from {e['from_material']} ({e['pct_before'][0]:g}% -> {e['pct_after'][0]:g}%) "
            f"to {e['to_material']} ({e['pct_before'][1]:g}% -> {e['pct_after'][1]:g}%) in component '{e['component_name']}'")


def _rule_status(t: bool, c: bool) -> str:
    return ("resolved" if t and not c else "introduced" if c and not t else "still_violated" if c else "still_satisfied")


def _ablation(tmpl: Template, candidate: dict[str, Any], rule: str, template_flag: bool) -> list[int]:
    """Mutation steps whose removal reverts `rule` to the template's value (confirmed single-step necessity)."""
    steps = []
    log = candidate["mutation_log"]
    for k in range(len(log)):
        rest = [e for i, e in enumerate(log) if i != k]
        try:
            comps = public_components(replay(tmpl.components, rest))
        except ValueError:
            continue
        if any(m["pct"] < 0 for c in comps for m in c["materials"]):
            continue
        if bool(oracle_eval("ablate", candidate["normalized_colour"], comps)[rule]) == template_flag:
            steps.append(log[k]["step"])
    return steps


def explain_candidate(candidate: dict[str, Any], ev: dict[str, Any], tev: dict[str, Any], tmpl: Template,
                      roles: list[str], cfg: EvaluationConfig = EvaluationConfig()) -> dict[str, Any]:
    """candidate: generator record; ev/tev: evaluation of the candidate / of its unmutated template."""
    prefs = {"satisfied": [], "partial": [], "not_satisfied": [], "unscorable": []}
    for p in ev["intent"]["preferences"]:
        row = {"preference": p["preference"], "requested_value": p["requested_value"],
               "satisfaction_0_1": p["satisfaction_0_1"], "explanation": p["explanation"]}
        if not p["scorable"]:
            prefs["unscorable"].append({**row, "reason": p["unscorable_reason"]})
        elif p["satisfaction_0_1"] >= cfg.satisfied_min:
            prefs["satisfied"].append(row)
        elif p["satisfaction_0_1"] <= cfg.not_satisfied_max:
            prefs["not_satisfied"].append(row)
        else:
            prefs["partial"].append(row)
    o_c, o_t = ev["sorting"]["oracle"], tev["sorting"]["oracle"]
    rules = []
    for r in RULES:
        name = r[:3].upper()
        status = _rule_status(bool(o_t[r]), bool(o_c[r]))
        row = {"rule": name, "candidate_violated": bool(o_c[r]), "template_violated": bool(o_t[r]), "vs_template": status}
        if status in ("resolved", "introduced"):
            row["confirmed_by_mutation_steps"] = _ablation(tmpl, candidate, r, bool(o_t[r]))
        rules.append(row)
    mutations = [{"step": e["step"], "type": e["type"], "reason": e["reason"], "description": describe_mutation(e)}
                 for e in candidate["mutation_log"]]
    dv = ev["sorting"]["violation_count"] - tev["sorting"]["violation_count"]
    di = None if ev["intent_alignment_raw"] is None or tev["intent_alignment_raw"] is None \
        else round(100 * (ev["intent_alignment_raw"] - tev["intent_alignment_raw"]), 2)
    dp = round(100 * (ev["plausibility_raw"] - tev["plausibility_raw"]), 2)
    statements = []
    for r in rules:
        if r["vs_template"] in ("resolved", "introduced"):
            steps = r["confirmed_by_mutation_steps"]
            how = (f"confirmed: undoing mutation step(s) {steps} restores the template's {r['rule']} result" if steps
                   else "no single mutation step alone is confirmed to cause this change")
            verb = "no longer violated" if r["vs_template"] == "resolved" else "newly violated"
            statements.append(f"{r['rule']} is {verb} compared with the template ({how}).")
    for p in prefs["satisfied"]:
        statements.append(f"Preference '{p['preference']}={p['requested_value']}' satisfied: {p['explanation']}.")
    for p in prefs["not_satisfied"] + prefs["partial"]:
        statements.append(f"Preference '{p['preference']}={p['requested_value']}' not fully satisfied "
                          f"(satisfaction {p['satisfaction_0_1']:g}): {p['explanation']}.")
    for p in prefs["unscorable"]:
        statements.append(f"Preference '{p['preference']}={p['requested_value']}' could not be scored ({p['reason']}).")
    trade = [f"Sorting rule violations: template {tev['sorting']['violation_count']} -> candidate {ev['sorting']['violation_count']} ({dv:+d})."]
    if di is not None:
        trade.append(f"Intent alignment index: template {100 * tev['intent_alignment_raw']:.1f} -> candidate "
                     f"{100 * ev['intent_alignment_raw']:.1f} ({di:+.1f} points).")
    trade.append(f"Dataset-relative plausibility index: template {100 * tev['plausibility_raw']:.1f} -> candidate "
                 f"{100 * ev['plausibility_raw']:.1f} ({dp:+.1f} points).")
    if dv < 0 and di is not None and di < 0:
        trade.append("Trade-off: sorting rule violations decreased while intent alignment decreased relative to the template.")
    if dv > 0 and di is not None and di > 0:
        trade.append("Trade-off: intent alignment increased while sorting rule violations increased relative to the template.")
    return {"candidate_id": candidate["candidate_id"], "roles": roles, "template_garment_id": candidate["template_garment_id"],
            "preferences": prefs, "sorting": {"violation_count": ev["sorting"]["violation_count"],
                                              "template_violation_count": tev["sorting"]["violation_count"],
                                              "sorting_compatibility_index_0_100": ev["sorting"]["sorting_compatibility_index_0_100"],
                                              "rules": rules, "sr_explanation": o_c["explanation"]},
            "mutations": mutations, "deltas_vs_template": {"violation_count": dv, "intent_points": di, "plausibility_points": dp},
            "trade_offs": trade, "statements": statements, "disclaimer": DISCLAIMER}
