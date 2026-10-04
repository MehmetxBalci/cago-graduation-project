"""Perturbation + Plausibility validation tests (synthetic; TEST used only as evaluation examples)."""
from __future__ import annotations

import pytest

from cago.benchmark.perturbations import PerturbationConfig, load_eval_garments, perturb_garment, public
from cago.benchmark.plausibility_validation import WEIGHTINGS, ordering_tests, run_plausibility_validation, score_levels
from cago.evaluation.config import EvaluationConfig
from cago.evaluation.plausibility import contextual_support, evaluate_plausibility
from cago.generation.distance import topology_preserved
from cago.generation.support_tables import build_support_tables
from tests.synthetic_data import CTX, VOCAB, VOCAB_LIST, garment, make_rep_with_tests

REP = make_rep_with_tests()
SUP = build_support_tables(REP)
GS = load_eval_garments(REP, "test", seed=1)


def levels(g, seed=3):
    return perturb_garment(g, SUP, VOCAB_LIST, CTX, seed)


def test_test_garments_never_enter_train_support_tables():
    assert SUP.splits_used == ("train",) and SUP.n_train_garments == int((REP["split"] == "train").sum())
    rows = REP.to_dict("records") + [garment("EX", "pex", "test", [("linen", 100)], [("linen", 100)], cat="trousers")]
    import pandas as pd
    only_test_material = pd.DataFrame([r for r in rows if r["garment_id"] != "T3"])        # linen now exists in TEST only
    sup = build_support_tables(only_test_material)
    assert "linen" not in sup.allowed("trousers", "surface_component") and "linen" not in sup.materials_by_category["trousers"]
    assert sup.count("trousers", "surface_component", "linen") == 0
    assert all(g.garment_id.startswith("E") for g in GS) and not ({g.garment_id for g in GS} & set(REP.loc[REP["split"] == "train", "garment_id"]))


def test_load_eval_garments_is_clean_deterministic_and_one_per_parent():
    a, b = load_eval_garments(REP, "test", seed=5), load_eval_garments(REP, "test", seed=5)
    assert [g.garment_id for g in a] == [g.garment_id for g in b]
    dup = REP.to_dict("records") + [garment("E1b", "pe1", "test", [("cotton", 60), ("polyester", 40)], [("polyester", 100)])]
    import pandas as pd
    assert len([g for g in load_eval_garments(pd.DataFrame(dup), "test") if g.parent_product_id == "pe1"]) == 1
    assert "X1" not in {g.garment_id for g in a}                                       # silk (non-vocabulary) test garment excluded


def test_perturbation_topology_and_sums_preserved():
    for g in GS:
        for lv, p in levels(g).items():
            assert topology_preserved(public(g.components), p["components"]), (g.garment_id, lv)
            for c in p["components"]:
                assert abs(sum(m["pct"] for m in c["materials"]) - 100) <= 1e-6
                assert all(m["pct"] >= 0 for m in c["materials"])
            assert p["hard_valid"] is True


def test_pad_and_other_never_introduced():
    for seed in range(8):
        for g in GS:
            for lv, p in levels(g, seed).items():
                mats = {m["material"] for c in p["components"] for m in c["materials"]}
                assert mats <= VOCAB and not ({"PAD", "OTHER", "pad", "other"} & mats)


def test_level0_has_zero_perturbation_distance_and_same_composition():
    for g in GS:
        p = levels(g)["L0"]
        assert p["distance"]["n_substitutions"] == 0 and p["distance"]["abs_pct_change_total"] == 0 and p["distance"]["diagnostic_distance"] == 0
        assert p["components"] == public(g.components)


def test_larger_percentage_perturbation_has_larger_or_equal_distance():
    seen = 0
    for g in GS:
        lv = levels(g)
        if "L1" in lv and "L2" in lv:
            seen += 1
            assert lv["L2"]["distance"]["abs_pct_change_total"] >= lv["L1"]["distance"]["abs_pct_change_total"]
            assert lv["L1"]["distance"]["n_substitutions"] == lv["L2"]["distance"]["n_substitutions"] == 0   # same materials
            assert lv["L1"]["distance"]["abs_pct_change_total"] > 0
    assert seen >= 3
    assert PerturbationConfig().l2_min_delta > PerturbationConfig().l1_delta


def test_substitution_levels_change_exactly_one_slot_and_l3_uses_supported_material():
    for g in GS:
        lv = levels(g)
        for name in ("L3", "L4"):
            if name in lv:
                assert lv[name]["distance"]["n_substitutions"] == 1 and lv[name]["distance"]["n_substituted_components"] == 1
        if "L3" in lv:
            ci = lv["L3"]["info"]["component_index"]
            assert lv["L3"]["info"]["to_material"] in SUP.allowed(g.detail_category, g.components[ci]["component_class"])
            assert lv["L3"]["info"]["train_support_count"] > 0


def test_unsupported_context_substitution_reduces_contextual_support():
    checked = strict = 0
    for g in GS:
        lv = levels(g)
        if "L4" not in lv:
            continue
        checked += 1
        ci = lv["L4"]["info"]["component_index"]
        assert lv["L4"]["info"]["zero_support"] is True
        before = contextual_support(lv["L0"]["components"], g.detail_category, SUP)
        after = contextual_support(lv["L4"]["components"], g.detail_category, SUP)
        assert after["components"][ci]["support_count"] == 0 and after["components"][ci]["score"] == 0.0
        b, a = before["components"][ci]["score"], after["components"][ci]["score"]
        assert a <= b and after["score"] <= before["score"]                  # never higher
        if b > 0:                                                            # strictly lower whenever the original had support
            assert a < b and after["score"] < before["score"]
            strict += 1
    assert checked >= 4 and strict >= 3


def test_percentage_perturbation_leaves_contextual_support_unchanged_by_construction():
    for g in GS:
        lv = levels(g)
        if "L1" in lv:
            a = contextual_support(lv["L0"]["components"], g.detail_category, SUP)["score"]
            assert contextual_support(lv["L1"]["components"], g.detail_category, SUP)["score"] == a
            assert contextual_support(lv["L2"]["components"], g.detail_category, SUP)["score"] == a


def test_weight_sensitivity_is_deterministic_and_matches_formula():
    r1, rows1 = run_plausibility_validation(GS, SUP, VOCAB_LIST, CTX, seed=2, n_boot=50)
    r2, rows2 = run_plausibility_validation(GS, SUP, VOCAB_LIST, CTX, seed=2, n_boot=50)
    assert r1 == r2 and rows1 == rows2
    assert set(r1["weight_sensitivity"]["per_weighting"]) == {"0.25/0.75", "0.50/0.50", "0.75/0.25"} and r1["default_weighting"] == "0.50/0.50"
    for row in rows1:
        for (wc, wp) in WEIGHTINGS:
            assert row["scores"][f"{wc:.2f}/{wp:.2f}"] == pytest.approx(wc * row["contextual"] + wp * row["proximity"], abs=1e-5)
    assert r1["support_splits_used"] == ["train"]


def test_ordering_is_measured_not_forced():
    rows = [{"garment_id": "a", "level": "L0", "scores": {"w": 0.5}}, {"garment_id": "a", "level": "L1", "scores": {"w": 0.9}},   # violation
            {"garment_id": "a", "level": "L2", "scores": {"w": 0.4}}, {"garment_id": "a", "level": "L4", "scores": {"w": 0.6}},      # violation
            {"garment_id": "b", "level": "L0", "scores": {"w": 0.9}}, {"garment_id": "b", "level": "L1", "scores": {"w": 0.8}},
            {"garment_id": "b", "level": "L2", "scores": {"w": 0.7}}, {"garment_id": "b", "level": "L4", "scores": {"w": 0.1}}]
    for r in rows:
        r.setdefault("contextual", 0.0)
    out = ordering_tests(rows, "w", 20, 0)
    assert out["L0>=L1"]["expected_relation_share"] == 0.5 and out["L0>L4 (unsupported context scores lower)"]["expected_relation_share"] == 0.5
    assert out["chain L0>=L1>=L2 (per garment)"]["share"] == 0.5 and out["all expected (L0>=L1>=L2 and L4<L0)"]["share"] == 0.5


def test_score_levels_hard_validity_and_levels_available():
    rows = score_levels(GS, SUP, VOCAB_LIST, CTX, seed=1)
    assert {r["level"] for r in rows} <= {"L0", "L1", "L2", "L3", "L4"} and all(r["hard_valid"] for r in rows)
    assert sum(r["level"] == "L0" for r in rows) == len(GS)


def test_plausibility_wording_is_dataset_relative():
    p = evaluate_plausibility(public(GS[0].components), GS[0].detail_category, {"n_substitutions": 0, "abs_pct_change_total": 0.0}, SUP, EvaluationConfig())
    assert "not a guarantee of manufacturability" in p["note"] and "TRAIN" in p["note"]
