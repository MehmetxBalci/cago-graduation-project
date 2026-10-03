"""Fit/length text-evidence audit tests (synthetic + dataset-level)."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import pytest

from cago.audits.fit_length_audit import build_fit_length_audit, leakage_check, recommend
from cago.audits.fit_length_evidence import build_evidence, evaluate_text, parse_function_text


def ev(name=None, desc=None, func=None):
    return evaluate_text(name, desc, func)


def test_structured_fit_and_length_parsed():
    r = ev(func="Fit: Slim fit | length: Long | Pockets: With Pockets")
    assert (r["fit_label"], r["fit_label_source"]) == ("slim", "structured")
    assert (r["length_label"], r["length_label_source"]) == ("long", "structured")
    kv, other = parse_function_text("・Fit: Oversized | Sock Fit: Regular | description: A | note")
    assert ("fit", "Oversized") in kv and ("sock fit", "Regular") in kv and other == "A | note"


def test_sleeve_length_and_free_long_never_label_length():
    r = ev(name="Long Sleeve Tee", desc="A long dress with long sleeves", func="sleeve_length: Long sleeve")
    assert r["length_label"] is None and r["length_status"] == "none" and "long" in r["length_weak_terms"]


def test_regular_and_standard_not_inferred_from_absence():
    r = ev(name="Plain tee", desc="soft cotton", func="Fit: Slim fit")
    assert r["length_label"] is None and r["length_status"] == "none"
    empty = ev()
    assert empty["fit_label"] is None and empty["length_label"] is None
    assert empty["fit_status"] == empty["length_status"] == "none"
    assert ev(func="length: Regular length")["length_label"] == "standard"
    assert ev(desc="regular length hem")["length_label_source"] == "phrase"


def test_multiple_structured_values_conflict_label_none():
    r = ev(func="length: Long, Regular length")
    assert r["length_label"] is None and r["length_status"] == "structured_conflict"
    r = ev(func="Fit: Loose fit, Skinny fit")        # mapped + unmapped -> conflict, no label
    assert r["fit_label"] is None and r["fit_status"] == "structured_conflict"
    assert ev(func="Fit: Relaxed, Relaxed fit")["fit_label"] == "relaxed"      # same label twice is fine


def test_weak_bare_terms_do_not_label():
    r = ev(name="Selvedge Slim Straight Jeans", desc="slim cut, regular price, loose threads")
    assert r["fit_label"] is None and {"slim", "regular", "loose"} <= set(r["fit_weak_terms"])
    assert ev(desc="skinny straps")["fit_label"] is None


def test_phrase_and_name_term_evidence():
    r = ev(name="Slim Fit Oxford Shirt")
    assert (r["fit_label"], r["fit_label_source"]) == ("slim", "phrase")
    assert ev(name="Oversized Parka")["fit_label"] == "oversized"
    assert ev(name="Ribbed Cropped Bra Top")["length_label"] == "cropped"
    assert ev(name="Cropped Sleeveless Top")["length_label"] == "cropped"
    assert ev(name="Cropped Sleeve Jacket")["length_label"] is None            # sleeve, not hem length
    assert ev(desc="cropped sleeves stay hidden")["length_label"] is None
    assert ev(desc="a cropped length top")["length_label"] == "cropped"


def test_structured_is_authoritative_and_conflicts_reported():
    r = ev(name="Slim Fit Shirt", func="Fit: Regular fit")
    assert r["fit_label"] == "regular" and r["fit_cross_source_conflict"] is True
    r = ev(desc="also available as slim fit", func="Fit: Loose fit")   # unmapped structured blocks phrase labelling
    assert r["fit_label"] is None and r["fit_status"] == "structured_unmapped"
    assert r["fit_structured_unmapped"] == ["loose fit"]
    r = ev(name="Slim Fit Relaxed Fit Combo")
    assert r["fit_label"] is None and r["fit_status"] == "phrase_conflict"


def test_raw_phrase_hits_by_source():
    r = ev(name="Wide-leg trousers", desc="ankle length, tapered", func="style: Straight leg | Fit: Slim fit")
    hits = set(r["raw_phrase_hits"])
    assert {"wide leg@name", "ankle length@description", "tapered@description", "straight leg@function",
            "slim fit@function"} <= hits


def _label_stats(train, val, test, tp=None):
    mk = lambda n, p: {"garments": n, "parents": p if p is not None else n, "share_of_split_pct": 0}
    return {"per_split": {"train": mk(train, tp), "val": mk(val, None), "test": mk(test, None)}}


def test_recommendation_uses_train_support_and_merge_hypothesis():
    stats = {"slim": _label_stats(5000, 100, 100), "skinny": _label_stats(100, 5000, 5000),
             "regular": _label_stats(5000, 10, 100), "relaxed": _label_stats(600, 60, 60, tp=100)}
    assert recommend("skinny", "fit", stats)["recommendation"] == "MERGE"          # large val/test cannot rescue a small train
    assert recommend("skinny", "fit", stats)["merge_into"] == "slim"
    assert recommend("slim", "fit", stats)["recommendation"] == "KEEP"
    assert recommend("regular", "fit", stats)["recommendation"] == "REMOVE_FROM_V1"  # val too small for evaluation
    assert recommend("relaxed", "fit", stats)["recommendation"] == "REMOVE_FROM_V1"  # too few parents
    assert recommend("cropped", "length", {"cropped": _label_stats(10, 99, 99)})["recommendation"] == "REMOVE_FROM_V1"


def _synthetic_ev(rows):
    """rows: (parent, product_name, function_text, split)."""
    g = pd.DataFrame([{"garment_id": f"g{i}", "parent_product_id": p, "detail_category": "trousers", "product_name": n,
                       "raw_description_text": None, "raw_function_text": f} for i, (p, n, f, _) in enumerate(rows)])
    sm = pd.DataFrame({"garment_id": g["garment_id"], "split": [r[3] for r in rows]})
    return build_evidence(g, sm)


def test_leakage_and_consistency_checks():
    rows = [("p1", "A", "Fit: Slim fit", "train"), ("p1", "A", "Fit: Slim fit", "train"),
            ("p2", "B", "Fit: Regular fit", "val"), ("p3", "C", "Fit: Regular fit", "test")]
    e = _synthetic_ev(rows)
    assert leakage_check(e)["parent_leakage"] is False
    e.loc[2, "split"] = "train"
    e.loc[3, "parent_product_id"] = "p2"           # p2 now in train and test
    assert leakage_check(e)["parent_leakage"] is True and leakage_check(e)["parents_in_multiple_splits"] == 1
    inc = _synthetic_ev([("p1", "A", "Fit: Slim fit", "train"), ("p1", "A", "Fit: Regular fit", "train")])
    assert leakage_check(inc)["train_parents_with_inconsistent_labels_across_variants"]["fit"] == 1


def test_synthetic_audit_runs_end_to_end():
    rows = [(f"p{i}", "Slim Fit Shirt" if i % 2 else "Tee", "Fit: Slim fit" if i % 2 else "length: Regular length",
             ["train", "val", "test"][i % 3]) for i in range(30)]
    a = build_fit_length_audit(_synthetic_ev(rows))
    assert a["garments"] == 30 and a["leakage"]["parent_leakage"] is False
    assert {r["label"] for r in a["recommendations"]["fit"]} == {"skinny", "slim", "regular", "relaxed", "oversized"}
    assert {r["label"] for r in a["recommendations"]["length"]} == {"cropped", "standard", "long"}
    assert all(r["recommendation"] in {"KEEP", "MERGE", "REMOVE_FROM_V1"} for d in ("fit", "length")
               for r in a["recommendations"][d])


PROCESSED = Path(os.environ.get("CAGO_PROCESSED_DIR") or Path(__file__).resolve().parents[1] / "data" / "processed")


@pytest.mark.skipif(not (PROCESSED / "fit_length_evidence.parquet").exists(), reason="fit/length outputs missing")
def test_real_fit_length_outputs_are_consistent():
    e = pd.read_parquet(PROCESSED / "fit_length_evidence.parquet")
    sm = pd.read_parquet(PROCESSED / "split_mapping.parquet")
    a = json.loads((PROCESSED / "fit_length_audit.json").read_text(encoding="utf-8"))
    assert len(e) == len(sm) and e["garment_id"].is_unique
    assert dict(zip(e["garment_id"], e["split"])) == dict(zip(sm["garment_id"], sm["split"]))
    assert a["leakage"]["parent_leakage"] is False and leakage_check(e)["parent_leakage"] is False
    for dim in ("fit", "length"):
        lab = e[f"{dim}_label"].notna()
        assert (e.loc[lab, f"{dim}_status"].isin(["labeled_structured", "labeled_phrase"])).all()
        assert (e.loc[~e[f"{dim}_any_strong_evidence"], f"{dim}_label"].isna()).all()     # no label without strong evidence
        assert a["dimensions"][dim]["labeled"]["train"]["garments"] == int((lab & (e["split"] == "train")).sum())
    std = e[e["length_label"] == "standard"]
    assert all(any(("regular length" in m or ":standard" in m) for m in ms) for ms in std["length_raw_matches"])
    assert set(json.loads((PROCESSED / "fit_length_patterns.json").read_text(encoding="utf-8"))["fit"]["labels"]) == \
        {"skinny", "slim", "regular", "relaxed", "oversized"}
