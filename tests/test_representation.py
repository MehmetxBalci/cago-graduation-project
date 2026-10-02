"""Garment representation + vocabulary tests (synthetic) and dataset-level checks."""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest

from cago.preprocessing.split import assert_no_leakage, assign_splits
from cago.representation.builder import build_representation, is_usable, representation_hash, sort_materials
from cago.representation.vocabulary import fit_vocabulary, mapping_table, token_for


def _vocab(rows, split, min_count=2, known=()):
    mr = pd.DataFrame(rows, columns=["garment_id", "material_canonical"])
    sm = pd.DataFrame(split, columns=["garment_id", "split"])
    return fit_vocabulary(mr, sm, min_count, known)


def test_vocabulary_is_train_only_and_rare_to_other():
    rows = [("g1", "cotton")] * 3 + [("g2", "polyester")] * 2 + [("g3", "silk")] * 1 \
        + [("v1", "wool")] * 10 + [("t1", "wool")] * 10 + [("v2", "cotton")] * 5
    split = [("g1", "train"), ("g2", "train"), ("g3", "train"), ("v1", "val"), ("t1", "test"), ("v2", "val")]
    v = _vocab(rows, split, min_count=2, known=["linen", "wool"])
    assert v["fit_split"] == "train" and v["n_train_garments"] == 3
    assert v["tokens"][:2] == ["PAD", "OTHER"] and set(v["tokens"][2:]) == {"cotton", "polyester"}
    assert token_for("silk", v) == "OTHER"                # rare (1 < 2)
    assert token_for("wool", v) == "OTHER"                # frequent only in val/test -> must not enter vocab
    assert token_for("linen", v) == "OTHER" and token_for(None, v) == "OTHER"
    reasons = {r["material_canonical"]: r["token_reason"] for r in v["count_table"]}
    assert reasons["silk"] == "rare_in_train" and reasons["wool"] == "unseen_in_train" and reasons["cotton"] == "in_vocab"
    cnt = {r["material_canonical"]: r["train_occurrences"] for r in v["count_table"]}
    assert cnt["cotton"] == 3 and cnt["wool"] == 0       # val/test cotton and wool rows not counted


def test_vocabulary_changes_only_with_train_data_and_threshold_is_configurable():
    rows = [("g1", "cotton")] * 3 + [("g2", "silk")] * 1
    split = [("g1", "train"), ("g2", "train")]
    v1 = _vocab(rows, split, min_count=1)
    assert "silk" in v1["tokens"] and v1["vocabulary_size"] == 4
    assert "silk" not in _vocab(rows, split, min_count=2)["tokens"]
    # adding val/test garments leaves the vocabulary identical
    rows2 = rows + [("v1", "wool")] * 99
    v3 = _vocab(rows2, split + [("v1", "val")], min_count=1)
    assert v3["tokens"] == v1["tokens"] and v3["threshold_sweep"] == v1["threshold_sweep"]
    with pytest.raises(ValueError):
        _vocab(rows, split, min_count=0)
    assert list(mapping_table(v1).columns[:2]) == ["material_canonical", "material_family"]


def test_unspecified_placeholder_never_in_vocab():
    v = _vocab([("g1", "unspecified_material")] * 50, [("g1", "train")], min_count=1)
    assert token_for("unspecified_material", v) == "OTHER"


def test_deterministic_material_ordering():
    a = [{"raw": "Cotton", "canonical": "cotton", "pct": 50.0}, {"raw": "pes", "canonical": "polyester", "pct": 50.0},
         {"raw": "elastane", "canonical": "elastane", "pct": 60.0}]
    b = list(reversed(a))
    assert sort_materials(a) == sort_materials(b)
    assert [m["canonical"] for m in sort_materials(a)] == ["elastane", "cotton", "polyester"]   # pct desc, then name
    c = sort_materials([{"raw": "x", "canonical": None, "pct": 50.0}, {"raw": "a", "canonical": "zinc", "pct": 50.0},
                        {"raw": "n", "canonical": "wool", "pct": None}])
    assert [m["canonical"] for m in c] == ["zinc", None, "wool"]     # unmapped sorts by raw name; null pct last


def test_per_component_percentage_validation():
    assert is_usable("valid", 100.0) and is_usable("valid", 99.0) and is_usable("valid", 101.0)
    assert not is_usable("percentage_out_of_tolerance", 98.9) and not is_usable("zero_sum_component", 0.0)
    assert not is_usable("valid", None) and not is_usable("missing_percentage", float("nan"))


def _tables(mats_by_component, shuffle=False):
    comps, mrows = [], []
    for i, (cid, (cls, name, status, mats)) in enumerate(mats_by_component.items()):
        total = sum(p for _, p in mats)
        comps.append({"component_id": cid, "garment_id": "g1", "component_index": i, "component_class": cls,
                      "component_name_normalized": name, "validation_status": status, "pct_sum_calculated": total})
        for j, (m, p) in enumerate(mats):
            mrows.append({"component_id": cid, "garment_id": "g1", "material_index": j, "material_raw": m,
                          "material_canonical": m if m != "mystery" else None, "pct": p})
    if shuffle:
        mrows = list(reversed(mrows))
        for k, r in enumerate(mrows):  # keep material_index meaning: order within component is by index
            pass
    g = pd.DataFrame([{"garment_id": "g1", "source_row_number": 1, "parent_product_id": "p1", "gender_section": "women",
                       "parent_category": "bottoms", "detail_category": "trousers", "variant_colour_normalized": "black",
                       "product_name": "Quick-dry trousers", "raw_description_text": None, "raw_function_text": None}])
    sm = pd.DataFrame([{"garment_id": "g1", "split": "train"}])
    return g, pd.DataFrame(comps), pd.DataFrame(mrows), sm


def test_representation_active_vs_anomalous_not_repaired():
    spec = {"c1": ("surface_component", "shell", "valid", [("cotton", 60.0), ("elastane", 40.0)]),
            "c2": ("lining_component", "lining", "percentage_out_of_tolerance", [("cotton", 60.0), ("polyester", 38.9)]),
            "c3": ("trim_component", "rib", "valid", [("cotton", 60.0), ("mystery", 40.0)])}
    g, c, m, sm = _tables(spec)
    vocab = _vocab([("g1", "cotton")] * 5 + [("g1", "elastane")] * 5, [("g1", "train")])
    rep = build_representation(g, c, m, sm, vocab)
    r = rep.iloc[0]
    assert r.n_active_components == 2 and r.n_anomalous_components == 1 and not r.is_fully_usable
    assert [x["component_id"] for x in r.components] == ["c1", "c3"]
    assert r.anomalous_components[0]["percentages"] == [60.0, 38.9]            # preserved as-is
    assert r.components[0]["materials"] == ["cotton", "elastane"] and r.components[0]["percentages"] == [60.0, 40.0]
    assert r.components[1]["materials"] == ["cotton", None] and r.components[1]["ml_tokens"] == ["cotton", "OTHER"]
    assert r.has_unmapped_material and r.has_other_token and "quick_dry" in r.text_evidence_tags
    assert r.target_segment == "women" and r.gender_section == "women" and "gender" not in r.index and r.normalized_colour == "black" and r.split == "train" and r.parent_product_id == "p1"
    for comp in r.components:
        assert abs(sum(comp["percentages"]) - 100) <= 1


def test_representation_is_deterministic_and_order_invariant():
    spec = {"c1": ("surface_component", "shell", "valid", [("polyester", 50.0), ("cotton", 50.0)])}
    g, c, m, sm = _tables(spec)
    vocab = _vocab([("g1", "cotton")] * 5 + [("g1", "polyester")] * 5, [("g1", "train")])
    r1 = build_representation(g, c, m, sm, vocab)
    r2 = build_representation(g, c, m.iloc[::-1].reset_index(drop=True), sm, vocab)
    assert representation_hash(r1) == representation_hash(r2) == representation_hash(build_representation(g, c, m, sm, vocab))
    assert r1.iloc[0].components[0]["materials"] == ["cotton", "polyester"]


def test_zero_parent_leakage_synthetic():
    g = pd.DataFrame({"garment_id": [f"g{i}" for i in range(600)],
                      "parent_product_id": [f"p{i // 4}" for i in range(600)]})
    sm = assign_splits(g)
    assert_no_leakage(sm)
    assert sm.groupby("parent_product_id")["split"].nunique().max() == 1


PROCESSED = Path(os.environ.get("CAGO_PROCESSED_DIR") or Path(__file__).resolve().parents[1] / "data" / "processed")


@pytest.mark.skipif(not (PROCESSED / "garment_representation.parquet").exists(), reason="representation outputs missing")
def test_real_representation_integrity():
    import json
    rep = pd.read_parquet(PROCESSED / "garment_representation.parquet")
    g = pd.read_parquet(PROCESSED / "garments.parquet", columns=["garment_id"])
    c = pd.read_parquet(PROCESSED / "components.parquet", columns=["component_id", "garment_id"])
    sm = pd.read_parquet(PROCESSED / "split_mapping.parquet")
    assert len(rep) == len(g) and rep["garment_id"].is_unique and set(rep["garment_id"]) == set(g["garment_id"])
    assert rep["n_active_components"].sum() + rep["n_anomalous_components"].sum() == len(c)
    assert_no_leakage(rep[["garment_id", "parent_product_id", "split"]])
    assert dict(zip(sm["garment_id"], sm["split"])) == dict(zip(rep["garment_id"], rep["split"]))
    for comps in rep["components"]:
        for comp in comps:
            assert abs(comp["pct_sum"] - 100) <= 1 and abs(sum(comp["percentages"]) - comp["pct_sum"]) < 1e-6
            pairs = list(zip(comp["percentages"], comp["materials"]))
            assert all(p >= 0 for p, _ in pairs)
            assert [-p for p, _ in pairs] == sorted(-p for p, _ in pairs)          # pct descending
    v = json.loads((PROCESSED / "ml_material_vocabulary.json").read_text(encoding="utf-8"))
    assert v["fit_split"] == "train" and v["tokens"][:2] == ["PAD", "OTHER"]
    train_ids = set(rep.loc[rep["split"] == "train", "garment_id"])
    recount = {}
    for gid, comps in zip(rep["garment_id"], rep["components"]):
        if gid in train_ids:
            for comp in comps:
                for mat in comp["materials"]:
                    if mat is not None:
                        recount[mat] = recount.get(mat, 0) + 1
    assert {r["material_canonical"]: r["train_occurrences"] for r in v["count_table"]
            if r["train_occurrences"]} == recount
    csv = pd.read_csv(PROCESSED / "material_to_ml_token.csv")
    assert set(csv["ml_token"]) <= set(v["tokens"])


@pytest.mark.skipif(not (PROCESSED / "ml_material_vocabulary.json").exists(), reason="representation outputs missing")
def test_real_vocabulary_default_threshold_keeps_down_and_feather():
    import json
    v = json.loads((PROCESSED / "ml_material_vocabulary.json").read_text(encoding="utf-8"))
    assert v["min_count"] == 30 and {"down", "feather"} <= set(v["tokens"])
    assert v["canonical_to_token"]["down"] == "down" and v["canonical_to_token"]["feather"] == "feather"
