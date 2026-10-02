"""Integrity tests. Unit tests use synthetic data; dataset tests run the pipeline on the real files
(set CAGO_INPUT and CAGO_SUPPORT_DIR, otherwise skipped)."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import pytest

from cago.preprocessing.colours import is_exact_black, normalize_colour
from cago.preprocessing.ids import stable_hash
from cago.preprocessing.materials import MaterialMapper
from cago.preprocessing.split import assert_no_leakage, assign_splits
from cago.preprocessing.validation import validate_component

INPUT = os.environ.get("CAGO_INPUT")
SUPPORT = os.environ.get("CAGO_SUPPORT_DIR")
needs_data = pytest.mark.skipif(not (INPUT and SUPPORT), reason="CAGO_INPUT / CAGO_SUPPORT_DIR not set")


# ---------- unit tests ----------
def test_stable_hash_is_deterministic_and_not_builtin_hash():
    assert stable_hash("a", 1) == stable_hash("a", 1)
    assert stable_hash("a", 1) != stable_hash("a", 2)


@pytest.mark.parametrize("vals,status,valid", [
    ([60, 40], "valid", True), ([98.9, 0], "percentage_out_of_tolerance", False),
    ([99, 0], "valid", True), ([60.5, 40.5], "valid", True), ([0, 0], "zero_sum_component", False),
    ([60, None], "missing_percentage", False), ([60, "x"], "invalid_percentage", False),
    ([150], "invalid_percentage", False), ([-5, 105], "invalid_percentage", False), ([], "missing_percentage", False),
])
def test_validate_component(vals, status, valid):
    _, pv, st = validate_component(vals)
    assert (st, pv) == (status, valid)


def test_colour_normalization_and_exact_black():
    assert normalize_colour("  BLACK ") == "black"
    assert normalize_colour("Black   /  White") == "black / white"
    assert normalize_colour(None) is None
    assert is_exact_black("black")
    for c in ("black/white", "washed black", "blackberry", None):
        assert not is_exact_black(normalize_colour(c))


def test_unknown_material_not_silently_mapped():
    mp = MaterialMapper({"cotton": "cotton", "pes": "polyester", "polyester": "polyester"})
    assert mp.map("Cotton")[2] == "mapped_source_canonical"
    assert mp.map("PES")[2] == "mapped_source_alias"
    assert mp.map("unobtainium") == (None, "unknown", "unmapped")
    assert mp.map(None)[2] == "missing_material"


def test_split_keeps_parents_together_and_is_deterministic():
    g = pd.DataFrame({"garment_id": [f"g{i}" for i in range(1000)],
                      "parent_product_id": [str(i // 3) for i in range(1000)]})
    a, b = assign_splits(g), assign_splits(g)
    assert a.equals(b)
    assert_no_leakage(a)
    bad = a.copy(); bad.loc[0, "split"] = "test"; bad.loc[1, "split"] = "train"
    with pytest.raises(AssertionError):
        assert_no_leakage(bad)


def test_split_without_ids_for_missing_parent():
    g = pd.DataFrame({"garment_id": ["a", "b"], "parent_product_id": [None, None]})
    assert len(assign_splits(g)) == 2


# ---------- fix tests (synthetic end-to-end) ----------
def _synthetic_tables(tmp_path, rows):
    from cago.preprocessing.pipeline import build_tables
    (tmp_path / "4_material_normalization_table.csv").write_text(
        "mapping_type,canonical_material_name,raw_labels_joined,n_raw_labels\n"
        "canonical_group,polyester,polyester ; pes,2\ncanonical_group,cotton,cotton,1\n", encoding="utf-8")
    src = tmp_path / "in.jsonl"
    src.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return build_tables(src, tmp_path)


def _rec(parent="p1", colour="Black", mats=None):
    mats = mats or [{"material": "cotton", "pct": 100.0, "recycled_pct": None}]
    return {"parent_product_id": parent, "brand": "hm", "region": "uk", "url": f"u{parent}", "variant_colour": colour,
            "components_structured": [{"component_path_raw": "Shell", "component_name_norm": "shell",
                                       "component_class": "surface_component", "materials": mats,
                                       "pct_sum": 100.0, "pct_sum_flag": "ok"}]}


def test_recycled_info_only_when_status_ok(tmp_path):
    def m(rec):  # one material, pct 100
        return [{"material": "cotton", "pct": 100.0, "recycled_pct": rec}]
    t = _synthetic_tables(tmp_path, [_rec("a", mats=m(None)), _rec("b", mats=m(50.0)), _rec("c", mats=m("abc")),
                                     _rec("d", mats=m(150.0)), _rec("e", mats=m(0.0))])
    got = dict(zip(t["garments"]["parent_product_id"], t["garments"]["has_recycled_content_information"]))
    assert got == {"a": False, "b": True, "c": False, "d": False, "e": True}  # 0.0 is a real value; invalid is not info
    cm = t["component_materials"]
    assert cm["recycled_pct"].isna().sum() == 3  # null/invalid stay NULL, never 0


def test_unique_material_raw_and_canonical_counts(tmp_path):
    mats = [{"material": "polyester", "pct": 40.0, "recycled_pct": None},
            {"material": "pes", "pct": 30.0, "recycled_pct": None},
            {"material": "unobtainium", "pct": 30.0, "recycled_pct": None}]
    t = _synthetic_tables(tmp_path, [_rec(mats=mats)])
    g, cm = t["garments"], t["component_materials"]
    assert "unique_material_count" not in g.columns
    assert g.loc[0, "unique_material_raw_count"] == 3
    assert g.loc[0, "unique_material_canonical_count"] == 1       # unmapped is not counted/invented
    assert cm["material_canonical"].tolist()[:2] == ["polyester", "polyester"]
    assert pd.isna(cm.loc[2, "material_canonical"])
    assert cm.loc[2, "material_mapping_status"] == "unmapped"


def test_duplicate_key_reporting(tmp_path):
    rows = [_rec("a")] * 3 + [_rec("b")] + [_rec("c")] * 2
    t = _synthetic_tables(tmp_path, rows)
    assert t["duplicate_stats"] == {"duplicate_key_groups": 2, "rows_in_duplicate_key_groups": 5,
                                    "duplicate_extra_rows": 3}
    assert len(t["garments"]) == 6 and t["garments"]["garment_id"].is_unique  # nothing deleted


def test_split_numeric_parent_ids_are_valid_groups():
    n = 900
    g = pd.DataFrame({"garment_id": [f"g{i}" for i in range(n)],
                      "parent_product_id": pd.Series([i // 3 for i in range(n)], dtype=object)})
    out = assign_splits(g)
    assert out.groupby("parent_product_id")["split"].nunique().max() == 1
    assert out["split"].nunique() == 3
    g2 = g.copy()
    g2["parent_product_id"] = [float(i // 3) for i in range(n)]       # float scalar IDs also valid
    assert assign_splits(g2).groupby("parent_product_id")["split"].nunique().max() == 1


def test_split_missing_parent_ids_are_independent_groups():
    n = 600
    ids = [None if i % 2 else i // 2 for i in range(n)]   # None, and NaN below
    g = pd.DataFrame({"garment_id": [f"g{i}" for i in range(n)], "parent_product_id": pd.Series(ids, dtype=object)})
    out = assign_splits(g)
    missing = out[out["parent_product_id"].isna()]
    assert missing["split"].nunique() == 3                # not lumped into one "None" group
    g["parent_product_id"] = pd.Series([float("nan") if i % 2 else i // 2 for i in range(n)], dtype=object)
    assert assign_splits(g)[g["parent_product_id"].isna()]["split"].nunique() == 3


# ---------- dataset tests ----------
@pytest.fixture(scope="module")
def res(tmp_path_factory):
    from cago.preprocessing.run import run
    return run(Path(INPUT), Path(SUPPORT), tmp_path_factory.mktemp("out"))


@needs_data
def test_garment_count_equals_valid_json(res):
    n_valid = 0
    with open(INPUT, encoding="utf-8-sig") as fh:
        for line in fh:
            if line.strip():
                try:
                    json.loads(line); n_valid += 1
                except json.JSONDecodeError:
                    pass
    assert len(res["garments"]) == n_valid == res["audit"]["counts"]["valid_json_records"]


@needs_data
def test_ids_unique_and_references_valid(res):
    g, c, m = res["garments"], res["components"], res["component_materials"]
    assert g["garment_id"].is_unique and c["component_id"].is_unique
    assert g["source_row_number"].is_unique
    assert c["garment_id"].isin(g["garment_id"]).all()
    assert m["component_id"].isin(c["component_id"]).all()
    assert m["garment_id"].isin(g["garment_id"]).all()
    # component_materials garment_id must agree with the component's garment_id
    chk = m.merge(c[["component_id", "garment_id"]], on="component_id", suffixes=("", "_c"))
    assert (chk["garment_id"] == chk["garment_id_c"]).all()


@needs_data
def test_ids_reproducible_across_runs(res, tmp_path):
    from cago.preprocessing.run import run
    r2 = run(Path(INPUT), Path(SUPPORT), tmp_path)
    assert res["garments"]["garment_id"].tolist() == r2["garments"]["garment_id"].tolist()
    assert res["components"]["component_id"].tolist() == r2["components"]["component_id"].tolist()


@needs_data
def test_percentages_numeric_and_recycled_null_preserved(res):
    m = res["component_materials"]
    assert pd.api.types.is_float_dtype(m["pct"]) and pd.api.types.is_float_dtype(m["recycled_pct"])
    assert (m["pct"].dropna().between(0, 100)).all()
    assert m["recycled_pct"].isna().sum() > 0          # NULL not coerced to 0
    assert m["recycled_pct"].isna().sum() == (m["recycled_pct_status"] == "missing").sum()


@needs_data
def test_pct_valid_matches_independent_recomputation(res):
    c, m = res["components"], res["component_materials"]
    s = m.groupby("component_id")["pct"].sum(min_count=1)
    c2 = c.set_index("component_id")
    ok = (s.reindex(c2.index) - c2["pct_sum_calculated"]).abs().fillna(0) < 1e-9
    assert ok.all()
    expect = c2["pct_sum_calculated"].between(99, 101) & ~c2["validation_status"].isin(
        ["invalid_percentage", "missing_percentage"])
    assert (expect == c2["pct_valid"]).all()


@needs_data
def test_parent_product_id_not_assumed_unique(res):
    g = res["garments"]
    assert g["parent_product_id"].duplicated().any()  # test documents reality; pipeline must not dedupe
    assert g["garment_id"].is_unique


@needs_data
def test_no_silent_material_mapping(res):
    m = res["component_materials"]
    um = m[m["material_mapping_status"] == "unmapped"]
    assert um["material_canonical"].isna().all() and (um["material_family"] == "unknown").all()
    assert set(um["material_raw"]) == set(res["unmapped"]["material_raw"])
    assert m.loc[m["material_mapping_status"] != "unmapped", "material_canonical"].notna().all()


@needs_data
def test_exact_black_no_substring_matching(res):
    g = res["garments"]
    assert (g.loc[g["is_exact_black"], "variant_colour_normalized"] == "black").all()
    assert not g.loc[~g["is_exact_black"], "variant_colour_normalized"].eq("black").any()


@needs_data
def test_zero_parent_leakage_and_full_coverage(res):
    sm, g = res["split_mapping"], res["garments"]
    assert_no_leakage(sm)
    assert set(sm["garment_id"]) == set(g["garment_id"]) and len(sm) == len(g)
    assert sm.groupby("parent_product_id")["split"].nunique().max() == 1


@needs_data
def test_new_columns_and_recycled_flag_on_real_data(res):
    g, m = res["garments"], res["component_materials"]
    assert "unique_material_count" not in g.columns
    assert {"unique_material_raw_count", "unique_material_canonical_count"} <= set(g.columns)
    assert (g["unique_material_canonical_count"] <= g["unique_material_raw_count"]).all()
    ok_garments = set(m.loc[m["recycled_pct_status"] == "ok", "garment_id"])
    assert set(g.loc[g["has_recycled_content_information"], "garment_id"]) == ok_garments
    d = res["audit"]["counts"]
    assert d["duplicate_extra_rows"] == d["rows_in_duplicate_key_groups"] - d["duplicate_key_groups"]
    assert d["duplicate_extra_rows"] == len(g) - len(g.drop_duplicates(
        ["brand", "region", "parent_product_id", "url", "variant_colour_raw"]))
