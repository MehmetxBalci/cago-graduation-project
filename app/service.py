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

Localization (V1.1.0): the research steps run once and are language-independent. The result keeps the structured values
needed for wording (`render_data` per recommendation, `args` per message); `render_result` writes every user-facing text in
the requested language and `localize_result` re-renders a stored result in another language WITHOUT re-running anything.
"""
from __future__ import annotations

import copy
import re
import time
from dataclasses import asdict, dataclass
from typing import Any, Callable

from app.adapters import REQUEST_TO_UI, UI_LABELS, AppData, form_to_raw_request
from app.i18n import DEFAULT_LANGUAGE, EN, Translator, get_translator
from app.presenters import (ROLE_ORDER, ROLE_TITLES, change_sentence, composition_lines, conflict_text, invalid_value_text,  # noqa: F401
                            localize_composition, pref_name, preference_sentence, roles_text, rule_change_sentence, score_label,
                            sorting_summary_text, sr_status, trade_off_sentence)
from app.presenters import _pref_value  # noqa: E402  (display of requested values)
from cago.evaluation.config import EvaluationConfig
from cago.evaluation.pipeline import evaluate_and_select
from cago.generation_sorting.config import MODE_CONFIGS, SortingAwareGenerationConfig
from cago.generation_sorting.generator import generate_sorting_aware
from cago.requirements.schema import ENUMS, REMOVED_V1_VALUES, TRUE_ONLY_FIELDS
from cago.requirements.validation import validate_request

FINAL_TEST_BUDGET = {"n_templates": 10, "candidates_per_template": 8}
STATUS_OK, STATUS_INVALID, STATUS_NO_TEMPLATES, STATUS_NO_CANDIDATES, STATUS_NO_VALID = (
    "ok", "invalid_request", "no_templates", "no_candidates", "no_valid_candidates")
# result keys that carry research output (identical in every language; tested)
RESEARCH_KEYS = ("status", "raw_request", "request", "stats", "flags", "seed", "budget", "digest")
REC_RESEARCH_KEYS = ("candidate_id", "roles", "template_garment_id", "colour", "fit", "length", "intent_0_100", "plausibility_0_100",
                     "violation_count", "template_distance", "display_merged_duplicate_slots", "technical_statements")


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


ERROR_CODES = ("missing_required_field", "invalid_target_segment", "invalid_detail_category", "unknown_material", "invalid_value",
               "removed_in_v1", "unknown_field")
ERROR_TEXT = {c: EN.messages[f"error.{c}"] for c in ERROR_CODES}           # V1 name kept for compatibility (English templates)


def _msg(level: str, code: str, args: dict[str, Any] | None = None, fields: list[str] | None = None) -> dict[str, Any]:
    """Structured message; `text` is filled by render_result in the active language."""
    return {"level": level, "code": code, "text": "", "fields": fields or [], "args": args or {}}


def _label(field: str | None, tr: Translator = EN) -> str:
    ui = REQUEST_TO_UI.get(field or "", field or "")
    if ui in UI_LABELS:
        return tr.field(ui)
    return field or tr.t("field.request")


def _label_lc(field: str | None, tr: Translator = EN) -> str:
    ui = REQUEST_TO_UI.get(field or "", field or "")
    return tr.field_lc(ui) if ui in UI_LABELS else _label(field, tr).lower()


# ---------------------------------------------------------------- message rendering
def _allowed(field: str, tr: Translator) -> str:
    return tr.t("error.allowed_sep").join(f"'{tr.label(field, a)}'" for a in ENUMS[field])


def _error_detail(err: dict[str, Any], raw: dict[str, Any], tr: Translator) -> str:
    """Detail of one frozen validation error. English keeps the frozen engine wording (V1); other languages re-word it from
    the structured error (code, field, submitted value) -- the frozen message is only parsed, never changed."""
    code, fld, message = err["code"], err.get("field"), err["message"]
    if tr.lang == "en":
        return invalid_value_text(message, tr) if code == "invalid_value" else message
    value = raw.get(fld) if isinstance(raw, dict) and isinstance(fld, str) else None
    if code == "unknown_material":
        m = re.match(r"unknown material (.*)$", message)
        return m.group(1) if m else repr(value)
    if code == "unknown_field":
        return repr(fld)
    if code == "removed_in_v1" and fld in REMOVED_V1_VALUES and isinstance(value, str):
        hint = REMOVED_V1_VALUES[fld].get(value.strip().casefold())
        if hint:
            return tr.t("error.detail.removed_hint", value=repr(value), hint=f"'{tr.label(fld, hint)}'", allowed=_allowed(fld, tr))
        return tr.t("error.detail.removed", value=repr(value), allowed=_allowed(fld, tr))
    if code == "invalid_value":
        if fld in ENUMS:
            return tr.t("error.detail.enum", value=repr(value), allowed=_allowed(fld, tr))
        if fld in TRUE_ONLY_FIELDS:
            return tr.t("error.detail.true_only", value=repr(value))
        if fld == "colour":
            return tr.t("error.detail.colour")
        if fld == "forbidden_materials":
            return tr.t("error.detail.forbidden_list")
    if code == "invalid_request":
        return tr.t("error.detail.invalid_request")
    return message


def _render_error(a: dict[str, Any], raw: dict[str, Any], tr: Translator) -> str:
    err = a["error"]
    fld = err.get("field") if isinstance(err.get("field"), str) else None
    key = f"error.{err['code']}" if err["code"] in ERROR_CODES else "error.generic"
    label = _label_lc(fld, tr) if err["code"] == "missing_required_field" else _label(fld, tr)
    return tr.t(key, label=label, detail=_error_detail(err, raw, tr))


def _render_warning(w: dict[str, Any], tr: Translator) -> str:
    labels = tr.t("warning.labels_sep").join(_label(f, tr) for f in w.get("fields", []))
    if w["code"] == "control_not_available":
        return tr.t("warning.control_not_available", labels=labels)
    if w.get("severity") == "hard_override":
        return tr.t("warning.hard_override")
    if w["code"] == "preference_conflict":
        return tr.t("warning.preference_conflict", labels=labels, reason=conflict_text(w.get("fields", []), w["message"], tr))
    return tr.t("warning.unknown", message=w.get("message", w["code"]))


def _no_intent_text(args: dict[str, Any], tr: Translator) -> str:
    """Why there is no Intent-focused recommendation: no soft preference at all vs. preferences that could not be scored."""
    reasons = args.get("unscorable") or {}
    if not reasons:
        ignored = [_label_lc(f, tr) for f in args.get("ignored", [])]
        if ignored:
            return tr.t("msg.no_intent.ignored", prefs=tr.t("msg.no_intent.list_sep").join(ignored))
        return tr.t("msg.no_intent.none")

    def short(code: str) -> str:
        key = f"unscorable_short.{code}"
        return tr.t(key) if tr.has(key) else str(code)
    detail = tr.t("msg.no_intent.detail_sep").join(
        tr.t("msg.no_intent.detail", pref=pref_name(k, tr), reasons=tr.t("msg.no_intent.reason_sep").join(sorted({short(c) for c in v})))
        for k, v in sorted(reasons.items()))
    return tr.t("msg.no_intent.unscorable", detail=detail)


def render_message(m: dict[str, Any], a: dict[str, Any], raw: dict[str, Any], tr: Translator = EN) -> str:
    """Text of one message from its code and structured arguments (kept in result["render_data"]["message_args"])."""
    code = m["code"]
    if "error" in a:
        return _render_error(a, raw, tr)
    if "warning" in a:
        return _render_warning(a["warning"], tr)
    if code == "no_templates":
        n = a["train_garments_in_cell"]
        why = tr.t("msg.no_templates.empty_cell") if n == 0 else tr.t("msg.no_templates.unusable", n=n)
        return tr.t("msg.no_templates", why=why)
    if code == "no_candidates":
        parts = []
        if a.get("failed"):
            parts.append(tr.t("msg.no_candidates.failed", n=a["failed"]))
        if a.get("rejected"):
            parts.append(tr.t("msg.no_candidates.rejected", reasons=tr.t("msg.no_candidates.list_sep").join(
                tr.t("msg.no_candidates.rejection", reason=tr.label("rejection", k), n=n) for k, n in sorted(a["rejected"].items()))))
        return tr.t("msg.no_candidates", parts=tr.t("msg.no_candidates.sep").join(parts) + "." if parts else "")
    if code == "no_valid_candidates":
        return tr.t("msg.no_valid", n=a["n"])
    if code == "no_zero_violation":
        return tr.t("msg.no_zero_violation", min=a["min"], extra=tr.t("msg.no_zero_violation.sr4") if a.get("sr4") else "")
    if code == "single_pareto":
        return tr.t("msg.single_pareto")
    if code == "duplicate_roles":
        return tr.t("msg.duplicate_roles")
    if code == "no_intent":
        return _no_intent_text(a, tr)
    if code == "small_pool":
        return tr.t("msg.small_pool", n=a["n"])
    return m.get("text", "")


# ---------------------------------------------------------------- recommendation rendering
def _pstatus(p: dict[str, Any]) -> str:
    if not p["scorable"]:
        return "not_scored"
    if p["satisfaction_0_1"] >= 0.99:
        return "satisfied"
    if p["satisfaction_0_1"] <= 0.01:
        return "not_satisfied"
    return "partially_satisfied"


def _role_reason(role: str, rec: dict[str, Any], ctx: dict[str, Any], tr: Translator) -> str:
    vc, ia = rec["violation_count"], rec["intent_0_100"]
    if role == "balanced":
        objs = [tr.t("role.objective.violations")] + ([tr.t("role.objective.intent_loss")] if "intent_loss" in ctx["dims"] else []) \
            + [tr.t("role.objective.plausibility_loss")]
        return tr.t("role.balanced_reason", front_size=ctx["front_size"], objectives=tr.t("role.list_sep").join(objs[:-1]),
                    last_objective=objs[-1], distance=tr.num(ctx["balanced_distance"], ".3f"))
    if role == "sorting_focused":
        tail = tr.t("role.sorting_tail_intent", intent=f"{ia:.0f}") if ia is not None else ""
        if vc == 0:
            return tr.t("role.sorting_reason_zero", tail=tail)
        return tr.t("role.sorting_reason_min", count=vc, tail=tail)
    return tr.t("role.intent_reason", intent=f"{ia:.0f}")


def _preference_lines(intent_prefs: list[dict[str, Any]], tr: Translator) -> list[dict[str, Any]]:
    out = []
    for p in intent_prefs:
        status = _pstatus(p)
        req = p["requested_value"]
        requested = tr.t("value.yes") if req is True else (req if tr.lang == "en" else _pref_value(p["preference"], req, tr))
        out.append({"preference": _label(p["preference"], tr), "preference_id": p["preference"], "requested": requested,
                    "status": tr.t(f"pstatus.{status}"), "status_key": status, "satisfaction": p["satisfaction_0_1"],
                    "explanation": preference_sentence(p, tr), "technical": p["explanation"]})
    return out


def _comparison_lines(rec: dict[str, Any], others: list[dict[str, Any]], tr: Translator) -> list[str]:
    out = []
    for o in others:
        di = None if rec["intent_0_100"] is None or o["intent_0_100"] is None else rec["intent_0_100"] - o["intent_0_100"]
        dp = rec["plausibility_0_100"] - o["plausibility_0_100"]
        dv = rec["violation_count"] - o["violation_count"]
        parts = []
        if dv:
            parts.append(tr.t("compare.fewer_violations" if dv < 0 else "compare.more_violations", a=rec["violation_count"], b=o["violation_count"]))
        if di is not None and abs(di) >= 0.5:
            parts.append(tr.t("compare.higher_intent" if di > 0 else "compare.lower_intent", a=f"{rec['intent_0_100']:.0f}", b=f"{o['intent_0_100']:.0f}"))
        if abs(dp) >= 0.5:
            parts.append(tr.t("compare.higher_plausibility" if dp > 0 else "compare.lower_plausibility",
                              a=f"{rec['plausibility_0_100']:.0f}", b=f"{o['plausibility_0_100']:.0f}"))
        if parts:
            out.append(tr.t("compare.line", roles=roles_text(o["roles"], tr, "role.slash"), parts=tr.t("compare.parts_sep").join(parts)))
    return out


def _headline(rec: dict[str, Any], tr: Translator) -> list[str]:
    """Short evidence-based summary lines (preferences + remaining violations)."""
    out = []
    sep = tr.t("headline.list_sep")
    sat = [p for p in rec["preferences"] if p["status_key"] == "satisfied"]
    miss = [p for p in rec["preferences"] if p["status_key"] in ("not_satisfied", "partially_satisfied")]
    if sat:
        out.append(tr.t("headline.matches_many" if len(sat) > 1 else "headline.matches_one", prefs=sep.join(_label_lc(p["preference_id"], tr) for p in sat)))
    if miss:
        out.append(tr.t("headline.misses_many" if len(miss) > 1 else "headline.misses_one", prefs=sep.join(_label_lc(p["preference_id"], tr) for p in miss)))
    viol = [r for r in rec["sr"] if r["violated"]]
    if not viol:
        out.append(tr.t("sr.zero_violations"))
    else:
        out.append(tr.t("headline.retains_many" if len(viol) > 1 else "headline.retains_one",
                        rules=sep.join(tr.t("sr.rule_with_name", rule=r["rule"], name=tr.t(f"sr.{r['rule']}.name_lc")) for r in viol)))
    return out


def render_recommendation(rec: dict[str, Any], tr: Translator = EN) -> None:
    """Write every display field of one recommendation from its research values and `render_data` (in place)."""
    src = rec["render_data"]
    rec["role_titles"] = [tr.role(r) for r in rec["roles"]]
    rec["category"] = tr.label("category", src["category"])
    rec["composition"] = localize_composition(rec["composition"], tr)
    rec["intent_label"] = score_label(rec["intent_0_100"], tr)
    rec["plausibility_label"] = score_label(rec["plausibility_0_100"], tr)
    rec["sr"] = sr_status(src["oracle"], rec["colour"], tr)
    rec["sorting_summary"] = sorting_summary_text(rec["violation_count"], rec["sr"], tr)
    rec["preferences"] = _preference_lines(src["intent_preferences"], tr)
    rec["role_reasons"] = [_role_reason(r, rec, src["role_context"], tr) for r in rec["roles"]]
    rec["changes_from_template"] = [change_sentence(m, tr) for m in src["mutation_log"]]
    rec["confirmed_rule_changes"] = [t for t in (rule_change_sentence(r, tr) for r in src["rule_changes"]) if t]
    rec["trade_offs_vs_template"] = [trade_off_sentence(t, tr) for t in src["trade_offs"]]
    rec["headline"] = _headline(rec, tr)


def render_result(result: dict[str, Any], tr: Translator = EN) -> dict[str, Any]:
    """Fill every user-facing text of a service result in the language of `tr` (in place; research values untouched)."""
    result["lang"] = tr.lang
    result["config_note"] = tr.t("msg.config_note")
    raw = result.get("raw_request") or {}
    rd = result.setdefault("render_data", {})
    if "message_args" not in rd:                          # first rendering: move the structured inputs out of the messages
        rd["message_args"] = [m.pop("args", {}) for m in result["messages"]]
    for m, a in zip(result["messages"], rd["message_args"]):
        m["text"] = render_message(m, a, raw, tr)
    for rec in result["recommendations"]:
        render_recommendation(rec, tr)
    for rec in result["recommendations"]:
        rec["comparisons"] = _comparison_lines(rec, [o for o in result["recommendations"] if o is not rec], tr)
    for p in result["pareto_points"]:
        p["roles"] = [tr.role(x) for x in p["role_ids"]]
    return result


def localize_result(result: dict[str, Any], lang: str) -> dict[str, Any]:
    """A copy of a stored result re-rendered in `lang`. Pure presentation: nothing is generated or evaluated again."""
    return render_result(copy.deepcopy(result), get_translator(lang))


def research_view(result: dict[str, Any]) -> dict[str, Any]:
    """The language-independent part of a result (used to prove EN/TR equivalence)."""
    return {
        **{k: result.get(k) for k in RESEARCH_KEYS if k != "stats"},
        "stats": {k: v for k, v in (result.get("stats") or {}).items() if not k.startswith("seconds_")},   # timings are not results
        "message_codes": [(m["level"], m["code"], m["fields"]) for m in result["messages"]],
        "recommendations": [{**{k: r[k] for k in REC_RESEARCH_KEYS},
                             "composition": [[(m["material"], m["pct"]) for m in c["materials"]] for c in r["composition"]],
                             "sr_flags": [(x["rule"], x["violated"]) for x in r["sr"]],
                             "preference_scores": [(p["preference_id"], p["status_key"], p["satisfaction"]) for p in r["preferences"]]}
                            for r in result["recommendations"]],
        "pareto_points": [{k: v for k, v in p.items() if k != "roles"} for p in result["pareto_points"]],
    }


# ---------------------------------------------------------------- research run
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
        x = xmap[cid]
        comp = composition_lines(c["components"])
        recs.append({
            "candidate_id": cid, "roles": sorted(s["roles"], key=ROLE_ORDER.index), "template_garment_id": c["template_garment_id"],
            "composition": comp, "colour": c["normalized_colour"], "fit": t.fit_label, "length": t.length_label,
            "intent_0_100": e["intent"]["intent_alignment_0_100"], "plausibility_0_100": e["plausibility"]["plausibility_0_100"],
            "violation_count": e["sorting"]["violation_count"],
            "technical_statements": [m["description"] for m in x["mutations"]] + list(x["statements"]),
            "template_distance": e["template_distance_raw"],
            "display_merged_duplicate_slots": any(cl["had_duplicate_slots"] for cl in comp),
            "render_data": {                                       # structured, language-independent inputs of the wording
                "category": category, "oracle": dict(e["sorting"]["oracle"]), "intent_preferences": copy.deepcopy(e["intent"]["preferences"]),
                "mutation_log": copy.deepcopy(c["mutation_log"]), "rule_changes": copy.deepcopy(x["sorting"]["rules"]),
                "trade_offs": list(x["trade_offs"]),
                "role_context": {"front_size": len(front), "dims": dims, "balanced_distance": s.get("balanced_distance")},
            },
        })
    return recs


def generate_recommendations(user_request: dict[str, Any], seed: int = 0, data: AppData | None = None, app_cfg: AppConfig = AppConfig(),
                             progress: Callable[[str, float], None] | None = None, is_form: bool = False,
                             lang: str = DEFAULT_LANGUAGE) -> dict[str, Any]:
    """Run the full frozen pipeline for one user request. `user_request` uses the research request schema
    (or the UI form schema when `is_form=True`). Never raises for invalid user input; returns a status + messages instead.
    `lang` only selects the language of the texts (and progress messages); the research steps do not depend on it."""
    tr = get_translator(lang)
    if data is None:
        from app.adapters import load_app_data
        data = load_app_data()
    step = progress or (lambda stage, frac: None)
    t0 = time.perf_counter()
    raw = form_to_raw_request(user_request) if is_form else dict(user_request)
    out: dict[str, Any] = {"status": None, "messages": [], "raw_request": raw, "request": None, "recommendations": [], "pareto_points": [],
                           "stats": {}, "flags": {}, "seed": seed, "budget": asdict(app_cfg), "config_note": ""}
    step(tr.t("progress.validating"), 0.05)
    v = validate_request(raw, data.ctx)
    if not v.ok:
        out.update(status=STATUS_INVALID, messages=[
            _msg("error", e.code, {"error": e.to_dict()}, [e.field] if isinstance(e.field, str) else []) for e in v.errors])
        out["stats"]["seconds_total"] = round(time.perf_counter() - t0, 3)
        return render_result(out, tr)
    req = v.request
    out["request"] = req
    out["messages"] += [_msg("warning", w["code"], {"warning": copy.deepcopy(w)}, w.get("fields")) for w in req.get("warnings", [])]
    seg, cat = req["target_segment"], req["detail_category"]
    n_cell = data.cells.get(seg, {}).get(cat, 0)
    step(tr.t("progress.generating"), 0.15)
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
        out.update(status=STATUS_NO_TEMPLATES)
        out["messages"].append(_msg("error", "no_templates", {"train_garments_in_cell": pool["train_garments_in_cell"]}))
        out["stats"]["seconds_total"] = round(time.perf_counter() - t0, 3)
        return render_result(out, tr)
    if not res["candidates"]:
        out.update(status=STATUS_NO_CANDIDATES)
        out["messages"].append(_msg("error", "no_candidates", {"failed": len(res["failed_templates"]), "rejected": dict(res["rejected"])}))
        out["stats"]["seconds_total"] = round(time.perf_counter() - t0, 3)
        return render_result(out, tr)
    step(tr.t("progress.evaluating"), 0.7)
    t2 = time.perf_counter()
    pe = evaluate_and_select(req, data.rep_train, data.support, data.ctx, cfg=EvaluationConfig(), res=res)
    t_eval = time.perf_counter() - t2
    valid = pe["evaluation"]["valid"]
    out["stats"].update({"hard_valid": len(valid), "hard_invalid": len(pe["evaluation"]["excluded"]), "front_size": pe["pareto"]["front_size"],
                         "pareto_dimensions": pe["pareto"].get("dimensions", []), "seconds_evaluation": round(t_eval, 3)})
    if not valid:
        out.update(status=STATUS_NO_VALID)
        out["messages"].append(_msg("error", "no_valid_candidates", {"n": len(res["candidates"])}))
        out["stats"]["seconds_total"] = round(time.perf_counter() - t0, 3)
        return render_result(out, tr)
    recs = _recommendations(pe, res, cat)
    role_of = {r["candidate_id"]: r["roles"] for r in recs}
    out["recommendations"] = recs
    out["pareto_points"] = [{"candidate_id": e["candidate_id"], "intent_0_100": e["intent"]["intent_alignment_0_100"],
                             "plausibility_0_100": e["plausibility"]["plausibility_0_100"], "violation_count": e["sorting"]["violation_count"],
                             "is_pareto": bool(e["is_pareto"]), "pareto_rank": e["pareto_rank"],
                             "role_ids": list(role_of.get(e["candidate_id"], [])), "roles": []} for e in valid]
    min_vc = min(e["sorting"]["violation_count"] for e in valid)
    sr4_blocks = min_vc > 0 and all(e["sorting"]["oracle"]["sr4_violation"] for e in valid if e["sorting"]["violation_count"] == min_vc)
    out["flags"] = {"no_zero_violation_candidate": min_vc > 0, "min_violation_count": min_vc, "zero_blocked_by_colour": sr4_blocks,
                    "single_pareto_candidate": pe["pareto"]["front_size"] == 1,
                    "duplicate_roles": any(len(r["roles"]) > 1 for r in recs), "intent_focused_omitted": pe["selection"].get("intent_focused_omitted", False)}
    if out["flags"]["no_zero_violation_candidate"]:
        out["messages"].append(_msg("info", "no_zero_violation", {"min": min_vc, "sr4": sr4_blocks}))
    if out["flags"]["single_pareto_candidate"]:
        out["messages"].append(_msg("info", "single_pareto"))
    elif out["flags"]["duplicate_roles"]:
        out["messages"].append(_msg("info", "duplicate_roles"))
    if out["flags"]["intent_focused_omitted"]:
        unscorable: dict[str, list[str]] = {}
        for e in valid:
            if e["is_pareto"]:
                for u in e["intent"].get("unscorable_preferences", []):
                    unscorable.setdefault(u["preference"], [])
                    if u["reason"] not in unscorable[u["preference"]]:
                        unscorable[u["preference"]].append(u["reason"])
        ignored = [f for w in req.get("warnings", []) if w["code"] == "control_not_available" for f in w.get("fields", [])]
        out["messages"].append(_msg("info", "no_intent", {"unscorable": unscorable, "ignored": ignored}))
    if pool["pool_smaller_than_requested"]:
        out["messages"].append(_msg("info", "small_pool", {"n": pool["eligible_templates"]}))
    out["status"] = STATUS_OK
    out["digest"] = pe["digest"]
    out["stats"]["seconds_total"] = round(time.perf_counter() - t0, 3)
    render_result(out, tr)
    step(tr.t("progress.done"), 1.0)
    return out
