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
def test_unsupported_fields_disabled_and_empty_cell_explained():
    at = st_testing.AppTest.from_file(APP, default_timeout=180)
    at.run()
    sb = {s.label: s for s in at.sidebar.selectbox}
    sb["Garment category"].set_value("socks_hosiery")
    at.run()
    dis = {s.label: s.disabled for s in at.sidebar.selectbox}
    assert dis["Fit"] and dis["Length"] and not dis["Stretch"]
    sb = {s.label: s for s in at.sidebar.selectbox}
    sb["Segment"].set_value("baby")
    at.run()
    sb = {s.label: s for s in at.sidebar.selectbox}
    sb["Garment category"].set_value("skirts")
    at.run()
    at.sidebar.button[0].click()
    at.run()
    assert not at.exception and any("no TRAIN garments" in e.value for e in at.error)
