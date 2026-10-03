"""End-to-end candidate evaluation: hard gate, Oracle integrity, leakage, explanations."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path

import pandas as pd
import pytest

from cago.evaluation.candidate import evaluate_candidate, evaluate_request_candidates, hard_gate, sorting_summary
from cago.evaluation.config import EvaluationConfig
from cago.evaluation.explanations import DISCLAIMER, describe_mutation, explain_candidate
from cago.evaluation.pipeline import evaluate_and_select
from cago.generation.baseline import GenerationConfig, generate_baseline, oracle_eval, public_components
from cago.generation.mutations import apply_percentage, apply_substitution, clone_components
from cago.generation.support_tables import build_support_tables
from cago.generation.distance import template_distance
from cago.generation.template_selector import select_templates
from cago.oracle.engine import evaluate_garment
from cago.oracle.selection import make_component
from tests.synthetic_data import CTX, make_rep, request

REP = make_rep()
SUP = build_support_tables(REP)
GCFG = GenerationConfig(n_templates=5, mutations_per_template=6, seed=7)
CFG = EvaluationConfig()
FORBIDDEN_WORDS = ("recyclable", "sustainable", "guaranteed", "definitely", "probability", "will detect")


def run(req=None, rep=REP, sup=SUP, gcfg=GCFG):
    return evaluate_and_select(req or request(breathability="high", stretch="low"), rep, sup, CTX, gcfg, CFG)


# ---------------- hard gate
def test_hard_invalid_candidate_is_excluded_before_pareto():
    req = request(forbidden={"polyester"})
    res = generate_baseline(req, REP, SUP, CTX, GCFG)
    assert res["candidates"]
    bad = copy.deepcopy(res["candidates"][0])
    bad["candidate_id"] = "cand_bad_forbidden"
    bad["components"][0]["materials"][0]["material"] = "polyester"           # forbidden
    bad2 = copy.deepcopy(res["candidates"][1]); bad2["candidate_id"] = "cand_bad_sum"
    bad2["components"][0]["materials"][0]["pct"] += 0.5                      # no longer sums to 100
    bad3 = copy.deepcopy(res["candidates"][2]); bad3["candidate_id"] = "cand_bad_token"
    bad3["components"][0]["materials"][0]["material"] = "OTHER"
    bad4 = copy.deepcopy(res["candidates"][3]); bad4["candidate_id"] = "cand_bad_neg"
    bad4["components"][0]["materials"][0]["pct"] = -1.0
    res["candidates"] += [bad, bad2, bad3, bad4]
    ev = evaluate_request_candidates(res, SUP, CTX, CFG)
    ids_excluded = {x["candidate_id"] for x in ev["excluded"]}
    assert ids_excluded == {"cand_bad_forbidden", "cand_bad_sum", "cand_bad_token", "cand_bad_neg"}
    assert not ids_excluded & {e["candidate_id"] for e in ev["valid"]}
    codes = {x["candidate_id"]: {i["code"] for i in x["issues"]} for x in ev["excluded"]}
    assert "forbidden_material_present" in codes["cand_bad_forbidden"] and "percentage_sum_out_of_tolerance" in codes["cand_bad_sum"]
    assert "non_physical_token" in codes["cand_bad_token"] and "negative_percentage" in codes["cand_bad_neg"]
    # pipeline: excluded candidates never receive pareto fields or selections
    out = evaluate_and_select(req, REP, SUP, CTX, GCFG, CFG, res=res)
    assert all(not e["candidate_id"].startswith("cand_bad") for e in out["evaluation"]["valid"])
    assert all(not s["candidate_id"].startswith("cand_bad") for s in out["selection"]["selections"])
    assert len(out["evaluation"]["excluded"]) == 4
    assert hard_gate({**res["candidates"][0], "detail_category": "shorts"}, req, CTX)[0]["code"] == "request_mismatch"


def test_hard_constraints_give_no_intent_points():
    out = run(request(forbidden={"polyester"}))                             # only a hard constraint
    for e in out["evaluation"]["valid"]:
        assert e["intent"]["intent_alignment_raw"] is None and e["intent"]["n_active_preferences"] == 0
    assert out["pareto"]["dimensions"] == ["violation_count", "plausibility_loss"]
    assert out["selection"]["intent_focused_omitted"] is True


# ---------------- Oracle
def test_oracle_output_unchanged_by_evaluation():
    res = generate_baseline(request(), REP, SUP, CTX, GCFG)
    ev = evaluate_request_candidates(res, SUP, CTX, CFG)
    for c, e in zip(res["candidates"], ev["valid"]):
        before = copy.deepcopy(c["oracle"])
        row = evaluate_garment("x", c["normalized_colour"], [make_component(x["component_id"], x["component_name_normalized"], x["component_class"],
                               [(m["material"], m["pct"]) for m in x["materials"]]) for x in c["components"]])
        assert e["sorting"]["oracle"] == before == c["oracle"]              # stored Oracle used as is, nothing mutated
        assert e["sorting"]["violation_count"] == row["violation_count"] == sum(
            bool(before[f"sr{i}_violation"]) for i in range(1, 6))
        assert e["sorting"]["sorting_rules_satisfied"] == 5 - row["violation_count"]
        assert e["sorting"]["sorting_compatibility_index_0_100"] == 100 * (5 - row["violation_count"]) / 5
        assert "NOT a recyclability percentage" in e["sorting"]["index_note"]
    s = sorting_summary({"violation_count": 2, **{f"sr{i}_violation": i <= 2 for i in range(1, 6)}})
    assert s["sorting_compatibility_index_0_100"] == 60.0 and s["rules"]["SR1"] and not s["rules"]["SR3"]


# ---------------- leakage / determinism
def test_no_val_test_leakage_in_evaluation():
    out = run(request(preferred_dominant_material="cotton"))
    assert out["generation"]["templates"] and all(t.split == "train" for t in out["generation"]["templates"])
    for e in out["evaluation"]["valid"]:
        assert all(c["support_count"] >= 0 for c in e["plausibility"]["contextual_support"]["components"])
        assert "silk" not in json.dumps(e["plausibility"]["contextual_support"]["components"])
    bad = SUP.__class__(splits_used=("train", "val"))
    with pytest.raises(ValueError):
        evaluate_request_candidates(generate_baseline(request(), REP, SUP, CTX, GCFG), bad, CTX, CFG)


def test_pipeline_is_deterministic():
    a, b = run(), run()
    assert a["digest"] == b["digest"] and a["selection"]["by_role"] == b["selection"]["by_role"]
    assert run(gcfg=GenerationConfig(n_templates=5, mutations_per_template=6, seed=8))["digest"] != a["digest"]
    assert a["pareto"]["front_size"] >= 1 and all(e["pareto_rank"] >= 0 for e in a["evaluation"]["valid"])
    front = [e for e in a["evaluation"]["valid"] if e["is_pareto"]]
    assert {s["candidate_id"] for s in a["selection"]["selections"]} <= {e["candidate_id"] for e in front}


def test_objectives_are_kept_separate_for_pareto():
    out = run(request(breathability="high"))
    for e in out["evaluation"]["valid"]:
        o = e["objectives"]
        assert set(o) == {"violation_count", "intent_loss", "plausibility_loss"}
        assert o["intent_loss"] == pytest.approx(1 - e["intent_alignment_raw"], abs=1e-6)
        assert o["plausibility_loss"] == pytest.approx(1 - e["plausibility_raw"], abs=1e-6)
        assert "combined_score" not in e and "weighted_score" not in e


# ---------------- explanations
def _manual_candidate():
    """Template T1 (cotton 60 / polyester 40 shell; polyester lining) -> substitute shell polyester with nylon."""
    tmpl = next(t for t in select_templates(REP, request(), 10, 1)[0] if t.garment_id == "T1")
    comps = clone_components(tmpl.components)
    log = [apply_substitution(comps, 0, 1, "nylon", 0)]                       # SR1: cotton+polyester (ok) -> cotton+nylon (unsupported)
    pub = public_components(comps)
    cand = {"candidate_id": "cand_manual", "template_garment_id": "T1", "components": pub, "mutation_log": log, "n_mutations": 1,
            "normalized_colour": tmpl.colour, "target_segment": "women", "detail_category": "trousers",
            "template_distance": template_distance(public_components(tmpl.components), pub),
            "oracle": oracle_eval("cand_manual", tmpl.colour, pub)}
    return tmpl, cand


def test_explanations_contain_only_supported_before_after_changes():
    tmpl, cand = _manual_candidate()
    req = request(stretch="low", colour="black")
    ev = evaluate_candidate(cand, req, tmpl, SUP, CFG)
    from cago.evaluation.candidate import evaluate_template
    tev = evaluate_template(tmpl, req, SUP, CFG)
    ex = explain_candidate(cand, ev, tev, tmpl, ["balanced"], CFG)
    t_or, c_or = oracle_eval("t", tmpl.colour, public_components(tmpl.components)), cand["oracle"]
    for r in ex["sorting"]["rules"]:
        i = r["rule"][2]
        t, c = bool(t_or[f"sr{i}_violation"]), bool(c_or[f"sr{i}_violation"])
        assert (r["template_violated"], r["candidate_violated"]) == (t, c)
        expected = "resolved" if t and not c else "introduced" if c and not t else "still_violated" if c else "still_satisfied"
        assert r["vs_template"] == expected
    changed = [r for r in ex["sorting"]["rules"] if r["vs_template"] in ("resolved", "introduced")]
    assert changed and all("confirmed_by_mutation_steps" in r for r in changed)
    sr1 = next(r for r in ex["sorting"]["rules"] if r["rule"] == "SR1")
    assert sr1["vs_template"] == "introduced" and sr1["confirmed_by_mutation_steps"] == [0]   # ablation confirms the cause
    rule_statements = [s for s in ex["statements"] if s.split(" ")[0] in {f"SR{i}" for i in range(1, 6)}]
    assert len(rule_statements) == len(changed)                                          # unchanged rules are never mentioned
    assert [m["description"] for m in ex["mutations"]] == [describe_mutation(e) for e in cand["mutation_log"]]
    assert "Substituted polyester with nylon" in ex["mutations"][0]["description"]
    text = " ".join(ex["statements"] + ex["trade_offs"] + [ex["disclaimer"]]).lower()
    assert not any(w in text for w in FORBIDDEN_WORDS)
    assert ex["disclaimer"] == DISCLAIMER and ex["deltas_vs_template"]["violation_count"] == ev["sorting"]["violation_count"] - tev["sorting"]["violation_count"]


def test_ablation_does_not_attribute_without_confirmation():
    tmpl = next(t for t in select_templates(REP, request(), 10, 1)[0] if t.garment_id == "T1")
    comps = clone_components(tmpl.components)
    log = [apply_percentage(comps, 0, 0, 1, 1.0, 0)]                                    # cotton 60->59, polyester 40->41: no rule changes
    pub = public_components(comps)
    cand = {"candidate_id": "cand_pct", "template_garment_id": "T1", "components": pub, "mutation_log": log, "n_mutations": 1,
            "normalized_colour": tmpl.colour, "target_segment": "women", "detail_category": "trousers",
            "template_distance": template_distance(public_components(tmpl.components), pub),
            "oracle": oracle_eval("cand_pct", tmpl.colour, pub)}
    from cago.evaluation.candidate import evaluate_template
    req = request(colour="black")
    ev, tev = evaluate_candidate(cand, req, tmpl, SUP, CFG), evaluate_template(tmpl, req, SUP, CFG)
    ex = explain_candidate(cand, ev, tev, tmpl, ["sorting_focused"], CFG)
    assert all(r["vs_template"] in ("still_violated", "still_satisfied") for r in ex["sorting"]["rules"])
    assert not any("compared with the template (" in s for s in ex["statements"])
    assert "Moved 1 percentage points" in ex["mutations"][0]["description"]


def test_explanations_for_pipeline_selections():
    out = run(request(colour="black", breathability="high", fit="slim"))
    assert out["explanations"] and {e["candidate_id"] for e in out["explanations"]} == {s["candidate_id"] for s in out["selection"]["selections"]}
    for e in out["explanations"]:
        text = json.dumps(e).lower()
        assert not any(w in text for w in FORBIDDEN_WORDS)
        assert set(e["preferences"]) == {"satisfied", "partial", "not_satisfied", "unscorable"}
        assert e["roles"] and e["trade_offs"] and e["mutations"]


# ---------------- real data (skipped when outputs are missing)
PROCESSED = Path(os.environ.get("CAGO_PROCESSED_DIR") or Path(__file__).resolve().parents[1] / "data" / "processed")


@pytest.mark.skipif(not (PROCESSED / "garment_representation.parquet").exists(), reason="representation outputs missing")
def test_real_data_pipeline_end_to_end():
    from cago.requirements.validation import RequirementContext, validate_request
    rep = pd.read_parquet(PROCESSED / "garment_representation.parquet")
    ctx = RequirementContext.from_processed(PROCESSED)
    sup = build_support_tables(rep)
    v = validate_request({"target_segment": "women", "detail_category": "trousers", "forbidden_materials": ["polyester"],
                          "preferred_dominant_material": "linen", "stretch": "low", "breathability": "high",
                          "fit": "relaxed", "length_cut": "long"}, ctx)
    g = GenerationConfig(n_templates=5, mutations_per_template=4, seed=3)
    a = evaluate_and_select(v.request, rep, sup, ctx, g, CFG)
    b = evaluate_and_select(v.request, rep, sup, ctx, g, CFG)
    assert a["digest"] == b["digest"] and a["evaluation"]["valid"] and a["pareto"]["front_size"] >= 1
    assert {"balanced", "sorting_focused"} <= set(a["selection"]["by_role"]) and not a["evaluation"]["excluded"]
    train_ids = set(rep.loc[rep["split"] == "train", "garment_id"])
    assert all(e["template_garment_id"] in train_ids for e in a["evaluation"]["valid"])
