"""Intent Alignment validation / isolation tests."""
from __future__ import annotations

import pytest

from cago.benchmark.intent_validation import (Case, add_component, add_text, base_case, colour_experiments, compare, dominant_experiments,
                                              exact_check, functional_experiments, label_experiments, run_intent_validation, sats, shift_material,
                                              stretch_real_experiments, stretch_threshold_checks, summarize)
from cago.benchmark.perturbations import load_eval_garments, public
from cago.evaluation.config import EvaluationConfig
from cago.evaluation.intent import evaluate_intent
from tests.synthetic_data import VOCAB_LIST, make_rep_with_tests, request, surface

REP = make_rep_with_tests()
GS = load_eval_garments(REP, "test", seed=1)
G = {g.garment_id: g for g in GS}


def test_dominant_material_intent_responds_in_correct_direction():
    recs = dominant_experiments(GS, VOCAB_LIST)
    names = {r["experiment"] for r in recs}
    assert {"dominant_material_original_matches", "dominant_substitution", "dominant_percentage_swap"} <= names
    for r in recs:
        assert r["passed"], r
        if r["experiment"] == "dominant_material_original_matches":
            assert r["observed"] == 1.0
        else:
            assert (r["target_before"], r["target_after"], r["observed"]) == (1.0, 0.0, "decrease")
            assert r["unintended"] == []                                    # colour / fit / length / stretch untouched


def test_only_relevant_intent_component_decreases_on_substitution():
    g = G["E1"]
    base = base_case(g, extra={"preferred_dominant_material": "cotton", "stretch": "none"})
    comps = [dict(c) for c in base.components]
    var = Case(base.soft, [{**comps[0], "materials": [{"material": "linen", "pct": 60.0}, {"material": "polyester", "pct": 40.0}]}, comps[1]],
               base.colour, base.fit_label, base.length_label)
    r = compare("dominant_substitution", "E1", base, var, "preferred_dominant_material", "decrease")
    assert r["passed"] and r["affected"] == ["preferred_dominant_material"] and r["unintended"] == []


def test_colour_change_affects_colour_intent_only():
    recs = colour_experiments(GS)
    ch = [r for r in recs if r["experiment"] == "colour_changed"]
    assert ch and all(r["passed"] and r["affected"] == ["colour"] and r["unintended"] == [] for r in ch)
    assert all(r["observed"] == 1.0 for r in recs if r["experiment"] == "colour_exact_match")
    g = G["E2"]
    base = base_case(g, extra={"stretch": "low", "preferred_dominant_material": "cotton"})
    from cago.benchmark.intent_validation import with_
    s0, s1 = sats(base), sats(with_(base, colour="red"))
    assert s0["colour"] == 1.0 and s1["colour"] == 0.0
    assert all(s0[k] == s1[k] for k in s0 if k != "colour")                 # stretch, fit, length, dominant unchanged


def test_stretch_boundary_behavior_remains_correct():
    recs = stretch_threshold_checks()
    assert len(recs) == 15 and all(r["passed"] for r in recs) and all(r["unintended"] == [] for r in recs)
    table = {(r["experiment"].split("elastane=")[1].split("%")[0], r["experiment"].split("request=")[1].rstrip(")")): r["observed"] for r in recs}
    assert table[("0", "none")] == 1.0 and table[("0.5", "low")] == 1.0 and table[("2", "low")] == 1.0
    assert table[("2.01", "low")] == 0.0 and table[("2.01", "high")] == 1.0 and table[("5", "high")] == 1.0 and table[("5", "none")] == 0.0
    real = stretch_real_experiments(GS)
    assert all(r["passed"] for r in real)
    shift = [r for r in real if r["experiment"] == "elastane_shift_low_to_high"]
    assert all(r["unintended"] == [] for r in shift)


def test_fit_length_exact_match_and_mismatch_validation():
    recs = label_experiments(GS)
    match = [r for r in recs if r["experiment"].endswith("_exact_match")]
    mism = [r for r in recs if r["experiment"].endswith("_mismatch_supported_label")]
    unl = [r for r in recs if "unlabeled" in r["experiment"]]
    assert match and mism and unl
    assert all(r["observed"] == 1.0 and r["passed"] for r in match)
    assert all(r["observed"] == "decrease" and r["target_before"] == 1.0 and r["target_after"] == 0.0 and r["unintended"] == [] for r in mism)
    assert all(r["observed"] is None and r["passed"] for r in unl)            # unlabeled -> unscorable, never an automatic 0
    assert {r["garment_id"] for r in match} <= {"E1", "E2", "E4"}


def test_no_soft_preference_requests_still_yield_null_intent():
    for g in GS:
        r = evaluate_intent(request()["soft_preferences"], public(g.components), g.colour, g.fit_label, g.length_label, g.text_tags, EvaluationConfig())
        assert r["intent_alignment_raw"] is None and r["intent_alignment_0_100"] is None and r["n_active_preferences"] == 0
    r = evaluate_intent(request(thermal_warmth="standard")["soft_preferences"], surface([("cotton", 100)]), "black", None, None)
    assert r["intent_alignment_raw"] is None


def test_functional_proxy_direction_with_controlled_evidence():
    recs = functional_experiments(GS)
    assert recs
    by = {}
    for r in recs:
        by.setdefault(r["experiment"], []).append(r)
        assert r["passed"], r
        assert r["unintended"] == []                                         # independent preferences never move
    assert {"water_text_evidence_added", "water_coating_added", "thermal_heavy_filling_added"} <= set(by)
    base = base_case(G["E3"], include=(), extra={"water_repellent": True})
    assert sats(add_text(base, "membrane"))["water_repellent"] > sats(base)["water_repellent"]
    assert add_text(add_text(base, "membrane"), "membrane") is None          # evidence already present -> not testable
    coated = add_component(base, "coating", "surface_component", "polyurethane")
    assert sats(coated)["water_repellent"] > sats(base)["water_repellent"]
    assert sats(base_case(G["E3"], include=(), extra={"breathability": "high"}))["breathability"] >= 0
    assert shift_material(base_case(G["E3"], include=()), "wool", "cotton") is None   # cotton already present: no shift


def test_proxy_coupling_is_reported_not_hidden():
    recs = functional_experiments(GS)
    coupled = [r for r in recs if r["experiment"] == "breathability_filling_added"]
    assert coupled and all("thermal_warmth" in r["coupled_functional_changes"] for r in coupled)
    summ = summarize(recs)
    assert summ["breathability_filling_added"]["coupled_functional_changes"].get("thermal_warmth", 0) == len(coupled)


def test_isolation_accuracy_and_summary_structure():
    out = run_intent_validation(GS, VOCAB_LIST)
    iso = out["experiments"]["_isolation_overall"]
    assert iso["n_cases"] > 0 and iso["isolation_accuracy"] == 1.0 and iso["intended_direction_and_isolated"] == 1.0
    assert out["overall"]["experiments_passing"] == out["overall"]["experiments"] and out["overall"]["case_pass_rate"] == 1.0
    for name, v in out["experiments"].items():
        if not name.startswith("_"):
            assert {"n_cases", "expected", "observed_counts", "pass_rate", "status", "affected_subcomponents",
                    "unintended_changes", "isolation_accuracy"} <= set(v)
    assert "not measured garment performance" in out["note"]


def test_failing_expectation_is_reported_as_fail():
    base = base_case(G["E1"], extra={"stretch": "none"})
    r = compare("deliberately_wrong_expectation", "E1", base, base, "stretch", "increase")     # nothing changes
    assert r["passed"] is False and r["observed"] == "unchanged"
    s = summarize([r])
    assert s["deliberately_wrong_expectation"]["status"] == "FAIL" and s["deliberately_wrong_expectation"]["failures"]
    ex = exact_check("x", "E1", base, "stretch", 0.0)
    assert ex["passed"] is False
