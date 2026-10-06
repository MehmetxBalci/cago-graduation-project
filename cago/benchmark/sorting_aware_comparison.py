"""VAL-only development comparison: Baseline A vs Generator B variants under the SAME Candidate Evaluation + Pareto V1.

Descriptive development analysis (not a final TEST evaluation). Paired comparisons are by request.
"""
from __future__ import annotations

import time
from collections import Counter
from statistics import mean
from typing import Any, Callable

import pandas as pd

from cago.benchmark.benchmark_requests import TYPES
from cago.benchmark.runner import POOL_BINS, STAGES, _row, aggregate_stage, pool_bin
from cago.benchmark.sorting_aware_requests import assert_dev_only
from cago.benchmark.statistics import bootstrap_ci, describe
from cago.evaluation.candidate import RULES, evaluate_request_candidates
from cago.evaluation.config import EvaluationConfig
from cago.generation.baseline import GenerationConfig, generate_baseline
from cago.generation.support_tables import SupportTables
from cago.generation.template_selector import composition_signature
from cago.generation_sorting.config import MODE_CONFIGS, NONDOMINATED_LOCAL, SortingAwareGenerationConfig
from cago.generation_sorting.generator import generate_sorting_aware
from cago.optimization.pareto import pareto_sort
from cago.optimization.selection import select_designs
from cago.preprocessing.ids import stable_hash
from cago.requirements.validation import RequirementContext, validate_request

SR = ("SR1", "SR2", "SR3", "SR4", "SR5")
STAGE_KEYS = STAGES[1:]            # B..F stages (A_templates is the shared template reference)


def default_variants(n_templates: int, per_template: int, seed: int, policy_variants: bool = True) -> dict[str, Callable]:
    """name -> generator(request, rep, support, ctx) with identical template / candidate / attempt budgets."""
    def A(req, rep, sup, ctx):
        return generate_baseline(req, rep, sup, ctx, GenerationConfig(n_templates=n_templates, mutations_per_template=per_template, seed=seed))

    def B(name, **kw):
        cfg = SortingAwareGenerationConfig(n_templates=n_templates, candidates_per_template=per_template, seed=seed, **kw)
        return lambda req, rep, sup, ctx: generate_sorting_aware(req, rep, sup, ctx, cfg)

    out = {"A_baseline": A, "B1_proposal_only": B("B1", **MODE_CONFIGS["B1"]), "B2_repair_only": B("B2", **MODE_CONFIGS["B2"]),
           "B3_proposal_plus_repair": B("B3", **MODE_CONFIGS["B3"])}
    if policy_variants:
        out["B3_nondominated_local"] = B("B3n", **MODE_CONFIGS["B3"], policy=NONDOMINATED_LOCAL)
    return out


def _digest(valid, sel) -> str:
    return stable_hash([[e["candidate_id"], e["objectives"], e["pareto_rank"]] for e in valid], sel.get("by_role", {}), length=16)


def run_variant(req: dict[str, Any], rep: pd.DataFrame, support: SupportTables, ctx: RequirementContext, gen: Callable,
                ecfg: EvaluationConfig) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    t0 = time.perf_counter()
    res = gen(req, rep, support, ctx)
    secs = time.perf_counter() - t0
    ev = evaluate_request_candidates(res, support, ctx, ecfg)
    valid = ev["valid"]
    pareto = pareto_sort(valid, ecfg.objective_decimals) if valid else {"dimensions": [], "front_size": 0}
    sel = select_designs(valid, pareto["dimensions"], ecfg) if valid else {"by_role": {}}
    emap = {e["candidate_id"]: e for e in valid}
    rows = []
    for e in valid:
        t = ev["templates"][e["template_garment_id"]]
        rows.append(_row("", e, t, "B_hard_valid_candidates"))
        if e["is_pareto"]:
            rows.append(_row("", e, t, "C_pareto_front"))
    for role, st in (("balanced", "D_balanced"), ("sorting_focused", "E_sorting_focused"), ("intent_focused", "F_intent_focused")):
        cid = sel["by_role"].get(role)
        if cid:
            rows.append(_row("", emap[cid], ev["templates"][emap[cid]["template_garment_id"]], st))
    front = [e for e in valid if e["is_pareto"]]
    sigs = [composition_signature([{**c, "materials": c["materials"]} for c in cand["components"]]) for cand in res["candidates"]]
    search = dict(res.get("search", {}))
    rec = {"generated": len(res["candidates"]), "requested": res["config"]["n_templates"] * res["config"]["mutations_per_template"],
           "hard_valid": len(valid), "attempts": res["attempts"], "rejected": res["rejected"],
           "unique_candidate_rate": round(len(set(sigs)) / len(sigs), 4) if sigs else None,
           "template_ids": [t.garment_id for t in res["templates"]], "pool": res["template_pool"]["eligible_templates"],
           "front_size": pareto["front_size"], "pareto_dims": pareto["dimensions"],
           "front_violation_levels": len({e["sorting"]["violation_count"] for e in front}),
           "front_intent_range": None if not front or front[0]["intent_alignment_raw"] is None else round(max(e["intent_alignment_raw"] for e in front) - min(e["intent_alignment_raw"] for e in front), 4),
           "front_plaus_range": round(max(e["plausibility_raw"] for e in front) - min(e["plausibility_raw"] for e in front), 4) if front else None,
           "multiple_roles_same_candidate": bool(sel.get("multiple_roles_same_candidate")),
           "min_violation_valid": min((e["sorting"]["violation_count"] for e in valid), default=None),
           "no_zero_violation_candidate": bool(valid) and min(e["sorting"]["violation_count"] for e in valid) > 0,
           "no_zero_violation_in_front": bool(front) and min(e["sorting"]["violation_count"] for e in front) > 0,
           "search": search, "seconds": round(secs, 4), "digest": _digest(valid, sel)}
    return rec, rows, ev


def _by_request(rows, key) -> dict[str, float]:
    g: dict[str, list[float]] = {}
    for r in rows:
        v = key(r)
        if v is not None:
            g.setdefault(r["request_id"], []).append(float(v))
    return {k: mean(v) for k, v in g.items()}


def paired(rows_a, rows_b, key, n_boot: int, seed: int) -> dict[str, Any]:
    """Request-level paired difference (B - A) of per-request means; bootstrap CI over requests."""
    a, b = _by_request(rows_a, key), _by_request(rows_b, key)
    ids = sorted(set(a) & set(b))
    d = [b[i] - a[i] for i in ids]
    if not d:
        return {"n_requests": 0}
    return {"n_requests": len(d), "mean_diff": round(mean(d), 4), "median_ci95": bootstrap_ci(d, "median", n_boot, seed),
            "mean_ci95": bootstrap_ci(d, "mean", n_boot, seed), "share_improved_or_equal": None, "share_nonzero": round(sum(abs(x) > 1e-9 for x in d) / len(d), 4)}


METRICS = {"violation_count": lambda r: r["vc"], "zero_violation": lambda r: float(r["vc"] == 0),
           "intent_0_1": lambda r: r["intent"], "plausibility_0_1": lambda r: r["plaus"], "template_distance": lambda r: r["dist"],
           **{f"{s}_rate": (lambda r, s=s: float(r["sr"][s])) for s in SR}}


def run_comparison(requests: list[dict[str, Any]], rep_dev: pd.DataFrame, ctx: RequirementContext, support: SupportTables,
                   variants: dict[str, Callable], ecfg: EvaluationConfig = EvaluationConfig(), n_boot: int = 500, seed: int = 0,
                   rerun_check: int = 5, baseline: str = "A_baseline") -> dict[str, Any]:
    assert_dev_only(rep_dev)
    if tuple(support.splits_used) != ("train",):
        raise ValueError("support tables must be TRAIN-only")
    recs: dict[str, dict[str, Any]] = {n: {} for n in variants}
    rows: dict[str, dict[str, list]] = {n: {s: [] for s in STAGE_KEYS} for n in variants}
    trows: list[dict[str, Any]] = []
    requests_ok, invalid = [], []
    for rq in requests:
        v = validate_request(rq["raw"], ctx)
        if not v.ok:
            invalid.append(rq["request_id"])
            continue
        requests_ok.append(rq)
        for name, gen in variants.items():
            rec, rr, ev = run_variant(v.request, rep_dev, support, ctx, gen, ecfg)
            recs[name][rq["request_id"]] = {**rec, "request_core": {"hard": v.request["hard_constraints"],
                                                                      "soft": {k: x for k, x in v.request["soft_preferences"].items() if x is not None}},
                                            "cell": rq["cell"], "type": rq["type"]}
            for r in rr:
                r["request_id"] = rq["request_id"]
                rows[name][r["stage"]].append(r)
            if name == baseline:
                for tid, te in ev["templates"].items():
                    if tid in rec["template_ids"]:
                        r = _row(rq["request_id"], te, te, "A_templates")
                        trows.append(r)
    det = []
    for rq in requests_ok[:rerun_check]:
        v = validate_request(rq["raw"], ctx)
        name = "B3_proposal_plus_repair" if "B3_proposal_plus_repair" in variants else next(iter(variants))
        det.append(run_variant(v.request, rep_dev, support, ctx, variants[name], ecfg)[0]["digest"] == recs[name][rq["request_id"]]["digest"])
    return summarize(requests_ok, invalid, recs, rows, trows, n_boot, seed, baseline, det)


def _agg_variant(name, recs, rows, n_boot, seed) -> dict[str, Any]:
    rs = list(recs.values())
    ok = [r for r in rs]
    out: dict[str, Any] = {}
    out["stages"] = {s: aggregate_stage(rows[s], n_boot, seed) for s in STAGE_KEYS}
    gen, req = sum(r["generated"] for r in ok), sum(r["requested"] for r in ok)
    srch = Counter()
    for r in ok:
        srch.update(r["search"])
    n_final = srch.get("candidates_final", 0)
    out["search"] = {
        "candidates_generated": gen, "candidates_requested": req, "generated_over_requested": round(gen / max(1, req), 4),
        "hard_valid": sum(r["hard_valid"] for r in ok), "mutation_attempts": sum(r["attempts"] for r in ok),
        "unique_candidate_rate_mean": round(mean(r["unique_candidate_rate"] for r in ok if r["unique_candidate_rate"] is not None), 4) if any(r["unique_candidate_rate"] is not None for r in ok) else None,
        "oracle_full_evals": srch.get("oracle_full_evals", 0), "fast_rule_evals": srch.get("fast_rule_evals", 0),
        "intent_evals_in_repair": srch.get("intent_evals", 0), "plausibility_evals_in_repair": srch.get("plausibility_evals", 0),
        "repair_proposals_evaluated": srch.get("repair_proposals_evaluated", 0), "repair_accepted": srch.get("repair_accepted", 0),
        "repair_acceptance_rate": round(srch["repair_accepted"] / srch["repair_proposals_evaluated"], 4) if srch.get("repair_proposals_evaluated") else None,
        "candidates_with_accepted_repair": None, "mean_seconds_per_request_informational": round(mean(r["seconds"] for r in ok), 3) if ok else None,
        "rejected": dict(sum((Counter(r["rejected"]) for r in ok), Counter()))}
    out["unresolved_after_generation"] = {
        "candidates_final": n_final, **{f"{r}": srch.get(f"unresolved:{r}", 0) for r in ("SR1", "SR2", "SR3", "SR5")},
        "SR4_immutable_violation": srch.get("sr4_immutable_violation", 0),
        "candidates_with_unresolved_repairable": srch.get("candidates_with_unresolved_repairable", 0)} if n_final else None
    out["failure_analysis"] = {k: v for k, v in sorted(srch.items()) if k.startswith(("repair_rejected", "no_train_supported", "repair_cycle", "proposals_introducing", "accepted_repairs_introducing", "repair_accepted", "confirmed_fixed", "not_attempted"))}
    out["pareto"] = {"front_size": describe([r["front_size"] for r in ok if r["hard_valid"]], 2),
                     "front_size_is_one_rate": round(sum(r["front_size"] == 1 for r in ok if r["hard_valid"]) / max(1, sum(bool(r["hard_valid"]) for r in ok)), 4),
                     "front_violation_levels_mean": round(mean(r["front_violation_levels"] for r in ok if r["hard_valid"]), 3) if any(r["hard_valid"] for r in ok) else None,
                     "front_intent_range_mean": round(mean(r["front_intent_range"] for r in ok if r["front_intent_range"] is not None), 4) if any(r["front_intent_range"] is not None for r in ok) else None,
                     "front_plausibility_range_mean": round(mean(r["front_plaus_range"] for r in ok if r["front_plaus_range"] is not None), 4) if any(r["front_plaus_range"] is not None for r in ok) else None,
                     "selection_role_duplicate_rate": round(sum(r["multiple_roles_same_candidate"] for r in ok if r["hard_valid"]) / max(1, sum(bool(r["hard_valid"]) for r in ok)), 4)}
    valid_reqs = [r for r in ok if r["hard_valid"]]
    out["requests_without_zero_violation_candidate"] = {"count": sum(r["no_zero_violation_candidate"] for r in valid_reqs), "n_requests": len(valid_reqs),
                                                         "rate": round(sum(r["no_zero_violation_candidate"] for r in valid_reqs) / len(valid_reqs), 4) if valid_reqs else None}
    out["requests_without_zero_violation_pareto_candidate"] = {"count": sum(r["no_zero_violation_in_front"] for r in valid_reqs), "n_requests": len(valid_reqs)}
    return out


def small_pool(recs_by_variant, rows_by_variant, n_boot, seed, baseline) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for bname, lo, hi in POOL_BINS:
        ids = {i for i, r in recs_by_variant[baseline].items() if lo <= r["pool"] <= hi}
        cell: dict[str, Any] = {"n_requests": len(ids), "flag": "SMALL POOL: interpret with caution" if bname in ("<5", "5-19") and ids else None, "variants": {}}
        for name, recs in recs_by_variant.items():
            rr = [recs[i] for i in ids]
            valid = [x for x in rr if x["hard_valid"]]
            rowsB = [r for r in rows_by_variant[name]["B_hard_valid_candidates"] if r["request_id"] in ids]
            rowsE = [r for r in rows_by_variant[name]["E_sorting_focused"] if r["request_id"] in ids]
            rowsD = [r for r in rows_by_variant[name]["D_balanced"] if r["request_id"] in ids]
            srch = Counter()
            for x in rr:
                srch.update(x["search"])
            cell["variants"][name] = {
                "generated_over_requested": round(sum(x["generated"] for x in rr) / max(1, sum(x["requested"] for x in rr)), 4) if rr else None,
                "no_candidates_rate": round(sum(x["hard_valid"] == 0 for x in rr) / len(rr), 4) if rr else None,
                "valid_pool_mean_violation": round(mean(r["vc"] for r in rowsB), 3) if rowsB else None,
                "valid_pool_zero_violation_rate": round(sum(r["vc"] == 0 for r in rowsB) / len(rowsB), 4) if rowsB else None,
                "sorting_focused_mean_violation": round(mean(r["vc"] for r in rowsE), 3) if rowsE else None,
                "balanced_mean_intent_0_100": round(100 * mean(r["intent"] for r in rowsD if r["intent"] is not None), 2) if any(r["intent"] is not None for r in rowsD) else None,
                "balanced_mean_plausibility_0_100": round(100 * mean(r["plaus"] for r in rowsD), 2) if rowsD else None,
                "unique_candidate_rate_mean": round(mean(x["unique_candidate_rate"] for x in valid), 4) if valid else None,
                "front_size_is_one_rate": round(sum(x["front_size"] == 1 for x in valid) / len(valid), 4) if valid else None,
                "repair_acceptance_rate": round(srch["repair_accepted"] / srch["repair_proposals_evaluated"], 4) if srch.get("repair_proposals_evaluated") else None,
                "no_train_supported_alternative": sum(v for k, v in srch.items() if k.startswith("no_train_supported_alternative")),
                "repair_rejected_total": sum(v for k, v in srch.items() if k.startswith("repair_rejected")),
                "unresolved_repairable_rate": round(srch.get("candidates_with_unresolved_repairable", 0) / srch["candidates_final"], 4) if srch.get("candidates_final") else None}
        cell["paired_valid_pool_violation_vs_A"] = {n: paired([r for r in rows_by_variant[baseline]["B_hard_valid_candidates"] if r["request_id"] in ids],
                                                              [r for r in rows_by_variant[n]["B_hard_valid_candidates"] if r["request_id"] in ids],
                                                              METRICS["violation_count"], n_boot, seed)
                                                    for n in rows_by_variant if n != baseline}
        out[bname] = cell
    return out


def summarize(requests, invalid, recs, rows, trows, n_boot, seed, baseline, det) -> dict[str, Any]:
    variants = list(recs)
    base_ids = set(recs[baseline])
    same_templates = all(recs[n][i]["template_ids"] == recs[baseline][i]["template_ids"] for n in variants for i in base_ids)
    res: dict[str, Any] = {
        "coverage": {"n_requests": len(requests), "invalid_requests": invalid, "cells": len({tuple(r["cell"]) for r in requests}),
                     "segments": dict(Counter(r["cell"][0] for r in requests)), "categories": len({r["cell"][1] for r in requests}),
                     "types": dict(Counter(r["type"] for r in requests)), "variants": variants},
        "fairness": {"identical_template_pool_and_selection_across_variants": same_templates,
                     "candidates_requested_per_variant": {n: sum(r["requested"] for r in recs[n].values()) for n in variants},
                     "mutation_attempt_budget_per_candidate": "Baseline A max_attempts=25; Generator B max_proposal_attempts=25 (+ bounded repair steps, reported separately)"},
        "determinism": {"rerun_requests": len(det), "all_identical": all(det)},
        "template_reference": aggregate_stage(trows, n_boot, seed),
        "per_variant": {n: _agg_variant(n, recs[n], rows[n], n_boot, seed) for n in variants},
        "paired_vs_baseline": {}, "small_pool": small_pool(recs, rows, n_boot, seed, baseline), "records": recs}
    for n in variants:
        if n == baseline:
            continue
        res["paired_vs_baseline"][n] = {s: {m: paired(rows[baseline][s], rows[n][s], fn, n_boot, seed) for m, fn in METRICS.items()} for s in STAGE_KEYS}
    return res
