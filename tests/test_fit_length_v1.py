"""Fit/Length V1 integration tests: vocabulary, evidence priority, representation fields, strict schema, capabilities."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import pytest

from cago.config.fit_length_v1 import FIT_LABELS_V1, LENGTH_LABELS_V1
from cago.preprocessing.split import assert_no_leakage
from cago.representation.builder import build_representation, fit_length_hash
from cago.representation.fit_length import evaluate_fit_length_v1 as ev
from cago.requirements.capabilities import (fit_length_support, is_supported, load_capabilities, revise_capabilities)
from cago.requirements.validation import RequirementContext, validate_request

CAPS = load_capabilities()
CTX = RequirementContext(target_segments=frozenset({"women"}), categories=frozenset(CAPS["categories"]),
                         materials=frozenset({"cotton"}), capabilities=CAPS)
BASE = {"target_segment": "women", "detail_category": "trousers"}


# ---------------- vocabulary / merges
def test_v1_vocabularies_are_frozen():
    assert FIT_LABELS_V1 == ("slim", "regular", "relaxed", "oversized") and LENGTH_LABELS_V1 == ("standard", "long")


@pytest.mark.parametrize("func", ["Fit: Skinny fit", "Fit: Super Skinny Fit", "Fit: Skinny"])
def test_skinny_merges_into_slim(func):
    r = ev(None, None, func)
    assert (r["fit_label"], r["fit_label_source"], r["fit_status"]) == ("slim", "structured", "labeled_structured")
    assert r["fit_merged_from"] == ["skinny->slim"] and r["fit_label_via_merge_only"] is True
    assert r["fit_evidence_confidence"] == "high"
    native = ev(None, None, "Fit: Slim fit, Skinny fit")             # same V1 label from two raw values: not a conflict
    assert native["fit_label"] == "slim" and native["fit_label_via_merge_only"] is False and not native["fit_conflict"]
    assert ev("Skinny Fit Jeans", None, None)["fit_label"] == "slim"      # phrase evidence merges too


@pytest.mark.parametrize("func", ["Fit: Loose fit", "Fit: Loose"])
def test_loose_merges_into_relaxed(func):
    r = ev(None, None, func)
    assert r["fit_label"] == "relaxed" and r["fit_merged_from"] == ["loose->relaxed"] and r["fit_label_via_merge_only"]
    p = ev("Loose Fit Hoodie", None, None)
    assert (p["fit_label"], p["fit_label_source"], p["fit_evidence_confidence"]) == ("relaxed", "phrase", "medium")
    assert "skinny" not in FIT_LABELS_V1 and "loose" not in FIT_LABELS_V1


def test_cropped_excluded_from_v1_labels():
    r = ev(None, None, "length: Cropped")
    assert r["length_label"] is None and r["length_status"] == "structured_unsupported_v1"
    assert r["length_unsupported_evidence"] == ["cropped"] and r["length_evidence_confidence"] is None
    p = ev("Cropped Tee", None, None)
    assert p["length_label"] is None and p["length_status"] == "phrase_unsupported_v1"
    m = ev(None, None, "length: Long, Cropped")                       # mixed with a V1 label -> conflict, unlabeled
    assert m["length_label"] is None and m["length_status"] == "structured_conflict" and m["length_conflict"]
    c = ev("Cropped Tee", "regular length hem", None)               # cropped contradicts standard -> conflict
    assert c["length_label"] is None and c["length_status"] == "phrase_conflict"
    s = ev("Cropped Tee", None, "length: Regular length")            # structured still wins; contradiction is recorded
    assert s["length_label"] == "standard" and s["length_cross_source_conflict"] and s["length_unsupported_evidence"] == ["cropped"]


# ---------------- evidence priority / conflicts / no inference
def test_structured_evidence_has_priority_over_phrases():
    r = ev("Slim Fit Shirt", None, "Fit: Regular fit")
    assert (r["fit_label"], r["fit_label_source"]) == ("regular", "structured") and r["fit_cross_source_conflict"]
    assert r["fit_evidence_confidence"] == "high"
    assert any(e.startswith("phrase:name:") for e in r["fit_raw_evidence"]) and "structured:fit:regular fit" in r["fit_raw_evidence"]
    u = ev("Slim Fit Shirt", None, "Fit: Tight")                      # unmapped structured must not be overwritten
    assert u["fit_label"] is None and u["fit_status"] == "structured_unmapped" and u["fit_evidence_confidence"] is None


def test_conflicts_remain_unlabeled_and_preserved():
    f = ev(None, None, "Fit: Slim fit, Relaxed fit")
    assert f["fit_label"] is None and f["fit_status"] == "structured_conflict" and f["fit_conflict"]
    assert f["fit_conflict_labels"] == ["relaxed", "slim"] and f["fit_label_source"] is None
    lg = ev(None, None, "length: Long, Regular length")
    assert lg["length_label"] is None and lg["length_conflict_labels"] == ["long", "standard"]
    p = ev("Slim Fit Relaxed Fit Combo", None, None)
    assert p["fit_label"] is None and p["fit_status"] == "phrase_conflict" and p["fit_evidence_confidence"] is None


def test_no_label_from_absence_or_weak_terms():
    e = ev("Plain tee", "regular price, slim straps, long sleeves, loose threads", "sleeve_length: Long sleeve")
    assert e["fit_label"] is None and e["length_label"] is None
    assert e["fit_status"] == e["length_status"] == "none"
    assert e["fit_evidence_confidence"] is None and e["length_evidence_confidence"] is None
    assert ev(None, None, "length: Regular length")["length_label"] == "standard"            # explicit only


def test_confidence_mapping():
    assert ev(None, None, "Fit: Regular")["fit_evidence_confidence"] == "high"
    assert ev("Regular Fit Tee", None, None)["fit_evidence_confidence"] == "medium"
    assert ev(None, "regular length", None)["length_evidence_confidence"] == "medium"
    for r in (ev(None, None, "Fit: Slim fit, Loose fit"), ev(None, None, "length: Cropped"), ev(None, None, None)):
        assert r["fit_evidence_confidence"] is None and r["length_evidence_confidence"] is None
    assert set(filter(None, [ev(None, None, "Fit: Slim")["fit_evidence_confidence"]])) <= {"high", "medium"}


# ---------------- representation fields
def _tables(func, name="Tee"):
    comps = pd.DataFrame([{"component_id": "c1", "garment_id": "g1", "component_index": 0,
                           "component_class": "surface_component", "component_name_normalized": "shell",
                           "validation_status": "valid", "pct_sum_calculated": 100.0}])
    mats = pd.DataFrame([{"component_id": "c1", "garment_id": "g1", "material_index": 0, "material_raw": "cotton",
                          "material_canonical": "cotton", "pct": 100.0}])
    g = pd.DataFrame([{"garment_id": "g1", "source_row_number": 1, "parent_product_id": "p1", "gender_section": "women",
                       "parent_category": "bottoms", "detail_category": "trousers", "variant_colour_normalized": "black",
                       "product_name": name, "raw_description_text": None, "raw_function_text": func}])
    sm = pd.DataFrame([{"garment_id": "g1", "split": "train"}])
    vocab = {"canonical_to_token": {"cotton": "cotton"}, "count_table": []}
    return g, comps, mats, sm, vocab


def test_representation_has_fit_length_fields():
    rep = build_representation(*_tables("Fit: Skinny fit | length: Regular length"))
    r = rep.iloc[0]
    for col in ("fit_label", "fit_label_source", "fit_status", "fit_evidence_confidence", "length_label",
                "length_label_source", "length_status", "length_evidence_confidence", "fit_conflict", "fit_merged_from",
                "fit_raw_evidence", "length_raw_evidence", "length_unsupported_evidence"):
        assert col in rep.columns, col
    assert (r.fit_label, r.fit_label_source, r.fit_status, r.fit_evidence_confidence) == ("slim", "structured", "labeled_structured", "high")
    assert (r.length_label, r.length_status) == ("standard", "labeled_structured")
    none = build_representation(*_tables(None)).iloc[0]
    assert none.fit_label is None and none.length_label is None and none.fit_status == "none"
    assert fit_length_hash(rep) == fit_length_hash(build_representation(*_tables("Fit: Skinny fit | length: Regular length")))


# ---------------- strict requirement schema
def test_removed_values_rejected_and_v1_values_accepted():
    for fld, val, hint in (("fit", "skinny", "slim"), ("fit", "Skinny", "slim"), ("fit", "loose", "relaxed"),
                           ("length_cut", "cropped", None)):
        r = validate_request({**BASE, fld: val}, CTX)
        assert not r.ok and r.error_codes() == ["removed_in_v1"], (fld, val)
        assert hint is None or repr(hint) in r.errors[0].message
    for fit in FIT_LABELS_V1:
        assert validate_request({**BASE, "fit": fit}, CTX).ok
    for ln in LENGTH_LABELS_V1:
        assert validate_request({**BASE, "length_cut": ln}, CTX).ok
    assert "invalid_value" in validate_request({**BASE, "fit": "baggy"}, CTX).error_codes()


# ---------------- train-only capability decisions
def _rep(rows):
    return pd.DataFrame(rows, columns=["detail_category", "split", "parent_product_id", "fit_label", "length_label"])


def _caps(fit=True, length=True):
    return {"categories": {"cat": {"parent_category": "x", "controls": {"fit": fit, "length_cut": length}}}}


def test_capability_decisions_use_train_only():
    rows = [("cat", "train", f"p{i}", "regular", None) for i in range(10)]                   # weak train support
    rows += [("cat", sp, f"{sp}{i}", "regular", "long") for sp in ("val", "test") for i in range(500)]   # huge val/test
    new, changes = revise_capabilities(_caps(), fit_length_support(_rep(rows)), 100, 50)
    assert new["categories"]["cat"]["controls"] == {"fit": False, "length_cut": False}
    assert {c["control"] for c in changes} == {"fit", "length_cut"}
    assert new["fit_length_v1"]["basis"].startswith("TRAIN")
    sup = fit_length_support(_rep(rows))["cat"]["fit"]["regular"]
    assert sup == {"garments": 10, "parents": 10}                                         # val/test never counted
    train_rows = [("cat", "train", f"p{i}", "relaxed", "long") for i in range(120)]
    new2, ch2 = revise_capabilities(_caps(), fit_length_support(_rep(train_rows)), 100, 50)
    assert new2["categories"]["cat"]["controls"] == {"fit": True, "length_cut": True} and ch2 == []


def test_capability_revision_is_disable_only_and_idempotent():
    rows = [("cat", "train", f"p{i}", "slim", "long") for i in range(200)]
    caps = _caps(fit=False, length=True)                                                   # fit disabled by design
    new, _ = revise_capabilities(caps, fit_length_support(_rep(rows)), 100, 50)
    assert new["categories"]["cat"]["controls"]["fit"] is False                            # supported but NOT auto-enabled
    assert [r["control"] for r in new["fit_length_v1"]["supported_but_disabled_by_design"]] == ["fit"]
    again, ch = revise_capabilities(new, fit_length_support(_rep(rows)), 100, 50)
    assert again["categories"] == new["categories"] and ch == []
    assert is_supported({"slim": {"garments": 100, "parents": 50}}) and not is_supported({"slim": {"garments": 100, "parents": 49}})


def test_parent_leakage_remains_zero_synthetic():
    m = pd.DataFrame({"garment_id": ["a", "b", "c"], "parent_product_id": ["p1", "p1", "p2"],
                      "split": ["train", "train", "val"]})
    assert_no_leakage(m)


# ---------------- dataset-level
PROCESSED = Path(os.environ.get("CAGO_PROCESSED_DIR") or Path(__file__).resolve().parents[1] / "data" / "processed")


@pytest.mark.skipif(not (PROCESSED / "garment_representation.parquet").exists(), reason="representation outputs missing")
def test_real_representation_fit_length_v1():
    rep = pd.read_parquet(PROCESSED / "garment_representation.parquet")
    a = json.loads((PROCESSED / "representation_audit.json").read_text(encoding="utf-8"))
    assert set(rep["fit_label"].dropna()) <= set(FIT_LABELS_V1) and set(rep["length_label"].dropna()) <= set(LENGTH_LABELS_V1)
    assert not rep["length_label"].eq("cropped").any() and not rep["fit_label"].isin(["skinny", "loose"]).any()
    for dim in ("fit", "length"):
        lab = rep[f"{dim}_label"].notna()
        assert (rep.loc[~lab, f"{dim}_evidence_confidence"].isna()).all()
        assert rep.loc[lab, f"{dim}_evidence_confidence"].isin(["high", "medium"]).all()
        assert (rep.loc[lab, f"{dim}_label_source"].isin(["structured", "phrase"])).all()
        assert (rep.loc[~lab, f"{dim}_label_source"].isna()).all()
        assert (rep.loc[rep[f"{dim}_conflict"], f"{dim}_label"].isna()).all()
        assert a["fit_length_v1"][dim]["labeled"]["train"]["garments"] == int((lab & (rep["split"] == "train")).sum())
    assert a["split"]["parent_leakage_count"] == 0
    assert_no_leakage(rep[["garment_id", "parent_product_id", "split"]])


@pytest.mark.skipif(not (PROCESSED / "garment_representation.parquet").exists(), reason="representation outputs missing")
def test_real_capabilities_consistent_with_train_support():
    rep = pd.read_parquet(PROCESSED / "garment_representation.parquet")
    caps = json.loads((PROCESSED / "category_capabilities.json").read_text(encoding="utf-8"))
    support = fit_length_support(rep)
    assert caps == load_capabilities()                                                    # processed copy == package source
    for cat, entry in caps["categories"].items():
        for ctrl in ("fit", "length_cut"):
            if entry["controls"][ctrl]:
                assert is_supported(support[cat][ctrl]), (cat, ctrl)                      # enabled => TRAIN support
            assert entry["fit_length_support_train"][ctrl] == support[cat][ctrl]
