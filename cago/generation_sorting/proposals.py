"""Mode A (sorting_aware_proposal): bias the random mutation proposals with Oracle violation information.

The frozen Template Baseline proposal generators are reused unchanged; each proposal's weight is multiplied by
exp(strength * (repairable violations before - after)) using the Oracle's own rule functions on the resulting
composition, and rule-targeted 'merge into an existing fibre' proposals (which the baseline never generates) are added
whenever a repairable rule is violated. TRAIN support, hard-constraint filters and pct bounds still apply.
"""
from __future__ import annotations

import math
import random
from typing import Any

from cago.generation.mutations import MutationContext, apply_percentage, apply_substitution, propose_percentage, propose_substitutions
from cago.generation_sorting.config import SortingAwareGenerationConfig
from cago.generation_sorting.oracle_view import analyze
from cago.generation_sorting.repairs import slot_substitutions, _r9


def _count(a: dict[str, Any], rules) -> int:
    return sum(bool(a["flags"][r]) for r in rules)


def _with_materials(components, ci: int, materials) -> list[dict[str, Any]]:
    out = list(components)
    out[ci] = {**components[ci], "materials": materials}
    return out


def merge_proposals(components, a, m: MutationContext, cfg) -> list[tuple[int, int, str, float]]:
    """(ci, slot, existing_material, weight): targeted fibre merges in the readable / hidden components."""
    targets = [i for i in (a["readable_index"], a["sr5_hidden_index"]) if i is not None]
    out = []
    for ci in dict.fromkeys(targets):
        comp = components[ci]
        present = {x["material"] for x in comp["materials"]}
        for si in range(len(comp["materials"])):
            for r, w in slot_substitutions(comp, si, m.category, m.support, m.forbidden):
                if r in present:
                    out.append((ci, si, r, w))
    return out


def biased_mutate_once(components, rng: random.Random, m: MutationContext, step: int, cfg: SortingAwareGenerationConfig,
                       counters=None) -> dict[str, Any] | None:
    allowed = cfg.allowed_rules()
    a0 = analyze(components, m.colour, counters)
    v0 = _count(a0, allowed)
    subs = propose_substitutions(components, m)
    pcts = propose_percentage(components, m)
    if v0:
        have = {(ci, si, r) for ci, si, r, _ in subs}
        subs = subs + [e for e in merge_proposals(components, a0, m, cfg) if (e[0], e[1], e[2]) not in have]
    k = cfg.proposal_bias_strength

    def bias(new_components) -> float:
        return math.exp(max(-6.0, min(6.0, k * (v0 - _count(analyze(new_components, m.colour, counters), allowed)))))

    subs_w = []
    for ci, si, r, w in subs:
        mats = [dict(x) for x in components[ci]["materials"]]
        mats[si]["material"] = r
        subs_w.append((ci, si, r, w * bias(_with_materials(components, ci, mats))))
    pcts_w = []
    for ci, i, j, d, w in pcts:
        mats = [dict(x) for x in components[ci]["materials"]]
        mats[i]["pct"], mats[j]["pct"] = _r9(mats[i]["pct"] - d), _r9(mats[j]["pct"] + d)
        pcts_w.append((ci, i, j, d, w * bias(_with_materials(components, ci, mats))))
    if not subs_w and not pcts_w:
        return None
    use_sub = bool(subs_w) and (not pcts_w or rng.random() < m.settings.p_substitution)
    if use_sub:
        ci, si, r, _ = _pick(rng, subs_w, [x[3] for x in subs_w])
        return apply_substitution(components, ci, si, r, step)
    ci, i, j, d, _ = _pick(rng, pcts_w, [x[4] for x in pcts_w])
    return apply_percentage(components, ci, i, j, d, step)


def _pick(rng: random.Random, items: list, weights: list[float]):
    total = sum(weights)
    x, acc = rng.random() * total, 0.0
    for it, w in zip(items, weights):
        acc += w
        if x <= acc:
            return it
    return items[-1]
