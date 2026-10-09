"""V1 release-readiness tests for the application layer: unusable data files, TRAIN-only loading without fallback,
accurate 'no Intent-focused' messages, plain-language wording (display only) and widget behaviour."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from app import adapters
from app.adapters import DataLoadError, MissingDataError, load_app_data, read_train_representation
from app.presenters import (change_sentence, conflict_text, contains_banned_claim, evidence_phrase, invalid_value_text, preference_sentence,
                            rule_change_sentence, trade_off_sentence)
from app.service import STATUS_INVALID, STATUS_OK, AppConfig, generate_recommendations
from app.tests.app_fixtures import CAPS, DATA, REP_ALL, VOCAB_DOC

ROOT = Path(__file__).resolve().parents[2]
SMALL = AppConfig(n_templates=5, candidates_per_template=5)
BASE = {"target_segment": "women", "detail_category": "trousers"}


def write_valid(d: Path, rep: pd.DataFrame = REP_ALL) -> Path:
    rep.to_parquet(d / "garment_representation.parquet")
    (d / "ml_material_vocabulary.json").write_text(json.dumps(VOCAB_DOC), encoding="utf-8")
    (d / "category_capabilities.json").write_text(json.dumps(CAPS), encoding="utf-8")
    return d


# ---------------------------------------------------------------- unusable data files
def test_valid_fixture_directory_loads(tmp_path):
    data = load_app_data(write_valid(tmp_path))
    assert set(data.rep_train["split"]) == {"train"} and data.loaded_splits == ("train",)


@pytest.mark.parametrize("name,content", [
    ("garment_representation.parquet", b"not a parquet file"),
    ("ml_material_vocabulary.json", b"{broken json"),
    ("category_capabilities.json", b"\xff\xfe\x00 not utf8"),
])
def test_corrupted_file_raises_data_load_error(tmp_path, name, content):
    write_valid(tmp_path)
    (tmp_path / name).write_bytes(content)
    with pytest.raises(DataLoadError) as e:
        load_app_data(tmp_path)
    assert e.value.file == name and e.value.problem


def test_missing_columns_never_fall_back_to_reading_all_splits(tmp_path, monkeypatch):
    REP_ALL.drop(columns=["detail_category"]).to_parquet(tmp_path / "garment_representation.parquet")
    calls = []
    real = pd.read_parquet
    monkeypatch.setattr(adapters.pd, "read_parquet", lambda *a, **k: calls.append(k) or real(*a, **k))
    with pytest.raises(DataLoadError) as e:
        read_train_representation(tmp_path)
    assert "detail_category" in e.value.problem
    assert calls == []                                       # schema check fails before any row is read


def test_every_row_read_uses_the_train_filter(tmp_path, monkeypatch):
    REP_ALL.to_parquet(tmp_path / "garment_representation.parquet")
    calls = []
    real = pd.read_parquet
    monkeypatch.setattr(adapters.pd, "read_parquet", lambda *a, **k: calls.append(k) or real(*a, **k))
    read_train_representation(tmp_path)
    assert calls and all(k.get("filters") == [("split", "==", "train")] for k in calls)


def test_no_train_rows_is_reported(tmp_path):
    write_valid(tmp_path, REP_ALL[REP_ALL["split"] != "train"])
    with pytest.raises(DataLoadError) as e:
        load_app_data(tmp_path)
    assert "no rows with split == 'train'" in e.value.problem


def test_incomplete_json_structure_is_reported(tmp_path):
    write_valid(tmp_path)
    (tmp_path / "ml_material_vocabulary.json").write_text(json.dumps({"tokens": []}), encoding="utf-8")
    with pytest.raises(DataLoadError) as e:
        load_app_data(tmp_path)
    assert "special_tokens" in e.value.problem and "canonical_to_token" in e.value.problem
    write_valid(tmp_path)
    (tmp_path / "category_capabilities.json").write_text(json.dumps({"version": 1}), encoding="utf-8")
    with pytest.raises(DataLoadError) as e:
        load_app_data(tmp_path)
    assert "categories" in e.value.problem


def test_directory_with_required_name_counts_as_missing(tmp_path):
    write_valid(tmp_path)
    (tmp_path / "category_capabilities.json").unlink()
    (tmp_path / "category_capabilities.json").mkdir()
    with pytest.raises(MissingDataError) as e:
        load_app_data(tmp_path)
    assert list(e.value.missing) == ["category_capabilities.json"]


# ---------------------------------------------------------------- Intent-focused omission messages
def no_intent_message(req):
    r = generate_recommendations({**BASE, **req}, data=DATA, app_cfg=SMALL)
    assert r["status"] == STATUS_OK
    return r, next((m["text"] for m in r["messages"] if m["code"] == "no_intent"), None)


def test_no_intent_message_without_preferences():
    r, msg = no_intent_message({})
    assert r["flags"]["intent_focused_omitted"] and msg.startswith("No soft preference was given")


def test_no_intent_message_for_given_but_unscorable_preference():
    r, msg = no_intent_message({"thermal_warmth": "standard"})
    assert r["flags"]["intent_focused_omitted"]
    assert "No soft preference was given" not in msg and "thermal warmth" in msg and "neutral" in msg


def test_scorable_preference_produces_no_omission_message():
    r, msg = no_intent_message({"breathability": "high"})
    assert not r["flags"]["intent_focused_omitted"] and msg is None


# ---------------------------------------------------------------- plain-language wording (display only)
def test_preference_lines_are_readable_and_keep_technical_evidence():
    r = generate_recommendations({**BASE, "breathability": "high", "preferred_dominant_material": "cotton"}, data=DATA, app_cfg=SMALL)
    assert r["status"] == STATUS_OK
    for rec in r["recommendations"]:
        for p in rec["preferences"]:
            assert "_share=" not in p["explanation"] and "proxy '" not in p["explanation"]
            assert p["technical"]                                                     # frozen explanation kept verbatim
        assert all(not c.startswith("Change 0") for c in rec["changes_from_template"])
        assert not contains_banned_claim(json.dumps(rec, default=str))


def test_readable_preferences_do_not_change_scores():
    """The readable layer is derived from the frozen evaluation; scores, statuses and the digest are unchanged."""
    a = generate_recommendations({**BASE, "breathability": "high"}, data=DATA, app_cfg=SMALL, seed=3)
    b = generate_recommendations({**BASE, "breathability": "high"}, data=DATA, app_cfg=SMALL, seed=3)
    assert a["digest"] == b["digest"]
    for ra, rb in zip(a["recommendations"], b["recommendations"]):
        assert [(p["status"], p["satisfaction"]) for p in ra["preferences"]] == [(p["status"], p["satisfaction"]) for p in rb["preferences"]]


def test_evidence_and_preference_sentences():
    assert evidence_phrase("breathable_fibre_share=0.85").endswith(": 85%")
    assert evidence_phrase("bucket=none") == "stretch level: no elastane (no stretch)"
    assert evidence_phrase("text:membrane,lamination") == "product text mentions membrane, lamination"
    assert evidence_phrase("unknown_token") == "unknown_token"
    p = {"preference": "breathability", "requested_value": "high", "scorable": True, "satisfaction_0_1": 1.0,
         "evidence": ["breathable_fibre_share=1.00"], "unscorable_reason": None}
    s = preference_sentence(p)
    assert "fully meets 'high' breathability" in s and "100%" in s and "not a measured property" in s
    p = {"preference": "fit", "requested_value": "slim", "scorable": False, "satisfaction_0_1": None, "evidence": [],
         "unscorable_reason": "no_label_evidence"}
    assert "not counted as a miss" in preference_sentence(p)
    p = {"preference": "stretch", "requested_value": "high", "scorable": True, "satisfaction_0_1": 0.0,
         "evidence": ["elastane=0%", "bucket=none", "bucket=none"], "unscorable_reason": None}
    s = preference_sentence(p)
    assert "does not meet 'high' stretch" in s and s.count("stretch level") == 1
    p = {"preference": "preferred_dominant_material", "requested_value": "linen", "scorable": True, "satisfaction_0_1": 0.0,
         "evidence": ["primary_component=shell", "dominant=cotton=60%"], "unscorable_reason": None}
    assert preference_sentence(p) == "The largest material in the main fabric (shell) is cotton at 60%, not linen."


def test_change_and_rule_sentences_use_consistent_numbering():
    sub = {"step": 0, "type": "substitution", "reason": "forbidden_repair", "component_name": "shell", "from_material": "elastane",
           "to_material": "cotton", "pct": 3.0}
    assert change_sentence(sub).startswith("Change 1: replaced elastane with cotton in the shell component") and "forbidden" in change_sentence(sub)
    mv = {"step": 1, "type": "percentage", "component_name": "shell", "from_material": "polyester", "to_material": "cotton", "delta": 1.0,
          "pct_before": [40.0, 60.0], "pct_after": [39.0, 61.0]}
    assert change_sentence(mv) == ("Change 2: moved 1 percentage point from polyester to cotton in the shell component "
                                   "(polyester 40% → 39%, cotton 60% → 61%).")
    r = {"rule": "SR1", "vs_template": "resolved", "confirmed_by_mutation_steps": [0]}
    assert "confirmed: undoing change 1 on its own" in rule_change_sentence(r)
    r2 = {"rule": "SR2", "vs_template": "introduced", "confirmed_by_mutation_steps": [0, 2]}
    assert "undoing any one of changes 1 or 3 on its own removes the flag" in rule_change_sentence(r2)
    assert rule_change_sentence({"rule": "SR2", "vs_template": "still_satisfied"}) is None
    assert "→" in trade_off_sentence("Sorting rule violations: template 1 -> candidate 0 (-1).")


def test_validation_and_conflict_texts_are_user_facing():
    r = generate_recommendations({**BASE, "breathability": "very_high"}, data=DATA, app_cfg=SMALL)
    assert r["status"] == STATUS_INVALID and "use null" not in json.dumps(r["messages"])
    assert "No preference" in invalid_value_text("'x' is not one of ['low'] (use null for no preference)")
    r = generate_recommendations({**BASE, "stretch": "high", "forbidden_materials": ["elastane"]}, data=DATA, app_cfg=SMALL)
    w = next(m for m in r["messages"] if m["code"] == "preference_conflict")
    assert "elastane is forbidden" in w["text"]
    assert conflict_text(["x"], "fallback") == "fallback"


def test_research_inputs_unchanged_by_wording_layer(monkeypatch):
    """The request passed to frozen generation/evaluation equals the validated request (wording happens afterwards)."""
    import app.service as svc
    seen = {}
    real = svc.evaluate_and_select
    monkeypatch.setattr(svc, "evaluate_and_select", lambda req, *a, **k: seen.setdefault("req", json.dumps(req, sort_keys=True, default=str)) and real(req, *a, **k))
    r = svc.generate_recommendations({**BASE, "breathability": "high"}, data=DATA, app_cfg=SMALL)
    assert seen["req"] == json.dumps(r["request"], sort_keys=True, default=str)


# ---------------------------------------------------------------- Streamlit UI
st_testing = pytest.importorskip("streamlit.testing.v1")
APP = str(ROOT / "app" / "streamlit_app.py")


def test_corrupted_data_screen(monkeypatch, tmp_path):
    write_valid(tmp_path)
    (tmp_path / "garment_representation.parquet").write_bytes(b"corrupted")
    monkeypatch.setenv("CAGO_PROCESSED_DIR", str(tmp_path))
    at = st_testing.AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception
    assert any("cannot be used" in e.value and "garment_representation.parquet" in e.value for e in at.error)


def test_disabled_field_does_not_keep_a_stale_value(monkeypatch, tmp_path):
    """A preference chosen for one category is reset when the next category disables that field (fixture copy with fit
    disabled for shorts)."""
    write_valid(tmp_path)
    caps = json.loads(json.dumps(CAPS))
    caps["categories"]["shorts"]["controls"]["fit"] = False
    (tmp_path / "category_capabilities.json").write_text(json.dumps(caps), encoding="utf-8")
    monkeypatch.setenv("CAGO_PROCESSED_DIR", str(tmp_path))
    at = st_testing.AppTest.from_file(APP, default_timeout=120)
    at.run()
    {s.label: s for s in at.sidebar.selectbox}["Garment category"].set_value("trousers")
    at.run()
    {s.label: s for s in at.sidebar.selectbox}["Fit"].set_value("relaxed")
    at.sidebar.button[0].click()
    at.run()
    assert {s.label: s for s in at.sidebar.selectbox}["Fit"].value == "relaxed"
    {s.label: s for s in at.sidebar.selectbox}["Garment category"].set_value("shorts")
    at.run()
    fit = {s.label: s for s in at.sidebar.selectbox}["Fit"]
    assert fit.disabled and fit.value == "No preference"
