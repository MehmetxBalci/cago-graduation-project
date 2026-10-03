"""Intent Alignment tests."""
from __future__ import annotations

import pytest

from cago.evaluation.config import EvaluationConfig, INTENT_CONFIDENCE
from cago.evaluation.intent import dominant_material, evaluate_intent, transform_score
from cago.requirements.properties import build_profile
from tests.synthetic_data import request, surface

CFG = EvaluationConfig()


def ev(soft, comps, colour="black", fit=None, length=None, tags=()):
    return evaluate_intent(request(**soft)["soft_preferences"], comps, colour, fit, length, tags, CFG)


def pref(r, name):
    return next(p for p in r["preferences"] if p["preference"] == name)


def test_unspecified_preferences_excluded_from_intent():
    r = ev({"colour": "black"}, surface([("cotton", 100)]))
    assert [p["preference"] for p in r["preferences"]] == ["colour"] and r["n_active_preferences"] == 1
    assert r["intent_alignment_raw"] == 1.0                           # other (null) preferences did not reduce it
    r2 = ev({"colour": "black", "stretch": "low"}, surface([("cotton", 100)]))
    assert r2["n_active_preferences"] == 2 and r2["intent_alignment_raw"] < 1.0


def test_no_scorable_preferences_gives_null_not_100():
    r = ev({}, surface([("cotton", 100)]))
    assert r["intent_alignment_raw"] is None and r["intent_alignment_0_100"] is None and r["n_scorable_preferences"] == 0
    neutral = ev({"thermal_warmth": "standard", "breathability": "standard"}, surface([("cotton", 100)]))
    assert neutral["intent_alignment_raw"] is None and neutral["n_active_preferences"] == 2
    assert {u["reason"] for u in neutral["unscorable_preferences"]} == {"neutral_value"}
    unl = ev({"fit": "slim", "length_cut": "long"}, surface([("cotton", 100)]), fit=None, length=None)   # unlabeled template
    assert unl["intent_alignment_raw"] is None and {u["reason"] for u in unl["unscorable_preferences"]} == {"no_label_evidence"}


def test_dominant_material_exact_match_and_tie_rule():
    comps = surface([("linen", 56), ("cotton", 44)])
    assert pref(ev({"preferred_dominant_material": "linen"}, comps), "preferred_dominant_material")["satisfaction_0_1"] == 1.0
    assert pref(ev({"preferred_dominant_material": "cotton"}, comps), "preferred_dominant_material")["satisfaction_0_1"] == 0.0
    tie = surface([("linen", 50), ("cotton", 50)])
    dom, tied = dominant_material(build_profile(tie), 1e-9)
    assert dom == "cotton" and tied == ["cotton", "linen"]                      # alphabetical tie-break, documented
    r = ev({"preferred_dominant_material": "linen"}, tie)
    assert pref(r, "preferred_dominant_material")["satisfaction_0_1"] == 0.0
    assert any("tie_among" in e for e in pref(r, "preferred_dominant_material")["evidence"])
    # primary component = first surface component, not a bigger lining
    two = surface([("cotton", 60), ("wool", 40)]) + [{"component_id": "l", "source_component_index": 1, "component_class": "lining_component",
                                                     "component_name_normalized": "lining", "materials": [{"material": "polyester", "pct": 100.0}]}]
    assert pref(ev({"preferred_dominant_material": "cotton"}, two), "preferred_dominant_material")["satisfaction_0_1"] == 1.0


def test_stretch_scoring_uses_elastane_percentage():
    comps = surface([("cotton", 95), ("elastane", 5)])
    for want, sat in (("high", 1.0), ("low", 0.0), ("none", 0.0)):
        p = pref(ev({"stretch": want}, comps), "stretch")
        assert p["satisfaction_0_1"] == sat and p["confidence_class"] == "strong_proxy"
    assert pref(ev({"stretch": "none"}, surface([("cotton", 100)])), "stretch")["satisfaction_0_1"] == 1.0
    assert pref(ev({"stretch": "low"}, surface([("cotton", 98), ("elastane", 2)])), "stretch")["satisfaction_0_1"] == 1.0
    assert "elastane=5%" in pref(ev({"stretch": "high"}, comps), "stretch")["evidence"][0]


def test_confidence_weighted_intent_score():
    comps = surface([("cotton", 100)])                                   # colour matches (1.0 weight), stretch 'high' fails
    r = ev({"colour": "black", "stretch": "high", "breathability": "high"}, comps)
    sat = {p["preference"]: p["satisfaction_0_1"] for p in r["preferences"]}
    w = {k: INTENT_CONFIDENCE[k][1] for k in sat}
    expected = sum(w[k] * sat[k] for k in sat) / sum(w.values())
    assert r["intent_alignment_raw"] == pytest.approx(expected, abs=1e-5)
    assert r["intent_alignment_0_100"] == pytest.approx(100 * expected, abs=0.01)
    assert INTENT_CONFIDENCE["breathability"][1] == 0.5 and INTENT_CONFIDENCE["colour"][1] == 1.0
    assert INTENT_CONFIDENCE["thermal_warmth"][1] == 0.75 and INTENT_CONFIDENCE["stretch"][1] == 1.0
    for k, v in INTENT_CONFIDENCE.items():
        assert v[1] in (1.0, 0.75, 0.5)


def test_fit_length_colour_exact_and_unscorable():
    r = ev({"fit": "slim", "length_cut": "long", "colour": "red"}, surface([("cotton", 100)]), fit="slim", length="standard")
    assert pref(r, "fit")["satisfaction_0_1"] == 1.0 and pref(r, "length_cut")["satisfaction_0_1"] == 0.0
    assert pref(r, "colour")["satisfaction_0_1"] == 0.0
    assert pref(ev({"colour": "black"}, surface([("cotton", 100)]), colour=None), "colour")["scorable"] is False


def test_transform_is_explicit_and_no_evidence_is_not_half_satisfied():
    s, tf = transform_score("stretch", 1.0, CFG)
    assert (s, "(proxy + 1) / 2" in tf) == (1.0, True) and transform_score("stretch", -1.0, CFG)[0] == 0.0
    s2, tf2 = transform_score("water_repellent", 0.0, CFG)
    assert s2 == 0.0 and "clamp" in tf2                                   # no evidence -> 0, not 0.5
    p = pref(ev({"water_repellent": True}, surface([("polyester", 100)])), "water_repellent")
    assert p["satisfaction_0_1"] < 0.5 and "synthetic shell alone is not proof" in " ".join(p["evidence"])
    coat = surface([("polyester", 100)]) + [{"component_id": "k", "source_component_index": 1, "component_class": "surface_component",
                                            "component_name_normalized": "coating", "materials": [{"material": "polyurethane", "pct": 100.0}]}]
    assert pref(ev({"water_repellent": True}, coat), "water_repellent")["satisfaction_0_1"] > 0.5
    assert p["transform"] == "satisfaction = clamp(proxy, 0, 1)"
