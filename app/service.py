"""Central application service: user request -> validation -> frozen B3 generation -> frozen evaluation / Pareto / selection ->
UI-friendly output.

The research pipeline is called, never re-implemented:
  * validation:   cago.requirements.validation.validate_request
  * generation:   cago.generation_sorting.generator.generate_sorting_aware with the frozen B3 configuration
                  (proposal + repair, STRICT_SORTING, frozen floors / repair limits). Only the candidate budget and the seed are
                  application runtime parameters.
  * evaluation:   cago.evaluation.pipeline.evaluate_and_select (hard gate, Intent, SR1-SR5, Plausibility, Pareto, selections,
                  evidence-based explanations).
Only TRAIN rows / TRAIN support tables are used.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any, Callable

from app.adapters import REQUEST_TO_UI, UI_LABELS, AppData, form_to_raw_request
from app.presenters import (PREFERENCE_NAMES, ROLE_ORDER, ROLE_TITLES, ZERO_VIOLATION_TEXT, change_sentence, composition_lines,
                            conflict_text, invalid_value_text, preference_sentence, rule_change_sentence, score_label,
                            sorting_summary_text, sr_status, trade_off_sentence)
from cago.evaluation.config import EvaluationConfig
from cago.evaluation.pipeline import evaluate_and_select
from cago.generation_sorting.config import MODE_CONFIGS, SortingAwareGenerationConfig
from cago.generation_sorting.generator import generate_sorting_aware
from cago.requirements.validation import validate_request

FINAL_TEST_BUDGET = {"n_templates": 10, "candidates_per_template": 8}
STATUS_OK, STATUS_INVALID, STATUS_NO_TEMPLATES, STATUS_NO_CANDIDATES, STATUS_NO_VALID = (
    "ok", "invalid_request", "no_templates", "no_candidates", "no_valid_candidates")


@dataclass(frozen=True)
class AppConfig:
    """Application runtime parameters (NOT research configuration). Defaults equal the final TEST evaluation budget, which is
    responsive enough for the demo; smaller values can be chosen in the UI. Results of the app never reproduce the benchmark,
    because the benchmark requests are different."""
    n_templates: int = FINAL_TEST_BUDGET["n_templates"]
    candidates_per_template: int = FINAL_TEST_BUDGET["candidates_per_template"]

    def __post_init__(self):
        if not (1 <= self.n_templates <= 20 and 1 <= self.candidates_per_template <= 20):
            raise ValueError("demo budget must be between 1 and 20 templates / candidates per template")


def b3_config(app_cfg: AppConfig, seed: int) -> SortingAwareGenerationConfig:
    """Frozen B3 configuration; only n_templates / candidates_per_template / seed come from the app."""
    return SortingAwareGenerationConfig(n_templates=app_cfg.n_templates, candidates_per_template=app_cfg.candidates_per_template, seed=seed,
                                        **MODE_CONFIGS["B3"])


ERROR_TEXT = {
    "missing_required_field": "Please choose a {label}.",
    "invalid_target_segment": "This segment is not available in the CAGO TRAIN data.",
    "invalid_detail_category": "This garment category is not available in the CAGO TRAIN data.",
    "unknown_material": "Unknown material: {detail}.",
    "invalid_value": "Invalid value for {label}: {detail}.",
    "removed_in_v1": "{label}: {detail}.",
    "unknown_field": "Unknown field: {detail}.",
}


def _msg(level: str, code: str, text: str, fields: list[str] | None = None) -> dict[str, Any]:
    return {"level": level, "code": code, "text": text, "fields": fields or []}


def _label(field: str | None) -> str:
    return UI_LABELS.get(REQUEST_TO_UI.get(field or "", field or ""), field or "request")


def validation_messages(result) -> list[dict[str, Any]]:
    out = []
    for e in result.errors:
        fld = e.field if isinstance(e.field, str) else None
        tpl = ERROR_TEXT.get(e.code, "{detail}")
        detail = invalid_value_text(e.message) if e.code == "invalid_value" else e.message
        out.append(_msg("error", e.code, tpl.format(label=_label(fld).lower() if e.code == "missing_required_field" else _label(fld), detail=detail),
                        [fld] if fld else []))
    return out


def warning_messages(request: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for w in request.get("warnings", []):
        labels = ", ".join(_label(f) for f in w.get("fields", []))
        if w["code"] == "control_not_available":
            text = f"{labels} is not available for this garment category, so this preference was not used."
        elif w.get("severity") == "hard_override":
            text = "Your preferred material is also forbidden. Forbidden materials are a hard constraint, so the preference was not used."
        elif w["code"] == "preference_conflict":
            text = (f"Possible conflict between {labels}: {conflict_text(w.get('fields', []), w['message'])}. "
                    "Both preferences are kept; the trade-off is visible in the results.")
        else:
            text = w.get("message", w["code"])
        out.append(_msg("warning", w["code"], text, w.get("fields")))
    return out


def _role_reason(role: str, e: dict[str, Any], sel_row: dict[str, Any], front_size: int, dims: list[str]) -> str:
    vc = e["sorting"]["violation_count"]
    ia = e["intent"]["intent_alignment_0_100"]
    if role == "balanced":
        objs = ["sorting-rule violations (scaled 0–5)"] + (["intent loss"] if "intent_loss" in dims else []) + ["plausibility loss"]
        return (f"Balanced was selected because it is closest to the ideal point among the {front_size} Pareto candidate(s), giving equal weight "
                f"to {', '.join(objs[:-1])} and {objs[-1]} (distance {sel_row['balanced_distance']:.3f}).")
    if role == "sorting_focused":
        tail = f", while keeping an intent alignment of {ia:.0f}/100" if ia is not None else ""
        if vc == 0:
            return f"Sorting-focused was selected because it has no detected SR1–SR5 violations{tail}."
        return (f"Sorting-focused was selected because it has the lowest violation count on the Pareto front ({vc}){tail}. "
                "No Pareto candidate reached zero detected violations.")
    return f"Intent-focused was selected because it has the highest intent alignment on the Pareto front ({ia:.0f}/100)."


def _preference_lines(e: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for p in e["intent"]["preferences"]:
        if not p["scorable"]:
            status = "not scored"
        elif p["satisfaction_0_1"] >= 0.99:
            status = "satisfied"
        elif p["satisfaction_0_1"] <= 0.01:
            status = "not satisfied"
        else:
            status = "partially satisfied"
        req = p["requested_value"]
        out.append({"preference": _label(p["preference"]), "requested": "yes" if req is True else req, "status": status,
                    "satisfaction": p["satisfaction_0_1"], "explanation": preference_sentence(p), "technical": p["explanation"]})
    return out


def _comparison_lines(rec: dict[str, Any], others: list[dict[str, Any]]) -> list[str]:
    out = []
    for o in others:
        di = None if rec["intent_0_100"] is None or o["intent_0_100"] is None else rec["intent_0_100"] - o["intent_0_100"]
        dp = rec["plausibility_0_100"] - o["plausibility_0_100"]
        dv = rec["violation_count"] - o["violation_count"]
        parts = []
        if dv:
            parts.append(f"{'fewer' if dv < 0 else 'more'} sorting-rule violations ({rec['violation_count']} vs {o['violation_count']})")
        if di is not None and abs(di) >= 0.5:
            parts.append(f"{'higher' if di > 0 else 'lower'} intent alignment ({rec['intent_0_100']:.0f} vs {o['intent_0_100']:.0f})")
        if abs(dp) >= 0.5:
            parts.append(f"{'higher' if dp > 0 else 'lower'} dataset-relative plausibility ({rec['plausibility_0_100']:.0f} vs {o['plausibility_0_100']:.0f})")
        if parts:
            out.append(f"Compared with the {' / '.join(ROLE_TITLES[r] for r in o['roles'])} recommendation, this candidate has " + ", ".join(parts) + ".")
    return out


def _headline(rec: dict[str, Any]) -> list[str]:
    """Short evidence-based summary lines (preferences + remaining violations)."""
    out = []
    sat = [p for p in rec["preferences"] if p["status"] == "satisfied"]
    miss = [p for p in rec["preferences"] if p["status"] in ("not satisfied", "partially satisfied")]
    if sat:
        out.append("Matches your " + ", ".join(p["preference"].lower() for p in sat) + " preference" + ("s" if len(sat) > 1 else "") + ".")
    if miss:
        out.append("Does not fully meet your " + ", ".join(p["preference"].lower() for p in miss) + " preference" + ("s" if len(miss) > 1 else "") + ".")
    viol = [r for r in rec["sr"] if r["violated"]]
    if not viol:
        out.append(ZERO_VIOLATION_TEXT)
    else:
        out.append("Retains " + ", ".join(f"{r['rule']} ({r['name'].lower()})" for r in viol) + " sorting-screening violation"
                   + ("s" if len(viol) > 1 else "") + ".")
    return out


def _recommendations(pe: dict[str, Any], res: dict[str, Any], category: str) -> list[dict[str, Any]]:
    sel = pe["selection"]
    emap = {e["candidate_id"]: e for e in pe["evaluation"]["valid"]}
    cmap = {c["candidate_id"]: c for c in res["candidates"]}
    tmap = {t.garment_id: t for t in res["templates"]}
    xmap = {x["candidate_id"]: x for x in pe["explanations"]}
    front = [e for e in pe["evaluation"]["valid"] if e["is_pareto"]]
    dims = list(pe["pareto"].get("dimensions", []))
    rows = sorted(sel["selections"], key=lambda s: min(ROLE_ORDER.index(r) for r in s["roles"]))
    recs = []
    for s in rows:
        cid = s["candidate_id"]
        e, c = emap[cid], cmap[cid]
        t = tmap[c["template_garment_id"]]
        roles = sorted(s["roles"], key=ROLE_ORDER.index)
        sr = sr_status(e["sorting"]["oracle"], c["normalized_colour"])
        x = xmap[cid]
        rec = {
            "candidate_id": cid, "roles": roles, "role_titles": [ROLE_TITLES[r] for r in roles],
            "category": category.replace("_", " "), "template_garment_id": c["template_garment_id"],
            "composition": composition_lines(c["components"]), "colour": c["normalized_colour"],
            "fit": t.fit_label, "length": t.length_label,
            "intent_0_100": e["intent"]["intent_alignment_0_100"], "intent_label": score_label(e["intent"]["intent_alignment_0_100"]),
            "plausibility_0_100": e["plausibility"]["plausibility_0_100"], "plausibility_label": score_label(e["plausibility"]["plausibility_0_100"]),
            "violation_count": e["sorting"]["violation_count"], "sr": sr, "sorting_summary": sorting_summary_text(e["sorting"]["violation_count"], sr),
            "preferences": _preference_lines(e),
            "role_reasons": [_role_reason(r, e, s, len(front), dims) for r in roles],
            "changes_from_template": [change_sentence(m) for m in c["mutation_log"]],
            "confirmed_rule_changes": [t for t in (rule_change_sentence(r) for r in x["sorting"]["rules"]) if t],
            "trade_offs_vs_template": [trade_off_sentence(t) for t in x["trade_offs"]],
            "technical_statements": [m["description"] for m in x["mutations"]] + list(x["statements"]),
            "template_distance": e["template_distance_raw"],
            "display_merged_duplicate_slots": any(cl["had_duplicate_slots"] for cl in composition_lines(c["components"])),
        }
        rec["headline"] = _headline(rec)
        recs.append(rec)
    for r in recs:
        r["comparisons"] = _comparison_lines(r, [o for o in recs if o is not r])
    return recs


_UNSCORABLE_SHORT = {"neutral_value": "'standard' is neutral and not scored", "no_label_evidence": "the templates have no label for it",
                     "no_primary_component_materials": "no main-fabric materials", "candidate_colour_unavailable": "no recorded colour"}


def _no_intent_text(valid: list[dict[str, Any]], ignored: list[str] | None = None) -> str:
    """Why there is no Intent-focused recommendation: no soft preference at all vs. preferences that could not be scored."""
    reasons: dict[str, set[str]] = {}
    for e in valid:
        for u in e["intent"].get("unscorable_preferences", []):
            reasons.setdefault(u["preference"], set()).add(_UNSCORABLE_SHORT.get(u["reason"], str(u["reason"])))
    if not reasons:
        if ignored:
            return ("Your soft preference(s) (" + ", ".join(ignored) + ") are not available for this garment category and were not used, "
                    "so there is no Intent-focused recommendation.")
        return "No soft preference was given, so there is no Intent-focused recommendation."
    detail = "; ".join(f"{PREFERENCE_NAMES.get(k, k)}: {', '.join(sorted(v))}" for k, v in sorted(reasons.items()))
    return ("None of your soft preferences could be scored for the Pareto-front candidates (" + detail + "), so there is no Intent-focused "
            "recommendation and intent alignment is shown as n/a.")


def generate_recommendations(user_request: dict[str, Any], seed: int = 0, data: AppData | None = None, app_cfg: AppConfig = AppConfig(),
                             progress: Callable[[str, float], None] | None = None, is_form: bool = False) -> dict[str, Any]:
    """Run the full frozen pipeline for one user request. `user_request` uses the research request schema
    (or the UI form schema when `is_form=True`). Never raises for invalid user input; returns a status + messages instead."""
    if data is None:
        from app.adapters import load_app_data
        data = load_app_data()
    step = progress or (lambda stage, frac: None)
    t0 = time.perf_counter()
    raw = form_to_raw_request(user_request) if is_form else dict(user_request)
    out: dict[str, Any] = {"status": None, "messages": [], "raw_request": raw, "request": None, "recommendations": [], "pareto_points": [],
                           "stats": {}, "flags": {}, "seed": seed, "budget": asdict(app_cfg), "config_note":
                           "Generator B3 (proposal + repair, STRICT_SORTING) with frozen research settings; only the candidate budget and seed are app parameters."}
    step("Validating your requirements", 0.05)
    v = validate_request(raw, data.ctx)
    if not v.ok:
        out.update(status=STATUS_INVALID, messages=validation_messages(v))
        out["stats"]["seconds_total"] = round(time.perf_counter() - t0, 3)
        return out
    req = v.request
    out["request"] = req
    out["messages"] += warning_messages(req)
    seg, cat = req["target_segment"], req["detail_category"]
    n_cell = data.cells.get(seg, {}).get(cat, 0)
    step("Generating candidates (Generator B3)", 0.15)
    t1 = time.perf_counter()
    res = generate_sorting_aware(req, data.rep_train, data.support, data.ctx, b3_config(app_cfg, seed))
    t_gen = time.perf_counter() - t1
    pool = res["template_pool"]
    out["stats"].update({"train_garments_in_cell": pool["train_garments_in_cell"], "eligible_templates": pool["eligible_templates"],
                         "templates_used": pool["selected"], "candidates_requested": app_cfg.n_templates * app_cfg.candidates_per_template,
                         "candidates_generated": len(res["candidates"]), "templates_dropped_forbidden": len(res["failed_templates"]),
                         "rejections": res["rejected"], "repairs_accepted": res["search"].get("repair_accepted", 0),
                         "seconds_generation": round(t_gen, 3)})
    if n_cell == 0 or pool["eligible_templates"] == 0:
        why = ("there are no TRAIN garments for this segment and category" if pool["train_garments_in_cell"] == 0 else
               f"none of the {pool['train_garments_in_cell']} TRAIN garments in this cell has a clean, fully usable composition")
        out.update(status=STATUS_NO_TEMPLATES)
        out["messages"].append(_msg("error", "no_templates", f"No recommendations can be generated because {why}. "
                                    "CAGO only builds designs from TRAIN garment templates of the same segment and category."))
        out["stats"]["seconds_total"] = round(time.perf_counter() - t0, 3)
        return out
    if not res["candidates"]:
        parts = []
        if res["failed_templates"]:
            parts.append(f"{len(res['failed_templates'])} template(s) contain a forbidden material that has no TRAIN-supported replacement")
        if res["rejected"]:
            parts.append("other attempts were rejected: " + ", ".join(f"{k.replace('_', ' ')} ({n})" for k, n in sorted(res["rejected"].items())))
        out.update(status=STATUS_NO_CANDIDATES)
        out["messages"].append(_msg("error", "no_candidates", "No candidate could be generated. " + ("; ".join(parts) + "." if parts else "")
                                    + " Try removing a forbidden material or choosing another category."))
        out["stats"]["seconds_total"] = round(time.perf_counter() - t0, 3)
        return out
    step("Evaluating candidates (Intent, SR1–SR5, Plausibility) and selecting", 0.7)
    t2 = time.perf_counter()
    pe = evaluate_and_select(req, data.rep_train, data.support, data.ctx, cfg=EvaluationConfig(), res=res)
    t_eval = time.perf_counter() - t2
    valid = pe["evaluation"]["valid"]
    out["stats"].update({"hard_valid": len(valid), "hard_invalid": len(pe["evaluation"]["excluded"]), "front_size": pe["pareto"]["front_size"],
                         "pareto_dimensions": pe["pareto"].get("dimensions", []), "seconds_evaluation": round(t_eval, 3)})
    if not valid:
        out.update(status=STATUS_NO_VALID)
        out["messages"].append(_msg("error", "no_valid_candidates", f"All {len(res['candidates'])} generated candidates failed the hard validity checks, "
                                    "so no recommendation is shown."))
        out["stats"]["seconds_total"] = round(time.perf_counter() - t0, 3)
        return out
    recs = _recommendations(pe, res, cat)
    role_of = {cid: r["roles"] for r in recs for cid in [r["candidate_id"]]}
    out["recommendations"] = recs
    out["pareto_points"] = [{"candidate_id": e["candidate_id"], "intent_0_100": e["intent"]["intent_alignment_0_100"],
                             "plausibility_0_100": e["plausibility"]["plausibility_0_100"], "violation_count": e["sorting"]["violation_count"],
                             "is_pareto": bool(e["is_pareto"]), "pareto_rank": e["pareto_rank"],
                             "roles": [ROLE_TITLES[x] for x in role_of.get(e["candidate_id"], [])]} for e in valid]
    min_vc = min(e["sorting"]["violation_count"] for e in valid)
    sr4_blocks = min_vc > 0 and all(e["sorting"]["oracle"]["sr4_violation"] for e in valid if e["sorting"]["violation_count"] == min_vc)
    out["flags"] = {"no_zero_violation_candidate": min_vc > 0, "min_violation_count": min_vc, "zero_blocked_by_colour": sr4_blocks,
                    "single_pareto_candidate": pe["pareto"]["front_size"] == 1,
                    "duplicate_roles": any(len(r["roles"]) > 1 for r in recs), "intent_focused_omitted": pe["selection"].get("intent_focused_omitted", False)}
    if out["flags"]["no_zero_violation_candidate"]:
        extra = (" Every candidate with the lowest violation count keeps the SR4 colour flag: the colour is inherited from TRAIN templates and is "
                 "not changed by CAGO V1." if sr4_blocks else "")
        out["messages"].append(_msg("info", "no_zero_violation", f"No candidate reached zero detected SR1–SR5 violations (lowest: {min_vc}).{extra}"))
    if out["flags"]["single_pareto_candidate"]:
        out["messages"].append(_msg("info", "single_pareto", "Only one candidate is non-dominated, so all recommendation roles point to the same design."))
    elif out["flags"]["duplicate_roles"]:
        out["messages"].append(_msg("info", "duplicate_roles", "One candidate fulfils several recommendation roles; it is shown once with all its roles."))
    if out["flags"]["intent_focused_omitted"]:
        out["messages"].append(_msg("info", "no_intent", _no_intent_text(
            [e for e in valid if e["is_pareto"]],
            [_label(f).lower() for w in req.get("warnings", []) if w["code"] == "control_not_available" for f in w.get("fields", [])])))
    if pool["pool_smaller_than_requested"]:
        out["messages"].append(_msg("info", "small_pool", f"Only {pool['eligible_templates']} eligible TRAIN template(s) exist for this cell; "
                                    "fewer and less diverse candidates are possible."))
    out["status"] = STATUS_OK
    out["digest"] = pe["digest"]
    out["stats"]["seconds_total"] = round(time.perf_counter() - t0, 3)
    step("Done", 1.0)
    return out
