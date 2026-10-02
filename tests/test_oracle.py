"""Oracle v1 tests: synthetic rule tests + real-data reproduction of the published counts."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from cago.oracle.config import PUBLISHED_COUNTS, PUBLISHED_N, canon_material
from cago.oracle.engine import evaluate_garment
from cago.oracle.selection import make_component


def comp(name, cls, mats, cid=None):
    """mats: dict material -> pct (or list of (material, pct) to allow duplicates)."""
    items = list(mats.items()) if isinstance(mats, dict) else mats
    return make_component(cid or f"c_{name}", name, cls, items)


def surface(mats, name="main"):
    return comp(name, "surface_component", mats)


def ev(comps, colour="Red"):
    return evaluate_garment("g1", colour, comps)


# ---------- SR1 ----------
@pytest.mark.parametrize("mat,viol,reason", [("cotton", False, "supported_mono"), ("polyester", False, "supported_mono"),
                                             ("linen", True, "unsupported_mono"), ("elastane", True, "unsupported_mono")])
def test_sr1_mono(mat, viol, reason):
    r = ev([surface({mat: 100.0})])
    assert (r["sr1_violation"], r["sr1_reason"]) == (viol, reason)


@pytest.mark.parametrize("mats,viol,reason", [
    ({"cotton": 95.0, "elastane": 5.0}, False, "supported_binary"),
    ({"elastane": 10.0, "cotton": 90.0}, False, "supported_binary"),      # order-insensitive
    ({"cotton": 50.0, "linen": 50.0}, True, "unsupported_binary"),
    ({"nylon": 80.0, "elastane": 20.0}, True, "unsupported_binary"),      # not in baseline set
])
def test_sr1_binary(mats, viol, reason):
    r = ev([surface(mats)])
    assert (r["sr1_violation"], r["sr1_reason"]) == (viol, reason)


def test_three_fibres_sr1_and_sr2():
    r = ev([surface({"cotton": 60.0, "polyester": 30.0, "elastane": 10.0})])
    assert r["sr1_violation"] and r["sr1_reason"] == "more_than_two_fibres"
    assert r["sr2_violation"] and r["sr2_fibre_count"] == 3
    assert not ev([surface({"cotton": 60.0, "polyester": 40.0})])["sr2_violation"]


def test_no_readable_material():
    r = ev([])
    assert r["sr1_violation"] and r["sr1_reason"] == "no_readable_material"
    assert not r["sr2_violation"] and not r["sr3_violation"] and not r["sr5_violation"]
    assert r["readable_component_source"] is None


def test_zero_pct_material_ignored_in_sr1_to_sr3():
    r = ev([surface({"cotton": 100.0, "polyester": 0.0})])
    assert r["n_distinct_fibres"] == 1
    assert not r["sr1_violation"] and not r["sr3_violation"]
    r = ev([surface({"cotton": 60.0, "polyester": 40.0, "elastane": 0.0})])
    assert not r["sr2_violation"] and r["n_distinct_fibres"] == 2


def test_duplicate_materials_aggregated_and_canonicalized():
    r = ev([surface([("cotton", 3.0), ("Cotton", 2.0), ("PES", 95.0)])])
    assert json.loads(r["readable_materials"]) == [{"material": "polyester", "pct": 95.0},
                                                   {"material": "cotton", "pct": 5.0}]
    assert not r["sr3_violation"]       # 3+2 aggregates to exactly 5.0
    assert canon_material("Merino") == "wool" and canon_material("polyamide") == "nylon"
    assert canon_material("cashmere") == "wool" and canon_material("  ") is None


# ---------- SR3 ----------
def test_sr3_boundary_and_dominant():
    r = ev([surface({"cotton": 95.1, "elastane": 4.9})])
    assert r["sr3_violation"] and json.loads(r["sr3_trigger_materials"]) == [{"material": "elastane", "pct": 4.9}]
    assert not ev([surface({"cotton": 95.0, "elastane": 5.0})])["sr3_violation"]       # exactly 5.0 passes
    # dominant fibre is never checked, even if below 5 (3 equal-ish fibres: dominant pct 3.4 can't be < others)
    assert not ev([surface({"cotton": 4.0})])["sr3_violation"]
    r = ev([surface({"cotton": 4.0, "polyester": 3.0})])      # dominant 4.0 not checked, minor 3.0 checked
    assert [t["material"] for t in json.loads(r["sr3_trigger_materials"])] == ["polyester"]


# ---------- SR4 ----------
def test_sr4_exact_black_only():
    for colour in ("Black", "BLACK", "  black "):
        r = ev([surface({"cotton": 100.0})], colour)
        assert r["sr4_violation"] and r["sr4_normalized_colour"] == "black"
    for colour in ("black/white", "Washed black", "Blackberry", None, ""):
        assert not ev([surface({"cotton": 100.0})], colour)["sr4_violation"]


# ---------- SR5 ----------
def test_sr5_coating_selected_before_shell():
    shell = comp("shell", "surface_component", {"cotton": 100.0})
    coat = comp("coating", "surface_component", {"polyurethane": 100.0})
    lining = comp("lining", "lining_component", {"polyurethane": 100.0})
    r = ev([shell, coat, lining])          # coating comes later in order but is selected as the reference
    assert r["sr5_surface_component"] == "coating" and r["sr5_surface_source"] == "surface_coating"
    assert not r["sr5_violation"]          # polyurethane lining present in coating reference
    r = ev([shell, lining])                # without coating the shell is the reference -> mismatch
    assert r["sr5_surface_component"] == "shell" and r["sr5_violation"]
    # SR1-SR3 readable component is still the FIRST surface component (shell), independent of SR5
    assert ev([shell, coat, lining])["readable_component_name"] == "shell"


def test_sr5_hidden_boundary_and_membership():
    shell = comp("shell", "surface_component", {"cotton": 100.0})
    assert not ev([shell, comp("lining", "lining_component", {"polyester": 5.0, "cotton": 95.0})])["sr5_violation"]
    r = ev([shell, comp("lining", "lining_component", {"polyester": 5.1, "cotton": 94.9})])
    assert r["sr5_violation"] and r["sr5_hidden_component"] == "lining"
    assert json.loads(r["sr5_trigger_materials"]) == [{"material": "polyester", "pct": 5.1}]
    assert not ev([shell, comp("lining", "lining_component", {"cotton": 100.0})])["sr5_violation"]   # present at surface


def test_sr5_hidden_by_name_or_class():
    shell = comp("shell", "surface_component", {"cotton": 100.0})
    assert ev([shell, comp("padding", "other_component", {"polyester": 100.0})])["sr5_violation"]    # name only
    assert ev([shell, comp("weird", "filling_component", {"polyester": 100.0})])["sr5_violation"]    # class only
    assert not ev([shell, comp("pocket_lining", "pocket_component", {"polyester": 100.0})])["sr5_violation"]


def test_sr5_no_hidden_component_passes():
    assert not ev([surface({"cotton": 100.0}), comp("collar", "trim_component", {"nylon": 100.0})])["sr5_violation"]


def test_first_component_fallback():
    trim = comp("collar", "trim_component", {"cotton": 100.0})
    lining = comp("lining", "lining_component", {"cotton": 100.0})
    r = ev([trim, lining])
    assert r["readable_component_source"] == "first_component_fallback" and r["readable_component_name"] == "collar"
    assert r["sr5_surface_source"] == "first_component_fallback" and not r["sr5_violation"]
    assert ev([trim, comp("lining", "lining_component", {"polyester": 100.0})])["sr5_violation"]


def test_violation_count_is_indicator_count():
    r = ev([surface({"cotton": 96.0, "polyester": 3.0, "elastane": 1.0}),
            comp("lining", "lining_component", {"nylon": 100.0})], "Black")
    assert (r["sr1_violation"], r["sr2_violation"], r["sr3_violation"], r["sr4_violation"], r["sr5_violation"]) == (True,) * 5
    assert r["violation_count"] == 5 and r["any_violation"]
    assert ev([surface({"cotton": 100.0})])["violation_count"] == 0


# ---------- real-data reproduction ----------
def _processed_dir() -> Path | None:
    p = os.environ.get("CAGO_PROCESSED_DIR") or str(Path(__file__).resolve().parents[1] / "data" / "processed")
    return Path(p) if (Path(p) / "component_materials.parquet").exists() else None


@pytest.mark.skipif(_processed_dir() is None, reason="processed parquet not available")
def test_reproduces_published_counts():
    from cago.oracle.engine import run_oracle
    res = run_oracle(_processed_dir())
    assert len(res) == PUBLISHED_N and res["garment_id"].is_unique
    got = {"SR1": res.sr1_violation.sum(), "SR2": res.sr2_violation.sum(), "SR3": res.sr3_violation.sum(),
           "SR4": res.sr4_violation.sum(), "SR5": res.sr5_violation.sum(), "ANY": res.any_violation.sum()}
    assert {k: int(v) for k, v in got.items()} == PUBLISHED_COUNTS
    assert (res.violation_count == res[["sr1_violation", "sr2_violation", "sr3_violation",
                                        "sr4_violation", "sr5_violation"]].sum(axis=1)).all()
