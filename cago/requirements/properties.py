"""Functional-property PROXY rules. These score composition/component evidence only; they are not physical
guarantees (no measured stretch, warmth, breathability, durability, wicking or water repellency).

All weights live in `PropertyRules` so they can be tuned later. Scores are in [-1, 1] (higher = better match
for the requested property); each result lists its evidence.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from cago.config.materials import FAMILY_BY_CANONICAL
from cago.requirements.conflicts import fit_stretch_compat

# ---------------------------------------------------------------- text evidence
TEXT_PATTERNS: dict[str, str] = {
    "brushed": r"\bbrushed\b", "fleece": r"\bfleece\b", "padded": r"\bpadded\b", "thermal": r"\bthermal\b",
    "reinforced": r"\breinforced\b", "durable": r"\bdurable\b", "ripstop": r"\brip[- ]?stop\b",
    "heavyweight": r"\bheavy[- ]?weight\b", "double_layer": r"\bdouble[- ]layer(?:ed)?\b",
    "quick_dry": r"\bquick[- ]dr(?:y|ying)\b", "moisture_wicking": r"\b(?:moisture[- ]wicking|wicking)\b",
    "water_resistant": r"\bwater[- ](?:resistant|repellent|repellency)\b",
    "membrane": r"\bmembrane\b", "lamination": r"\blaminat(?:ed|ion)\b",
}
_COMPILED = {k: re.compile(v, re.IGNORECASE) for k, v in TEXT_PATTERNS.items()}


def extract_text_tags(*texts: Any) -> list[str]:
    """Sorted evidence tags found in the given free texts (None/non-str ignored)."""
    blob = " ".join(t for t in texts if isinstance(t, str))
    return sorted(tag for tag, rx in _COMPILED.items() if rx.search(blob))


# ---------------------------------------------------------------- config
@dataclass(frozen=True)
class StretchLimits:
    """Elastane % bounds for stretch buckets. `high_max=None` = no upper bound (do not hard-code unrealistic caps).

    Hook: pass `limits_by_category` (e.g. fitted on TRAIN data later) to score_stretch/score_preferences.
    """
    low_max: float = 2.0
    high_max: float | None = None


@dataclass(frozen=True)
class PropertyRules:
    light_materials: tuple[str, ...] = ("cotton", "linen", "lyocell", "viscose")
    breathable_materials: tuple[str, ...] = ("linen", "cotton", "lyocell", "viscose")
    heavy_materials: tuple[str, ...] = ("wool", "acrylic")
    wick_materials: tuple[str, ...] = ("polyester", "nylon")
    polyester_blend_partners: tuple[str, ...] = ("nylon", "cotton")
    filling_names: frozenset[str] = frozenset({"filling", "padding", "body_filling", "upper_body_filling",
                                               "under_body_filling"})
    filling_penalty_light: float = 0.5
    wool_penalty_light: float = 1.0
    filling_reward_heavy: float = 0.5
    poly_filling_reward_heavy: float = 0.3
    coating_penalty_breath: float = 0.5
    filling_penalty_breath: float = 0.3
    heavyweight_text_penalty_breath: float = 0.2
    polyester_blend_weight_durable: float = 0.5
    text_bonus: float = 0.15
    text_bonus_cap: float = 0.45
    thermal_text: tuple[str, ...] = ("brushed", "fleece", "padded", "thermal")
    durable_text: tuple[str, ...] = ("reinforced", "durable", "ripstop", "heavyweight", "double_layer")
    wick_text: tuple[str, ...] = ("quick_dry", "moisture_wicking")
    water_strong_weight: float = 0.5
    water_support_weight: float = 0.2
    synthetic_shell_min_share: float = 50.0


DEFAULT_RULES = PropertyRules()


# ---------------------------------------------------------------- profile
@dataclass
class GarmentProfile:
    """Composition summary used by the proxies (works for dataset garments and generated candidates)."""
    primary_name: str | None
    primary_shares: dict[str, float]
    coating_present: bool
    filling_present: bool
    filling_shares: dict[str, float]
    dominant: str | None
    colour: str | None = None
    text_tags: frozenset[str] = field(default_factory=frozenset)

    @property
    def elastane_pct(self) -> float:
        return self.primary_shares.get("elastane", 0.0)


def _shares(materials: Iterable[dict[str, Any]]) -> dict[str, float]:
    out: dict[str, float] = {}
    for m in materials:
        name, pct = m.get("material"), m.get("pct")
        if name is None or pct is None:
            continue
        out[name] = out.get(name, 0.0) + float(pct)
    return out


def build_profile(components: list[dict[str, Any]], colour: str | None = None,
                  text_tags: Iterable[str] = (), rules: PropertyRules = DEFAULT_RULES) -> GarmentProfile:
    """components: ordered dicts with component_class, component_name_normalized(or component_name), materials=[{material,pct}].

    Primary component = first surface_component, else first component.
    """
    def cname(c): return c.get("component_name_normalized", c.get("component_name"))
    primary = next((c for c in components if c.get("component_class") == "surface_component"),
                   components[0] if components else None)
    pshares = _shares(primary["materials"]) if primary else {}
    fill: dict[str, float] = {}
    filling_present = False
    for c in components:
        if c.get("component_class") == "filling_component" or cname(c) in rules.filling_names:
            filling_present = True
            for k, v in _shares(c["materials"]).items():
                fill[k] = fill.get(k, 0.0) + v
    coating = any(cname(c) == "coating" for c in components)
    dom = sorted(pshares.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if pshares else None
    return GarmentProfile(cname(primary) if primary else None, pshares, coating, filling_present, fill, dom,
                          colour, frozenset(text_tags))


# ---------------------------------------------------------------- scoring helpers
def _clamp(x: float) -> float:
    return max(-1.0, min(1.0, x))


def _res(score: float | None, evidence: list[str], **extra: Any) -> dict[str, Any]:
    return {"score": None if score is None else round(_clamp(score), 4), "evidence": evidence, "proxy": True, **extra}


def stretch_bucket(elastane_pct: float, limits: StretchLimits = StretchLimits()) -> str:
    """none: elastane == 0; low: 0 < e <= low_max; high: e > low_max (optionally <= high_max, else 'out_of_range')."""
    if elastane_pct <= 1e-9:
        return "none"
    if elastane_pct <= limits.low_max:
        return "low"
    if limits.high_max is not None and elastane_pct > limits.high_max:
        return "out_of_range"
    return "high"


def score_stretch(requested: str, p: GarmentProfile, limits: StretchLimits = StretchLimits()) -> dict[str, Any]:
    bucket = stretch_bucket(p.elastane_pct, limits)
    return _res(1.0 if bucket == requested else -1.0, [f"elastane={p.elastane_pct:g}%", f"bucket={bucket}"],
                bucket=bucket)


def score_thermal(requested: str, p: GarmentProfile, r: PropertyRules = DEFAULT_RULES) -> dict[str, Any]:
    sh, ev = p.primary_shares, []
    if requested == "standard":
        return _res(0.0, ["neutral"])
    if requested == "light":
        s = sum(sh.get(m, 0.0) for m in r.light_materials) / 100
        ev.append(f"light_fibre_share={s:.2f}")
        wool = sh.get("wool", 0.0) / 100 * r.wool_penalty_light
        if wool:
            s -= wool; ev.append(f"wool_penalty={wool:.2f}")
        if p.filling_present:
            s -= r.filling_penalty_light; ev.append("filling_penalty")
        return _res(s, ev)
    s = sum(sh.get(m, 0.0) for m in r.heavy_materials) / 100
    ev.append(f"wool_acrylic_share={s:.2f}")
    if p.filling_present:
        s += r.filling_reward_heavy; ev.append("filling_present")
        poly = p.filling_shares.get("polyester", 0.0) / max(sum(p.filling_shares.values()), 1e-9)
        if poly:
            s += r.poly_filling_reward_heavy * poly; ev.append(f"polyester_filling_share={poly:.2f}")
    tags = [t for t in r.thermal_text if t in p.text_tags]
    if tags:
        s += min(len(tags) * r.text_bonus, r.text_bonus_cap); ev.append("text:" + ",".join(tags))
    return _res(s, ev)


def score_breathability(requested: str, p: GarmentProfile, r: PropertyRules = DEFAULT_RULES) -> dict[str, Any]:
    if requested == "standard":
        return _res(0.0, ["neutral"])
    s = sum(p.primary_shares.get(m, 0.0) for m in r.breathable_materials) / 100
    ev = [f"breathable_fibre_share={s:.2f}"]
    if p.coating_present:
        s -= r.coating_penalty_breath; ev.append("coating_penalty")
    if p.filling_present:
        s -= r.filling_penalty_breath; ev.append("filling_penalty")
    if "heavyweight" in p.text_tags:
        s -= r.heavyweight_text_penalty_breath; ev.append("text:heavyweight")
    return _res(s, ev)


def score_durability(requested: str, p: GarmentProfile, r: PropertyRules = DEFAULT_RULES) -> dict[str, Any]:
    if requested == "standard":
        return _res(0.0, ["neutral"])
    sh = p.primary_shares
    s = sh.get("nylon", 0.0) / 100
    ev = [f"nylon_share={s:.2f}"]
    poly = sh.get("polyester", 0.0)
    if poly and any(sh.get(m, 0.0) for m in r.polyester_blend_partners):
        s += r.polyester_blend_weight_durable * poly / 100; ev.append("polyester_blend")
    tags = [t for t in r.durable_text if t in p.text_tags]
    if tags:
        s += min(len(tags) * r.text_bonus, r.text_bonus_cap); ev.append("text:" + ",".join(tags))
    return _res(s, ev)


def score_moisture_wicking(p: GarmentProfile, r: PropertyRules = DEFAULT_RULES) -> dict[str, Any]:
    """Polyester/nylon share (+ optional text). Microfibre is never inferred."""
    s = sum(p.primary_shares.get(m, 0.0) for m in r.wick_materials) / 100
    ev = [f"polyester_nylon_share={s:.2f}"]
    tags = [t for t in r.wick_text if t in p.text_tags]
    if tags:
        s += min(len(tags) * r.text_bonus, r.text_bonus_cap); ev.append("text:" + ",".join(tags))
    return _res(s, ev)


def score_water_repellent(p: GarmentProfile, r: PropertyRules = DEFAULT_RULES) -> dict[str, Any]:
    """Strong evidence: coating component, membrane/lamination text, water-resistant/repellent text.
    A synthetic shell is supporting evidence only and can never count as proof on its own."""
    strong = []
    if p.coating_present:
        strong.append("coating_component")
    for tag in ("membrane", "lamination", "water_resistant"):
        if tag in p.text_tags:
            strong.append(f"text:{tag}")
    synth = sum(v for k, v in p.primary_shares.items() if FAMILY_BY_CANONICAL.get(k) == "synthetic")
    support = synth >= r.synthetic_shell_min_share
    s = r.water_strong_weight * len(strong) + (r.water_support_weight if support else 0.0)
    ev = [*strong, *(["supporting:synthetic_shell"] if support else [])]
    return _res(s, ev, proven=bool(strong))


def score_dominant_material(preferred: str, p: GarmentProfile) -> dict[str, Any]:
    if p.dominant == preferred:
        return _res(1.0, ["dominant"])
    if preferred in p.primary_shares:
        return _res(0.25, ["present_not_dominant"])
    return _res(0.0, ["absent"])


def score_colour(preferred: str, p: GarmentProfile) -> dict[str, Any]:
    """Exact normalized-colour match only (no semantic merging)."""
    return _res(1.0 if p.colour == preferred else 0.0, ["exact_match" if p.colour == preferred else "no_match"])


def score_fit(fit: str, p: GarmentProfile, limits: StretchLimits = StretchLimits()) -> dict[str, Any]:
    bucket = stretch_bucket(p.elastane_pct, limits)
    if bucket == "out_of_range":
        return _res(0.0, ["stretch_out_of_range"])
    return _res(fit_stretch_compat(fit, bucket), [f"stretch_bucket={bucket}"])


def score_preferences(soft: dict[str, Any], p: GarmentProfile, category: str | None = None,
                      limits_by_category: dict[str, StretchLimits] | None = None,
                      rules: PropertyRules = DEFAULT_RULES) -> dict[str, Any]:
    """Score one candidate profile against the normalized soft preferences. Null preferences are skipped;
    length_cut is not scorable from composition (reported as scorable=False)."""
    lim = (limits_by_category or {}).get(category or "", StretchLimits())
    fns: dict[str, Callable[[Any], dict[str, Any]]] = {
        "stretch": lambda v: score_stretch(v, p, lim),
        "thermal_warmth": lambda v: score_thermal(v, p, rules),
        "breathability": lambda v: score_breathability(v, p, rules),
        "durability_wear": lambda v: score_durability(v, p, rules),
        "moisture_wicking": lambda v: score_moisture_wicking(p, rules),
        "water_repellent": lambda v: score_water_repellent(p, rules),
        "fit": lambda v: score_fit(v, p, lim),
        "preferred_dominant_material": lambda v: score_dominant_material(v, p),
        "colour": lambda v: score_colour(v, p),
    }
    per: dict[str, Any] = {}
    for name, value in soft.items():
        if value is None:
            continue
        if name == "length_cut":
            per[name] = {"score": None, "scorable": False, "evidence": ["not derivable from composition"], "proxy": True}
        elif name in fns:
            per[name] = fns[name](value)
    vals = [v["score"] for v in per.values() if v["score"] is not None]
    return {"per_property": per, "diagnostic_mean_score": round(sum(vals) / len(vals), 4) if vals else None,
            "note": "DIAGNOSTIC ONLY: unweighted mean of proxy scores; NOT the Intent Alignment Score and not a "
                    "performance, sustainability or recyclability score"}
