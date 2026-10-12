"""V1.2.0 segment-aware category filtering.

Availability = number of TRAIN garments in the exact (segment, category) cell that the frozen template selector accepts as
templates. Only categories with at least one such template are offered for a segment, in English and Turkish.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from app.adapters import build_app_data, eligible_template_counts, load_app_data, read_train_representation
from app.i18n import Translator
from app.service import STATUS_INVALID, STATUS_NO_TEMPLATES, STATUS_OK, AppConfig, generate_recommendations
from app.state import resolve_category
from app.tests.app_fixtures import DATA, REP_TRAIN, VOCAB_DOC
from app.tests.category_fixtures import CAPS_EXT, DATA_EXT, EXPECTED_AVAILABLE, REP_EXT_ALL, REP_EXT_TRAIN
from cago.generation.template_selector import select_templates

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
SMALL = AppConfig(n_templates=3, candidates_per_template=3)
TR = Translator("tr", strict=True)


# ================================================================ availability definition
def test_available_categories_per_segment():
    assert {s: DATA_EXT.available_categories(s) for s in DATA_EXT.segments()} == EXPECTED_AVAILABLE
    assert DATA_EXT.segments() == ["women", "men", "kids"]                          # baby exists only in VAL / TEST
    assert DATA_EXT.available_categories("baby") == [] and DATA_EXT.available_categories(None) == []


def test_counts_equal_the_frozen_template_selector_pool():
    """For every TRAIN cell the app count equals `eligible_templates` reported by the frozen selector."""
    for (seg, cat), _ in REP_EXT_TRAIN.groupby(["target_segment", "detail_category"]):
        _, diag = select_templates(REP_EXT_TRAIN, {"target_segment": seg, "detail_category": cat, "soft_preferences": {}}, 1, 0)
        assert DATA_EXT.eligible_templates(seg, cat) == diag["eligible_templates"], (seg, cat)
        assert DATA_EXT.is_available(seg, cat) == (diag["eligible_templates"] > 0)


def test_availability_matches_the_service_template_pool():
    for seg in DATA_EXT.segments():
        for cat in sorted(set(REP_EXT_TRAIN["detail_category"])):
            r = generate_recommendations({"target_segment": seg, "detail_category": cat}, data=DATA_EXT, app_cfg=SMALL)
            if r["status"] == STATUS_INVALID:
                continue
            assert r["stats"]["eligible_templates"] == DATA_EXT.eligible_templates(seg, cat)
            assert (r["status"] != STATUS_NO_TEMPLATES) == DATA_EXT.is_available(seg, cat), (seg, cat, r["status"])


def test_train_garments_alone_do_not_make_a_category_available():
    """men/trousers and kids/dresses have TRAIN garments, but none is an eligible template."""
    assert DATA_EXT.cells["men"]["trousers"] == 2 and DATA_EXT.eligible_templates("men", "trousers") == 0
    assert DATA_EXT.cells["kids"]["dresses"] == 2 and DATA_EXT.available_categories("kids") == []
    assert "trousers" in CAPS_EXT["categories"] and "trousers" not in DATA_EXT.available_categories("men")   # vocabulary != availability


def test_original_fixture():
    assert DATA.available_categories("women") == ["trousers"] and DATA.available_categories("men") == ["shorts"]


# ================================================================ TRAIN-only
def test_availability_is_train_only():
    with pytest.raises(ValueError):
        eligible_template_counts(REP_EXT_ALL)                                         # VAL / TEST rows are refused
    assert "dresses" not in DATA_EXT.eligible.get("men", {}) and "baby" not in DATA_EXT.eligible   # VAL/TEST-only cells


def test_val_and_test_rows_never_change_availability(tmp_path):
    REP_EXT_ALL.to_parquet(tmp_path / "garment_representation.parquet")
    (tmp_path / "ml_material_vocabulary.json").write_text(json.dumps(VOCAB_DOC), encoding="utf-8")
    (tmp_path / "category_capabilities.json").write_text(json.dumps(CAPS_EXT), encoding="utf-8")
    loaded = load_app_data(tmp_path)
    assert loaded.eligible == DATA_EXT.eligible and set(loaded.rep_train["split"]) == {"train"}
    rows = REP_EXT_ALL.to_dict("records")
    for x in rows:                                     # make every VAL/TEST garment a new cell in every segment
        if x["split"] != "train":
            x["target_segment"], x["detail_category"] = "kids", "jeans"
    pd.DataFrame(rows).to_parquet(tmp_path / "garment_representation.parquet")
    again = build_app_data(read_train_representation(tmp_path), VOCAB_DOC, CAPS_EXT)
    assert again.eligible == DATA_EXT.eligible and again.available_categories("kids") == []


# ================================================================ service: combinations submitted directly
@pytest.mark.parametrize("seg,cat,status", [("men", "trousers", STATUS_NO_TEMPLATES), ("kids", "dresses", STATUS_NO_TEMPLATES),
                                            ("men", "dresses", STATUS_NO_TEMPLATES), ("baby", "skirts", STATUS_INVALID),
                                            ("women", "capes", STATUS_INVALID)])
@pytest.mark.parametrize("lang", ["en", "tr"])
def test_unsupported_combinations_are_rejected_by_the_service(seg, cat, status, lang, monkeypatch):
    import cago.generation_sorting.generator as gen
    monkeypatch.setattr(gen, "generate_for_template", lambda *a, **k: pytest.fail("a template was used"))
    r = generate_recommendations({"target_segment": seg, "detail_category": cat}, data=DATA_EXT, app_cfg=SMALL, lang=lang)
    assert r["status"] == status and r["recommendations"] == [] and r["pareto_points"] == []
    assert r["messages"] and all(m["level"] == "error" for m in r["messages"] if m["code"] in ("no_templates", "invalid_target_segment",
                                                                                                "invalid_detail_category"))
    if status == STATUS_NO_TEMPLATES:
        assert r["stats"]["eligible_templates"] == 0 and r["stats"]["candidates_generated"] == 0


def test_available_combinations_reach_the_generator():
    for seg, cats in EXPECTED_AVAILABLE.items():
        for cat in cats:
            r = generate_recommendations({"target_segment": seg, "detail_category": cat}, data=DATA_EXT, app_cfg=SMALL)
            assert r["status"] not in (STATUS_NO_TEMPLATES, STATUS_INVALID) and r["stats"]["templates_used"] > 0, (seg, cat)
    assert generate_recommendations({"target_segment": "women", "detail_category": "trousers"}, data=DATA_EXT, app_cfg=SMALL)["status"] == STATUS_OK


# ================================================================ selection rules (pure)
@pytest.mark.parametrize("available,current,expected", [
    (["shorts", "trousers"], "shorts", "shorts"),           # still valid -> preserved
    (["shorts"], "trousers", "shorts"),                     # disappeared -> replaced
    (["dresses", "trousers"], "shorts", "trousers"),        # replaced by the V1 default when available
    (["dresses", "jeans"], None, "dresses"),                # no selection yet -> first available
    ([], "trousers", None),                                 # segment without categories -> cleared
    (["shorts"], "Şort", "shorts"),                         # a display label is never accepted as a value
])
def test_resolve_category(available, current, expected):
    assert resolve_category(available, current) == expected


def test_category_labels_are_translated_and_reversible():
    cats = DATA_EXT.available_categories("women")
    labels = TR.option_labels("category", cats)
    assert labels == {"shorts": "Şort", "trousers": "Pantolon"}
    assert all(TR.to_internal("category", lab, cats) == c for c, lab in labels.items())
    assert Translator("en", strict=True).option_labels("category", cats) == {"shorts": "shorts", "trousers": "trousers"}
    assert not TR.has("form.no_templates_suffix") and not Translator("en").has("form.no_templates_suffix")


# ================================================================ Streamlit (headless AppTest)
st_testing = pytest.importorskip("streamlit.testing.v1")
APP = str(ROOT / "app" / "streamlit_app.py")


@pytest.fixture
def app_ext(monkeypatch, tmp_path):
    REP_EXT_ALL.to_parquet(tmp_path / "garment_representation.parquet")
    (tmp_path / "ml_material_vocabulary.json").write_text(json.dumps(VOCAB_DOC), encoding="utf-8")
    (tmp_path / "category_capabilities.json").write_text(json.dumps(CAPS_EXT), encoding="utf-8")
    monkeypatch.setenv("CAGO_PROCESSED_DIR", str(tmp_path))
    at = st_testing.AppTest.from_file(APP, default_timeout=180)
    at.run()
    assert not at.exception
    return at


def sb(at):
    return {s.label: s for s in at.sidebar.selectbox}


def rerun(at):
    at.run()
    assert not at.exception


def switch(at, lang):
    at.button_group[0].set_value(lang)
    rerun(at)


def all_option_text(at) -> str:
    return " ".join(o for s in at.sidebar.selectbox for o in s.options)


def test_dropdown_lists_only_available_categories_in_both_languages(app_ext):
    at = app_ext
    for lang, seg_label, cat_label, expected in (("en", "Segment", "Garment category", {"women": ["shorts", "trousers"], "men": ["shorts"]}),
                                                 ("tr", "Hedef grup", "Giysi kategorisi", {"women": ["Şort", "Pantolon"], "men": ["Şort"]})):
        switch(at, lang)
        for seg, opts in expected.items():
            sb(at)[seg_label].set_value(seg)
            rerun(at)
            assert sb(at)[cat_label].options == opts
            assert "TRAIN templates" not in all_option_text(at) and "TRAIN şablonu yok" not in all_option_text(at)


def test_segment_change_preserves_valid_and_replaces_invalid_category(app_ext):
    at = app_ext
    assert sb(at)["Garment category"].value == "trousers"
    sb(at)["Preferred dominant material"].set_value("cotton")
    sb(at)["Breathability"].set_value("high")
    rerun(at)
    sb(at)["Segment"].set_value("men")                                    # trousers disappears -> shorts
    rerun(at)
    assert (sb(at)["Garment category"].value, sb(at)["Garment category"].options) == ("shorts", ["shorts"])
    assert sb(at)["Preferred dominant material"].value == "cotton" and sb(at)["Breathability"].value == "high"
    sb(at)["Segment"].set_value("women")                                  # shorts is still valid for women -> preserved
    rerun(at)
    assert sb(at)["Garment category"].value == "shorts" and at.session_state["w_category"] == "shorts"


def test_empty_segment_disables_generation_and_restores_inputs(app_ext):
    at = app_ext
    sb(at)["Garment category"].set_value("shorts")
    sb(at)["Fit"].set_value("relaxed")
    rerun(at)
    for lang, seg_label, text in (("en", "Segment", "No garment category has an eligible TRAIN template"),
                                  ("tr", "Hedef grup", "uygun TRAIN şablonu olan hiçbir giysi kategorisi yok")):
        switch(at, lang)
        sb(at)[seg_label].set_value("kids")
        rerun(at)
        assert list(sb(at)) == [seg_label]                                 # no category (or other) selector is offered
        assert any(text in w.value for w in at.sidebar.warning) and any(text in i.value for i in at.info)
        assert at.sidebar.button[0].disabled                                  # a browser user cannot press it (AppTest refuses too)
        assert "cago_generation_count" not in at.session_state
        sb(at)[seg_label].set_value("women")
        rerun(at)
    switch(at, "en")
    assert sb(at)["Garment category"].value == "shorts" and sb(at)["Fit"].value == "relaxed"      # restored after the empty segment
    assert "cago_result" not in at.session_state


@pytest.mark.parametrize("stale", ["trousers", "dresses", "Şort", "jeans"])
def test_stale_category_state_is_replaced_before_any_submission(stale, monkeypatch, tmp_path):
    """Session state carrying a category that is not available for the segment (old session, previous segment, a display
    label, an unknown id) is replaced before the selector is drawn, so it can never be submitted."""
    import app.service as svc
    seen = []
    real = svc.generate_recommendations
    monkeypatch.setattr(svc, "generate_recommendations", lambda req, *a, **k: seen.append(dict(req)) or real(req, *a, **k))
    REP_EXT_ALL.to_parquet(tmp_path / "garment_representation.parquet")
    (tmp_path / "ml_material_vocabulary.json").write_text(json.dumps(VOCAB_DOC), encoding="utf-8")
    (tmp_path / "category_capabilities.json").write_text(json.dumps(CAPS_EXT), encoding="utf-8")
    monkeypatch.setenv("CAGO_PROCESSED_DIR", str(tmp_path))
    at = st_testing.AppTest.from_file(APP, default_timeout=180)
    at.session_state["w_segment"] = "men"
    at.session_state["w_category"] = stale
    rerun(at)
    assert sb(at)["Garment category"].value == "shorts" and at.session_state["w_category"] == "shorts"
    at.sidebar.button[0].click()
    rerun(at)
    assert [(r["segment"], r["category"]) for r in seen] == [("men", "shorts")]
    assert at.session_state["cago_result"]["raw_request"]["detail_category"] == "shorts"


def test_language_switch_right_after_segment_change(app_ext, monkeypatch):
    import app.service as svc
    calls = []
    real = svc.generate_recommendations
    monkeypatch.setattr(svc, "generate_recommendations", lambda *a, **k: calls.append(1) or real(*a, **k))
    at = app_ext
    sb(at)["Segment"].set_value("men")
    rerun(at)
    switch(at, "tr")
    assert (sb(at)["Hedef grup"].value, sb(at)["Giysi kategorisi"].value) == ("men", "shorts")
    assert sb(at)["Hedef grup"].options[1] == "Erkek" and sb(at)["Giysi kategorisi"].options == ["Şort"]
    switch(at, "en")
    assert (sb(at)["Segment"].value, sb(at)["Garment category"].value) == ("men", "shorts") and calls == []


def test_result_from_previous_segment_is_identified_and_kept_on_language_switch(app_ext, monkeypatch):
    import app.service as svc
    calls = []
    real = svc.generate_recommendations
    monkeypatch.setattr(svc, "generate_recommendations", lambda *a, **k: calls.append(1) or real(*a, **k))
    at = app_ext
    sb(at)["Preferred dominant material"].set_value("cotton")
    rerun(at)
    at.sidebar.button[0].click()
    rerun(at)
    digest = at.session_state["cago_result"]["digest"]
    heads = [s.value for s in at.subheader]
    sb(at)["Segment"].set_value("men")
    rerun(at)
    assert any("settings changed" in w.value for w in at.warning)
    assert any("previous request: Segment: women · Garment category: trousers" in c.value for c in at.caption)
    switch(at, "tr")
    assert any("ayarlar değişti" in w.value for w in at.warning)
    assert any("önceki isteğe aittir: Hedef grup: Kadın · Giysi kategorisi: Pantolon" in c.value for c in at.caption)
    switch(at, "en")
    assert calls == [1] and at.session_state["cago_generation_count"] == 1 and at.session_state["cago_result"]["digest"] == digest
    assert [s.value for s in at.subheader] == heads
    sb(at)["Segment"].set_value("women")                                  # back to the generating request -> not stale any more
    rerun(at)
    sb(at)["Garment category"].set_value("trousers")
    rerun(at)
    assert not any("settings changed" in w.value for w in at.warning)


def test_category_specific_options_refresh(app_ext):
    at = app_ext
    def colours(seg, cat):
        return ["No preference"] + [c for c, _ in DATA_EXT.colours[(seg, cat)][:40]]
    assert sb(at)["Colour"].options == colours("women", "trousers")
    assert sb(at)["Preferred dominant material"].options[1:] == DATA_EXT.materials_for("trousers")
    sb(at)["Garment category"].set_value("shorts")
    rerun(at)
    assert sb(at)["Colour"].options == colours("women", "shorts")              # colours of the (women, shorts) cell
    assert sb(at)["Preferred dominant material"].options[1:] == DATA_EXT.materials_for("shorts")
    sb(at)["Segment"].set_value("men")
    rerun(at)
    assert sb(at)["Colour"].options == colours("men", "shorts")


# ================================================================ real data (skipped without the processed files)
@pytest.mark.skipif(not (PROCESSED / "garment_representation.parquet").is_file(), reason="processed data missing")
def test_real_data_categories_match_frozen_selector():
    data = load_app_data(PROCESSED)
    for (seg, cat), _ in data.rep_train.groupby(["target_segment", "detail_category"]):
        _, diag = select_templates(data.rep_train, {"target_segment": seg, "detail_category": cat, "soft_preferences": {}}, 1, 0)
        assert data.eligible_templates(seg, cat) == diag["eligible_templates"]
    assert "skirts" not in data.available_categories("baby")                  # V1 scenario S3: empty TRAIN pool


def test_fixture_train_rows_are_the_only_input():
    assert set(REP_TRAIN["split"]) == {"train"} and set(REP_EXT_TRAIN["split"]) == {"train"}
