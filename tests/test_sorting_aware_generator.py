"""Generator B: topology, hard constraints, determinism, budget, duplicates, TRAIN-only support, baseline untouched."""
from __future__ import annotations

import copy
import inspect
from pathlib import Path

import pandas as pd
import pytest

from cago.benchmark.sorting_aware_requests import assert_dev_only, dev_view
from cago.generation.baseline import GenerationConfig, candidates_hash, generate_baseline, oracle_eval
from cago.generation.distance import topology_preserved
from cago.generation.support_tables import build_support_tables
from cago.generation.template_selector import composition_signature
from cago.generation_sorting.config import MODE_CONFIGS, NONDOMINATED_LOCAL, SortingAwareGenerationConfig
from cago.generation_sorting.generator import generate_sorting_aware
from cago.generation_sorting.trace import verify_trace
from cago.requirements.validation import validate_candidate
from tests.sorting_fixtures import DEV, REP, SUP
from tests.synthetic_data import CTX, request

KW = dict(n_templates=6, candidates_per_template=6, seed=3)


def gen(req=None, support=SUP, rep=DEV, **kw):
    cfg = SortingAwareGenerationConfig(**{**KW, **MODE_CONFIGS["B3"], **kw})
    return generate_sorting_aware(req or request(), rep, support, CTX, cfg)


def test_whole_garment_topology_and_labels_preserved():
    res = gen(request(fit="slim"))
    tmap = {t.garment_id: t for t in res["templates"]}
    assert res["candidates"]
    for c in res["candidates"]:
        t = tmap[c["template_garment_id"]]
        assert t.split == "train" and c["normalized_colour"] == t.colour                        # colour (SR4) never mutated
        assert topology_preserved([{k: v for k, v in x.items() if not k.startswith("_")} for x in t.components], c["components"])
        assert [(x["component_class"], x["component_name_normalized"], x["component_id"]) for x in c["components"]] == \
            [(x["component_class"], x["component_name_normalized"], x["component_id"]) for x in t.components]
        assert {x["component_id"].split("_c")[0] for x in c["components"]} == {c["template_garment_id"]}   # one template, no mixing
        assert all(len(a["materials"]) == len(b["materials"]) for a, b in zip(c["components"], t.components))


def test_hard_constraints_always_respected_and_no_special_tokens():
    req = request(forbidden={"polyester", "nylon"})
    for kw in (MODE_CONFIGS["B1"], MODE_CONFIGS["B2"], MODE_CONFIGS["B3"], {**MODE_CONFIGS["B3"], "policy": NONDOMINATED_LOCAL}):
        res = generate_sorting_aware(req, DEV, SUP, CTX, SortingAwareGenerationConfig(**{**KW, **kw}))
        assert res["candidates"]
        for c in res["candidates"]:
            mats = {m["material"] for x in c["components"] for m in x["materials"]}
            assert not (mats & {"polyester", "nylon", "OTHER", "PAD"})
            assert validate_candidate(c["components"], ["polyester", "nylon"], CTX) == []
            for x in c["components"]:                                                          # exact 100, non-negative
                assert abs(sum(m["pct"] for m in x["materials"]) - 100) <= 1e-6 and all(m["pct"] >= 0 for m in x["materials"])
            assert c["hard_validation"]["passed"] is True


def test_strict_policy_never_ends_with_more_violations_than_before_repair():
    res = gen(request(stretch="low"))
    n = 0
    for c in res["candidates"]:
        pre = oracle_eval("p", c["normalized_colour"], c["pre_repair_components"])["violation_count"]
        assert c["oracle"]["violation_count"] <= pre
        n += c["oracle"]["violation_count"] < pre
        t = next(t for t in res["templates"] if t.garment_id == c["template_garment_id"])
        assert verify_trace(t.components, c["pre_repair_components"], c["repair_trace"], c["components"])
    assert n > 0


def test_repair_log_entries_are_replayable_and_faithful():
    from cago.generation.mutations import replay
    res = gen()
    tmap = {t.garment_id: t for t in res["templates"]}
    for c in res["candidates"]:
        assert [[(m["material"], m["pct"]) for m in x["materials"]] for x in replay(tmap[c["template_garment_id"]].components, c["mutation_log"])] == \
            [[(m["material"], m["pct"]) for m in x["materials"]] for x in c["components"]]
        assert c["n_mutations"] == len(c["mutation_log"])


def test_duplicate_compositions_rejected_within_a_request():
    res = gen(candidates_per_template=14, n_templates=3)
    sigs = [composition_signature(c["components"]) for c in res["candidates"]]
    assert len(sigs) == len(set(sigs)) > 5
    assert all(composition_signature(c["components"]) not in {composition_signature(t.components) for t in res["templates"]} for c in res["candidates"])
    assert res["rejected"].get("duplicate_candidate", 0) + res["rejected"].get("identical_to_template", 0) >= 0


def test_deterministic_for_same_seed_and_seed_sensitive():
    a, b = gen(), gen()
    assert [c["candidate_id"] for c in a["candidates"]] == [c["candidate_id"] for c in b["candidates"]]
    assert [c["components"] for c in a["candidates"]] == [c["components"] for c in b["candidates"]]
    assert [c["repair_trace"] for c in a["candidates"]] == [c["repair_trace"] for c in b["candidates"]]
    assert a["search"] == b["search"] and a["rejected"] == b["rejected"]
    c = gen(seed=99)
    assert [x["components"] for x in c["candidates"]] != [x["components"] for x in a["candidates"]]


def test_search_budget_is_bounded_and_generation_terminates():
    res = gen(max_proposal_attempts=2, candidates_per_template=5)
    assert res["attempts"] <= KW["n_templates"] * 5 * 2
    assert len(res["candidates"]) <= KW["n_templates"] * 5
    cfg = SortingAwareGenerationConfig(**{**KW, **MODE_CONFIGS["B3"], "max_repair_steps": 2, "max_repair_proposals_per_step": 3})
    r = generate_sorting_aware(request(), DEV, SUP, CTX, cfg)
    assert all(len(c["repair_trace"]) <= 2 * 3 for c in r["candidates"])
    assert r["search"].get("repair_steps_started", 0) <= len(r["candidates"]) * 2 * 6 + 10
    none = gen(max_repair_steps=0)
    assert all(c["repair_trace"] == [] for c in none["candidates"])


def test_only_train_support_creates_new_materials_and_combinations():
    only_train = build_support_tables(REP[REP["split"] == "train"])
    assert SUP.materials_by_category_class == only_train.materials_by_category_class and SUP.combos_by_category_class == only_train.combos_by_category_class
    assert SUP.splits_used == ("train",)
    # VAL-only combination {linen, wool} and TEST-only garments contribute nothing
    assert SUP.combo_count("trousers", "surface_component", {"linen", "wool"}) == 0 and "wool" in SUP.allowed("trousers", "surface_component")
    assert SUP.count("trousers", "surface_component", "wool") == 3                                  # TEST/VAL wool rows not counted
    res = gen(candidates_per_template=10)
    for c in res["candidates"]:
        for s in c["repair_trace"]:
            for e in s["entries"]:
                if e["type"] == "substitution" and e["reason"] and e["reason"].startswith("sorting_repair") and s["operation"] != "revert_mutation_step":
                    assert e["to_material"] in SUP.allowed("trousers", c["components"][e["component_index"]]["component_class"])
        for x in c["components"]:
            combo = frozenset(m["material"] for m in x["materials"])
            assert combo != frozenset({"linen", "wool"})                                            # never produced from VAL-only evidence
    bad = SUP.__class__(splits_used=("train", "val"))
    with pytest.raises(ValueError):
        generate_sorting_aware(request(), DEV, bad, CTX)


def test_val_rows_do_not_alter_train_support_tables():
    rows = DEV.to_dict("records")
    from tests.synthetic_data import garment
    for r in rows:
        if r["split"] == "val":
            r["components"] = garment("Z", "pz", "val", [("elastane", 100)], [("viscose", 100)])["components"]
    assert build_support_tables(pd.DataFrame(rows)).materials_by_category_class == SUP.materials_by_category_class


def test_no_test_usage_anywhere_in_the_development_pipeline():
    assert "test" not in set(DEV["split"]) and "test" in set(REP["split"])
    assert_dev_only(DEV)
    with pytest.raises(ValueError):
        assert_dev_only(REP)
    scrambled = REP.to_dict("records")
    from tests.synthetic_data import garment
    for r in scrambled:
        if r["split"] == "test":
            r["components"] = garment("Z", "pz", "test", [("acrylic" if False else "elastane", 100)], [("viscose", 100)])["components"]
            r["target_segment"], r["detail_category"] = "women", "trousers"
    a = gen(rep=dev_view(REP))
    b = gen(rep=dev_view(pd.DataFrame(scrambled)))
    assert [c["components"] for c in a["candidates"]] == [c["components"] for c in b["candidates"]]
    root = Path(__file__).resolve().parents[1]
    for f in list((root / "cago" / "generation_sorting").glob("*.py")) + [root / "cago/benchmark/sorting_aware_requests.py",
                                                                          root / "cago/benchmark/sorting_aware_comparison.py",
                                                                          root / "scripts/run_sorting_aware_comparison.py", root / "scripts/run_sorting_aware_generator.py"]:
        src = f.read_text(encoding="utf-8")
        assert '"test"' not in src and "'test'" not in src and "== \"test\"" not in src, f.name        # no TEST split literal anywhere


def test_baseline_generator_output_unchanged_and_shared_state_untouched():
    snapshot = copy.deepcopy((SUP.materials_by_category_class, SUP.combos_by_category_class))
    b1 = generate_baseline(request(forbidden={"nylon"}, stretch="low"), DEV, SUP, CTX, GenerationConfig(n_templates=5, mutations_per_template=6, seed=3))
    assert len(b1["candidates"]) == 30 and candidates_hash(b1["candidates"]) == "4e721ed60bfce95c4201bb1d1cf1324a"
    b2 = generate_baseline(request(), DEV, SUP, CTX, GenerationConfig(n_templates=4, mutations_per_template=5, seed=11))
    assert len(b2["candidates"]) == 20 and candidates_hash(b2["candidates"]) == "efdb01840c6bef98df5f76a37192e393"
    gen()                                                                                          # Generator B run in between
    gen(request(forbidden={"nylon"}))
    b1b = generate_baseline(request(forbidden={"nylon"}, stretch="low"), DEV, SUP, CTX, GenerationConfig(n_templates=5, mutations_per_template=6, seed=3))
    assert candidates_hash(b1b["candidates"]) == candidates_hash(b1["candidates"])
    assert (SUP.materials_by_category_class, SUP.combos_by_category_class) == snapshot
    assert "sorting_aware" not in inspect.getsource(generate_baseline) and not hasattr(generate_baseline, "repair")


def test_frozen_oracle_behaviour_unchanged():
    from cago.oracle.config import PUBLISHED_COUNTS
    assert PUBLISHED_COUNTS == {"SR1": 17303, "SR2": 9504, "SR3": 8228, "SR4": 6515, "SR5": 3878, "ANY": 23908}
    from cago.oracle.engine import evaluate_garment
    from cago.oracle.selection import make_component
    comps = [make_component("c", "shell", "surface_component", [("cotton", 96.0), ("polyester", 4.0)])]
    r = evaluate_garment("g", "black", comps)
    assert (r["sr1_violation"], r["sr2_violation"], r["sr3_violation"], r["sr4_violation"], r["sr5_violation"]) == (False, False, True, True, False)
    assert not evaluate_garment("g", "red", [make_component("c", "shell", "surface_component", [("cotton", 95.0), ("polyester", 5.0)])])["sr3_violation"]
