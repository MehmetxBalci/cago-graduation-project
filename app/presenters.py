"""Presentation helpers: display-only normalisation, SR wording, cards and evidence-based explanations.

Nothing here feeds back into generation or evaluation. In particular `merge_display_materials` returns a NEW list and never
mutates the candidate that was evaluated.

V1.1.0: every user-facing sentence is built from the localization catalogs (app/i18n). Each function takes an optional
`tr` translator (default English, which reproduces the V1.0.0 wording exactly); internal identifiers are only formatted for
display, never replaced.
"""
from __future__ import annotations

import json
import re
from typing import Any

from app.i18n import EN, Translator

ROLE_ORDER = ("balanced", "sorting_focused", "intent_focused")
SR_ORDER = ("SR1", "SR2", "SR3", "SR4", "SR5")
ROLE_TITLES = {r: EN.role(r) for r in ROLE_ORDER}
SR_RULES = {r: (EN.sr_name(r), EN.t(f"sr.{r}.ok")) for r in SR_ORDER}
ZERO_VIOLATION_TEXT = EN.t("sr.zero_violations")
DISCLAIMER_KEYS = tuple(f"disclaimer.{i}" for i in range(1, 6))
DISCLAIMER = [EN.t(k) for k in DISCLAIMER_KEYS]
BANNED_CLAIMS = ("recyclability percentage", "sustainability percentage", "guaranteed recyclable", "% recyclable", "ai confidence",
                 "is recyclable", "100% recyclable", "sustainable %", "recyclability %", "manufacturability probability")
BANNED_CLAIMS_TR = ("geri dönüştürülebilirlik yüzdesi", "sürdürülebilirlik yüzdesi", "geri dönüştürülebilir olduğu garanti",
                    "garantili geri dönüştürülebilir", "%100 geri dönüştürülebilir", "geri dönüştürülebilirdir", "yapay zekâ güveni",
                    "yapay zeka güveni", "üretilebilirlik olasılığı", "geri dönüştürülebilir yüzde")


def roles_text(roles: list[str], tr: Translator = EN, sep_key: str = "role.joiner") -> str:
    return tr.t(sep_key).join(tr.role(r) for r in roles)


def disclaimer(tr: Translator = EN) -> list[str]:
    return [tr.t(k) for k in DISCLAIMER_KEYS]


def sr_rules(tr: Translator = EN) -> dict[str, tuple[str, str]]:
    return {r: (tr.sr_name(r), tr.t(f"sr.{r}.ok")) for r in SR_ORDER}


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


def fmt_pct(p: float, tr: Translator = EN) -> str:
    return tr.pct(p)


def materials_text(materials: list[dict[str, Any]], tr: Translator = EN) -> str:
    return ", ".join(tr.t("sr.material_pct", material=tr.label("material", m["material"]), pct=tr.pct(float(m["pct"]))) for m in materials)


def composition_lines(components: list[dict[str, Any]], tr: Translator = EN) -> list[dict[str, Any]]:
    out = []
    for c in components:
        merged = merge_display_materials(c["materials"])
        out.append({"component": tr.label("component", c["component_name_normalized"]), "component_id": c["component_name_normalized"],
                    "component_class": c["component_class"].replace("_component", ""),
                    "materials": merged, "text": materials_text(merged, tr),
                    "had_duplicate_slots": any(m["merged_slots"] > 1 for m in merged)})
    return out


def localize_composition(lines: list[dict[str, Any]], tr: Translator = EN) -> list[dict[str, Any]]:
    """Re-render stored composition lines (internal material ids are kept in `materials`)."""
    return [{**c, "component": tr.label("component", c.get("component_id", c["component"])), "text": materials_text(c["materials"], tr)}
            for c in lines]


def _json_list(v: Any) -> list[dict[str, Any]]:
    if isinstance(v, str):
        try:
            return json.loads(v)
        except ValueError:
            return []
    return list(v or [])


def sr_detail(rule: str, oracle: dict[str, Any], colour: str | None, tr: Translator = EN) -> str:
    """Plain-language reason for a VIOLATED rule, built from the Oracle's own outputs."""
    if rule == "SR1":
        code = oracle.get("sr1_reason")
        key = f"sr.sr1_reason.{code}"
        reason = tr.t(key) if tr.has(key) or EN.has(key) else code
        return tr.t("sr.sr1_detail", reason=reason)
    if rule == "SR2":
        return tr.t("sr.sr2_detail", count=oracle.get("sr2_fibre_count"))
    if rule == "SR3":
        t = _json_list(oracle.get("sr3_trigger_materials"))
        return tr.t("sr.sr3_detail", materials=materials_text(t, tr)) if t else tr.t("sr.sr3_detail_generic")
    if rule == "SR4":
        return tr.t("sr.sr4_detail", colour=tr.label("colour", colour))
    if rule == "SR5":
        t = _json_list(oracle.get("sr5_trigger_materials"))
        hidden = oracle.get("sr5_hidden_component")
        where = tr.label("component", hidden) if hidden else tr.t("sr.sr5_hidden_layer")
        return tr.t("sr.sr5_detail", where=where, materials=materials_text(t, tr))
    return ""


def sr_status(oracle: dict[str, Any], colour: str | None, tr: Translator = EN) -> list[dict[str, Any]]:
    rows = []
    for r in SR_ORDER:
        v = bool(oracle[f"sr{r[2]}_violation"])
        rows.append({"rule": r, "name": tr.sr_name(r), "violated": v, "status": tr.t("sr.status.violated" if v else "sr.status.ok"),
                     "detail": sr_detail(r, oracle, colour, tr) if v else tr.t(f"sr.{r}.ok")})
    return rows


def sorting_summary_text(vc: int, sr_rows: list[dict[str, Any]], tr: Translator = EN) -> str:
    if vc == 0:
        return tr.t("sr.zero_violations")
    flagged = tr.t("sr.list_sep").join(tr.t("sr.rule_with_name", rule=r["rule"], name=tr.t(f"sr.{r['rule']}.name_lc"))
                                       for r in sr_rows if r["violated"])
    return tr.t("sr.summary_flagged", count=vc, rules=flagged)


def score_label(x: float | None, tr: Translator = EN) -> str:
    return tr.t("score.not_scored") if x is None else tr.t("score.value", value=f"{x:.0f}")


def contains_banned_claim(text: str) -> list[str]:
    low = text.lower()
    return [b for b in BANNED_CLAIMS + BANNED_CLAIMS_TR if b in low]


# ---------------------------------------------------------------- plain-language wording (display only)
# The frozen evaluation produces technical evidence tokens (e.g. "breathable_fibre_share=0.85"). The functions below turn the
# structured values into readable sentences; they never change a score, a status or the composition. The original technical
# explanation stays available next to the readable sentence.
PREFERENCE_IDS = ("preferred_dominant_material", "colour", "fit", "length_cut", "stretch", "thermal_warmth", "breathability",
                  "durability_wear", "moisture_wicking", "water_repellent")
PREFERENCE_NAMES = {p: EN.t(f"pref.{p}") for p in PREFERENCE_IDS}
_SHARE_KEYS = ("breathable_fibre_share", "light_fibre_share", "wool_acrylic_share", "nylon_share", "polyester_nylon_share",
               "polyester_filling_share", "wool_penalty")
_FLAG_KEYS = {"coating_penalty": "flag.coating_penalty", "filling_penalty": "flag.filling_penalty", "filling_present": "flag.filling_present",
              "polyester_blend": "flag.polyester_blend", "coating_component": "flag.coating_component",
              "supporting:synthetic_shell": "flag.supporting_synthetic_shell", "strong_evidence_present": "flag.strong_evidence_present",
              "no_strong_evidence (synthetic shell alone is not proof)": "flag.no_strong_evidence", "neutral": "flag.neutral"}
_BUCKETS = ("none", "low", "high", "out_of_range")
_UNSCORABLE = ("neutral_value", "no_label_evidence", "no_primary_component_materials", "candidate_colour_unavailable")


def pref_name(pref: str, tr: Translator = EN) -> str:
    key = f"pref.{pref}"
    return tr.t(key) if pref in PREFERENCE_IDS else pref.replace("_", " ")


def _pref_value(pref: str, val: Any, tr: Translator) -> str:
    """Requested value of a preference for display (enum values / materials / colours translated)."""
    if pref == "preferred_dominant_material":
        return tr.label("material", val)
    if pref == "colour":
        return tr.label("colour", val)
    if pref in ("fit", "length_cut", "stretch", "thermal_warmth", "breathability", "durability_wear"):
        return tr.label(pref, val)
    return str(val)


def evidence_phrase(token: str, tr: Translator = EN) -> str:
    """One technical evidence token -> readable phrase (unknown tokens are returned unchanged)."""
    if token in _FLAG_KEYS:
        return tr.t(_FLAG_KEYS[token])
    if token.startswith("text:"):
        if tr.lang == "en":
            return tr.t("evidence.text_mentions", terms=token[5:].replace("_", " ").replace(",", ", "))
        return tr.t("evidence.text_mentions", terms=tr.t("evidence.text_sep").join(tr.label("text_tag", x) for x in token[5:].split(",")))
    if "=" in token:
        key, val = token.split("=", 1)
        if key in _SHARE_KEYS:
            try:
                return tr.t("evidence.share_pct", text=tr.t(f"share.{key}"), pct=_whole_pct(float(val) * 100, tr))
            except ValueError:
                return tr.t("evidence.share_raw", text=tr.t(f"share.{key}"), value=val)
        if key == "elastane":
            return tr.t("evidence.elastane", value=val if tr.lang == "en" else tr.pct_token(val))
        if key in ("bucket", "stretch_bucket"):
            return tr.t("evidence.stretch_level", bucket=tr.t(f"bucket.{val}") if val in _BUCKETS else val)
        if key == "primary_component":
            return tr.t("evidence.main_fabric", component=tr.label("component", val))
        if key == "template_label":
            return tr.t("evidence.template_label", label=val)
        if key == "candidate_colour":
            return tr.t("evidence.colour", colour=tr.label("colour", val))
    return token


def _whole_pct(p: float, tr: Translator) -> str:
    return f"{p:.0f}%" if tr.lang == "en" else f"%{p:.0f}"


def preference_sentence(p: dict[str, Any], tr: Translator = EN) -> str:
    """Readable explanation for one frozen intent entry (keys: preference, requested_value, scorable, satisfaction_0_1,
    evidence, unscorable_reason)."""
    name = pref_name(p["preference"], tr)
    val = p["requested_value"]
    shown = val if tr.lang == "en" else _pref_value(p["preference"], val, tr)
    if not p["scorable"]:
        reason = p.get("unscorable_reason")
        why = tr.t(f"unscorable.{reason}", pref=name) if reason in _UNSCORABLE else (str(reason) if reason else tr.t("unscorable.no_evidence"))
        return tr.t("explain.not_scored", why=why)
    ev = [str(t) for t in p.get("evidence", [])]
    if p["preference"] == "preferred_dominant_material":
        dom = next((t.split("=", 2) for t in ev if t.startswith("dominant=")), None)
        prim = next((t.split("=", 1)[1] for t in ev if t.startswith("primary_component=")), None)
        where = tr.t("explain.dominant_where_named", component=tr.label("component", prim)) if prim and prim != "main" else tr.t("explain.dominant_where")
        if dom and len(dom) == 3:
            pct = dom[2] if tr.lang == "en" else tr.pct_token(dom[2])
            if dom[1] == val:
                return tr.t("explain.dominant_match", where=where, material=tr.label("material", dom[1]), pct=pct)
            return tr.t("explain.dominant_mismatch", where=where, material=tr.label("material", dom[1]), pct=pct, requested=shown)
    if p["preference"] in ("fit", "length_cut", "colour"):
        got = next((t.split("=", 1)[1] for t in ev if "=" in t), None)
        src = tr.t("explain.label_src_colour" if p["preference"] == "colour" else "explain.label_src")
        if got is not None:
            got_shown = got if tr.lang == "en" else _pref_value(p["preference"], got, tr)
            return tr.t("explain.label_value", name=name, got=got_shown, src=src, requested=shown)
    sat = p["satisfaction_0_1"]
    phrases = list(dict.fromkeys(evidence_phrase(t, tr) for t in ev if t != "neutral"))      # de-duplicated, order kept
    level = "full" if sat >= 0.99 else "none" if sat <= 0.01 else "partial"
    head = tr.t(f"explain.bool.{level}", name=name) if isinstance(val, bool) else tr.t(f"explain.enum.{level}", value=shown, name=name)
    tail = tr.t("explain.evidence_join", phrases=tr.t("explain.evidence_sep").join(phrases)) if phrases else ""
    return head + tail + tr.t("explain.proxy_tail")


def _pp(d: float, tr: Translator = EN) -> str:
    return tr.t("change.points_one" if abs(float(d) - 1) < 1e-9 else "change.points_many", value=tr.num(d, "g"))


def change_number(step: int) -> int:
    """Generator steps are 0-based; the UI numbers changes from 1 (used consistently for changes and rule attributions)."""
    return int(step) + 1


def change_sentence(e: dict[str, Any], tr: Translator = EN) -> str:
    """Readable description of one mutation-log entry (frozen generator log)."""
    comp = tr.t("change.component", component=tr.label("component", str(e.get("component_name", "component"))))
    m = lambda x: tr.label("material", x)  # noqa: E731
    if e["type"] == "substitution":
        why = tr.t("change.forbidden_reason") if e.get("reason") == "forbidden_repair" else ""
        return tr.t("change.substitution", n=change_number(e["step"]), from_material=m(e["from_material"]), to_material=m(e["to_material"]),
                    component=comp, pct=tr.pct(float(e["pct"])), why=why)
    b, a = e["pct_before"], e["pct_after"]
    if e["from_material"] == e["to_material"]:
        return tr.t("change.move_same", n=change_number(e["step"]), points=_pp(e["delta"], tr), material=m(e["from_material"]), component=comp)
    return tr.t("change.move", n=change_number(e["step"]), points=_pp(e["delta"], tr), from_material=m(e["from_material"]),
                to_material=m(e["to_material"]), component=comp, from_before=tr.pct(float(b[0])), from_after=tr.pct(float(a[0])),
                to_before=tr.pct(float(b[1])), to_after=tr.pct(float(a[1])))


def rule_change_sentence(r: dict[str, Any], tr: Translator = EN) -> str | None:
    """Readable statement for an SR rule whose result differs from the template (frozen ablation evidence)."""
    if r.get("vs_template") not in ("resolved", "introduced"):
        return None
    name = tr.t(f"sr.{r['rule']}.name_lc") if r["rule"] in SR_ORDER else r["rule"].lower()
    steps = [change_number(x) for x in (r.get("confirmed_by_mutation_steps") or [])]
    undo = ""
    if len(steps) == 1:
        undo = tr.t("rulechange.undo_one", n=steps[0])
    elif steps:
        undo = tr.t("rulechange.undo_many", first=tr.t("rulechange.undo_sep").join(map(str, steps[:-1])), last=steps[-1])
    kind = r["vs_template"]
    head = tr.t(f"rulechange.{kind}", rule=r["rule"], name=name)
    tail = tr.t(f"rulechange.{kind}_confirmed", undo=undo) if steps else tr.t("rulechange.unconfirmed")
    return head + tail + tr.t("rulechange.end")


_TRADE_OFF = (
    ("tradeoff.violations", re.compile(r"^Sorting rule violations: template (\S+) -> candidate (\S+) \((\S+)\)\.$")),
    ("tradeoff.intent", re.compile(r"^Intent alignment index: template (\S+) -> candidate (\S+) \((\S+) points\)\.$")),
    ("tradeoff.plausibility", re.compile(r"^Dataset-relative plausibility index: template (\S+) -> candidate (\S+) \((\S+) points\)\.$")),
)


_TRADE_OFF_FIXED = ("tradeoff.fewer_violations_lower_intent", "tradeoff.more_violations_higher_intent")


def trade_off_sentence(s: str, tr: Translator = EN) -> str:
    """Wording of the frozen template-vs-candidate trade-off lines. English: light clean-up of the frozen text (V1);
    other languages: the numbers are parsed from the frozen line and re-worded (unparsed lines are shown unchanged)."""
    if tr.lang == "en":
        return (s.replace(" -> ", " → ").replace("Sorting rule violations:", "SR1–SR5 violations:")
                .replace("Intent alignment index:", "Intent alignment:").replace("Dataset-relative plausibility index:", "Dataset-relative plausibility:"))
    for key in _TRADE_OFF_FIXED:
        if s == EN.t(key):
            return tr.t(key)
    for key, rx in _TRADE_OFF:
        mt = rx.match(s)
        if mt:
            template, candidate, delta = (x.replace(".", ",") if tr.lang == "tr" else x for x in mt.groups())   # keep frozen precision
            return tr.t(key, template=template, candidate=candidate, delta=delta)
    return s


_CONFLICT_KEYS = {
    frozenset({"fit", "stretch"}): "conflict.fit_stretch",
    frozenset({"breathability", "water_repellent"}): "conflict.breathability_water_repellent",
    frozenset({"thermal_warmth", "breathability"}): "conflict.thermal_warmth_breathability",
    frozenset({"stretch", "forbidden_materials"}): "conflict.stretch_forbidden_materials",
    frozenset({"moisture_wicking", "forbidden_materials"}): "conflict.moisture_wicking_forbidden_materials",
    frozenset({"preferred_dominant_material", "stretch"}): "conflict.preferred_dominant_material_stretch",
}


def conflict_text(fields: list[str], fallback: str, tr: Translator = EN) -> str:
    key = _CONFLICT_KEYS.get(frozenset(fields))
    if key:
        return tr.t(key)
    return fallback if tr.lang == "en" else tr.t("conflict.generic")


def invalid_value_text(detail: str, tr: Translator = EN) -> str:
    """Remove API-only hints ("use null ...") from frozen validation messages shown in the UI (English rendering)."""
    return (detail.replace(" (use null for no preference)", tr.t("error.no_preference_hint"))
            .replace("use true or null", tr.t("error.true_only_hint")))


# ---------------------------------------------------------------- request summary (V1.2: identifies which request a result belongs to)
_SUMMARY_FIELDS = (("target_segment", "segment", "segment"), ("detail_category", "category", "category"),
                   ("preferred_dominant_material", "preferred_material", "material"), ("forbidden_materials", "forbidden_materials", "material"),
                   ("colour", "colour", "colour"), ("fit", "fit", "fit"), ("length_cut", "length", "length_cut"),
                   ("stretch", "stretch", "stretch"), ("thermal_warmth", "thermal_warmth", "thermal_warmth"),
                   ("breathability", "breathability", "breathability"), ("durability_wear", "durability", "durability_wear"),
                   ("moisture_wicking", "moisture_wicking", None), ("water_repellent", "water_repellent", None))


def request_summary(raw_request: dict[str, Any], tr: Translator = EN) -> str:
    """Readable one-line summary of a raw request (internal values shown with their display labels)."""
    parts = []
    for rf, ui, domain in _SUMMARY_FIELDS:
        v = raw_request.get(rf)
        if v is None or v == [] or v is False:
            continue
        if v is True:
            shown = tr.t("value.yes")
        elif isinstance(v, list):
            shown = tr.t("request.list_sep").join(tr.label(domain, x) for x in v)
        else:
            shown = tr.label(domain, v) if domain else str(v)
        parts.append(tr.t("request.item", label=tr.field(ui), value=shown))
    return tr.t("request.sep").join(parts)
