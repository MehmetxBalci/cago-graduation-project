"""Benchmark request construction, runner, stage aggregation, small-pool flags and trade-off statistics."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import pytest

from cago.benchmark.benchmark_requests import TYPES, build_benchmark_requests, derived_preferences, forbidden_candidate
from cago.benchmark.perturbations import load_eval_garments
from cago.benchmark.runner import (POOL_BINS, aggregate_stage, pool_bin, run_benchmark, run_request, small_pool_analysis, trade_flags,
                                   trade_off_frequencies)
from cago.evaluation.config import EvaluationConfig
from cago.generation.baseline import GenerationConfig
from cago.generation.support_tables import build_support_tables
from tests.synthetic_data import CTX_FULL, garment, make_rep_with_tests

REP = make_rep_with_tests()
SUP = build_support_tables(REP)
TESTS = load_eval_garments(REP, "test", seed=0, one_per_parent=False)
GCFG = GenerationConfig(n_templates=5, mutations_per_template=5, seed=0)
CFG = EvaluationConfig()


def test_benchmark_request_generation_is_deterministic():
    a = build_benchmark_requests(TESTS, SUP, seed=3)
    b = build_benchmark_requests(TESTS, SUP, seed=3)
    assert a == b and len(a) == 2 * len(TYPES)                              # 2 TEST cells x 3 request types
    assert [tuple(r["cell"]) for r in a] == sorted(tuple(r["cell"]) for r in a)               # cells in sorted order
    assert [r["type"] for r in a][:3] == list(TYPES)                                          # fixed type order within a cell
    assert {tuple(r["cell"]) for r in a} == {("women", "trousers"), ("men", "shorts")}
    assert {r["type"] for r in a} == set(TYPES)
    sub = build_benchmark_requests(TESTS, SUP, seed=3, max_requests=4)
    assert len(sub) == 4 and sub == build_benchmark_requests(TESTS, SUP, seed=3, max_requests=4)
    assert {r["request_id"] for r in sub} <= {r["request_id"] for r in a}


def test_requests_are_built_from_test_cells_and_observable_properties_only():
    reqs = {r["request_id"]: r for r in build_benchmark_requests(TESTS, SUP, seed=0)}
    nopref = reqs["women|trousers|no_pref"]["raw"]
    assert set(nopref) == {"target_segment", "detail_category"} and reqs["women|trousers|no_pref"]["source_test_garment"] is None
    full = reqs["men|shorts|derived_full"]
    g = next(x for x in TESTS if x.garment_id == full["source_test_garment"])
    assert g.garment_id.startswith("E") and full["raw"]["colour"] == g.colour
    assert "preferred_dominant_material" in full["raw"] and full["raw"]["stretch"] in ("none", "low", "high")
    forb = reqs["women|trousers|derived_forbid"]
    fg = next(x for x in TESTS if x.garment_id == forb["source_test_garment"])
    used = {m["material"] for c in fg.components for m in c["materials"]}
    assert forb["raw"]["forbidden_materials"][0] not in used and forb["raw"]["forbidden_materials"][0] in SUP.materials_by_category["trousers"]
    assert forbidden_candidate(fg, SUP) == forb["raw"]["forbidden_materials"][0]
    assert derived_preferences(g, full=False).keys() <= {"preferred_dominant_material", "stretch"}


def test_small_template_pools_are_flagged_and_binned():
    assert [pool_bin(n) for n in (0, 4, 5, 19, 20, 99, 100, 1000)] == ["<5", "<5", "5-19", "5-19", "20-99", "20-99", ">=100", ">=100"]
    assert [b[0] for b in POOL_BINS] == ["<5", "5-19", "20-99", ">=100"]
    reqs = build_benchmark_requests(TESTS, SUP, seed=0)
    out = run_benchmark(reqs, REP, CTX_FULL, SUP, GCFG, CFG, n_boot=40, seed=0, rerun_check=2)
    small = out["small_pool"]
    by_cell = {tuple(r["cell"]): r["pool"] for r in out["records"] if r["status"] != "invalid_request"}
    assert by_cell[("men", "shorts")]["bin"] == "<5" and by_cell[("women", "trousers")]["bin"] == "5-19"
    assert small["<5"]["n_requests"] == 3 and small["<5"]["flag"] == "SMALL POOL: interpret with caution"
    assert small["5-19"]["n_requests"] == 3 and small["5-19"]["flag"] is not None
    assert small["20-99"]["n_requests"] == 0 and small["20-99"]["flag"] is None and small[">=100"]["n_requests"] == 0


def test_runner_records_stages_and_hard_validity():
    reqs = build_benchmark_requests(TESTS, SUP, seed=0)
    out = run_benchmark(reqs, REP, CTX_FULL, SUP, GCFG, CFG, n_boot=40, seed=0, rerun_check=3)
    c = out["coverage"]
    assert c["n_requests"] == 6 and c["n_invalid"] == 0 and c["cells"] == 2 and c["requests_with_soft_preferences"] >= 3
    assert out["totals"]["candidates_generated"] > 0 and out["totals"]["hard_valid_rate"] == 1.0
    st = out["stages"]
    n = {k: v["n_rows"] for k, v in st.items()}
    assert n["A_templates"] > 0 and n["B_hard_valid_candidates"] >= n["C_pareto_front"] >= n["D_balanced"] >= 1
    assert st["B_hard_valid_candidates"]["template_distance"]["abs_pct_change_mean"] > 0
    assert st["A_templates"]["template_distance"]["n_substitutions_mean"] == 0
    assert 0 < st["A_templates"]["template_hard_valid_rate"] <= 1.0          # <1 when a template still holds a forbidden material (repaired in candidates)
    for rec in out["records"]:
        assert rec["hard_valid"] <= rec["generated"] and len(rec["candidate_violation_distribution"]) == 6
        assert sum(rec["candidate_violation_distribution"].values()) == rec["hard_valid"]
        assert rec["front_size"] >= 1 and rec["selected"]["balanced"] is not None and rec["selected"]["sorting_focused"] is not None
        if not rec["request_core"]["soft"]:
            assert rec["selected"]["intent_focused"] is None and rec["intent_dimension"] == "none_scorable"
    assert st["E_sorting_focused"]["violation_count"]["pooled"]["mean"] <= st["B_hard_valid_candidates"]["violation_count"]["pooled"]["mean"]
    assert "paired_vs_own_template" in st["D_balanced"] and out["determinism"]["all_identical"] is True
    assert out["support_splits_used"] == ["train"]


def test_runner_is_deterministic_and_seed_sensitive():
    reqs = build_benchmark_requests(TESTS, SUP, seed=0)
    a = run_benchmark(reqs, REP, CTX_FULL, SUP, GCFG, CFG, n_boot=40, seed=1, rerun_check=0)
    b = run_benchmark(reqs, REP, CTX_FULL, SUP, GCFG, CFG, n_boot=40, seed=1, rerun_check=0)
    assert json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)
    c = run_benchmark(reqs, REP, CTX_FULL, SUP, GenerationConfig(n_templates=5, mutations_per_template=5, seed=9), CFG, n_boot=40, seed=1, rerun_check=0)
    assert [r["digest"] for r in a["records"]] != [r["digest"] for r in c["records"]]


def test_no_val_test_leakage_in_benchmark_fitting_and_support():
    assert SUP.splits_used == ("train",)
    out = run_benchmark(build_benchmark_requests(TESTS, SUP, seed=0), REP, CTX_FULL, SUP, GCFG, CFG, n_boot=20, rerun_check=0)
    assert out["support_splits_used"] == ["train"]
    rows = REP.to_dict("records")
    for r in rows:
        if r["split"] == "test":                                                # rewrite every TEST garment completely
            r["components"] = garment("Z", "pz", "test", [("nylon", 100)], [("nylon", 100)])["components"]
    sup2 = build_support_tables(pd.DataFrame(rows))
    assert sup2.materials_by_category_class == SUP.materials_by_category_class and sup2.combos_by_category_class == SUP.combos_by_category_class
    bad = build_support_tables(REP)
    bad.splits_used = ("train", "test")
    with pytest.raises(ValueError):
        run_benchmark([], REP, CTX_FULL, bad, GCFG, CFG)


def test_trade_flags_definitions():
    row = lambda **k: {"vc": 1, "t_vc": 3, "intent": 0.5, "t_intent": 0.7, "plaus": 0.6, "t_plaus": 0.9, **k}
    f = trade_flags(row(), 0.2)
    assert f == {"sorting_up_intent_down": True, "intent_up_sorting_down": False, "sorting_up_plaus_drop": True, "all_three_improve": False}
    f = trade_flags(row(vc=4, intent=0.9), 0.2)
    assert f["intent_up_sorting_down"] is True and f["sorting_up_intent_down"] is False and f["sorting_up_plaus_drop"] is False
    f = trade_flags(row(vc=0, intent=0.9, plaus=0.95), 0.2)
    assert f["all_three_improve"] is True and f["sorting_up_plaus_drop"] is False
    f = trade_flags(row(intent=None), 0.2)
    assert f["sorting_up_intent_down"] is None and f["all_three_improve"] is None and f["sorting_up_plaus_drop"] is True
    assert trade_flags(row(vc=3, plaus=0.5), 0.2)["sorting_up_plaus_drop"] is False                 # no sorting improvement


def test_trade_off_frequencies_and_zero_violation_front():
    rows = [{"request_id": "r1", "stage": "C_pareto_front", "vc": 0, "t_vc": 2, "intent": 0.4, "t_intent": 0.6, "plaus": 0.9, "t_plaus": 0.9},
            {"request_id": "r1", "stage": "C_pareto_front", "vc": 3, "t_vc": 2, "intent": 0.8, "t_intent": 0.6, "plaus": 0.9, "t_plaus": 0.9},
            {"request_id": "r2", "stage": "C_pareto_front", "vc": 1, "t_vc": 2, "intent": None, "t_intent": None, "plaus": 0.9, "t_plaus": 0.5}]
    recs = [{"status": "ok", "no_zero_violation_in_front": False}, {"status": "ok", "no_zero_violation_in_front": True},
            {"status": "no_valid_candidates", "no_zero_violation_in_front": False}]
    t = trade_off_frequencies({"C_pareto_front": rows}, recs, 0.2)
    c = t["per_stage"]["C_pareto_front"]
    assert c["sorting_up_intent_down"] == {"count": 1, "defined_n": 2, "rate": 0.5} and c["intent_up_sorting_down"]["count"] == 1
    assert c["all_three_improve"]["defined_n"] == 2 and c["sorting_up_plaus_drop"]["count"] == 0
    assert t["requests_without_zero_violation_pareto_candidate"] == {"count": 1, "n_requests": 2, "rate": 0.5}


def test_aggregate_stage_statistics():
    rows = [{"request_id": f"r{i % 2}", "stage": "B_hard_valid_candidates", "vc": v, "sr": {k: v > 1 for k in ("SR1", "SR2", "SR3", "SR4", "SR5")},
             "intent": None if i == 0 else 0.5, "plaus": 0.8, "n_sub": 1, "abs_pct": 2.0, "dist": 1.02} for i, v in enumerate([0, 1, 2, 3])]
    a = aggregate_stage(rows, 50, 1)
    assert a["n_rows"] == 4 and a["n_requests"] == 2 and a["zero_violation_rate_pooled"] == 0.25 and a["any_violation_rate"] == 0.75
    assert a["intent_null_rate"] == 0.25 and a["intent_0_100"]["n"] == 3 and a["sr_rates"]["SR1"] == 0.5
    assert a["violation_count"]["per_request_mean_median_ci95"]["level"] == 0.95 and aggregate_stage([], 10, 0) == {"n_rows": 0}


def test_run_request_marks_invalid_requests_and_empty_pools():
    bad = run_request({"request_id": "x", "cell": ["women", "trousers"], "type": "t", "source_test_garment": None,
                       "raw": {"target_segment": "robots", "detail_category": "trousers"}}, REP, CTX_FULL, SUP, GCFG, CFG)
    assert bad[0]["status"] == "invalid_request" and bad[1] == []
    empty = run_request({"request_id": "y", "cell": ["men", "trousers"], "type": "no_pref", "source_test_garment": None,
                         "raw": {"target_segment": "men", "detail_category": "trousers"}}, REP, CTX_FULL, SUP, GCFG, CFG)
    assert empty[0]["status"] == "no_valid_candidates" and empty[0]["pool"]["eligible_templates"] == 0 and empty[0]["pool"]["bin"] == "<5"


def test_small_pool_analysis_handles_empty_input():
    s = small_pool_analysis([], {}, 10, 0)
    assert all(v["n_requests"] == 0 and v["flag"] is None for v in s.values())


PROCESSED = Path(os.environ.get("CAGO_PROCESSED_DIR") or Path(__file__).resolve().parents[1] / "data" / "processed")


@pytest.mark.skipif(not (PROCESSED / "baseline_benchmark.json").exists(), reason="benchmark outputs missing")
def test_real_benchmark_outputs_are_compact_and_consistent():
    b = json.loads((PROCESSED / "baseline_benchmark.json").read_text(encoding="utf-8"))
    assert 100 <= b["coverage"]["n_requests"] <= 300 and b["coverage"]["categories"] >= 10 and len(b["coverage"]["segments"]) >= 3
    assert b["support_splits_used"] == ["train"] and b["determinism"]["all_identical"] is True
    assert b["totals"]["hard_valid_rate"] == 1.0 and (PROCESSED / "baseline_benchmark.json").stat().st_size < 3_000_000
    assert set(b["small_pool"]) == {"<5", "5-19", "20-99", ">=100"} and "candidates" not in b
    assert sum(v["n_requests"] for v in b["small_pool"].values()) == b["coverage"]["n_ok"] + b["coverage"]["n_no_valid_candidates"]
