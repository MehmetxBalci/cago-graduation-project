"""Requirement engine tests (synthetic; context built from the editable capabilities JSON)."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from cago.requirements.capabilities import (coverage_report, generate_capabilities, load_capabilities)
from cago.requirements.properties import (StretchLimits, build_profile, extract_text_tags, score_breathability,
                                          score_preferences, score_stretch, score_thermal, score_water_repellent,
                                          stretch_bucket)
from cago.requirements.validation import RequirementContext, validate_candidate, validate_request

CAPS = load_capabilities()
MATERIALS = frozenset({"cotton", "linen", "polyester", "nylon", "elastane", "wool", "viscose", "acrylic", "lyocell"})
CTX = RequirementContext(
    target_segments=frozenset({"women", "men", "kids", "baby"}), categories=frozenset(CAPS["categories"]),
    materials=MATERIALS, capabilities=CAPS, aliases={"polyamide": "nylon", "spandex": "elastane"},
    component_classes=frozenset({"surface_component", "lining_component"}),
    component_names=frozenset({"main", "shell", "lining", "coating"}), ml_tokens=frozenset({"OTHER", "PAD"}))
BASE = {"target_segment": "women", "detail_category": "trousers"}


def ok(**extra):
    r = validate_request({**BASE, **extra}, CTX)
    assert r.ok, r.errors
    return r


# ---------------- schema / required fields
@pytest.mark.parametrize("raw,code", [({}, "missing_required_field"), ({"target_segment": "women"}, "missing_required_field"),
                                      ({"detail_category": "trousers"}, "missing_required_field"),
                                      ({"target_segment": " ", "detail_category": "trousers"}, "missing_required_field")])
def test_required_fields(raw, code):
    r = validate_request(raw, CTX)
    assert not r.ok and code in r.error_codes() and r.request is None


def test_invalid_target_segment_and_category_and_unknown_field():
    r = validate_request({"target_segment": "robots", "detail_category": "capes", "colour_x": 1}, CTX)
    assert {"invalid_target_segment", "invalid_detail_category", "unknown_field"} <= set(r.error_codes())
    assert validate_request("nope", CTX).error_codes() == ["invalid_request"]


def test_null_optional_preferences_and_normalized_shape():
    r = ok()
    soft = r.request["soft_preferences"]
    assert all(v is None for v in soft.values())
    assert r.request["hard_constraints"] == {"forbidden_materials": []} and r.warnings == []
    assert {"target_segment", "detail_category", "hard_constraints", "soft_preferences", "warnings"} <= set(r.request)
    r2 = ok(target_segment="  WOMEN ", forbidden_materials=None, stretch=None, moisture_wicking=None)
    assert r2.request["target_segment"] == "women" and "gender" not in r2.request


def test_enum_validation_errors():
    for k, v in (("stretch", "medium"), ("fit", "baggy"), ("thermal_warmth", "arctic"), ("length_cut", "mini"),
                 ("moisture_wicking", False), ("water_repellent", "true"), ("colour", "   ")):
        assert "invalid_value" in validate_request({**BASE, k: v}, CTX).error_codes(), k
    assert ok(thermal_warmth="standard", breathability="standard", durability_wear="standard").ok


def test_forbidden_materials_validated_normalized_deduped():
    assert "unknown_material" in validate_request({**BASE, "forbidden_materials": ["unobtainium"]}, CTX).error_codes()
    assert "invalid_value" in validate_request({**BASE, "forbidden_materials": "polyester"}, CTX).error_codes()
    r = ok(forbidden_materials=["Polyamide", "nylon", " POLYESTER "])
    assert r.request["hard_constraints"]["forbidden_materials"] == ["nylon", "polyester"]


def test_material_preference_validation():
    assert "unknown_material" in validate_request({**BASE, "preferred_dominant_material": "kryptonite"}, CTX).error_codes()
    assert ok(preferred_dominant_material="Linen").request["soft_preferences"]["preferred_dominant_material"] == "linen"
    r = ok(preferred_dominant_material="linen", forbidden_materials=["linen"])      # hard wins, no rejection
    assert r.request["soft_preferences"]["preferred_dominant_material"] is None
    assert r.request["ignored_preferences"]["preferred_dominant_material"] == "linen"
    assert "preference_conflict" in r.warning_codes()


def test_soft_preferences_never_hard_fail():
    r = ok(fit="slim", stretch="none", breathability="high", water_repellent=True, colour="Black")
    assert r.ok and r.request["soft_preferences"]["colour"] == "black"


# ---------------- conflicts
def test_fit_stretch_conflict_warning():
    r = ok(fit="slim", stretch="none")                 # V1: slim also covers former skinny
    w = [x for x in r.warnings if x["code"] == "preference_conflict"]
    assert w and set(w[0]["fields"]) == {"fit", "stretch"} and w[0]["severity"] == "mild"
    assert not [x for x in ok(fit="slim", stretch="high").warnings if x["code"] == "preference_conflict"]
    assert [x for x in ok(fit="oversized", stretch="high").warnings if x["code"] == "preference_conflict"]
    assert not [x for x in ok(fit="regular", stretch="none").warnings]
    assert any(x["code"] == "preference_conflict" for x in ok(stretch="high", forbidden_materials=["elastane"]).warnings)


# ---------------- capabilities
def test_category_capability_filtering():
    r = validate_request({"target_segment": "women", "detail_category": "swimwear", "fit": "slim", "length_cut": "long",
                          "water_repellent": True, "stretch": "high"}, CTX)
    assert r.ok
    soft = r.request["soft_preferences"]
    assert soft["fit"] is None and soft["length_cut"] is None and soft["water_repellent"] is None
    assert soft["stretch"] == "high"
    assert set(r.request["ignored_preferences"]) == {"fit", "length_cut", "water_repellent"}
    assert r.warning_codes().count("control_not_available") == 3
    # trousers support length_cut; socks do not expose cut options
    assert ok(length_cut="long").request["soft_preferences"]["length_cut"] == "long"
    s = validate_request({"target_segment": "men", "detail_category": "socks_hosiery", "length_cut": "long", "fit": "slim"}, CTX)
    assert s.request["soft_preferences"]["length_cut"] is None and s.request["soft_preferences"]["fit"] is None


def test_capabilities_generation_and_coverage():
    caps = generate_capabilities({"trousers": "bottoms", "new_cat": "overall"}, "test")
    assert not any(caps["categories"]["new_cat"]["controls"].values()) and caps["categories"]["new_cat"]["needs_review"]
    assert coverage_report(CAPS, CAPS["categories"])["missing_in_capabilities"] == []
    assert len(CAPS["categories"]) == 23


# ---------------- stretch + proxies
def test_stretch_rules_and_hooks():
    assert stretch_bucket(0) == "none" and stretch_bucket(0.5) == "low" and stretch_bucket(2.0) == "low"
    assert stretch_bucket(2.01) == "high" and stretch_bucket(40.0) == "high"          # no hard-coded upper bound
    assert stretch_bucket(5.0, StretchLimits(low_max=4.0, high_max=4.5)) == "out_of_range"   # category-relative hook
    comps = [{"component_class": "surface_component", "component_name_normalized": "main",
              "materials": [{"material": "cotton", "pct": 98.0}, {"material": "elastane", "pct": 2.0}]}]
    p = build_profile(comps)
    assert score_stretch("low", p)["score"] == 1.0 and score_stretch("none", p)["score"] == -1.0
    assert score_stretch("high", p, StretchLimits(low_max=1.0))["score"] == 1.0


def _surf(mats, name="main"):
    return {"component_class": "surface_component", "component_name_normalized": name,
            "materials": [{"material": m, "pct": x} for m, x in mats.items()]}


def test_water_repellent_synthetic_shell_alone_is_not_proof():
    p = build_profile([_surf({"polyester": 100.0})])
    r = score_water_repellent(p)
    assert r["proven"] is False and r["score"] <= 0.2
    coat = build_profile([_surf({"polyester": 100.0}), {"component_class": "surface_component",
                                                         "component_name_normalized": "coating",
                                                         "materials": [{"material": "polyurethane", "pct": 100.0}]}])
    assert score_water_repellent(coat)["proven"] is True
    txt = build_profile([_surf({"cotton": 100.0})], text_tags=extract_text_tags("Water-resistant membrane shell"))
    assert score_water_repellent(txt)["proven"] and "text:membrane" in score_water_repellent(txt)["evidence"]


def test_thermal_and_breathability_proxies():
    cotton, wool = build_profile([_surf({"cotton": 100.0})]), build_profile([_surf({"wool": 100.0})])
    assert score_thermal("light", cotton)["score"] > score_thermal("light", wool)["score"]
    assert score_thermal("heavy", wool)["score"] > score_thermal("heavy", cotton)["score"]
    assert score_thermal("standard", wool)["score"] == 0.0
    padded = build_profile([_surf({"nylon": 100.0}), {"component_class": "filling_component",
                                                       "component_name_normalized": "padding",
                                                       "materials": [{"material": "polyester", "pct": 100.0}]}])
    assert score_thermal("heavy", padded)["score"] > 0 and score_breathability("high", padded)["score"] < 0
    out = score_preferences({"length_cut": "long", "stretch": None, "colour": "black"}, cotton)
    assert out["per_property"]["length_cut"]["scorable"] is False and "stretch" not in out["per_property"]


def test_text_tags_and_no_microfibre_inference():
    tags = extract_text_tags("Quick-dry, moisture wicking fabric. Ripstop, brushed fleece lining.", None)
    assert {"quick_dry", "moisture_wicking", "ripstop", "brushed", "fleece"} <= set(tags)
    assert "microfibre" not in " ".join(tags) and extract_text_tags(None, 3) == []


# ---------------- hard constraints on candidates
def _cand(mats, cls="surface_component", name="main"):
    return [{"component_class": cls, "component_name_normalized": name,
             "materials": [{"material": m, "pct": x} for m, x in mats]}]


def test_candidate_hard_constraints():
    assert validate_candidate(_cand([("cotton", 60.0), ("linen", 40.0)]), ["polyester"], CTX) == []
    codes = lambda c, f=(): [i.code for i in validate_candidate(c, list(f), CTX)]
    assert "forbidden_material_present" in codes(_cand([("polyester", 100.0)]), ["polyester"])
    assert "percentage_sum_out_of_tolerance" in codes(_cand([("cotton", 90.0)]))
    assert "negative_percentage" in codes(_cand([("cotton", 110.0), ("linen", -10.0)]))
    assert "unknown_material" in codes(_cand([("unobtainium", 100.0)]))
    assert "unknown_component_name" in codes(_cand([("cotton", 100.0)], name="weirdpart"))
    assert "unknown_component_class" in codes(_cand([("cotton", 100.0)], cls="alien_component"))
    assert "invalid_percentage" in codes(_cand([("cotton", None)]))


# ---------------- dataset-level (processed outputs)
PROCESSED = Path(os.environ.get("CAGO_PROCESSED_DIR") or Path(__file__).resolve().parents[1] / "data" / "processed")


@pytest.mark.skipif(not (PROCESSED / "ml_material_vocabulary.json").exists(), reason="representation outputs missing")
def test_real_context_and_spec_example():
    ctx = RequirementContext.from_processed(PROCESSED)
    assert len(ctx.categories) == 23 and "women" in ctx.target_segments and ctx.target_segments == {"women", "men", "kids", "baby"}
    assert coverage_report(ctx.capabilities, ctx.categories)["missing_in_capabilities"] == []
    r = validate_request({"target_segment": "women", "detail_category": "trousers", "forbidden_materials": ["polyester"],
                          "preferred_dominant_material": "linen", "stretch": "low", "breathability": "high",
                          "fit": "relaxed", "length_cut": "long"}, ctx)
    assert r.ok and r.warnings == []
    assert "unknown_material" in validate_request({**BASE, "forbidden_materials": ["polyamide-x"]}, ctx).error_codes()


# ---------------- requested changes: target_segment, training-only tokens, strict candidate sums, diagnostic score
def test_gender_field_is_no_longer_accepted():
    r = validate_request({"gender": "women", "detail_category": "trousers"}, CTX)
    assert not r.ok and {"unknown_field", "missing_required_field"} <= set(r.error_codes())


def test_pad_and_other_rejected_as_physical_materials():
    codes = lambda c: [i.code for i in validate_candidate(c, [], CTX)]
    assert "non_physical_token" in codes(_cand([("OTHER", 50.0), ("cotton", 50.0)]))
    assert "non_physical_token" in codes(_cand([("PAD", 100.0)]))
    assert "non_physical_token" in codes(_cand([("other", 100.0)]))        # case-insensitive
    assert validate_candidate(_cand([("cotton", 50.0), ("linen", 50.0)]), [], CTX) == []


def test_candidate_percentages_must_sum_to_100_strictly():
    codes = lambda c: [i.code for i in validate_candidate(c, [], CTX)]
    assert "percentage_sum_out_of_tolerance" in codes(_cand([("cotton", 99.5), ("linen", 0.0)]))   # fine for source data, not for candidates
    assert "percentage_sum_out_of_tolerance" in codes(_cand([("cotton", 100.01)]))
    assert codes(_cand([("cotton", 100.0000001)])) == []                                           # within 1e-6
    assert codes(_cand([("cotton", 33.3), ("linen", 33.3), ("viscose", 33.4)])) == []              # float sum ~100


def test_property_scoring_mean_is_diagnostic_only():
    p = build_profile([_surf({"cotton": 100.0})])
    out = score_preferences({"breathability": "high"}, p)
    assert "mean_score" not in out and out["diagnostic_mean_score"] is not None
    assert "NOT the Intent Alignment Score" in out["note"]


@pytest.mark.skipif(not (PROCESSED / "ml_material_vocabulary.json").exists(), reason="representation outputs missing")
def test_real_context_special_tokens_are_not_materials():
    ctx = RequirementContext.from_processed(PROCESSED)
    assert ctx.ml_tokens == {"PAD", "OTHER"}
    assert not (ctx.ml_tokens & ctx.materials)
    assert validate_candidate(_cand([("polyester", 60.0), ("cotton", 40.0)], name="main"), ["wool"], ctx) == []
    assert [i.code for i in validate_candidate(_cand([("OTHER", 100.0)]), [], ctx)] == ["non_physical_token"]
