"""VAL-only development comparison: fairness, paired statistics, ablation variants, small-pool strata, no TEST usage."""
from __future__ import annotations

import json

import pandas as pd
import pytest

from cago.benchmark.sorting_aware_comparison import METRICS, default_variants, paired, run_comparison
from cago.benchmark.sorting_aware_requests import assert_dev_only, build_val_requests, dev_view, load_val_garments
from cago.benchmark.sorting_aware_report import render_comparison_md
from cago.generation.support_tables import build_support_tables
from tests.sorting_fixtures import DEV, REP, SUP
from tests.synthetic_data import CTX_FULL

VARIANTS = default_variants(5, 5, 0)


def test_val_requests_come_only_from_val_garments_and_are_deterministic():
    garments = load_val_garments(DEV, 0)
    assert {g.garment_id for g in garments} == {"V1", "V2", "V3", "V4"}
    reqs = build_val_requests(DEV, SUP, 0)
    assert reqs == build_val_requests(DEV, SUP, 0) and {tuple(r["cell"]) for r in reqs} == {("women", "trousers"), ("men", "shorts")}
    assert {r["source_test_garment"] for r in reqs if r["source_test_garment"]} <= {"V1", "V2", "V3", "V4"}
    with pytest.raises(ValueError):
        build_val_requests(REP, SUP, 0)                                                     # TEST rows present -> refused
    with pytest.raises(ValueError):
        load_val_garments(REP)
    assert_dev_only(dev_view(REP))


def test_comparison_is_fair_paired_and_deterministic():
    reqs = build_val_requests(DEV, SUP, 0)
    out = run_comparison(reqs, DEV, CTX_FULL, SUP, VARIANTS, n_boot=30, seed=0, rerun_check=3)
    assert out["fairness"]["identical_template_pool_and_selection_across_variants"] is True
    assert out["determinism"]["all_identical"] is True and set(out["per_variant"]) == set(VARIANTS)
    assert out["coverage"]["variants"] == list(VARIANTS) and out["coverage"]["n_requests"] == 6
    req = out["fairness"]["candidates_requested_per_variant"]
    assert len(set(req.values())) == 1                                                       # same requested candidate budget
    for name, v in out["per_variant"].items():
        assert v["search"]["candidates_generated"] <= v["search"]["candidates_requested"]
        assert v["search"]["mutation_attempts"] > 0 and v["search"]["unique_candidate_rate_mean"] in (None, 1.0) or name == "A_baseline"
    a, b3 = out["per_variant"]["A_baseline"], out["per_variant"]["B3_proposal_plus_repair"]
    assert a["search"]["repair_proposals_evaluated"] == 0 and b3["search"]["repair_proposals_evaluated"] > 0
    assert b3["search"]["repair_acceptance_rate"] is not None and 0 <= b3["search"]["repair_acceptance_rate"] <= 1
    assert b3["unresolved_after_generation"]["candidates_final"] > 0 and "SR4_immutable_violation" in b3["unresolved_after_generation"]
    pv = out["paired_vs_baseline"]["B3_proposal_plus_repair"]
    assert set(pv) == {"B_hard_valid_candidates", "C_pareto_front", "D_balanced", "E_sorting_focused", "F_intent_focused"}
    assert set(pv["B_hard_valid_candidates"]) == set(METRICS) and pv["B_hard_valid_candidates"]["violation_count"]["n_requests"] >= 1
    again = run_comparison(reqs, DEV, CTX_FULL, SUP, VARIANTS, n_boot=30, seed=0, rerun_check=0)
    for n in VARIANTS:
        assert [r["digest"] for r in again["records"][n].values()] == [r["digest"] for r in out["records"][n].values()]
    md = render_comparison_md({**out, "seed": 0, "n_bootstrap": 30})
    low = md.lower()
    assert "not a recyclability" in low and not any(w in low for w in ("guaranteed recyclable", "sustainable %", "manufacturability probability", "ai-generated"))


def test_small_pools_are_flagged_and_stratified():
    out = run_comparison(build_val_requests(DEV, SUP, 0), DEV, CTX_FULL, SUP, VARIANTS, n_boot=20, seed=0, rerun_check=0)
    sp = out["small_pool"]
    assert set(sp) == {"<5", "5-19", "20-99", ">=100"}
    assert sp["<5"]["n_requests"] == 3 and sp["<5"]["flag"] is not None                         # men/shorts: 3 TRAIN templates
    from cago.benchmark.runner import pool_bin
    pool = next(r["pool"] for r in out["records"]["A_baseline"].values() if r["cell"] == ["women", "trousers"])
    big = pool_bin(pool)
    assert big in ("20-99", ">=100") and sp[big]["n_requests"] == 3 and sp[big]["flag"] is None      # large synthetic pool: not flagged
    assert sp["5-19"]["n_requests"] == 0 and sp["5-19"]["flag"] is None
    for cell in sp.values():
        if cell["n_requests"]:
            assert set(cell["variants"]) == set(VARIANTS)
            assert {"repair_acceptance_rate", "no_train_supported_alternative", "unresolved_repairable_rate", "generated_over_requested"} <= set(cell["variants"]["B3_proposal_plus_repair"])


def test_comparison_refuses_test_rows_and_non_train_support():
    reqs = build_val_requests(DEV, SUP, 0)
    with pytest.raises(ValueError):
        run_comparison(reqs, REP, CTX_FULL, SUP, VARIANTS, n_boot=10)
    bad = build_support_tables(DEV)
    bad.splits_used = ("train", "val")
    with pytest.raises(ValueError):
        run_comparison(reqs, DEV, CTX_FULL, bad, VARIANTS, n_boot=10)


def test_paired_statistic_is_request_level():
    ra = [{"request_id": "r1", "vc": 3}, {"request_id": "r1", "vc": 1}, {"request_id": "r2", "vc": 2}]
    rb = [{"request_id": "r1", "vc": 1}, {"request_id": "r2", "vc": 0}, {"request_id": "r3", "vc": 9}]
    p = paired(ra, rb, lambda r: r["vc"], 50, 0)
    assert p["n_requests"] == 2 and p["mean_diff"] == -1.5                                       # r3 unpaired; means 2->1 and 2->0
    assert paired(ra, rb, lambda r: r["vc"], 50, 0) == p


def test_every_variant_hard_valid_pool_and_ablation_names():
    out = run_comparison(build_val_requests(DEV, SUP, 0), DEV, CTX_FULL, SUP, VARIANTS, n_boot=20, seed=0, rerun_check=0)
    assert list(VARIANTS)[:4] == ["A_baseline", "B1_proposal_only", "B2_repair_only", "B3_proposal_plus_repair"]
    for rec in out["records"]["B3_proposal_plus_repair"].values():
        assert rec["hard_valid"] == rec["generated"]                                              # hard gate removed nothing
    assert json.dumps(out, default=str)
