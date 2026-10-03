"""TRAIN-only template selection: exact (target_segment, detail_category) match; preferences only RANK."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from cago.generation.support_tables import TRAIN, to_py
from cago.preprocessing.ids import stable_hash
from cago.requirements.properties import build_profile, score_preferences

EXACT_100_TOL = 1e-6


@dataclass
class Template:
    garment_id: str
    parent_product_id: Any
    target_segment: str
    detail_category: str
    split: str
    colour: str | None
    fit_label: str | None
    length_label: str | None
    text_tags: tuple[str, ...]
    components: list[dict[str, Any]]            # complete, ordered, plain-Python component records
    n_forbidden_slots: int = 0
    rank_score: float = 0.0


def template_components(row_components: Any) -> list[dict[str, Any]]:
    """Plain-Python components: [{component_id, source_component_index, component_class,
    component_name_normalized, materials:[{material, pct}]}] in the representation's order."""
    out = []
    for c in to_py(row_components):
        out.append({"component_id": c["component_id"], "source_component_index": c["source_component_index"],
                    "component_class": c["component_class"], "component_name_normalized": c["component_name_normalized"],
                    "materials": [{"material": m, "pct": float(p)} for m, p in zip(c["materials"], c["percentages"])],
                    "_ml_tokens": list(c["ml_tokens"])})
    return out


def ineligibility_reason(row: Any, comps: list[dict[str, Any]]) -> str | None:
    """Why a TRAIN garment cannot be a clean template (None = eligible)."""
    if not row.is_fully_usable or not comps:
        return "anomalous_or_missing_component"
    if row.has_unmapped_material:
        return "unmapped_material"
    if row.has_other_token:
        return "non_vocab_material_token"
    for c in comps:
        total = sum(m["pct"] for m in c["materials"])
        if abs(total - 100.0) > EXACT_100_TOL or any(m["pct"] < 0 for m in c["materials"]):
            return "component_sum_not_100"
    return None


def composition_signature(comps: list[dict[str, Any]]) -> tuple:
    return tuple((c["component_class"], c["component_name_normalized"],
                  tuple((m["material"], round(m["pct"], 6)) for m in c["materials"])) for c in comps)


def select_templates(rep: pd.DataFrame, request: dict[str, Any], n_templates: int, seed: int,
                     forbidden: frozenset[str] = frozenset()) -> tuple[list[Template], dict[str, Any]]:
    """Pick up to n templates from TRAIN garments of the exact segment + category.

    Hard filters: split == train, exact target_segment and detail_category, clean-template eligibility.
    Soft preferences only rank (fewest forbidden-material repairs first, then diagnostic preference match, then a
    seeded hash). One template per parent product and per distinct composition.
    """
    seg, cat = request["target_segment"], request["detail_category"]
    soft = request.get("soft_preferences", {})
    cell = rep[(rep["split"] == TRAIN) & (rep["target_segment"] == seg) & (rep["detail_category"] == cat)]
    reasons: Counter = Counter()
    pool: list[Template] = []
    for row in cell.itertuples(index=False):
        comps = template_components(row.components)
        why = ineligibility_reason(row, comps)
        if why:
            reasons[why] += 1
            continue
        tags = tuple(to_py(row.text_evidence_tags))
        profile_comps = [{"component_class": c["component_class"], "component_name_normalized": c["component_name_normalized"],
                          "materials": c["materials"]} for c in comps]
        prof = build_profile(profile_comps, row.normalized_colour, tags)
        diag = score_preferences({k: v for k, v in soft.items() if k not in ("fit", "length_cut")}, prof, cat)
        bonus = 0.5 * (soft.get("fit") is not None and row.fit_label == soft.get("fit")) \
            + 0.5 * (soft.get("length_cut") is not None and row.length_label == soft.get("length_cut"))
        pool.append(Template(row.garment_id, row.parent_product_id, seg, cat, row.split, row.normalized_colour,
                             row.fit_label, row.length_label, tags, comps,
                             sum(m["material"] in forbidden for c in comps for m in c["materials"]),
                             float(diag["diagnostic_mean_score"] or 0.0) + bonus))
    pool.sort(key=lambda t: (t.n_forbidden_slots, -t.rank_score, stable_hash(seed, t.garment_id, length=16)))
    chosen, parents, sigs = [], set(), set()
    for t in pool:
        sig = composition_signature(t.components)
        if t.parent_product_id in parents or sig in sigs:
            continue
        parents.add(t.parent_product_id); sigs.add(sig); chosen.append(t)
        if len(chosen) >= n_templates:
            break
    diag = {"train_garments_in_cell": len(cell), "eligible_templates": len(pool),
            "ineligible_reasons": dict(reasons), "selected": len(chosen),
            "selected_distinct_parents": len(parents), "requested": n_templates,
            "pool_smaller_than_requested": len(chosen) < n_templates,
            "selected_requiring_forbidden_repair": sum(t.n_forbidden_slots > 0 for t in chosen)}
    return chosen, diag
