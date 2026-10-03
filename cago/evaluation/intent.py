"""Transparent, decomposed Intent Alignment (a preference-alignment index, NOT a physical-performance score).

IntentAlignment = sum(confidence_i * satisfaction_i) / sum(confidence_i) over explicitly requested AND scorable
preferences. NULL preferences never count; if nothing is scorable the result is null (never an invented 100).
"""
from __future__ import annotations

from typing import Any, Callable

from cago.evaluation.config import INTENT_ORDER, NEUTRAL_VALUES, EvaluationConfig
from cago.requirements.properties import (GarmentProfile, StretchLimits, build_profile, score_breathability,
                                          score_durability, score_moisture_wicking, score_stretch, score_thermal,
                                          score_water_repellent)

FORMULA = ("IntentAlignment = sum(confidence_i * satisfaction_i) / sum(confidence_i) over requested, scorable "
           "preferences; reported x100")


def transform_score(pref: str, proxy_score: float, cfg: EvaluationConfig) -> tuple[float, str]:
    """Proxy [-1,1] -> satisfaction [0,1]; the transform used is returned so it is never hidden."""
    kind = cfg.transform[pref]
    if kind == "affine_signed":
        return (proxy_score + 1.0) / 2.0, "satisfaction = (proxy + 1) / 2"
    if kind == "clipped_reward":
        return max(0.0, min(1.0, proxy_score)), "satisfaction = clamp(proxy, 0, 1)"
    raise ValueError(f"unknown transform {kind!r}")


def dominant_material(profile: GarmentProfile, tol: float) -> tuple[str | None, list[str]]:
    """Highest-percentage material of the primary (first surface, else first) component.

    Ties (within tol) are broken alphabetically by canonical name - the same order the representation uses
    (percentage descending, then name). Returns (dominant, all tied top materials).
    """
    if not profile.primary_shares:
        return None, []
    ordered = sorted(profile.primary_shares.items(), key=lambda kv: (-kv[1], kv[0]))
    top = ordered[0][1]
    tied = [m for m, p in ordered if abs(p - top) <= tol]
    return ordered[0][0], tied


def _entry(pref, value, sat, conf_class, weight, evidence, explanation, scorable=True, reason=None, proxy=None, tf=None):
    return {"preference": pref, "requested_value": value, "scorable": scorable,
            "satisfaction_0_1": None if sat is None else round(sat, 6), "evidence_confidence": weight,
            "confidence_class": conf_class, "evidence": evidence, "explanation": explanation,
            "unscorable_reason": reason, "proxy_score_raw": proxy, "transform": tf}


def evaluate_intent(soft: dict[str, Any], components: list[dict[str, Any]], colour: str | None,
                    fit_label: str | None, length_label: str | None, text_tags=(), cfg: EvaluationConfig = EvaluationConfig(),
                    limits: StretchLimits = StretchLimits()) -> dict[str, Any]:
    """Evaluate every explicitly requested soft preference for one composition.

    components: ordered dicts with component_class, component_name_normalized, materials=[{material, pct}].
    fit_label / length_label: V1 labels carried by the template (topology is preserved, so they are not re-derived).
    """
    prof = build_profile(components, colour, text_tags)
    out: list[dict[str, Any]] = []
    for pref in INTENT_ORDER:
        value = soft.get(pref)
        if value is None:
            continue
        cls, w = cfg.confidence[pref]

        def unscorable(reason: str, expl: str, ev=None):
            return _entry(pref, value, None, cls, w, ev or [], expl, False, reason)

        if pref in NEUTRAL_VALUES and value == NEUTRAL_VALUES[pref]:
            out.append(unscorable("neutral_value", f"'{value}' is a neutral request and is not scored"))
        elif pref == "preferred_dominant_material":
            dom, tied = dominant_material(prof, cfg.dominant_tie_tolerance)
            if dom is None:
                out.append(unscorable("no_primary_component_materials", "no materials in the primary component"))
                continue
            ok = dom == value
            ev = [f"primary_component={prof.primary_name}", f"dominant={dom}={prof.primary_shares[dom]:g}%"]
            if len(tied) > 1:
                ev.append(f"tie_among={tied}; resolved alphabetically")
            out.append(_entry(pref, value, 1.0 if ok else 0.0, cls, w, ev,
                              f"{value} is {'' if ok else 'not '}the highest-percentage material of the primary component"
                              f" ('{dom}' at {prof.primary_shares[dom]:g}%)"))
        elif pref == "colour":
            if colour is None:
                out.append(unscorable("candidate_colour_unavailable", "candidate has no normalized colour"))
                continue
            ok = colour == value
            out.append(_entry(pref, value, 1.0 if ok else 0.0, cls, w, [f"candidate_colour={colour}"],
                              f"candidate colour '{colour}' {'matches' if ok else 'does not match'} requested '{value}' (exact match)"))
        elif pref in ("fit", "length_cut"):
            label = fit_label if pref == "fit" else length_label
            if label is None:
                out.append(unscorable("no_label_evidence", f"template has no V1 {pref} label; unscorable, not zero"))
                continue
            ok = label == value
            out.append(_entry(pref, value, 1.0 if ok else 0.0, cls, w, [f"template_label={label}", "label inherited from template"],
                              f"template {pref} label '{label}' {'matches' if ok else 'differs from'} requested '{value}'"))
        else:
            fns: dict[str, Callable[[], dict[str, Any]]] = {
                "stretch": lambda: score_stretch(value, prof, limits),
                "thermal_warmth": lambda: score_thermal(value, prof),
                "breathability": lambda: score_breathability(value, prof),
                "durability_wear": lambda: score_durability(value, prof),
                "moisture_wicking": lambda: score_moisture_wicking(prof),
                "water_repellent": lambda: score_water_repellent(prof),
            }
            r = fns[pref]()
            sat, tf = transform_score(pref, r["score"], cfg)
            extra = []
            if pref == "water_repellent":
                extra = ["strong_evidence_present" if r.get("proven") else "no_strong_evidence (synthetic shell alone is not proof)"]
            if pref == "stretch":
                extra = [f"bucket={r['bucket']}"]
            out.append(_entry(pref, value, sat, cls, w, [*r["evidence"], *extra],
                              f"proxy '{pref}={value}' scored {r['score']:g} from composition/text evidence "
                              f"({'; '.join(r['evidence'])})", proxy=r["score"], tf=tf))
    scorable = [e for e in out if e["scorable"]]
    wsum = sum(e["evidence_confidence"] for e in scorable)
    raw = sum(e["evidence_confidence"] * e["satisfaction_0_1"] for e in scorable) / wsum if scorable else None
    return {"intent_alignment_raw": None if raw is None else round(raw, 6),
            "intent_alignment_0_100": None if raw is None else round(100 * raw, 2),
            "n_active_preferences": len(out), "n_scorable_preferences": len(scorable),
            "unscorable_preferences": [{"preference": e["preference"], "reason": e["unscorable_reason"]} for e in out if not e["scorable"]],
            "preferences": out, "formula": FORMULA,
            "note": "preference-alignment index from composition/label evidence; not a physical-performance score"}
