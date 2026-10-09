"""Application-layer tests (no browser needed)."""
from __future__ import annotations

import copy
import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import pytest

from app.adapters import (MissingDataError, build_app_data, field_availability, form_to_raw_request, load_app_data, missing_files,
                          read_train_representation)
from app.integrity import verify
from app.presenters import BANNED_CLAIMS, ZERO_VIOLATION_TEXT, composition_lines, contains_banned_claim, merge_display_materials, sorting_summary_text, sr_status
from app.service import (STATUS_INVALID, STATUS_NO_CANDIDATES, STATUS_NO_TEMPLATES, STATUS_OK, AppConfig, b3_config, generate_recommendations)
from app.state import current_result, result_is_stale, store_result
from app.tests.app_fixtures import CAPS, DATA, REP_ALL, REP_TRAIN, VOCAB_DOC

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
SMALL = AppConfig(n_templates=5, candidates_per_template=5)
BASE = {"target_segment": "women", "detail_category": "trousers"}


def run(req=None, seed=0, cfg=SMALL, **kw):
    return generate_recommendations({**BASE, **(req or {})}, seed=seed, data=DATA, app_cfg=cfg, **kw)


def all_text(result) -> str:
    return json.dumps({k: result[k] for k in ("messages", "recommendations")}, default=str)


# ---------------------------------------------------------------- adapters
def test_request_adapter_mapping():
    form = {"segment": "women", "category": "trousers", "preferred_material": "linen", "forbidden_materials": ["polyester", "nylon"],
            "colour": "black", "fit": "relaxed", "length": "long", "stretch": "low", "thermal_warmth": None, "breathability": "high",
            "durability": "reinforced", "moisture_wicking": True, "water_repellent": False}
    assert form_to_raw_request(form) == {"target_segment": "women", "detail_category": "trousers", "preferred_dominant_material": "linen",
                                         "forbidden_materials": ["polyester", "nylon"], "colour": "black", "fit": "relaxed", "length_cut": "long",
                                         "stretch": "low", "breathability": "high", "durability_wear": "reinforced", "moisture_wicking": True}
    assert form_to_raw_request({"segment": "men", "category": "shorts", "forbidden_materials": [], "colour": "  ", "fit": None}) == \
        {"target_segment": "men", "detail_category": "shorts"}
    r1 = generate_recommendations({"segment": "women", "category": "trousers", "stretch": "low"}, data=DATA, app_cfg=SMALL, is_form=True)
    r2 = run({"stretch": "low"})
    assert r1["raw_request"] == r2["raw_request"] and r1["digest"] == r2["digest"]


def test_field_availability_marks_unsupported_fields():
    caps = copy.deepcopy(CAPS)
    caps["categories"]["shorts"]["controls"]["length_cut"] = False
    caps["categories"]["shorts"]["control_decisions"] = {"length_cut": "disabled_insufficient_train_support"}
    caps["categories"]["shorts"]["controls"]["water_repellent"] = False
    a = field_availability("shorts", caps)
    assert a["length"] == {"enabled": False, "reason": "not enough labelled TRAIN garments for this category"}
    assert a["water_repellent"]["enabled"] is False and "not applicable" in a["water_repellent"]["reason"]
    assert a["fit"]["enabled"] is True and a["fit"]["reason"] is None
    assert all(not v["enabled"] for v in field_availability("unknown_category", caps).values())


def test_unsupported_preference_is_reported_not_silently_ignored():
    data = build_app_data(REP_TRAIN, VOCAB_DOC, {"categories": {"trousers": {"controls": {"stretch": False}}, "shorts": {"controls": {}}}})
    r = generate_recommendations({**BASE, "stretch": "high"}, data=data, app_cfg=SMALL)
    assert r["status"] == STATUS_OK
    w = [m for m in r["messages"] if m["code"] == "control_not_available"]
    assert w and "Stretch" in w[0]["text"] and "not used" in w[0]["text"]
    assert r["request"]["soft_preferences"]["stretch"] is None and r["request"]["ignored_preferences"] == {"stretch": "high"}


# ---------------------------------------------------------------- validation
@pytest.mark.parametrize("req,code", [({"stretch": "medium"}, "invalid_value"), ({"preferred_dominant_material": "kryptonite"}, "unknown_material"),
                                      ({"fit": "skinny"}, "removed_in_v1"), ({"target_segment": None}, "missing_required_field"),
                                      ({"target_segment": "robots"}, "invalid_target_segment"), ({"detail_category": "capes"}, "invalid_detail_category"),
                                      ({"bogus": 1}, "unknown_field")])
def test_validation_errors_are_returned_not_raised(req, code):
    r = run(req)
    assert r["status"] == STATUS_INVALID and r["recommendations"] == [] and code in [m["code"] for m in r["messages"]]
    assert all(m["level"] == "error" and m["text"] for m in r["messages"])


def test_forbidden_preferred_material_conflict_is_explained():
    r = run({"preferred_dominant_material": "cotton", "forbidden_materials": ["cotton"]})
    assert r["status"] == STATUS_OK
    assert any("hard constraint" in m["text"] for m in r["messages"])
    for rec in r["recommendations"]:
        assert all(m["material"] != "cotton" for c in rec["composition"] for m in c["materials"])


# ---------------------------------------------------------------- generation flow
def test_successful_generation_flow():
    r = run({"preferred_dominant_material": "cotton", "breathability": "high", "colour": "black"})
    assert r["status"] == STATUS_OK and r["recommendations"] and r["stats"]["hard_valid"] > 0 and r["stats"]["front_size"] >= 1
    roles = [x for rec in r["recommendations"] for x in rec["roles"]]
    assert {"balanced", "sorting_focused", "intent_focused"} == set(roles)
    for rec in r["recommendations"]:
        for k in ("roles", "category", "composition", "colour", "fit", "length", "intent_0_100", "plausibility_0_100", "sr", "violation_count",
                  "sorting_summary", "role_reasons", "preferences", "headline"):
            assert k in rec
        assert [x["rule"] for x in rec["sr"]] == ["SR1", "SR2", "SR3", "SR4", "SR5"]
        assert rec["violation_count"] == sum(x["violated"] for x in rec["sr"])
        assert len(rec["role_reasons"]) == len(rec["roles"])
    assert r["stats"]["seconds_total"] >= 0 and r["pareto_points"]
    assert sum(p["is_pareto"] for p in r["pareto_points"]) == r["stats"]["front_size"]
    assert {p["candidate_id"] for p in r["pareto_points"] if p["roles"]} == {rec["candidate_id"] for rec in r["recommendations"]}


def test_progress_callback_and_timing():
    seen = []
    r = run(progress=lambda text, frac: seen.append(frac))
    assert seen[0] < seen[-1] == 1.0 and r["stats"]["seconds_generation"] >= 0 and r["stats"]["seconds_evaluation"] >= 0


def test_uses_frozen_b3_configuration_with_only_budget_and_seed_changed():
    m = json.loads((ROOT / "configs" / "final_test_evaluation_manifest.json").read_text(encoding="utf-8"))["configs"]["generator_B3_sorting_aware"]
    app = json.loads(json.dumps(asdict(b3_config(AppConfig(), 0)), default=str))
    assert app == m                                                              # default app config == final TEST configuration
    small = json.loads(json.dumps(asdict(b3_config(AppConfig(3, 4), 9)), default=str))
    diff = {k for k in m if m[k] != small[k]}
    assert diff == {"n_templates", "candidates_per_template", "seed"}
    assert small["policy"] == "STRICT_SORTING" and small["sorting_aware_proposal"] and small["sorting_aware_repair"]
    with pytest.raises(ValueError):
        AppConfig(0, 5)


# ---------------------------------------------------------------- TRAIN-only
def test_application_uses_train_only_generation_support(tmp_path):
    assert set(DATA.rep_train["split"]) == {"train"} and DATA.support.splits_used == ("train",) and DATA.loaded_splits == ("train",)
    with pytest.raises(ValueError):
        build_app_data(REP_ALL, VOCAB_DOC, CAPS)
    REP_ALL.to_parquet(tmp_path / "garment_representation.parquet")
    rt = read_train_representation(tmp_path)
    assert set(rt["split"]) == {"train"} and len(rt) == len(REP_TRAIN)
    r = run()
    train_ids = set(REP_TRAIN["garment_id"])
    assert all(rec["template_garment_id"] in train_ids for rec in r["recommendations"])
    from tests.synthetic_data import garment
    rows = REP_ALL.to_dict("records")
    for x in rows:
        if x["split"] != "train":                                                # rewrite every VAL/TEST garment
            x["components"] = garment("Z", "pz", x["split"], [("elastane", 100)], [("viscose", 100)])["components"]
    pd.DataFrame(rows).to_parquet(tmp_path / "garment_representation.parquet")
    data2 = build_app_data(read_train_representation(tmp_path), VOCAB_DOC, CAPS)
    assert generate_recommendations(BASE, data=data2, app_cfg=SMALL)["digest"] == r["digest"]


def test_missing_data_is_detected(tmp_path):
    assert set(missing_files(tmp_path)) == {"garment_representation.parquet", "ml_material_vocabulary.json", "category_capabilities.json"}
    with pytest.raises(MissingDataError) as e:
        load_app_data(tmp_path)
    assert "garment_representation.parquet" in e.value.missing and e.value.missing["garment_representation.parquet"]


# ---------------------------------------------------------------- display-only normalisation
def test_presentation_only_duplicate_material_merging():
    mats = [{"material": "cotton", "pct": 95.0}, {"material": "Cotton", "pct": 5.0}, {"material": "polyester", "pct": 0.0}]
    before = copy.deepcopy(mats)
    merged = merge_display_materials(mats)
    assert [(m["material"], m["pct"]) for m in merged] == [("cotton", 100.0), ("polyester", 0.0)] and merged[0]["merged_slots"] == 2
    assert mats == before                                                        # input untouched
    comps = [{"component_name_normalized": "main", "component_class": "surface_component", "materials": [{"material": "cotton", "pct": 95.0},
                                                                                                          {"material": "cotton", "pct": 5.0}]}]
    snapshot = copy.deepcopy(comps)
    lines = composition_lines(comps)
    assert lines[0]["text"] == "cotton 100%" and lines[0]["had_duplicate_slots"] and comps == snapshot


def test_merged_view_is_never_fed_back_into_evaluation(monkeypatch):
    import app.service as svc
    calls = {}
    real = svc.evaluate_and_select

    def spy(req, rep, sup, ctx, cfg=None, res=None):
        calls["components"] = copy.deepcopy([c["components"] for c in res["candidates"]])
        out = real(req, rep, sup, ctx, cfg=cfg, res=res)
        calls["after"] = [c["components"] for c in res["candidates"]]
        return out
    monkeypatch.setattr(svc, "evaluate_and_select", spy)
    r = run({"stretch": "low"})
    assert r["status"] == STATUS_OK and calls["components"] == calls["after"]   # presenters ran after evaluation and changed nothing
    slot_counts = [len(c["materials"]) for comps in calls["components"] for c in comps]
    assert slot_counts                                                           # evaluation saw the raw slot structure


# ---------------------------------------------------------------- dedup / multiple roles
def test_recommendations_are_deduplicated_by_candidate():
    r = run({"breathability": "high"})
    ids = [rec["candidate_id"] for rec in r["recommendations"]]
    assert len(ids) == len(set(ids)) <= 3
    roles = [x for rec in r["recommendations"] for x in rec["roles"]]
    assert len(roles) == len(set(roles))
    assert r["flags"]["duplicate_roles"] == any(len(rec["roles"]) > 1 for rec in r["recommendations"])


def test_identical_candidate_selected_for_multiple_roles():
    r = run({"colour": "black"}, cfg=AppConfig(1, 1))                            # a single candidate fills every role
    assert r["status"] == STATUS_OK and len(r["recommendations"]) == 1
    rec = r["recommendations"][0]
    assert rec["roles"] == ["balanced", "sorting_focused", "intent_focused"] and rec["role_titles"] == ["Balanced", "Sorting-focused", "Intent-focused"]
    assert r["flags"]["single_pareto_candidate"] and any(m["code"] == "single_pareto" for m in r["messages"])


# ---------------------------------------------------------------- empty / failure states
def test_empty_template_state():
    r = run({"target_segment": "men"})                                           # men/trousers has no TRAIN garments in the fixture
    assert r["status"] == STATUS_NO_TEMPLATES and r["recommendations"] == [] and r["stats"]["eligible_templates"] == 0
    assert "no TRAIN garments" in r["messages"][-1]["text"]


def test_empty_candidate_state():
    r = generate_recommendations({"target_segment": "men", "detail_category": "shorts", "forbidden_materials": ["cotton"]}, data=DATA, app_cfg=SMALL)
    assert r["status"] == STATUS_NO_CANDIDATES and r["recommendations"] == [] and r["stats"]["candidates_generated"] == 0
    assert r["stats"]["templates_dropped_forbidden"] >= 1 and "forbidden material" in r["messages"][-1]["text"]


def test_no_zero_violation_state_is_explained():
    r = run({"colour": "black"}, cfg=AppConfig(1, 1))
    if r["flags"]["no_zero_violation_candidate"]:
        assert any(m["code"] == "no_zero_violation" for m in r["messages"])
    bl = generate_recommendations({"target_segment": "women", "detail_category": "trousers"}, data=build_app_data(
        REP_TRAIN.assign(normalized_colour="black"), VOCAB_DOC, CAPS), app_cfg=SMALL)
    assert bl["flags"]["no_zero_violation_candidate"] and bl["flags"]["zero_blocked_by_colour"]
    msg = next(m for m in bl["messages"] if m["code"] == "no_zero_violation")
    assert "SR4" in msg["text"] and "not changed" in msg["text"]


# ---------------------------------------------------------------- wording
def test_sr_wording_does_not_claim_recyclability():
    assert ZERO_VIOLATION_TEXT == "No violations detected under the CAGO SR1–SR5 sorting-screening rules."
    o = {"sr1_violation": False, "sr2_violation": False, "sr3_violation": False, "sr4_violation": False, "sr5_violation": False}
    assert sorting_summary_text(0, sr_status(o, "red")) == ZERO_VIOLATION_TEXT
    o4 = {**o, "sr4_violation": True}
    t = sorting_summary_text(1, sr_status(o4, "black"))
    assert t.startswith("1 of 5") and "SR4" in t
    for req in ({}, {"colour": "black"}, {"breathability": "high", "stretch": "low"}, {"forbidden_materials": ["polyester"]}):
        text = all_text(run(req))
        assert contains_banned_claim(text) == [], (req, contains_banned_claim(text))
    assert contains_banned_claim("This is 100% recyclable") and "recyclability percentage" in BANNED_CLAIMS
    from app.presenters import DISCLAIMER
    assert not contains_banned_claim(" ".join(DISCLAIMER)) and any("does not guarantee recyclability" in d for d in DISCLAIMER)


# ---------------------------------------------------------------- determinism / state
def test_deterministic_seed_behaviour():
    a, b = run({"stretch": "low"}, seed=3), run({"stretch": "low"}, seed=3)
    assert a["digest"] == b["digest"] and [r["candidate_id"] for r in a["recommendations"]] == [r["candidate_id"] for r in b["recommendations"]]
    assert [r["composition"] for r in a["recommendations"]] == [r["composition"] for r in b["recommendations"]]
    c = run({"stretch": "low"}, seed=4)
    assert c["digest"] != a["digest"]


def test_session_state_helpers():
    state = {}
    assert current_result(state) is None and not result_is_stale(state, {}, 0, {})
    r = run()
    store_result(state, r)
    assert current_result(state) is r and not result_is_stale(state, r["raw_request"], r["seed"], r["budget"])
    assert result_is_stale(state, {**r["raw_request"], "stretch": "low"}, r["seed"], r["budget"]) and result_is_stale(state, r["raw_request"], 9, r["budget"])


# ---------------------------------------------------------------- frozen research integrity
def test_frozen_research_files_remain_unchanged():
    v = verify()
    assert v == {"changed": [], "missing": [], "added_in_frozen_dirs": []}, v
    snap = json.loads((ROOT / "app" / "frozen_research_hashes.json").read_text(encoding="utf-8"))
    assert set(snap["documented_changes"]) == {"requirements.txt"}
    assert "cago/oracle/rules.py" in snap["files"] and "data/processed/final_test_evaluation_report.json" in snap["files"]


@pytest.mark.skipif(not (ROOT / "configs" / "final_test_evaluation_manifest.json").exists(), reason="manifest missing")
def test_final_test_manifest_still_verifies():
    from cago.benchmark.final_test_manifest import verify_manifest
    m = json.loads((ROOT / "configs" / "final_test_evaluation_manifest.json").read_text(encoding="utf-8"))
    v = verify_manifest(m, ROOT, PROCESSED)
    assert v["ok"] and v["mismatches"]["new_code_changed_since_freeze"] == [], v["mismatches"]


# ---------------------------------------------------------------- real data (skipped without processed files)
@pytest.mark.skipif(missing_files(PROCESSED) != {}, reason="processed data missing")
def test_real_data_smoke():
    data = load_app_data(PROCESSED)
    assert set(data.rep_train["split"]) == {"train"} and data.support.n_train_garments == len(data.rep_train)
    r = generate_recommendations({"target_segment": "women", "detail_category": "trousers", "forbidden_materials": ["polyester"],
                                  "preferred_dominant_material": "linen", "breathability": "high", "fit": "relaxed", "length_cut": "long"}, data=data)
    assert r["status"] == STATUS_OK and r["recommendations"] and r["stats"]["seconds_total"] < 60
    for rec in r["recommendations"]:
        assert all(m["material"] != "polyester" for c in rec["composition"] for m in c["materials"])
    assert contains_banned_claim(all_text(r)) == []
    nt = generate_recommendations({"target_segment": "baby", "detail_category": "skirts"}, data=data)
    assert nt["status"] == STATUS_NO_TEMPLATES
