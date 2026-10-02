"""Garment Representation v1: one deterministic, component-aware record per garment."""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any

import pandas as pd

from cago.config.settings import PCT_TOLERANCE_HIGH, PCT_TOLERANCE_LOW
from cago.representation.vocabulary import OTHER, token_for
from cago.requirements.properties import extract_text_tags


def _name_key(canonical: str | None, raw: Any) -> str:
    return canonical if canonical is not None else "~" + str(raw).strip().casefold()


def sort_materials(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Percentage descending, then material name; null percentages last. Removes permutation ambiguity."""
    return sorted(items, key=lambda m: (m["pct"] is None, -(m["pct"] or 0.0), _name_key(m["canonical"], m["raw"])))


def _clean(v: Any) -> float | None:
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)


def is_usable(validation_status: str, pct_sum: Any) -> bool:
    """Active component: percentage-valid (99 <= sum <= 101). Anything else is preserved as anomalous."""
    s = _clean(pct_sum)
    return validation_status == "valid" and s is not None and PCT_TOLERANCE_LOW <= s <= PCT_TOLERANCE_HIGH


def build_representation(garments: pd.DataFrame, components: pd.DataFrame, component_materials: pd.DataFrame,
                         split_map: pd.DataFrame, vocab: dict[str, Any]) -> pd.DataFrame:
    """Build the representation table. Source percentages are never repaired or renormalized."""
    cm = component_materials.sort_values(["component_id", "material_index"], kind="stable")
    mats: dict[str, list[dict[str, Any]]] = {}
    for cid, raw, canon, pct in zip(cm["component_id"], cm["material_raw"], cm["material_canonical"], cm["pct"]):
        mats.setdefault(cid, []).append({"raw": raw, "canonical": None if pd.isna(canon) else canon, "pct": _clean(pct)})

    cs = components.sort_values(["garment_id", "component_index"], kind="stable")
    by_g: dict[str, list[Any]] = {}
    for row in cs.itertuples(index=False):
        by_g.setdefault(row.garment_id, []).append(row)

    split_of = dict(zip(split_map["garment_id"], split_map["split"]))
    out = []
    for g in garments.itertuples(index=False):
        active, anomalous = [], []
        has_unmapped = has_other = False
        for c in by_g.get(g.garment_id, []):
            ms = sort_materials(mats.get(c.component_id, []))
            if is_usable(c.validation_status, c.pct_sum_calculated):
                toks = [token_for(m["canonical"], vocab) for m in ms]
                has_unmapped |= any(m["canonical"] is None for m in ms)
                has_other |= any(t == OTHER for t in toks)
                active.append({
                    "component_id": c.component_id, "source_component_index": int(c.component_index),
                    "component_class": c.component_class, "component_name_normalized": c.component_name_normalized,
                    "material_count": len(ms), "materials": [m["canonical"] for m in ms],
                    "materials_raw": [m["raw"] for m in ms], "ml_tokens": toks,
                    "percentages": [m["pct"] for m in ms], "pct_sum": _clean(c.pct_sum_calculated)})
            else:
                anomalous.append({
                    "component_id": c.component_id, "source_component_index": int(c.component_index),
                    "component_class": c.component_class, "component_name_normalized": c.component_name_normalized,
                    "validation_status": c.validation_status, "pct_sum_calculated": _clean(c.pct_sum_calculated),
                    "materials_raw": [m["raw"] for m in ms], "percentages": [m["pct"] for m in ms]})
        out.append({
            "garment_id": g.garment_id, "source_row_number": int(g.source_row_number),
            "parent_product_id": g.parent_product_id, "split": split_of.get(g.garment_id),
            "target_segment": g.gender_section, "gender_section": g.gender_section,
            "parent_category": g.parent_category, "detail_category": g.detail_category,
            "normalized_colour": g.variant_colour_normalized,
            "n_active_components": len(active), "n_anomalous_components": len(anomalous),
            "is_fully_usable": bool(active) and not anomalous,
            "has_unmapped_material": bool(has_unmapped), "has_other_token": bool(has_other),
            "text_evidence_tags": extract_text_tags(g.product_name, g.raw_description_text, g.raw_function_text),
            "components": active, "anomalous_components": anomalous,
        })
    return pd.DataFrame(out)


def representation_hash(rep: pd.DataFrame) -> str:
    """Order-sensitive sha256 over the canonical JSON of (garment_id, components); for determinism checks."""
    h = hashlib.sha256()
    for gid, comps in zip(rep["garment_id"], rep["components"]):
        h.update(json.dumps([gid, list(comps)], sort_keys=True, ensure_ascii=False, default=list).encode("utf-8"))
    return h.hexdigest()
