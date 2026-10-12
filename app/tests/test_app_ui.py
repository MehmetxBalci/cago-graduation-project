"""Headless UI smoke tests with Streamlit's AppTest (no browser automation)."""
from __future__ import annotations

from pathlib import Path

import pytest

st_testing = pytest.importorskip("streamlit.testing.v1")
from app.adapters import missing_files  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
APP = str(ROOT / "app" / "streamlit_app.py")
HAS_DATA = missing_files(ROOT / "data" / "processed") == {}


def test_missing_data_screen(monkeypatch, tmp_path):
    monkeypatch.setenv("CAGO_PROCESSED_DIR", str(tmp_path))
    at = st_testing.AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception
    assert any("Required processed data files are missing" in e.value for e in at.error)


@pytest.mark.skipif(not HAS_DATA, reason="processed data missing")
def test_main_flow_renders_cards_and_chart(monkeypatch):
    monkeypatch.delenv("CAGO_PROCESSED_DIR", raising=False)
    at = st_testing.AppTest.from_file(APP, default_timeout=180)
    at.run()
    assert not at.exception and at.title[0].value == "CAGO"
    sb = {s.label: s for s in at.sidebar.selectbox}
    sb["Preferred dominant material"].set_value("linen")
    sb["Fit"].set_value("relaxed")
    at.sidebar.button[0].click()
    at.run()
    assert not at.exception
    heads = [s.value for s in at.subheader]
    assert any("Balanced" in h for h in heads) and any("Sorting-focused" in h for h in heads)
    assert any(h.value == "Pareto candidate overview" for h in at.header)
    texts = " ".join([x.value for x in at.markdown] + [x.value for x in at.success] + [x.value for x in at.warning] + [x.value for x in at.caption])
    assert "recyclability percentage" not in texts.lower() and "guaranteed recyclable" not in texts.lower()


@pytest.mark.skipif(not HAS_DATA, reason="processed data missing")
def test_unsupported_fields_disabled_and_empty_cell_explained(monkeypatch):
    """Real data, English and Turkish. AppTest `.options` are DISPLAY labels, so the expected options are produced with the
    widget's own formatter (`Selectbox.format_func`, the callable Streamlit registered for the rendered dropdown) applied to the
    canonical category identifiers of `available_categories`; the selected value itself stays a canonical identifier."""
    from app.adapters import load_app_data
    from app.i18n import get_translator
    from app.service import STATUS_NO_TEMPLATES, generate_recommendations

    monkeypatch.delenv("CAGO_PROCESSED_DIR", raising=False)
    data = load_app_data(ROOT / "data" / "processed")
    baby_categories = data.available_categories("baby")                     # canonical identifiers, e.g. "jumpsuits_overalls"
    assert data.eligible_templates("baby", "skirts") == 0 and "skirts" not in baby_categories   # V1 scenario S3: empty TRAIN pool
    at = st_testing.AppTest.from_file(APP, default_timeout=180)
    at.run()
    assert not at.exception

    def boxes():
        return {s.label: s for s in at.sidebar.selectbox}

    for lang, empty_pool_text in (("en", "no TRAIN garments"), ("tr", "TRAIN giysisi yok")):
        field = get_translator(lang).field                                  # widget labels from the same i18n catalog
        if lang != "en":
            at.button_group[0].set_value(lang)
            at.run()
            assert not at.exception
        boxes()[field("segment")].set_value("women")
        at.run()
        boxes()[field("category")].set_value("socks_hosiery")
        at.run()
        dis = {s.label: s.disabled for s in at.sidebar.selectbox}
        assert dis[field("fit")] and dis[field("length")] and not dis[field("stretch")]
        assert at.session_state["w_category"] == "socks_hosiery"

        boxes()[field("segment")].set_value("baby")
        at.run()
        assert not at.exception
        if baby_categories:
            category = boxes()[field("category")]
            display = category.format_func                                  # the widget's formatter, not a hand-made mapping
            assert category.options == [display(c) for c in baby_categories]
            assert display("skirts") not in category.options                # skirts excluded in this language
            assert category.value in baby_categories                        # selection stays a canonical identifier ...
            assert at.session_state["w_category"] == category.value         # ... in session state too
            assert display(category.value) in category.options              # only its label is displayed
            if lang == "tr":
                assert not set(baby_categories) & set(category.options)     # no raw identifier is shown in Turkish
        else:
            assert field("category") not in boxes() and at.sidebar.button[0].disabled

        r = generate_recommendations({"target_segment": "baby", "detail_category": "skirts"}, data=data, lang=lang)
        assert r["status"] == STATUS_NO_TEMPLATES and empty_pool_text in r["messages"][-1]["text"]
        assert r["raw_request"] == {"target_segment": "baby", "detail_category": "skirts"}
