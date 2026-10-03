"""Shared synthetic fixtures for evaluation/Pareto tests (new helper; existing tests untouched)."""
from __future__ import annotations

import pandas as pd

from cago.requirements.schema import SOFT_FIELDS
from cago.requirements.validation import RequirementContext

VOCAB = {"cotton", "polyester", "linen", "nylon", "wool", "elastane", "viscose"}
CTX = RequirementContext(
    target_segments=frozenset({"women", "men"}), categories=frozenset({"trousers", "shorts"}),
    materials=frozenset(VOCAB | {"silk", "zinc"}), capabilities={},
    component_classes=frozenset({"surface_component", "lining_component"}),
    component_names=frozenset({"shell", "lining"}), ml_tokens=frozenset({"OTHER", "PAD"}))


def comp(i, cls, name, mats, gid):
    return {"component_id": f"{gid}_c{i}", "source_component_index": i, "component_class": cls,
            "component_name_normalized": name, "material_count": len(mats), "materials": [m for m, _ in mats],
            "materials_raw": [m for m, _ in mats], "ml_tokens": [m if m in VOCAB else "OTHER" for m, _ in mats],
            "percentages": [float(p) for _, p in mats], "pct_sum": float(sum(p for _, p in mats))}


def garment(gid, parent, split, shell, lining, seg="women", cat="trousers", colour="black", fit=None, length=None):
    comps = [comp(0, "surface_component", "shell", shell, gid), comp(1, "lining_component", "lining", lining, gid)]
    return {"garment_id": gid, "parent_product_id": parent, "split": split, "target_segment": seg, "detail_category": cat,
            "normalized_colour": colour, "fit_label": fit, "length_label": length, "text_evidence_tags": [],
            "is_fully_usable": True, "has_unmapped_material": False,
            "has_other_token": any(m not in VOCAB for c in comps for m in c["materials"]), "components": comps}


def make_rep(extra=()):
    return pd.DataFrame([
        garment("T1", "p1", "train", [("cotton", 60), ("polyester", 40)], [("polyester", 100)], fit="slim", length="long"),
        garment("T2", "p2", "train", [("cotton", 98), ("elastane", 2)], [("viscose", 100)], fit="relaxed"),
        garment("T3", "p3", "train", [("linen", 100)], [("cotton", 100)], length="standard"),
        garment("T4", "p4", "train", [("polyester", 70), ("nylon", 30)], [("nylon", 100)]),
        garment("T5", "p5", "train", [("wool", 50), ("cotton", 50)], [("polyester", 100)]),
        garment("V1", "p6", "val", [("silk", 100)], [("viscose", 100)]),               # val/test-only material: silk
        garment("X1", "p7", "test", [("silk", 60), ("cotton", 40)], [("silk", 100)]),
        *extra])


def request(forbidden=(), **soft):
    s = {k: None for k in SOFT_FIELDS}
    s.update(soft)
    return {"target_segment": "women", "detail_category": "trousers",
            "hard_constraints": {"forbidden_materials": sorted(forbidden)}, "soft_preferences": s, "warnings": []}


def surface(mats, name="shell", cid="c0"):
    return [{"component_id": cid, "source_component_index": 0, "component_class": "surface_component",
             "component_name_normalized": name, "materials": [{"material": m, "pct": float(p)} for m, p in mats]}]
