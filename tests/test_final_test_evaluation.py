"""Final TEST evaluation: leakage, TRAIN-only construction, frozen configuration, determinism, pairing, bootstrap grouping,
missing results, schema consistency, cache/parallel equivalence and source-freeze integrity."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path

import pandas as pd
import pytest

from cago.benchmark.final_test_manifest import build_manifest, frozen_configs, is_new_code, manifest_digest, verify_manifest
from cago.benchmark.final_test_report import assemble_report, render_markdown, validate_report_schema
from cago.benchmark.final_test_requests import (assert_split_integrity, build_final_test_requests, check_split_integrity, cluster_ids, coverage_report,
                                                eligibility_audit, generation_view)
from cago.benchmark.final_test_runner import analyze_pairs, conditions_check, run_requests
from cago.benchmark.final_test_stats import cluster_bootstrap, paired_summary
from cago.evaluation.config import EvaluationConfig
from cago.generation.support_tables import build_support_tables
from tests.final_fixtures import CTX, REP, REP_GEN, SUP, VARIANTS

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = Path(os.environ.get("CAGO_PROCESSED_DIR") or ROOT / "data" / "processed")
MANIFEST = ROOT / "configs" / "final_test_evaluation_manifest.json"
A, B3 = "A_baseline", "B3_proposal_plus_repair"
REQS = build_final_test_requests(REP, SUP, "test", 0, 2)


@pytest.fixture(scope="module")
def raw():
    return run_requests(REQS, REP_GEN, CTX, SUP, VARIANTS, EvaluationConfig(), rerun_check=3)


# ---------------------------------------------------------------- split / parent leakage
def test_split_integrity_detects_parent_and_garment_leakage():
    ok = check_split_integrity(REP)
    assert ok["ok"] and not any(ok["parent_overlap"].values()) and ok["garment_id_unique"]
    leaked = REP.copy()
    leaked.loc[leaked["garment_id"] == "E1", "parent_product_id"] = leaked.loc[leaked["split"] == "train", "parent_product_id"].iloc[0]
    r = check_split_integrity(leaked)
    assert not r["ok"] and r["parent_overlap"]["train&test"] == 1
    with pytest.raises(ValueError):
        assert_split_integrity(leaked)
    assert not check_split_integrity(pd.concat([REP, REP.iloc[[0]]], ignore_index=True))["ok"]
    assert check_split_integrity(REP.assign(split=REP["split"].replace({"val": "dev"})))["unknown_splits"] == ["dev"]
    sm = pd.DataFrame({"garment_id": REP["garment_id"], "split": REP["split"]})
    assert check_split_integrity(REP, sm)["split_mapping_consistent_with_representation"] is True
    bad = sm.copy()
    bad.loc[0, "split"] = "test"
    assert check_split_integrity(REP, bad)["ok"] is False


@pytest.mark.skipif(not (PROCESSED / "garment_representation.parquet").exists(), reason="processed data missing")
def test_real_split_has_zero_parent_leakage():
    rep = pd.read_parquet(PROCESSED / "garment_representation.parquet", columns=["garment_id", "parent_product_id", "split"])
    sm = pd.read_parquet(PROCESSED / "split_mapping.parquet")
    r = assert_split_integrity(rep, sm)
    assert r["parent_overlap"] == {"train&val": 0, "train&test": 0, "val&test": 0} and r["parents_per_split"]["test"] > 5000


# ---------------------------------------------------------------- TRAIN-only construction
def test_generators_only_see_train_rows_and_support_is_train_only(raw):
    assert set(REP_GEN["split"]) == {"train"} and SUP.splits_used == ("train",) and SUP.n_train_garments == len(REP_GEN)
    train_ids = set(REP_GEN["garment_id"])
    test_ids = set(REP.loc[REP["split"] == "test", "garment_id"])
    used = {t for n in (A, B3) for r in raw["recs"][n].values() for t in r["template_ids"]}
    assert used and used <= train_ids and not (used & test_ids)
    with pytest.raises(ValueError):
        run_requests(REQS[:1], REP, CTX, SUP, VARIANTS, EvaluationConfig(), rerun_check=0)                 # full representation refused
    bad = build_support_tables(REP_GEN)
    bad.splits_used = ("train", "test")
    with pytest.raises(ValueError):
        run_requests(REQS[:1], REP_GEN, CTX, bad, VARIANTS, EvaluationConfig(), rerun_check=0)
    with pytest.raises(ValueError):
        build_final_test_requests(REP, bad, "test", 0)


def test_test_rows_cannot_change_generation_only_request_definition():
    from tests.synthetic_data import garment
    rows = REP.to_dict("records")
    for r in rows:
        if r["split"] == "test":
            r["components"] = garment("Z", "pz", "test", [("elastane", 100)], [("viscose", 100)])["components"]
    sc = pd.DataFrame(rows)
    assert generation_view(sc).equals(REP_GEN)
    assert build_support_tables(generation_view(sc)).materials_by_category_class == SUP.materials_by_category_class
    one = REQS[0]
    a = run_requests([one], REP_GEN, CTX, SUP, VARIANTS, EvaluationConfig(), rerun_check=0)
    b = run_requests([one], generation_view(sc), CTX, SUP, VARIANTS, EvaluationConfig(), rerun_check=0)
    assert [r["digest"] for r in a["recs"][B3].values()] == [r["digest"] for r in b["recs"][B3].values()]
    assert build_final_test_requests(REP, SUP, "test", 0, 2) != build_final_test_requests(sc, SUP, "test", 0, 2)   # documented role of TEST


# ---------------------------------------------------------------- request construction
def test_request_construction_is_deterministic_and_documented():
    assert REQS == build_final_test_requests(REP, SUP, "test", 0, 2)
    assert {r["type"] for r in REQS} == {"no_pref", "derived_full", "derived_forbid"}
    cells = {tuple(r["cell"]) for r in REQS}
    assert cells == {("women", "trousers"), ("men", "shorts")}
    for r in REQS:
        assert r["request_id"].startswith("|".join(r["cell"]))
        if r["type"] == "no_pref":
            assert set(r["raw"]) == {"target_segment", "detail_category"} and r["source_parent_product_id"] is None
        else:
            g = REP[REP["garment_id"] == r["source_garment_id"]].iloc[0]
            assert g["split"] == "test" and g["parent_product_id"] == r["source_parent_product_id"]
    for cell in cells:
        for t in ("derived_full", "derived_forbid"):
            ps = [r["source_parent_product_id"] for r in REQS if tuple(r["cell"]) == cell and r["type"] == t]
            assert len(ps) == len(set(ps))
    forb = [r for r in REQS if r["type"] == "derived_forbid" and "forbidden_materials" in r["raw"]]
    assert forb and all(r["raw"]["forbidden_materials"][0] in SUP.materials_by_category[r["cell"][1]] for r in forb)


def test_ineligible_test_garments_are_reported_not_silently_dropped():
    aud = eligibility_audit(REP, "test")
    assert aud["by_reason"].get("non_vocab_material_token") == 1 and aud["garments"] == int((REP["split"] == "test").sum())
    assert not any(r["source_garment_id"] == "E_bad" for r in REQS)
    cov = coverage_report(REQS, aud)
    assert cov["n_requests"] == len(REQS) and cov["cells"] == 2 and cov["types"]["no_pref"] == 2 and cov["evaluation_split_eligibility"] == aud
    only_bad = REP[(REP["split"] != "test") | (REP["garment_id"] == "E_bad")]
    assert [r["type"] for r in build_final_test_requests(only_bad, SUP, "test", 0, 2)] == ["no_pref"]     # the cell is kept


def test_cluster_ids_group_by_parent_and_cell():
    cl = cluster_ids(REQS)
    derived = [r for r in REQS if r["source_parent_product_id"] is not None]
    assert len({cl[r["request_id"]]["parent"] for r in derived}) == len({r["source_parent_product_id"] for r in derived})
    assert all(cl[r["request_id"]]["parent"].startswith("nopref:") for r in REQS if r["type"] == "no_pref")
    assert len({cl[r["request_id"]]["cell"] for r in REQS}) == 2


# ---------------------------------------------------------------- determinism, identical conditions, pairing
def test_runs_are_deterministic(raw):
    again = run_requests(REQS, REP_GEN, CTX, SUP, VARIANTS, EvaluationConfig(), rerun_check=0)
    for n in (A, B3):
        assert [(i, r["digest"]) for i, r in raw["recs"][n].items()] == [(i, r["digest"]) for i, r in again["recs"][n].items()]
    assert raw["determinism"]["all_identical"] is True and raw["determinism"]["checks"] == 6


def test_parallel_and_cached_execution_reproduce_sequential_results(raw, tmp_path):
    par = run_requests(REQS, REP_GEN, CTX, SUP, VARIANTS, EvaluationConfig(), rerun_check=0, workers=2, cache_dir=tmp_path / "c", cache_tag="t")
    assert par["requests_loaded_from_cache"] == 0 and len(list((tmp_path / "c").glob("t_*.pkl"))) == len(REQS)
    resumed = run_requests(REQS, REP_GEN, CTX, SUP, VARIANTS, EvaluationConfig(), rerun_check=0, cache_dir=tmp_path / "c", cache_tag="t")
    assert resumed["requests_loaded_from_cache"] == len(REQS)
    next(iter((tmp_path / "c").glob("t_*.pkl"))).unlink()                       # interrupted run: one request recomputed
    part = run_requests(REQS, REP_GEN, CTX, SUP, VARIANTS, EvaluationConfig(), rerun_check=0, cache_dir=tmp_path / "c", cache_tag="t")
    assert part["requests_loaded_from_cache"] == len(REQS) - 1
    for other in (par, resumed, part):
        for n in (A, B3):
            assert list(other["recs"][n]) == list(raw["recs"][n])               # request order preserved
            for i in raw["recs"][n]:
                for k in ("digest", "generated", "hard_valid", "stages", "pool", "front_size", "template_ids"):
                    assert other["recs"][n][i][k] == raw["recs"][n][i][k]
            assert other["rows"][n]["B_hard_valid_candidates"] == raw["rows"][n]["B_hard_valid_candidates"]
        assert other["template_rows"] == raw["template_rows"] and other["repair_side_effect_examples"] == raw["repair_side_effect_examples"]


def test_identical_comparison_conditions(raw):
    c = conditions_check(raw, A, B3, EvaluationConfig())
    assert c["identical_template_selection"] and c["identical_eligible_pool_size"] and c["identical_requested_budget"]
    assert c["requests_in_both"] == c["requests_run"] == len(REQS)
    cf = frozen_configs(10, 8, 0)
    a, b3 = cf["generator_A_baseline"], cf["generator_B3_sorting_aware"]
    assert a["n_templates"] == b3["n_templates"] == 10 and a["mutations_per_template"] == b3["candidates_per_template"] == 8
    assert a["seed"] == b3["seed"] == 0 and a["max_attempts"] == b3["max_proposal_attempts"] == 25
    assert b3["policy"] == "STRICT_SORTING" and b3["sorting_aware_proposal"] and b3["sorting_aware_repair"]
    assert b3["preserve_intent_floor"] == 0.15 and b3["preserve_plausibility_floor"] == 0.15


def test_pairing_is_by_request_id_not_position():
    cl = {i: {"parent": f"p{i}", "cell": "c"} for i in "abcde"}
    a = {"a": 1.0, "b": 2.0, "c": 3.0, "d": None}
    b = {"d": 9.0, "c": 1.0, "b": 2.0, "a": 0.0}
    s = paired_summary(a, b, list("abcde"), cl, 100, 0)
    assert s["n_paired"] == 3 and s["mean_diff"] == pytest.approx(-1.0) and (s["variant_lower"], s["equal"], s["variant_higher"]) == (2, 1, 0)
    assert (s["only_baseline_available"], s["only_variant_available"], s["neither_available"]) == (0, 1, 1)
    assert s["mean_baseline"] == pytest.approx(2.0) and s["mean_variant"] == pytest.approx(1.0)


def test_missing_results_are_counted_not_imputed(raw):
    ra = copy.deepcopy(raw)
    victim = next(i for i, r in ra["recs"][B3].items() if r["stages"]["D_balanced"] and ra["recs"][A][i]["stages"]["D_balanced"])
    ra["recs"][B3][victim]["stages"]["D_balanced"] = None
    s = analyze_pairs(ra, A, B3, 50, 0)["D_balanced"]["vc_mean"]
    full = analyze_pairs(raw, A, B3, 50, 0)["D_balanced"]["vc_mean"]
    assert s["only_baseline_available"] == full["only_baseline_available"] + 1 and s["n_paired"] == full["n_paired"] - 1
    assert s["n_requests_total"] == full["n_requests_total"] == len(REQS)
    empty = [{"request_id": "men|trousers|no_pref", "cell": ["men", "trousers"], "type": "no_pref", "source_garment_id": None,
              "source_parent_product_id": None, "parent_reused_across_types": False, "raw": {"target_segment": "men", "detail_category": "trousers"}},
             {"request_id": "bad", "cell": ["robots", "trousers"], "type": "no_pref", "source_garment_id": None, "source_parent_product_id": None,
              "parent_reused_across_types": False, "raw": {"target_segment": "robots", "detail_category": "trousers"}}]
    r = run_requests(empty, REP_GEN, CTX, SUP, VARIANTS, EvaluationConfig(), rerun_check=0)
    assert r["invalid"] == [{"request_id": "bad", "errors": ["invalid_target_segment"]}] and len(r["valid_requests"]) == 1
    assert r["recs"][A]["men|trousers|no_pref"]["hard_valid"] == 0 and r["recs"][B3]["men|trousers|no_pref"]["pool"] == 0
    p = analyze_pairs(r, A, B3, 20, 0)["B_hard_valid_candidates"]["vc_mean"]
    assert p["n_paired"] == 0 and p["neither_available"] == 1 and p["mean_diff"] is None


# ---------------------------------------------------------------- bootstrap grouping
def test_cluster_bootstrap_resamples_whole_clusters():
    values = [10, 10, 10, 10, 0]
    c = cluster_bootstrap(values, ["a", "a", "a", "a", "b"], "mean", 400, seed=3)
    assert c["n_clusters"] == 2 and c["n_requests"] == 5 and c["point"] == 8.0
    possible = {0.0, 8.0, 10.0}                                                  # only whole-cluster combinations are possible
    assert c["lo"] in possible and c["hi"] in possible
    naive = cluster_bootstrap(values, [f"r{i}" for i in range(5)], "mean", 400, seed=3)
    assert naive["n_clusters"] == 5 and (c["hi"] - c["lo"]) >= (naive["hi"] - naive["lo"])
    assert cluster_bootstrap(values, ["a", "a", "a", "a", "b"], "mean", 400, seed=3) == c
    with pytest.raises(ValueError):
        cluster_bootstrap([1, 2], ["a"], "mean")
    assert cluster_bootstrap([], [], "mean")["point"] is None


def test_paired_summary_uses_parent_and_cell_groupings():
    ids = [f"r{i}" for i in range(8)]
    cl = {i: {"parent": f"p{k // 4}", "cell": "c"} for k, i in enumerate(ids)}
    a = {i: 0.0 for i in ids}
    b = {i: -1.0 if k < 4 else 0.0 for k, i in enumerate(ids)}
    s = paired_summary(a, b, ids, cl, 200, 0)
    assert s["ci95"]["request"]["mean"]["n_clusters"] == 8 and s["ci95"]["parent"]["mean"]["n_clusters"] == 2 and s["ci95"]["cell"]["mean"]["n_clusters"] == 1
    w = lambda g: s["ci95"][g]["mean"]["hi"] - s["ci95"][g]["mean"]["lo"]
    assert w("cell") == 0.0 and w("parent") >= w("request")


# ---------------------------------------------------------------- report schema
def test_report_schema_and_markdown_are_consistent(raw):
    cov = coverage_report(REQS, eligibility_audit(REP, "test"))
    rep = assemble_report(raw, cov, {"split_integrity": check_split_integrity(REP)},
                          {"digest": "x", "verification_ok": True, "evaluation_split": "test", "new_code_changed_since_freeze": []}, 60, 0, EvaluationConfig())
    assert validate_report_schema(rep) == []
    json.dumps(rep, default=str)
    assert [o["metric"] for o in rep["primary_outcomes"]] == ["vc_mean", "vc_mean", "zero_share", "intent_mean", "plaus_mean"]
    assert set(rep["paired"]) == {"B_hard_valid_candidates", "C_pareto_front", "D_balanced", "E_sorting_focused", "F_intent_focused"}
    assert set(rep["breakdowns"]["by_template_pool_bin"]) <= {"<5", "5-19", "20-99", ">=100"} and len(rep["per_request"]) == len(REQS)
    assert rep["costs"]["ratios_variant_over_baseline"]["oracle_calls_generation_phase"] > 1 and "NOT equal" in rep["costs"]["fairness_statement"]
    md = render_markdown(rep)
    for h in ("## 1. Integrity", "## 2. Request coverage", "## 6. Pre-specified primary outcomes", "## 12. Failure analysis", "## 14. Limitations"):
        assert h in md
    low = md.lower()
    assert "does not mean recyclable" in low
    assert not any(w in low for w in ("recyclability %", "guaranteed recyclable", "sustainable %", "manufacturability probability", "ai-generated"))
    broken = dict(rep)
    broken.pop("paired")
    assert "missing key: paired" in validate_report_schema(broken)
    bad = copy.deepcopy(rep)
    bad["conditions"]["identical_template_selection"] = False
    assert any("template selection" in p for p in validate_report_schema(bad))


# ---------------------------------------------------------------- frozen configuration + source integrity
def _mini_project(tmp: Path) -> tuple[Path, Path]:
    root, data = tmp / "proj", tmp / "data"
    for d in ("cago", "scripts", "tests", "cago/benchmark"):
        (root / d).mkdir(parents=True, exist_ok=True)
    (root / "cago/a.py").write_text("X = 1\n")
    (root / "scripts/s.py").write_text("Y = 2\n")
    (root / "tests/t.py").write_text("Z = 3\n")
    (root / "cago/benchmark/final_test_x.py").write_text("N = 1\n")
    data.mkdir()
    REP[["garment_id", "parent_product_id", "split"]].to_parquet(data / "garment_representation.parquet")
    REP[["garment_id", "split"]].to_parquet(data / "split_mapping.parquet")
    (data / "ml_material_vocabulary.json").write_text("{}")
    return root, data


def test_manifest_detects_every_kind_of_drift(tmp_path):
    root, data = _mini_project(tmp_path)
    m = build_manifest(root, data)
    assert m["frozen_before_test_run"] and "cago/a.py" in m["frozen_files"] and "cago/benchmark/final_test_x.py" in m["new_evaluation_code"]
    assert "cago/benchmark/final_test_x.py" not in m["frozen_files"] and is_new_code("tests/final_fixtures.py") and not is_new_code("tests/synthetic_data.py")
    assert verify_manifest(m, root, data)["ok"] is True and manifest_digest(m) == manifest_digest(copy.deepcopy(m))
    (root / "cago/a.py").write_text("X = 2\n")
    v = verify_manifest(m, root, data)
    assert not v["ok"] and v["mismatches"]["frozen_files"] == ["cago/a.py"]
    (root / "cago/a.py").write_text("X = 1\n")
    (root / "cago/new_module.py").write_text("Q = 1\n")
    assert any(x.startswith("UNLISTED") for x in verify_manifest(m, root, data)["mismatches"]["frozen_files"])
    (root / "cago/new_module.py").unlink()
    (data / "ml_material_vocabulary.json").write_text('{"a": 1}')
    assert verify_manifest(m, root, data)["mismatches"]["data_artifacts"] == ["ml_material_vocabulary.json"]
    (data / "ml_material_vocabulary.json").write_text("{}")
    (root / "cago/benchmark/final_test_x.py").write_text("N = 2\n")
    v = verify_manifest(m, root, data)
    assert v["ok"] is True and v["mismatches"]["new_code_changed_since_freeze"] == ["cago/benchmark/final_test_x.py"]   # reported, not hidden
    drift = copy.deepcopy(m)
    drift["configs"]["generator_B3_sorting_aware"]["preserve_intent_floor"] = 0.5
    assert verify_manifest(drift, root, data)["mismatches"]["configs"]
    other = copy.deepcopy(m)
    other["splits"]["digest"] = "0" * 32
    assert verify_manifest(other, root, data)["mismatches"]["split_digest"]


@pytest.mark.skipif(not MANIFEST.exists() or not (PROCESSED / "split_mapping.parquet").exists(), reason="frozen manifest / data missing")
def test_frozen_sources_data_and_prior_results_are_unmodified():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    v = verify_manifest(m, ROOT, PROCESSED)
    assert v["ok"], v["mismatches"]
    assert v["mismatches"]["new_code_changed_since_freeze"] == []
    assert m["frozen_before_test_run"] is True and m["comparison_conditions"]["policy_B3"] == "STRICT_SORTING"
    assert len(m["frozen_files"]) > 80 and "cago/oracle/rules.py" in m["frozen_files"] and "cago/generation/baseline.py" in m["frozen_files"]
    assert "baseline_benchmark.json" in m["prior_results"] and "sorting_aware_val_comparison.json" in m["prior_results"]
    assert m["configs"] == json.loads(json.dumps(frozen_configs(10, 8, 0), default=str))
    assert len(m["analysis_plan"]["primary_outcomes"]) == 5 and "No hyperparameter" in m["no_tuning_statement"]


@pytest.mark.skipif(not (PROCESSED / "final_test_evaluation_report.json").exists(), reason="final TEST report not generated yet")
def test_final_report_on_disk_is_schema_consistent_and_manifest_bound():
    r = json.loads((PROCESSED / "final_test_evaluation_report.json").read_text(encoding="utf-8"))
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert validate_report_schema(r) == [] and r["manifest"]["digest"] == manifest_digest(m) and r["manifest"]["verification_ok"] is True
    assert r["manifest"]["evaluation_split"] == "test" and r["manifest"]["dry_run"] is False
    assert r["integrity"]["split_integrity"]["ok"] and r["integrity"]["generator_input_splits"] == ["train"] and r["integrity"]["templates_all_from_train"] is True
    assert r["conditions"]["identical_template_selection"] and r["determinism"]["all_identical"]
    assert (PROCESSED / "final_test_evaluation_report.md").exists()
