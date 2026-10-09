"""Orchestration of the final A-vs-B3 evaluation: identical conditions, per-request summaries, paired + clustered statistics.

No generator, metric, Pareto or selection logic is implemented here: frozen modules are called as they are.
Per-request work is a pure function of the request, so the optional process pool and the resumable per-request cache
cannot change any value (verified by tests: cached / parallel == sequential).
"""
from __future__ import annotations

import multiprocessing as mp
import pickle
import time
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any, Callable

import pandas as pd

from cago.benchmark.final_test_requests import cluster_ids
from cago.benchmark.final_test_stats import paired_summary
from cago.benchmark.runner import STAGES, _row, aggregate_stage, trade_flags
from cago.benchmark.sorting_aware_comparison import run_variant
from cago.evaluation.config import EvaluationConfig
from cago.generation.support_tables import SupportTables
from cago.preprocessing.ids import stable_hash
from cago.requirements.validation import RequirementContext, validate_request

SR = ("SR1", "SR2", "SR3", "SR4", "SR5")
STAGE_KEYS = STAGES[1:]
METRICS = ("vc_mean", "zero_share", *[f"{s}_rate" for s in SR], "intent_mean", "plaus_mean", "dist_mean")
PRIMARY = (("B_hard_valid_candidates", "vc_mean"), ("E_sorting_focused", "vc_mean"), ("B_hard_valid_candidates", "zero_share"),
           ("D_balanced", "intent_mean"), ("D_balanced", "plaus_mean"))
MAX_EXAMPLES = 6


def stage_summary(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    it = [r["intent"] for r in rows if r["intent"] is not None]
    d = {"n": len(rows), "vc_mean": mean(r["vc"] for r in rows), "zero_share": mean(float(r["vc"] == 0) for r in rows),
         "intent_mean": mean(it) if it else None, "plaus_mean": mean(r["plaus"] for r in rows), "dist_mean": mean(r["dist"] for r in rows)}
    for s in SR:
        d[f"{s}_rate"] = mean(float(r["sr"][s]) for r in rows)
    return d


def side_effect_examples(request_id: str, res: dict[str, Any], limit: int = MAX_EXAMPLES) -> list[dict[str, Any]]:
    """Accepted repairs that fixed one rule but introduced another (taken from the generator's own repair trace)."""
    out = []
    for c in res["candidates"]:
        for s in c.get("repair_trace", []):
            if s["accepted"] and s["introduced_rules"] and len(out) < limit:
                out.append({"request_id": request_id, "candidate_id": c["candidate_id"], "operation": s["operation"],
                            "targeted_rule": s["targeted_rule"], "confirmed_fixed_rules": s["confirmed_fixed_rules"],
                            "introduced_rules": s["introduced_rules"], "violations_before_after": [s["oracle_before"]["violation_count"], s["oracle_after"]["violation_count"]],
                            "intent_delta": s["intent_delta"], "plausibility_delta": s["plausibility_delta"]})
    return out


def _request_blob(rq, v, rep_gen, ctx, support, variants, ecfg, names, example_variant) -> dict[str, Any]:
    """Run every variant on ONE valid request; returns the picklable per-request result (pure function of the request)."""
    recs, rows, trows, examples = {}, {n: {s: [] for s in STAGE_KEYS} for n in names}, [], []
    for n in names:
        def gen(req, rep, sup, c, _g=variants[n], _n=n):
            res = _g(req, rep, sup, c)
            if _n == example_variant:
                examples.extend(side_effect_examples(rq["request_id"], res))
            return res
        t0 = time.perf_counter()
        rec, rr, ev = run_variant(v.request, rep_gen, support, ctx, gen, ecfg)
        total = time.perf_counter() - t0
        for r in rr:
            r["request_id"] = rq["request_id"]
            rows[n][r["stage"]].append(r)
        if n == names[0]:
            for tid, te in ev["templates"].items():
                if tid in rec["template_ids"]:
                    trows.append(_row(rq["request_id"], te, te, "A_templates"))
        recs[n] = {
            **{k2: rec[k2] for k2 in ("generated", "requested", "hard_valid", "attempts", "rejected", "unique_candidate_rate", "template_ids", "pool",
                                      "front_size", "front_violation_levels", "no_zero_violation_candidate", "no_zero_violation_in_front",
                                      "multiple_roles_same_candidate", "min_violation_valid", "search", "digest")},
            "seconds_generation_and_evaluation": round(total, 4), "seconds_generation_only": rec["seconds"],
            "request_core": {"hard": v.request["hard_constraints"], "soft": {a: b for a, b in v.request["soft_preferences"].items() if b is not None}},
            "ignored_preferences": sorted(v.request.get("ignored_preferences", {})), "cell": rq["cell"], "type": rq["type"],
            "stages": {s: stage_summary(rows[n][s]) for s in STAGE_KEYS}}
    return {"recs": recs, "rows": rows, "trows": trows, "examples": examples}


_G: dict[str, Any] = {}


def _worker(k: int) -> tuple[int, dict[str, Any]]:
    g = _G
    rq = g["requests"][k]
    return k, _request_blob(rq, validate_request(rq["raw"], g["ctx"]), g["rep_gen"], g["ctx"], g["support"], g["variants"], g["ecfg"],
                            g["names"], g["example_variant"])


def run_requests(requests: list[dict[str, Any]], rep_gen: pd.DataFrame, ctx: RequirementContext, support: SupportTables,
                 variants: dict[str, Callable], ecfg: EvaluationConfig, rerun_check: int = 10, progress: Callable | None = None,
                 cache_dir: Path | None = None, cache_tag: str = "", workers: int = 1, example_variant: str | None = None) -> dict[str, Any]:
    """Run every variant on every request under identical conditions. Invalid requests are recorded, never dropped.

    cache_dir: per-request results are pickled (atomic write) and reused after an interruption of the process.
    workers > 1: per-request work runs in a fork-based process pool; results are merged in request order.
    """
    if tuple(support.splits_used) != ("train",) or set(rep_gen["split"].unique()) - {"train"}:
        raise ValueError("generators must receive TRAIN-only support tables and TRAIN-only rows")
    names = list(variants)
    example_variant = example_variant or names[-1]
    cache = None if cache_dir is None else Path(cache_dir)
    if cache is not None:
        cache.mkdir(parents=True, exist_ok=True)
    invalid, valid_reqs = [], []
    for rq in requests:
        v = validate_request(rq["raw"], ctx)
        if v.ok:
            valid_reqs.append(rq)
        else:
            invalid.append({"request_id": rq["request_id"], "errors": [e.code for e in v.errors]})
    path = lambda rq: None if cache is None else cache / f"{cache_tag}_{stable_hash(rq['request_id'], length=20)}.pkl"
    blobs: dict[int, dict[str, Any]] = {}
    for k, rq in enumerate(valid_reqs):
        p = path(rq)
        if p is not None and p.exists():
            blobs[k] = pickle.loads(p.read_bytes())
    n_cached = len(blobs)
    todo = [k for k in range(len(valid_reqs)) if k not in blobs]

    def store(k, blob):
        blobs[k] = blob
        p = path(valid_reqs[k])
        if p is not None:
            tmp = p.with_suffix(".tmp")
            tmp.write_bytes(pickle.dumps(blob))
            tmp.replace(p)
        if progress and len(blobs) % 25 == 0:
            progress(len(blobs), len(valid_reqs))

    if workers > 1 and len(todo) > 1:
        _G.update(requests=valid_reqs, rep_gen=rep_gen, ctx=ctx, support=support, variants=variants, ecfg=ecfg, names=names,
                  example_variant=example_variant)
        with mp.get_context("fork").Pool(workers) as pool:
            for k, blob in pool.imap_unordered(_worker, todo, chunksize=1):
                store(k, blob)
        _G.clear()
    else:
        for k in todo:
            rq = valid_reqs[k]
            store(k, _request_blob(rq, validate_request(rq["raw"], ctx), rep_gen, ctx, support, variants, ecfg, names, example_variant))
    recs: dict[str, dict[str, Any]] = {n: {} for n in names}
    rows: dict[str, dict[str, list]] = {n: {s: [] for s in STAGE_KEYS} for n in names}
    trows: list[dict[str, Any]] = []
    examples: list[dict[str, Any]] = []
    for k, rq in enumerate(valid_reqs):                      # merge in request order (independent of execution order)
        b = blobs[k]
        for n in names:
            recs[n][rq["request_id"]] = b["recs"][n]
            for s in STAGE_KEYS:
                rows[n][s] += b["rows"][n][s]
        trows += b["trows"]
        examples += b["examples"]
    det = []
    for rq in valid_reqs[:rerun_check]:
        v = validate_request(rq["raw"], ctx)
        for n in names:
            det.append(run_variant(v.request, rep_gen, support, ctx, variants[n], ecfg)[0]["digest"] == recs[n][rq["request_id"]]["digest"])
    return {"names": names, "recs": recs, "rows": rows, "template_rows": trows, "invalid": invalid, "valid_requests": valid_reqs,
            "determinism": {"rerun_requests": min(rerun_check, len(valid_reqs)), "checks": len(det), "all_identical": all(det)},
            "requests_loaded_from_cache": n_cached, "repair_side_effect_examples": examples[:MAX_EXAMPLES],
            "repair_side_effect_examples_total": len(examples)}


def metric_maps(recs: dict[str, dict[str, Any]], stage: str) -> dict[str, dict[str, float | None]]:
    return {m: {rid: (r["stages"][stage][m] if r["stages"][stage] else None) for rid, r in recs.items()} for m in METRICS}


def analyze_pairs(raw: dict[str, Any], baseline: str, variant: str, n_boot: int, seed: int) -> dict[str, Any]:
    reqs = raw["valid_requests"]
    universe = [r["request_id"] for r in reqs]
    cl = cluster_ids(reqs)
    out: dict[str, Any] = {}
    for stage in STAGE_KEYS:
        a, b = metric_maps(raw["recs"][baseline], stage), metric_maps(raw["recs"][variant], stage)
        out[stage] = {m: paired_summary(a[m], b[m], universe, cl, n_boot, seed) for m in METRICS}
    return out


def breakdowns(raw, baseline, variant, key: Callable[[dict[str, Any]], str], n_boot: int, seed: int, min_n_ci: int = 10) -> dict[str, Any]:
    reqs = raw["valid_requests"]
    cl = cluster_ids(reqs)
    groups: dict[str, list[str]] = {}
    for rq in reqs:
        groups.setdefault(key(rq), []).append(rq["request_id"])
    out: dict[str, Any] = {}
    maps = {st: (metric_maps(raw["recs"][baseline], st), metric_maps(raw["recs"][variant], st)) for st, _ in PRIMARY}
    for g, ids in sorted(groups.items()):
        cell: dict[str, Any] = {"n_requests": len(ids)}
        for st, m in PRIMARY:
            a, b = maps[st][0][m], maps[st][1][m]
            cell[f"{st}:{m}"] = paired_summary({i: a[i] for i in ids}, {i: b[i] for i in ids}, ids, cl, n_boot, seed, with_ci=len(ids) >= min_n_ci)
        out[g] = cell
    return out


def stage_pooled(raw, n_boot: int, seed: int) -> dict[str, Any]:
    out = {"A_templates_reference": aggregate_stage(raw["template_rows"], n_boot, seed)}
    for n in raw["names"]:
        out[n] = {s: aggregate_stage(raw["rows"][n][s], n_boot, seed) for s in STAGE_KEYS}
    return out


def costs(raw, baseline: str, variant: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for n in raw["names"]:
        rs = list(raw["recs"][n].values())
        s = Counter()
        for r in rs:
            s.update(r["search"])
        gen = sum(r["generated"] for r in rs)
        n_templates = sum(len(r["template_ids"]) for r in rs)
        out[n] = {"requests": len(rs), "candidates_requested": sum(r["requested"] for r in rs), "candidates_generated": gen,
                  "generated_over_requested": round(gen / max(1, sum(r["requested"] for r in rs)), 4), "mutation_attempts": sum(r["attempts"] for r in rs),
                  "oracle_calls_generation_phase": gen + s.get("oracle_full_evals", 0), "oracle_calls_evaluation_phase_templates": n_templates,
                  "fast_rule_evals": s.get("fast_rule_evals", 0), "repair_proposals_evaluated": s.get("repair_proposals_evaluated", 0),
                  "repair_accepted": s.get("repair_accepted", 0), "intent_evals_in_repair": s.get("intent_evals", 0),
                  "plausibility_evals_in_repair": s.get("plausibility_evals", 0),
                  "seconds_generation_only_total": round(sum(r["seconds_generation_only"] for r in rs), 2),
                  "seconds_generation_and_evaluation_total": round(sum(r["seconds_generation_and_evaluation"] for r in rs), 2),
                  "seconds_per_request_mean": round(mean(r["seconds_generation_and_evaluation"] for r in rs), 4) if rs else None}
    a, b = out[baseline], out[variant]
    ratio = lambda k: None if not a[k] else round(b[k] / a[k], 3)
    out["ratios_variant_over_baseline"] = {k: ratio(k) for k in ("mutation_attempts", "oracle_calls_generation_phase", "seconds_generation_only_total",
                                                                  "seconds_generation_and_evaluation_total", "candidates_generated")}
    out["fairness_statement"] = ("Requested candidates, template pool, template selection, seed, attempt limit and evaluation are identical. "
                                 "Computational cost is NOT equal: Generator B3 performs additional Oracle-guided rule evaluations, Oracle calls and "
                                 "Intent/Plausibility evaluations for repairs (see ratios).")
    out["timing_note"] = "wall-clock seconds measured per request inside one worker process; informational only"
    return out


def conditions_check(raw, baseline: str, variant: str, ecfg: EvaluationConfig) -> dict[str, Any]:
    ra, rb = raw["recs"][baseline], raw["recs"][variant]
    ids = sorted(set(ra) & set(rb))
    return {"requests_in_both": len(ids), "requests_run": len(raw["valid_requests"]),
            "identical_template_selection": all(ra[i]["template_ids"] == rb[i]["template_ids"] for i in ids),
            "identical_eligible_pool_size": all(ra[i]["pool"] == rb[i]["pool"] for i in ids),
            "identical_requested_budget": all(ra[i]["requested"] == rb[i]["requested"] for i in ids),
            "identical_evaluation_config": True, "evaluation_config_fields": sorted(type(ecfg).__dataclass_fields__)}


def trade_off_counts(raw, drop: float) -> dict[str, Any]:
    out: dict[str, Any] = {"plausibility_drop_threshold_points": round(100 * drop, 1)}
    for n in raw["names"]:
        out[n] = {}
        for st in STAGE_KEYS:
            fl = [trade_flags(r, drop) for r in raw["rows"][n][st]]
            cell = {"n_rows": len(fl)}
            for k in ("sorting_up_intent_down", "intent_up_sorting_down", "sorting_up_plaus_drop", "all_three_improve"):
                d = [f[k] for f in fl if f[k] is not None]
                cell[k] = {"count": sum(d), "defined_n": len(d), "rate": round(sum(d) / len(d), 4) if d else None}
            out[n][st] = cell
    return out


def reproduce_request(rq: dict[str, Any], rep_gen: pd.DataFrame, ctx: RequirementContext, support: SupportTables,
                      variants: dict[str, Callable], ecfg: EvaluationConfig) -> dict[str, Any]:
    """Re-run ONE request for every variant and describe the selected designs (deterministic; used for the report's examples)."""
    from cago.evaluation.explanations import describe_mutation
    from cago.evaluation.pipeline import evaluate_and_select
    from cago.generation.baseline import GenerationConfig
    v = validate_request(rq["raw"], ctx)
    if not v.ok:
        return {"request_id": rq["request_id"], "invalid": [e.code for e in v.errors]}
    out: dict[str, Any] = {"request_id": rq["request_id"], "request": {"hard": v.request["hard_constraints"],
                                                                      "soft": {k: x for k, x in v.request["soft_preferences"].items() if x is not None}}, "variants": {}}
    for n, gen in variants.items():
        res = gen(v.request, rep_gen, support, ctx)
        pe = evaluate_and_select(v.request, rep_gen, support, ctx, GenerationConfig(), ecfg, res=res)
        emap = {e["candidate_id"]: e for e in pe["evaluation"]["valid"]}
        cmap = {c["candidate_id"]: c for c in res["candidates"]}
        designs = {}
        for role, cid in pe["selection"]["by_role"].items():
            if not cid:
                continue
            e, c = emap[cid], cmap[cid]
            designs[role] = {"candidate_id": cid, "template_garment_id": c["template_garment_id"], "violation_count": e["sorting"]["violation_count"],
                             "sr_violations": e["sorting"]["rules"], "intent_0_100": e["intent"]["intent_alignment_0_100"],
                             "plausibility_0_100": e["plausibility"]["plausibility_0_100"], "template_distance": e["template_distance_raw"],
                             "components": [[x["component_name_normalized"], [[m["material"], m["pct"]] for m in x["materials"]]] for x in c["components"]],
                             "mutations": [describe_mutation(m) for m in c["mutation_log"]]}
        out["variants"][n] = {"template_pool": res["template_pool"]["eligible_templates"], "generated": len(res["candidates"]), "front_size": pe["pareto"]["front_size"],
                              "designs": designs, "explanation_statements": {x["candidate_id"]: x["statements"][:4] for x in pe["explanations"]}}
    return out
