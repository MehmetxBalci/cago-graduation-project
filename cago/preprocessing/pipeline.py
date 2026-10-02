"""Flatten source JSONL into garments / components / component_materials tables."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from cago.config.settings import REQUIRED_COMPONENT_FIELDS, REQUIRED_GARMENT_FIELDS
from cago.preprocessing.colours import is_exact_black, normalize_colour
from cago.preprocessing.ids import make_component_id, make_garment_ids
from cago.preprocessing.io import read_jsonl
from cago.preprocessing.materials import MaterialMapper
from cago.preprocessing.validation import classify_pct, validate_component


def _missing(v: Any) -> bool:
    return v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, (list, dict)) and not v)


def _missing_fields(obj: dict[str, Any], fields: tuple[str, ...]) -> str | None:
    miss = [f for f in fields if _missing(obj.get(f))]
    return ";".join(miss) or None


def _num_or_none(v: Any) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def build_tables(input_path: Path, support_dir: Path) -> dict[str, Any]:
    """Read the JSONL and build the three tables plus read-level metadata."""
    records, malformed, blank = read_jsonl(Path(input_path))
    mapper = MaterialMapper.from_support_dir(Path(support_dir))

    keys = [(r.get("brand"), r.get("region"), r.get("parent_product_id"), r.get("url"), r.get("variant_colour"))
            for _, r in records]
    garment_ids, _ = make_garment_ids(keys)
    key_counts = Counter(keys)
    dup_sizes = [n for n in key_counts.values() if n > 1]
    duplicate_stats = {
        "duplicate_key_groups": len(dup_sizes),
        "rows_in_duplicate_key_groups": sum(dup_sizes),
        "duplicate_extra_rows": sum(n - 1 for n in dup_sizes),
    }

    g_rows, c_rows, m_rows = [], [], []
    for (row_no, rec), gid in zip(records, garment_ids):
        comps = rec.get("components_structured")
        comps = comps if isinstance(comps, list) else []
        colour_raw = rec.get("variant_colour")
        colour_norm = normalize_colour(colour_raw)
        raw_cat = rec.get("raw_category")
        has_recycled, mat_raws, mat_canons = False, set(), set()

        for ci, comp in enumerate(comps):
            comp = comp if isinstance(comp, dict) else {}
            cid = make_component_id(gid, ci, comp.get("component_path_raw"))
            mats = comp.get("materials")
            mats = mats if isinstance(mats, list) else []
            pcts = [(m.get("pct") if isinstance(m, dict) else None) for m in mats]
            total, pct_valid, status = validate_component(pcts)
            c_rows.append({
                "component_id": cid, "garment_id": gid, "component_index": ci,
                "component_name_raw": comp.get("component_path_raw"),
                "component_name_normalized": comp.get("component_name_norm"),
                "component_class": comp.get("component_class"),
                "component_normalization_source": comp.get("component_norm_source"),
                "material_count": len(mats),
                "pct_sum_source": _num_or_none(comp.get("pct_sum")),
                "pct_sum_calculated": total,
                "pct_sum_flag_source": comp.get("pct_sum_flag"),
                "pct_valid": pct_valid, "validation_status": status,
                "missing_fields": _missing_fields(comp, REQUIRED_COMPONENT_FIELDS),
                "component_raw_text": comp.get("raw_text"),
            })
            for mi, m in enumerate(mats):
                m = m if isinstance(m, dict) else {}
                raw = m.get("material")
                canon, family, mstatus = mapper.map(raw)
                pct, pct_status = classify_pct(m.get("pct"))
                rec_pct, rec_status = classify_pct(m.get("recycled_pct"))
                has_recycled |= rec_status == "ok"
                mat_raws.add(raw)
                if canon is not None:
                    mat_canons.add(canon)
                m_rows.append({
                    "garment_id": gid, "component_id": cid, "material_index": mi,
                    "material_raw": raw, "material_canonical": canon, "material_family": family,
                    "material_mapping_status": mstatus,
                    "pct": pct, "pct_status": pct_status,
                    "recycled_pct": rec_pct, "recycled_pct_status": rec_status,
                })

        g_rows.append({
            "garment_id": gid, "source_row_number": row_no,
            "parent_product_id": rec.get("parent_product_id"), "brand": rec.get("brand"),
            "region": rec.get("region"), "gender_section": rec.get("gender_section"),
            "parent_category": rec.get("parent_category"), "detail_category": rec.get("detail_category"),
            "detail_rule_source": rec.get("detail_rule_source"), "detail_rule_hit": rec.get("detail_rule_hit"),
            "raw_category": json.dumps(raw_cat, ensure_ascii=False) if isinstance(raw_cat, list) else raw_cat,
            "raw_category_type": type(raw_cat).__name__,
            "product_name": rec.get("product_name"), "url": rec.get("url"),
            "url_collected_at": rec.get("url_collected_at"), "scraped_at": rec.get("scraped_at"),
            "variant_colour_raw": colour_raw, "variant_colour_normalized": colour_norm,
            "is_exact_black": is_exact_black(colour_norm),
            "all_colour_labels": rec.get("all_colour_labels"),
            "composition_assignment_type": rec.get("composition_assignment_type"),
            "component_count": len(comps), "unique_material_raw_count": len({x for x in mat_raws if x is not None}),
            "unique_material_canonical_count": len(mat_canons),
            "has_recycled_content_information": bool(has_recycled),
            "raw_material_text": rec.get("raw_material_text"),
            "raw_material_text_full": rec.get("raw_material_text_full"),
            "raw_material_text_norm": rec.get("raw_material_text_norm"),
            "raw_description_text": rec.get("raw_description_text"),
            "raw_function_text": rec.get("raw_function_text"),
            "missing_required_fields": _missing_fields(rec, REQUIRED_GARMENT_FIELDS),
        })

    garments = pd.DataFrame(g_rows)
    components = pd.DataFrame(c_rows)
    cm = pd.DataFrame(m_rows)
    for col in ("pct", "recycled_pct"):
        cm[col] = cm[col].astype("float64")
    ok = components.groupby("garment_id")["pct_valid"].all()
    garments["all_components_pct_valid"] = garments["garment_id"].map(ok).fillna(False).astype(bool)

    return {"garments": garments, "components": components, "component_materials": cm,
            "malformed": malformed, "blank_lines": blank, "n_valid_json": len(records),
            "duplicate_stats": duplicate_stats, "mapper": mapper}
