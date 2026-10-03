"""Candidate evaluation: hard gate -> intent / sorting / plausibility (kept separate, never merged for Pareto)."""
from __future__ import annotations

from typing import Any

from cago.evaluation.config import EvaluationConfig
from cago.evaluation.intent import evaluate_intent
from cago.evaluation.plausibility import evaluate_plausibility
from cago.generation.baseline import oracle_eval, public_components
from cago.generation.distance import template_distance
from cago.generation.support_tables import SupportTables
from cago.generation.template_selector import Template
from cago.requirements.validation import RequirementContext, validate_candidate

RULES = ("sr1_violation", "sr2_violation", "sr3_violation", "sr4_violation", "sr5_violation")
SORTING_NOTE = ("equal-weight rule-satisfaction index over SR1-SR5; NOT a recyclability percentage and NOT an environmental-impact measure")


def hard_gate(candidate: dict[str, Any], request: dict[str, Any], ctx: RequirementContext) -> list[dict[str, str]]:
    """Pass/fail gate OUTSIDE scoring. [] = valid. Re-checks the generator's output independently."""
    forb = request["hard_constraints"]["forbidden_materials"]
    issues = [{"code": i.code, "where": str(i.field), "detail": i.message}
              for i in validate_candidate(candidate["components"], forb, ctx)]
    if candidate.get("target_segment") != request["target_segment"] or candidate.get("detail_category") != request["detail_category"]:
        issues.append({"code": "request_mismatch", "where": "candidate", "detail": "segment/category differ from request"})
    return issues


def sorting_summary(oracle: dict[str, Any]) -> dict[str, Any]:
    vc = int(oracle["violation_count"])
    return {"violation_count": vc, "sorting_rules_satisfied": 5 - vc,
            "sorting_compatibility_index_0_100": round(100 * (5 - vc) / 5, 2), "index_note": SORTING_NOTE,
            "rules": {r[:3].upper(): bool(oracle[r]) for r in RULES}, "oracle": oracle}


def _assemble(cid: str, template_id: str, request: dict[str, Any], components, colour, tmpl: Template, distance,
              oracle, support: SupportTables, cfg: EvaluationConfig) -> dict[str, Any]:
    soft = request["soft_preferences"]
    intent = evaluate_intent(soft, components, colour, tmpl.fit_label, tmpl.length_label, tmpl.text_tags, cfg)
    sorting = sorting_summary(oracle)
    plaus = evaluate_plausibility(components, request["detail_category"], distance, support, cfg)
    ir = intent["intent_alignment_raw"]
    return {
        "candidate_id": cid, "template_garment_id": template_id,
        "intent": intent, "sorting": sorting, "plausibility": plaus,
        "intent_alignment_raw": ir, "plausibility_raw": plaus["plausibility_raw"],
        "objectives": {"violation_count": sorting["violation_count"],
                       "intent_loss": None if ir is None else round(1.0 - ir, 6),
                       "plausibility_loss": round(1.0 - plaus["plausibility_raw"], 6)},
        "template_distance_raw": {k: distance[k] for k in ("n_substitutions", "abs_pct_change_total", "diagnostic_distance")},
    }


def evaluate_candidate(candidate: dict[str, Any], request: dict[str, Any], tmpl: Template, support: SupportTables,
                       cfg: EvaluationConfig = EvaluationConfig()) -> dict[str, Any]:
    """Score one hard-valid candidate. The stored Oracle result is used as is (recomputed only if absent)."""
    comps = candidate["components"]
    oracle = candidate.get("oracle") or oracle_eval(candidate["candidate_id"], candidate["normalized_colour"], comps)
    ev = _assemble(candidate["candidate_id"], candidate["template_garment_id"], request, comps, candidate["normalized_colour"],
                   tmpl, candidate["template_distance"], oracle, support, cfg)
    ev["n_mutations"] = candidate["n_mutations"]
    return ev


def evaluate_template(tmpl: Template, request: dict[str, Any], support: SupportTables,
                      cfg: EvaluationConfig = EvaluationConfig()) -> dict[str, Any]:
    """The unmutated template evaluated with the same functions (baseline for before/after comparisons).
    Hard constraints are NOT applied (a template may still contain a forbidden material that candidates repair)."""
    comps = public_components(tmpl.components)
    dist = template_distance(comps, comps)
    return _assemble("template:" + tmpl.garment_id, tmpl.garment_id, request, comps, tmpl.colour, tmpl, dist,
                     oracle_eval(tmpl.garment_id, tmpl.colour, comps), support, cfg)


def evaluate_request_candidates(res: dict[str, Any], support: SupportTables, ctx: RequirementContext,
                                cfg: EvaluationConfig = EvaluationConfig()) -> dict[str, Any]:
    """Hard-gate every generated candidate, then evaluate the valid ones. Invalid ones are listed, never scored."""
    if tuple(support.splits_used) != ("train",):
        raise ValueError("support tables must be TRAIN-only")
    req = res["request"]
    tmap = {t.garment_id: t for t in res["templates"]}
    valid, excluded = [], []
    for c in res["candidates"]:
        issues = hard_gate(c, req, ctx)
        if issues:
            excluded.append({"candidate_id": c["candidate_id"], "issues": issues})
        else:
            valid.append(evaluate_candidate(c, req, tmap[c["template_garment_id"]], support, cfg))
    templates = {t.garment_id: evaluate_template(t, req, support, cfg) for t in res["templates"]}
    return {"valid": valid, "excluded": excluded, "templates": templates}
