"""Controlled mutations on a cloned template. Topology (components, order, class/name, material count) is never changed.

Two mutation types:
  percentage   : move `delta` percentage points from one material slot to another in the same component
                 (same materials; non-negative; component sum preserved exactly).
  substitution : replace one material slot by a material observed in TRAIN for the same detail_category +
                 component class (never forbidden, never PAD/OTHER, never already in the component; the slot's
                 percentage must not exceed the largest percentage observed for that material in that context).
Selection is random (seeded rng) but weighted by TRAIN frequency, observed combinations, the preferred dominant
material and diagnostic property proxies. Every change is written to a mutation log that can be replayed.
"""
from __future__ import annotations

import copy
import math
import random
from dataclasses import dataclass, field
from typing import Any

from cago.generation.support_tables import SPECIAL_TOKENS, SupportTables
from cago.requirements.properties import build_profile, score_preferences

SURFACE = "surface_component"


class RepairError(Exception):
    """A forbidden material cannot be replaced by any admissible TRAIN-supported material."""


@dataclass(frozen=True)
class MutationSettings:
    pct_steps: tuple[float, ...] = (1.0, 2.0, 5.0, 10.0)
    min_pct: float = 1.0                  # a source slot is not pushed below min(current, min_pct)
    p_substitution: float = 0.5
    property_bias_beta: float = 1.0       # weight *= exp(beta * delta diagnostic property score)
    preferred_dominant_bias: float = 4.0
    observed_combo_bonus: float = 2.0


@dataclass
class MutationContext:
    category: str
    support: SupportTables
    forbidden: frozenset[str] = frozenset()
    preferred_dominant: str | None = None
    soft: dict[str, Any] = field(default_factory=dict)
    colour: str | None = None
    text_tags: frozenset[str] = frozenset()
    settings: MutationSettings = MutationSettings()


def _r(x: float) -> float:
    return round(x, 9)


def clone_components(components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return copy.deepcopy(components)


def _proxy_score(components: list[dict[str, Any]], m: MutationContext) -> float:
    prof = build_profile(components, m.colour, m.text_tags)
    s = score_preferences({k: v for k, v in m.soft.items() if k not in ("fit", "length_cut")}, prof, m.category)
    return float(s["diagnostic_mean_score"] or 0.0)


def _replace_component(components: list[dict[str, Any]], ci: int, materials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = list(components)
    out[ci] = {**components[ci], "materials": materials}
    return out


def _proxy_weight(components, ci, new_materials, base_score, m: MutationContext) -> float:
    if m.settings.property_bias_beta == 0 or not any(v is not None for k, v in m.soft.items() if k not in ("fit", "length_cut")):
        return 1.0
    delta = _proxy_score(_replace_component(components, ci, new_materials), m) - base_score
    return math.exp(max(-3.0, min(3.0, m.settings.property_bias_beta * delta)))


def _dominant_slot(materials: list[dict[str, Any]]) -> int:
    return max(range(len(materials)), key=lambda i: (materials[i]["pct"], -i))


# ---------------------------------------------------------------- proposals
def propose_substitutions(components, m: MutationContext, only_forbidden: bool = False):
    """[(ci, slot, replacement, weight)] — deterministic order."""
    out = []
    base = _proxy_score(components, m) if not only_forbidden else 0.0
    for ci, comp in enumerate(components):
        cls = comp["component_class"]
        pool = m.support.allowed(m.category, cls)
        present = {x["material"] for x in comp["materials"]}
        dom = _dominant_slot(comp["materials"])
        for si, slot in enumerate(comp["materials"]):
            if only_forbidden and slot["material"] not in m.forbidden:
                continue
            for r in pool:
                if (r == slot["material"] or r in present or r in m.forbidden or r.casefold() in SPECIAL_TOKENS):
                    continue
                bound = m.support.pct_max(m.category, cls, r)
                if bound is None or slot["pct"] > bound + 1e-9:
                    continue
                w = math.sqrt(m.support.count(m.category, cls, r))
                if m.support.combo_count(m.category, cls, (present - {slot["material"]}) | {r}):
                    w *= m.settings.observed_combo_bonus
                if cls == SURFACE and m.preferred_dominant:
                    if r == m.preferred_dominant and si == dom:
                        w *= m.settings.preferred_dominant_bias
                    if slot["material"] == m.preferred_dominant:
                        w *= 0.25
                if not only_forbidden:
                    new = [dict(x) for x in comp["materials"]]
                    new[si]["material"] = r
                    w *= _proxy_weight(components, ci, new, base, m)
                out.append((ci, si, r, w))
    return out


def propose_percentage(components, m: MutationContext):
    """[(ci, src_slot, dst_slot, delta, weight)] — transfers that keep every bound."""
    out = []
    base = _proxy_score(components, m)
    for ci, comp in enumerate(components):
        mats, cls = comp["materials"], comp["component_class"]
        if len(mats) < 2:
            continue
        for i, src in enumerate(mats):
            floor = min(src["pct"], m.settings.min_pct)
            for j, dst in enumerate(mats):
                if i == j:
                    continue
                cap = max(dst["pct"], m.support.pct_max(m.category, cls, dst["material"]) or 0.0)
                for d in m.settings.pct_steps:
                    if src["pct"] - d < floor - 1e-9 or dst["pct"] + d > cap + 1e-9:
                        continue
                    w = 1.0
                    if cls == SURFACE and m.preferred_dominant and dst["material"] == m.preferred_dominant:
                        w *= m.settings.preferred_dominant_bias
                    new = [dict(x) for x in mats]
                    new[i]["pct"] = _r(src["pct"] - d); new[j]["pct"] = _r(dst["pct"] + d)
                    out.append((ci, i, j, d, w * _proxy_weight(components, ci, new, base, m)))
    return out


def _choice(rng: random.Random, items: list, weights: list[float]):
    total = sum(weights)
    x, acc = rng.random() * total, 0.0
    for it, w in zip(items, weights):
        acc += w
        if x <= acc:
            return it
    return items[-1]


# ---------------------------------------------------------------- application (in place) + log
def apply_substitution(components, ci: int, si: int, r: str, step: int, reason: str | None = None) -> dict[str, Any]:
    slot = components[ci]["materials"][si]
    entry = {"step": step, "type": "substitution", "reason": reason, "component_index": ci,
             "component_name": components[ci]["component_name_normalized"], "slot": si,
             "from_material": slot["material"], "to_material": r, "pct": slot["pct"]}
    slot["material"] = r
    return entry


def apply_percentage(components, ci: int, i: int, j: int, d: float, step: int) -> dict[str, Any]:
    mats = components[ci]["materials"]
    entry = {"step": step, "type": "percentage", "reason": None, "component_index": ci,
             "component_name": components[ci]["component_name_normalized"], "from_slot": i, "to_slot": j,
             "from_material": mats[i]["material"], "to_material": mats[j]["material"], "delta": d,
             "pct_before": [mats[i]["pct"], mats[j]["pct"]]}
    mats[i]["pct"] = _r(mats[i]["pct"] - d)
    mats[j]["pct"] = _r(mats[j]["pct"] + d)
    entry["pct_after"] = [mats[i]["pct"], mats[j]["pct"]]
    return entry


def repair_forbidden(components, rng: random.Random, m: MutationContext, step0: int = 0) -> list[dict[str, Any]]:
    """Replace every forbidden material slot (mandatory, logged as reason='forbidden_repair')."""
    log = []
    while True:
        props = propose_substitutions(components, m, only_forbidden=True)
        pending = [(ci, si) for ci, c in enumerate(components) for si, s in enumerate(c["materials"])
                   if s["material"] in m.forbidden]
        if not pending:
            return log
        if not props:
            raise RepairError(f"no admissible replacement for forbidden slots {pending}")
        ci, si, r, _ = _choice(rng, props, [p[3] for p in props])
        log.append(apply_substitution(components, ci, si, r, step0 + len(log), "forbidden_repair"))


def mutate_once(components, rng: random.Random, m: MutationContext, step: int) -> dict[str, Any] | None:
    subs = propose_substitutions(components, m)
    pcts = propose_percentage(components, m)
    if not subs and not pcts:
        return None
    use_sub = bool(subs) and (not pcts or rng.random() < m.settings.p_substitution)
    if use_sub:
        ci, si, r, _ = _choice(rng, subs, [p[3] for p in subs])
        return apply_substitution(components, ci, si, r, step)
    ci, i, j, d, _ = _choice(rng, pcts, [p[4] for p in pcts])
    return apply_percentage(components, ci, i, j, d, step)


def replay(template_components, log: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Re-apply a mutation log to a fresh clone of the template (used to verify log == actual changes)."""
    comps = clone_components(template_components)
    for e in log:
        if e["type"] == "substitution":
            if comps[e["component_index"]]["materials"][e["slot"]]["material"] != e["from_material"]:
                raise ValueError(f"log step {e['step']} does not match state")
            apply_substitution(comps, e["component_index"], e["slot"], e["to_material"], e["step"], e["reason"])
        else:
            apply_percentage(comps, e["component_index"], e["from_slot"], e["to_slot"], e["delta"], e["step"])
    return comps
