"""Template baseline generator tests (synthetic) + real-data smoke test."""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest

from cago.generation.baseline import (GenerationConfig, candidates_hash, generate_baseline, normalize_candidate,
                                      oracle_eval, public_components)
from cago.generation.distance import template_distance, topology_preserved
from cago.generation.mutations import clone_components, replay
from cago.generation.support_tables import build_support_tables
from cago.generation.template_selector import select_templates, template_components
from cago.oracle.engine import evaluate_garment
from cago.oracle.selection import make_component
from cago.requirements.schema import SOFT_FIELDS
from cago.requirements.validation import RequirementContext, validate_candidate

VOCAB = {"cotton", "polyester", "linen", "nylon", "wool", "elastane", "viscose"}
CTX = RequirementContext(
    target_segments=frozenset({"women", "men"}), categories=frozenset({"trousers", "shorts"}),
    materials=frozenset(VOCAB | {"silk", "zinc"}), capabilities={}, component_classes=frozenset({"surface_component", "lining_component"}),
    component_names=frozenset({"shell", "lining"}), ml_tokens=frozenset({"OTHER", "PAD"}))


def comp(i, cls, name, mats, gid):
    return {"component_id": f"{gid}_c{i}", "source_component_index": i, "component_class": cls,
            "component_name_normalized": name, "material_count": len(mats), "materials": [m for m, _ in mats],
            "materials_raw": [m for m, _ in mats], "ml_tokens": [m if m in VOCAB else "OTHER" for m, _ in mats],
            "percentages": [float(p) for _, p in mats], "pct_sum": float(sum(p for _, p in mats))}


def garment(gid, parent, split, shell, lining, seg="women", cat="trousers", usable=True, colour="black"):
    comps = [comp(0, "surface_component", "shell", shell, gid), comp(1, "lining_component", "lining", lining, gid)]
    other = any(m not in VOCAB for c in comps for m in c["materials"])
    return {"garment_id": gid, "parent_product_id": parent, "split": split, "target_segment": seg, "detail_category": cat,
            "normalized_colour": colour, "fit_label": None, "length_label": None, "text_evidence_tags": [],
            "is_fully_usable": usable, "has_unmapped_material": False, "has_other_token": other, "components": comps}


def make_rep(extra=()):
    rows = [
        garment("T1", "p1", "train", [("cotton", 60), ("polyester", 40)], [("polyester", 100)]),
        garment("T2", "p2", "train", [("cotton", 98), ("elastane", 2)], [("viscose", 100)]),
        garment("T3", "p3", "train", [("linen", 100)], [("cotton", 100)]),
        garment("T4", "p4", "train", [("polyester", 70), ("nylon", 30)], [("nylon", 100)]),
        garment("T5", "p5", "train", [("wool", 50), ("cotton", 50)], [("polyester", 100)]),
        # val/test rows in the SAME cell, with a material (silk) that exists nowhere in TRAIN
        garment("V1", "p6", "val", [("silk", 100)], [("viscose", 100)]),
        garment("X1", "p7", "test", [("silk", 60), ("cotton", 40)], [("silk", 100)]),
        # other cells: must never be used for women/trousers
        garment("M1", "p8", "train", [("nylon", 100)], [("nylon", 100)], seg="men"),
        garment("S1", "p9", "train", [("wool", 100)], [("wool", 100)], cat="shorts"),
        # ineligible train garments in the cell
        garment("B1", "p10", "train", [("cotton", 70), ("zinc", 30)], [("cotton", 100)]),       # OTHER token
        garment("B2", "p11", "train", [("cotton", 100)], [("cotton", 100)], usable=False),     # anomalous component
        garment("B3", "p12", "train", [("cotton", 60), ("linen", 39.5)], [("cotton", 100)]),   # sums to 99.5
        *extra,
    ]
    return pd.DataFrame(rows)


def request(forbidden=(), **soft):
    s = {k: None for k in SOFT_FIELDS}
    s.update(soft)
    return {"target_segment": "women", "detail_category": "trousers",
            "hard_constraints": {"forbidden_materials": sorted(forbidden)}, "soft_preferences": s, "warnings": []}


CFG = GenerationConfig(n_templates=5, mutations_per_template=4, seed=7)
REP = make_rep()
SUP = build_support_tables(REP)


def gen(req=None, cfg=CFG, rep=REP, sup=SUP):
    return generate_baseline(req or request(), rep, sup, CTX, cfg)


# ---------------- template selection
def test_templates_are_exact_cell_train_only_and_clean():
    ts, diag = select_templates(REP, request(), 10, 1)
    assert {t.garment_id for t in ts} == {"T1", "T2", "T3", "T4", "T5"}
    assert all(t.split == "train" and t.target_segment == "women" and t.detail_category == "trousers" for t in ts)
    assert diag["ineligible_reasons"] == {"non_vocab_material_token": 1, "anomalous_or_missing_component": 1,
                                          "component_sum_not_100": 1}


def test_one_template_per_parent_product():
    rep = make_rep([garment("T1b", "p1", "train", [("cotton", 60), ("polyester", 40)], [("polyester", 100)], colour="red")])
    ts, _ = select_templates(rep, request(), 10, 1)
    assert len([t for t in ts if t.parent_product_id == "p1"]) == 1


def test_preferences_rank_but_do_not_filter():
    base, _ = select_templates(REP, request(), 10, 1)
    pref, _ = select_templates(REP, request(preferred_dominant_material="wool", breathability="high"), 10, 1)
    assert {t.garment_id for t in pref} == {t.garment_id for t in base}                  # nothing filtered out
    ranked, _ = select_templates(REP, request(breathability="high"), 10, 1)
    assert ranked[0].rank_score >= ranked[-1].rank_score
    assert ranked[0].garment_id in {"T3", "T2"}                                           # cotton/linen outrank polyester-heavy


# ---------------- topology / no mixing
def test_one_template_supplies_the_entire_component_hierarchy():
    res = gen()
    assert res["candidates"]
    tmap = {t.garment_id: t for t in res["templates"]}
    for c in res["candidates"]:
        t = tmap[c["template_garment_id"]]
        assert [x["component_id"] for x in c["components"]] == [x["component_id"] for x in t.components]
        assert [(x["component_class"], x["component_name_normalized"]) for x in c["components"]] == \
            [(x["component_class"], x["component_name_normalized"]) for x in t.components]
        assert topology_preserved(public_components(t.components), c["components"])
        assert [len(x["materials"]) for x in c["components"]] == [len(x["materials"]) for x in t.components]


def test_no_cross_garment_component_mixing():
    res = gen(cfg=GenerationConfig(n_templates=5, mutations_per_template=8, seed=3))
    owner = {c["component_id"]: g.garment_id for g in REP.itertuples() for c in g.components}
    for c in res["candidates"]:
        assert {owner[x["component_id"]] for x in c["components"]} == {c["template_garment_id"]}
        assert c["template_garment_id"] in {"T1", "T2", "T3", "T4", "T5"}


# ---------------- determinism
def test_deterministic_with_seed():
    a, b = gen(), gen()
    assert candidates_hash(a["candidates"]) == candidates_hash(b["candidates"]) and a["candidates"]
    assert [c["candidate_id"] for c in a["candidates"]] == [c["candidate_id"] for c in b["candidates"]]
    other = gen(cfg=GenerationConfig(n_templates=5, mutations_per_template=4, seed=8))
    assert candidates_hash(other["candidates"]) != candidates_hash(a["candidates"])


# ---------------- hard constraints
def test_forbidden_material_never_appears_and_is_repaired():
    res = gen(request(forbidden={"polyester"}))
    assert res["candidates"]
    for c in res["candidates"]:
        assert all(m["material"] != "polyester" for x in c["components"] for m in x["materials"])
        assert c["hard_validation"] == {"passed": True, "issues": []}
    repaired = [c for c in res["candidates"] if c["n_forbidden_repairs"]]
    assert repaired and {c["template_garment_id"] for c in repaired} <= {"T1", "T4", "T5"}
    assert all(e["reason"] == "forbidden_repair" for c in repaired for e in c["mutation_log"][:c["n_forbidden_repairs"]])
    assert all(t.n_forbidden_slots == 0 for t in res["templates"][:2])                    # clean templates ranked first


def test_unrepairable_forbidden_template_is_dropped():
    res = gen(request(forbidden={"polyester", "cotton", "viscose", "nylon"}))             # no lining material is admissible
    assert res["candidates"] == [] and res["rejected"]["unrepairable_forbidden_material"] >= 1
    assert res["failed_templates"]


def test_pad_and_other_never_appear():
    res = gen(cfg=GenerationConfig(n_templates=5, mutations_per_template=8, seed=11))
    mats = {m["material"] for c in res["candidates"] for x in c["components"] for m in x["materials"]}
    assert mats <= VOCAB and not ({"OTHER", "PAD", "other", "pad"} & mats) and "zinc" not in mats
    assert "zinc" not in SUP.allowed("trousers", "surface_component")                      # rare/OTHER material not offered
    issues = validate_candidate([{"component_class": "surface_component", "component_name_normalized": "shell",
                                  "materials": [{"material": "OTHER", "pct": 50.0}, {"material": "cotton", "pct": 50.0}]}], [], CTX)
    assert "non_physical_token" in [i.code for i in issues]


def test_percentages_sum_to_100_and_non_negative():
    res = gen(cfg=GenerationConfig(n_templates=5, mutations_per_template=10, seed=5))
    assert len(res["candidates"]) > 10
    for c in res["candidates"]:
        for x in c["components"]:
            assert abs(sum(m["pct"] for m in x["materials"]) - 100) <= 1e-6
            assert all(m["pct"] >= 0 for m in x["materials"])
        assert validate_candidate(c["components"], [], CTX) == []


def test_single_material_components_get_no_percentage_mutation():
    res = gen(cfg=GenerationConfig(n_templates=5, mutations_per_template=10, seed=2))
    for c in res["candidates"]:
        for e in c["mutation_log"]:
            if e["type"] == "percentage":
                assert len(c["components"][e["component_index"]]["materials"]) >= 2


# ---------------- TRAIN-only support
def test_substitutions_come_from_train_support_only():
    res = gen(cfg=GenerationConfig(n_templates=5, mutations_per_template=12, seed=9))
    subs = [(c, e) for c in res["candidates"] for e in c["mutation_log"] if e["type"] == "substitution"]
    assert subs
    for c, e in subs:
        cls = c["components"][e["component_index"]]["component_class"]
        assert e["to_material"] in SUP.allowed("trousers", cls)
        assert e["pct"] <= SUP.pct_max("trousers", cls, e["to_material"]) + 1e-9
        assert e["to_material"] != "silk"
    assert not any(m["material"] == "silk" for c in res["candidates"] for x in c["components"] for m in x["materials"])


def test_support_tables_have_no_val_test_leakage():
    assert SUP.splits_used == ("train",) and SUP.n_train_garments == int((REP["split"] == "train").sum())
    assert "silk" not in SUP.allowed("trousers", "surface_component") and "silk" not in SUP.allowed("trousers", "lining_component")
    assert all("silk" not in c for c in SUP.materials_by_category.values())
    only_train = build_support_tables(REP[REP["split"] == "train"])
    assert SUP.materials_by_category_class == only_train.materials_by_category_class
    assert SUP.combos_by_category_class == only_train.combos_by_category_class
    assert SUP.pct_max("trousers", "surface_component", "cotton") == only_train.pct_max("trousers", "surface_component", "cotton")
    empty = build_support_tables(REP[REP["split"] != "train"])
    assert empty.n_train_garments == 0 and not empty.materials_by_category
    # val/test content cannot change the tables
    rows = REP.to_dict("records")
    for r in rows:
        if r["split"] != "train":                                   # rewrite every val/test garment
            r["components"] = garment("Z", "pz", r["split"], [("nylon", 100)], [("nylon", 100)])["components"]
    assert build_support_tables(pd.DataFrame(rows)).materials_by_category_class == SUP.materials_by_category_class
    with pytest.raises(ValueError):
        generate_baseline(request(), REP, SUP.__class__(splits_used=("train", "val")), CTX, CFG)


# ---------------- mutation log / distance / oracle
def test_mutation_log_matches_actual_changes():
    res = gen(cfg=GenerationConfig(n_templates=5, mutations_per_template=10, seed=4))
    tmap = {t.garment_id: t for t in res["templates"]}
    assert res["candidates"]
    for c in res["candidates"]:
        t = tmap[c["template_garment_id"]]
        assert replay(t.components, c["mutation_log"]) is not None
        rep_comps = public_components(replay(t.components, c["mutation_log"]))
        assert rep_comps == c["components"]                                                # log reproduces the candidate exactly
        d = template_distance(public_components(t.components), c["components"])
        assert d == c["template_distance"]
        changed_slots = {(e["component_index"], e["slot"]) for e in c["mutation_log"] if e["type"] == "substitution"}
        assert d["n_substitutions"] <= len(changed_slots)                                  # a slot can be substituted twice
        for e in c["mutation_log"]:
            if e["type"] == "percentage":
                assert abs(sum(e["pct_after"]) - sum(e["pct_before"])) < 1e-9 and e["pct_after"][0] < e["pct_before"][0]
    broken = [dict(e) for e in res["candidates"][0]["mutation_log"]]
    broken[0] = {**broken[0], "from_material": "does_not_match"} if broken[0]["type"] == "substitution" else broken[0]
    if broken[0]["type"] == "substitution":
        with pytest.raises(ValueError):
            replay(tmap[res["candidates"][0]["template_garment_id"]].components, broken)


def test_template_distance_is_explainable():
    t = [{"component_id": "a", "source_component_index": 0, "component_class": "surface_component",
          "component_name_normalized": "shell", "materials": [{"material": "cotton", "pct": 60.0}, {"material": "polyester", "pct": 40.0}]}]
    c = clone_components(t)
    c[0]["materials"][0].update(material="linen", pct=55.0); c[0]["materials"][1]["pct"] = 45.0
    d = template_distance(t, c)
    assert (d["n_substitutions"], d["abs_pct_change_total"], d["n_pct_changed_slots"]) == (1, 10.0, 2)
    assert d["diagnostic_distance"] == pytest.approx(1.1) and "plausibility" in d["note"]
    assert template_distance(t, clone_components(t))["diagnostic_distance"] == 0
    bad = clone_components(t); bad.append(bad[0])
    with pytest.raises(ValueError):
        template_distance(t, bad)


def test_oracle_evaluates_generated_candidates():
    res = gen()
    for c in res["candidates"]:
        o = c["oracle"]
        assert {"sr1_violation", "sr2_violation", "sr3_violation", "sr4_violation", "sr5_violation", "violation_count"} <= set(o)
        row = evaluate_garment("x", c["normalized_colour"], [make_component(x["component_id"], x["component_name_normalized"],
                               x["component_class"], [(m["material"], m["pct"]) for m in x["materials"]]) for x in c["components"]])
        assert o["violation_count"] == row["violation_count"] and o["any_violation"] == row["any_violation"]
        assert c["property_proxies"]["note"].startswith("DIAGNOSTIC ONLY")
    mono = oracle_eval("x", "black", [{"component_id": "c", "component_name_normalized": "shell", "component_class": "surface_component",
                                         "materials": [{"material": "linen", "pct": 100.0}]}])
    assert mono["sr1_violation"] and mono["sr4_violation"] and mono["sr1_reason"] == "unsupported_mono"


def test_normalize_candidate_uses_representation_order():
    c = [{"component_id": "a", "component_class": "surface_component", "component_name_normalized": "shell",
          "materials": [{"material": "wool", "pct": 20.0}, {"material": "cotton", "pct": 80.0}]}]
    assert [m["material"] for m in normalize_candidate(c)[0]["materials"]] == ["cotton", "wool"]
    assert template_components(REP.iloc[0].components)[0]["materials"][0]["material"] == "cotton"


# ---------------- real data (skipped when outputs are missing)
PROCESSED = Path(os.environ.get("CAGO_PROCESSED_DIR") or Path(__file__).resolve().parents[1] / "data" / "processed")


@pytest.mark.skipif(not (PROCESSED / "garment_representation.parquet").exists(), reason="representation outputs missing")
def test_real_data_generation_is_valid_deterministic_and_train_only():
    from cago.requirements.validation import validate_request
    rep = pd.read_parquet(PROCESSED / "garment_representation.parquet")
    ctx = RequirementContext.from_processed(PROCESSED)
    sup = build_support_tables(rep)
    assert sup.splits_used == ("train",) and sup.n_train_garments == int((rep["split"] == "train").sum())
    v = validate_request({"target_segment": "women", "detail_category": "trousers", "forbidden_materials": ["polyester"],
                          "preferred_dominant_material": "linen", "breathability": "high"}, ctx)
    cfg = GenerationConfig(n_templates=4, mutations_per_template=3, seed=1)
    a = generate_baseline(v.request, rep, sup, ctx, cfg)
    b = generate_baseline(v.request, rep, sup, ctx, cfg)
    assert a["candidates"] and candidates_hash(a["candidates"]) == candidates_hash(b["candidates"])
    train_ids = set(rep.loc[rep["split"] == "train", "garment_id"])
    for c in a["candidates"]:
        assert c["template_garment_id"] in train_ids
        assert validate_candidate(c["components"], ["polyester"], ctx) == []
        assert not any(m["material"] in ("polyester", "OTHER", "PAD") for x in c["components"] for m in x["materials"])
