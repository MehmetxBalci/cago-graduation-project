"""Baseline benchmark runner: many request cells -> compact per-request records + stage aggregates.

Uses the frozen generator / evaluation / Pareto modules as they are (no explanations, no candidate dumps).
Every generation/support operation is TRAIN-only; TEST garments only define which requests are asked.
"""
from __future__ import annotations

from collections import Counter
from statistics import mean, median
from typing import Any

import pandas as pd

from cago.benchmark.statistics import bootstrap_ci, cluster_bootstrap_ci, describe
from cago.evaluation.candidate import RULES, evaluate_request_candidates
from cago.evaluation.config import EvaluationConfig
from cago.generation.baseline import GenerationConfig, generate_baseline, public_components
from cago.generation.support_tables import SupportTables
from cago.optimization.pareto import pareto_sort
from cago.optimization.selection import select_designs
from cago.preprocessing.ids import stable_hash
from cago.requirements.validation import RequirementContext, validate_candidate, validate_request

STAGES = ("A_templates", "B_hard_valid_candidates", "C_pareto_front", "D_balanced", "E_sorting_focused", "F_intent_focused")
POOL_BINS = (("<5", 0, 4), ("5-19", 5, 19), ("20-99", 20, 99), (">=100", 100, 10**9))


def pool_bin(n: int) -> str:
    return next(name for name, lo, hi in POOL_BINS if lo <= n <= hi)


def _row(request_id, e, t, stage) -> dict[str, Any]:
    """Compact stage row for a candidate evaluation `e` with its template's evaluation `t`."""
    return {"request_id": request_id, "stage": stage, "candidate_id": e["candidate_id"], "vc": e["sorting"]["violation_count"],
            "sr": {r[:3].upper(): bool(e["sorting"]["oracle"][r]) for r in RULES}, "intent": e["intent_alignment_raw"],
            "plaus": e["plausibility_raw"], "n_sub": e["template_distance_raw"]["n_substitutions"],
            "abs_pct": e["template_distance_raw"]["abs_pct_change_total"],
            "dist": e["template_distance_raw"]["diagnostic_distance"], "t_vc": t["sorting"]["violation_count"],
            "t_intent": t["intent_alignment_raw"], "t_plaus": t["plausibility_raw"]}


def trade_flags(row: dict[str, Any], drop: float) -> dict[str, bool | None]:
    dv, dp = row["vc"] - row["t_vc"], row["plaus"] - row["t_plaus"]
    di = None if row["intent"] is None or row["t_intent"] is None else row["intent"] - row["t_intent"]
    return {"sorting_up_intent_down": None if di is None else (dv < 0 and di < -1e-9),
            "intent_up_sorting_down": None if di is None else (di > 1e-9 and dv > 0),
            "sorting_up_plaus_drop": dv < 0 and dp < -drop,
            "all_three_improve": None if di is None else (dv < 0 and di > 1e-9 and dp > 1e-9)}


def run_request(rq: dict[str, Any], rep: pd.DataFrame, ctx: RequirementContext, support: SupportTables,
                gcfg: GenerationConfig, cfg: EvaluationConfig) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """(compact record, stage rows) for one benchmark request."""
    v = validate_request(rq["raw"], ctx)
    rec: dict[str, Any] = {"request_id": rq["request_id"], "cell": rq["cell"], "type": rq["type"],
                           "source_test_garment": rq["source_test_garment"]}
    if not v.ok:
        return {**rec, "status": "invalid_request", "errors": [e.code for e in v.errors]}, []
    req = v.request
    res = generate_baseline(req, rep, support, ctx, gcfg)
    ev = evaluate_request_candidates(res, support, ctx, cfg)
    valid = ev["valid"]
    pareto = pareto_sort(valid, cfg.objective_decimals) if valid else {"dimensions": [], "front_size": 0}
    sel = select_designs(valid, pareto["dimensions"], cfg) if valid else {"by_role": {}}
    emap = {e["candidate_id"]: e for e in valid}
    pool = res["template_pool"]
    forb = req["hard_constraints"]["forbidden_materials"]
    rows: list[dict[str, Any]] = []
    for t in res["templates"]:
        te = ev["templates"][t.garment_id]
        r = _row(rq["request_id"], te, te, "A_templates")
        r["candidate_id"] = t.garment_id
        r["hard_valid"] = not validate_candidate(public_components(t.components), forb, ctx)
        rows.append(r)
    for e in valid:
        t = ev["templates"][e["template_garment_id"]]
        rows.append(_row(rq["request_id"], e, t, "B_hard_valid_candidates"))
        if e["is_pareto"]:
            rows.append(_row(rq["request_id"], e, t, "C_pareto_front"))
    for role, stage in (("balanced", "D_balanced"), ("sorting_focused", "E_sorting_focused"), ("intent_focused", "F_intent_focused")):
        cid = sel["by_role"].get(role)
        if cid:
            e = emap[cid]
            rows.append(_row(rq["request_id"], e, ev["templates"][e["template_garment_id"]], stage))
    front = [e for e in valid if e["is_pareto"]]
    soft_active = sorted(k for k, x in req["soft_preferences"].items() if x is not None)
    rec.update({
        "status": "ok" if valid else "no_valid_candidates", "request_core": {"hard": req["hard_constraints"], "soft": {k: req["soft_preferences"][k] for k in soft_active}},
        "ignored_preferences": sorted(req.get("ignored_preferences", {})),
        "pool": {"train_garments_in_cell": pool["train_garments_in_cell"], "eligible_templates": pool["eligible_templates"],
                 "selected": pool["selected"], "bin": pool_bin(pool["eligible_templates"]),
                 "selected_requiring_forbidden_repair": pool["selected_requiring_forbidden_repair"]},
        "generated": len(res["candidates"]), "requested": gcfg.n_templates * gcfg.mutations_per_template,
        "hard_valid": len(valid), "rejected": res["rejected"],
        "pareto_dims": pareto["dimensions"], "intent_dimension": pareto.get("intent_dimension", "n/a"), "front_size": pareto["front_size"],
        "no_zero_violation_in_front": bool(front) and min(e["sorting"]["violation_count"] for e in front) > 0,
        "template_violation_counts": [r["vc"] for r in rows if r["stage"] == "A_templates"],
        "candidate_violation_distribution": {str(k): sum(e["sorting"]["violation_count"] == k for e in valid) for k in range(6)},
        "selected": {role: ({k: r[k] for k in ("candidate_id", "vc", "sr", "intent", "plaus", "n_sub", "abs_pct", "t_vc", "t_intent", "t_plaus")}
                            if (r := next((x for x in rows if x["stage"] == st and x["candidate_id"] == sel["by_role"].get(role)), None)) else None)
                     for role, st in (("balanced", "D_balanced"), ("sorting_focused", "E_sorting_focused"), ("intent_focused", "F_intent_focused"))},
        "digest": stable_hash([[e["candidate_id"], e["objectives"], e["pareto_rank"]] for e in valid], sel["by_role"], length=16)})
    return rec, rows


def _rate(rows, key) -> float | None:
    return round(sum(bool(key(r)) for r in rows) / len(rows), 4) if rows else None


def aggregate_stage(rows: list[dict[str, Any]], n_boot: int, seed: int) -> dict[str, Any]:
    if not rows:
        return {"n_rows": 0}
    by_req: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_req.setdefault(r["request_id"], []).append(r)
    vc_req = [mean(x["vc"] for x in rs) for rs in by_req.values()]
    out = {
        "n_rows": len(rows), "n_requests": len(by_req),
        "violation_count": {"pooled": describe([r["vc"] for r in rows], 3), "per_request_mean_median_ci95": bootstrap_ci(vc_req, "median", n_boot, seed)},
        "zero_violation_rate_pooled": _rate(rows, lambda r: r["vc"] == 0),
        "zero_violation_rate_per_request_mean": round(mean(_rate(rs, lambda r: r["vc"] == 0) for rs in by_req.values()), 4),
        "sr_rates": {k: _rate(rows, lambda r, k=k: r["sr"][k]) for k in ("SR1", "SR2", "SR3", "SR4", "SR5")},
        "any_violation_rate": _rate(rows, lambda r: r["vc"] > 0),
        "intent_0_100": describe([100 * r["intent"] for r in rows if r["intent"] is not None], 2),
        "intent_null_rate": _rate(rows, lambda r: r["intent"] is None),
        "plausibility_0_100": describe([100 * r["plaus"] for r in rows], 2),
        "template_distance": {"n_substitutions_mean": round(mean(r["n_sub"] for r in rows), 3),
                              "abs_pct_change_mean": round(mean(r["abs_pct"] for r in rows), 3),
                              "diagnostic_distance": describe([r["dist"] for r in rows], 3)}}
    if rows[0]["stage"] == "A_templates":
        out["template_hard_valid_rate"] = _rate(rows, lambda r: r.get("hard_valid"))
    return out


def paired_vs_templates(rows: list[dict[str, Any]], n_boot: int, seed: int) -> dict[str, Any]:
    """Cluster (request) bootstrap of the median paired difference to the row's own template."""
    by_req: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_req.setdefault(r["request_id"], []).append(r)
    def ci(fn):
        groups = [[fn(r) for r in rs if fn(r) is not None] for rs in by_req.values()]
        groups = [g for g in groups if g]
        return cluster_bootstrap_ci(groups, "median", n_boot, seed) if groups else {"n": 0}
    return {"violation_count_minus_template": ci(lambda r: r["vc"] - r["t_vc"]),
            "intent_points_minus_template": ci(lambda r: None if r["intent"] is None or r["t_intent"] is None else 100 * (r["intent"] - r["t_intent"])),
            "plausibility_points_minus_template": ci(lambda r: 100 * (r["plaus"] - r["t_plaus"]))}


def trade_off_frequencies(rows_by_stage: dict[str, list[dict[str, Any]]], records: list[dict[str, Any]], drop: float) -> dict[str, Any]:
    out: dict[str, Any] = {"plausibility_drop_threshold_points": round(100 * drop, 1), "per_stage": {}}
    for st in ("B_hard_valid_candidates", "C_pareto_front", "D_balanced", "E_sorting_focused", "F_intent_focused"):
        rows = rows_by_stage.get(st, [])
        fl = [trade_flags(r, drop) for r in rows]
        stage = {"n_rows": len(rows)}
        for k in ("sorting_up_intent_down", "intent_up_sorting_down", "sorting_up_plaus_drop", "all_three_improve"):
            defined = [f[k] for f in fl if f[k] is not None]
            stage[k] = {"count": sum(defined), "defined_n": len(defined), "rate": round(sum(defined) / len(defined), 4) if defined else None}
        out["per_stage"][st] = stage
    ok = [r for r in records if r["status"] == "ok"]
    out["requests_without_zero_violation_pareto_candidate"] = {
        "count": sum(r["no_zero_violation_in_front"] for r in ok), "n_requests": len(ok),
        "rate": round(sum(r["no_zero_violation_in_front"] for r in ok) / len(ok), 4) if ok else None}
    return out


def small_pool_analysis(records: list[dict[str, Any]], rows_by_stage, n_boot: int, seed: int) -> dict[str, Any]:
    ok = [r for r in records if r["status"] in ("ok", "no_valid_candidates")]
    out = {}
    for name, lo, hi in POOL_BINS:
        rs = [r for r in ok if lo <= r["pool"]["eligible_templates"] <= hi]
        ids = {r["request_id"] for r in rs}
        sf = [x for x in rows_by_stage.get("E_sorting_focused", []) if x["request_id"] in ids]
        bal = [x for x in rows_by_stage.get("D_balanced", []) if x["request_id"] in ids]
        tmp = [x for x in rows_by_stage.get("A_templates", []) if x["request_id"] in ids]
        valid_rs = [r for r in rs if r["hard_valid"]]
        out[name] = {
            "n_requests": len(rs), "n_cells": len({tuple(r["cell"]) for r in rs}),
            "eligible_pool_median": median([r["pool"]["eligible_templates"] for r in rs]) if rs else None,
            "candidates_generated_over_requested": round(sum(r["generated"] for r in rs) / max(1, sum(r["requested"] for r in rs)), 4) if rs else None,
            "hard_valid_rate": round(sum(r["hard_valid"] for r in rs) / max(1, sum(r["generated"] for r in rs)), 4) if rs else None,
            "front_size": describe([r["front_size"] for r in valid_rs], 2), "front_size_is_one_rate": round(sum(r["front_size"] == 1 for r in valid_rs) / len(valid_rs), 4) if valid_rs else None,
            "no_candidates_rate": round(sum(r["hard_valid"] == 0 for r in rs) / len(rs), 4) if rs else None,
            "template_mean_violation": round(mean(x["vc"] for x in tmp), 3) if tmp else None,
            "sorting_focused_mean_violation": round(mean(x["vc"] for x in sf), 3) if sf else None,
            "sorting_focused_zero_violation_rate": _rate(sf, lambda x: x["vc"] == 0),
            "balanced_mean_intent_0_100": round(100 * mean(x["intent"] for x in bal if x["intent"] is not None), 2) if any(x["intent"] is not None for x in bal) else None,
            "balanced_mean_plausibility_0_100": round(100 * mean(x["plaus"] for x in bal), 2) if bal else None,
            "no_zero_violation_pareto_rate": round(sum(r["no_zero_violation_in_front"] for r in valid_rs) / len(valid_rs), 4) if valid_rs else None,
            "flag": "SMALL POOL: interpret with caution" if name in ("<5", "5-19") and rs else None}
    return out


def run_benchmark(requests: list[dict[str, Any]], rep: pd.DataFrame, ctx: RequirementContext, support: SupportTables,
                  gcfg: GenerationConfig = GenerationConfig(), cfg: EvaluationConfig = EvaluationConfig(),
                  n_boot: int = 1000, seed: int = 0, rerun_check: int = 10) -> dict[str, Any]:
    if tuple(support.splits_used) != ("train",):
        raise ValueError("benchmark support tables must be TRAIN-only")
    records, rows = [], []
    for rq in requests:
        rec, rr = run_request(rq, rep, ctx, support, gcfg, cfg)
        records.append(rec)
        rows += rr
    rows_by_stage = {s: [r for r in rows if r["stage"] == s] for s in STAGES}
    ok = [r for r in records if r["status"] != "invalid_request"]
    rerun = [run_request(rq, rep, ctx, support, gcfg, cfg)[0].get("digest") == next(x for x in records if x["request_id"] == rq["request_id"]).get("digest")
             for rq in requests[:rerun_check]]
    stages = {s: aggregate_stage(rows_by_stage[s], n_boot, seed) for s in STAGES}
    for s in STAGES[1:]:
        stages[s]["paired_vs_own_template"] = paired_vs_templates(rows_by_stage[s], n_boot, seed) if rows_by_stage[s] else {}
    # request-level paired comparison to stage A (macro per request)
    macro = {}
    a_by = {}
    for r in rows_by_stage["A_templates"]:
        a_by.setdefault(r["request_id"], []).append(r["vc"])
    for s in STAGES[1:]:
        by = {}
        for r in rows_by_stage[s]:
            by.setdefault(r["request_id"], []).append(r["vc"])
        ids = sorted(set(by) & set(a_by))
        macro[s] = {"n_requests": len(ids), "mean_violation_minus_templates_per_request": bootstrap_ci(
            [mean(by[i]) - mean(a_by[i]) for i in ids], "median", n_boot, seed) if ids else {"n": 0}}
    return {
        "coverage": {"n_requests": len(requests), "n_ok": sum(r["status"] == "ok" for r in records),
                     "n_invalid": sum(r["status"] == "invalid_request" for r in records),
                     "n_no_valid_candidates": sum(r["status"] == "no_valid_candidates" for r in records),
                     "cells": len({tuple(r["cell"]) for r in records}),
                     "segments": dict(Counter(r["cell"][0] for r in records)), "categories": len({r["cell"][1] for r in records}),
                     "types": dict(Counter(r["type"] for r in records)),
                     "requests_with_soft_preferences": sum(bool(r.get("request_core", {}).get("soft")) for r in ok),
                     "requests_with_forbidden_materials": sum(bool(r.get("request_core", {}).get("hard", {}).get("forbidden_materials")) for r in ok)},
        "totals": {"candidates_generated": sum(r.get("generated", 0) for r in ok), "hard_valid": sum(r.get("hard_valid", 0) for r in ok),
                   "hard_valid_rate": round(sum(r.get("hard_valid", 0) for r in ok) / max(1, sum(r.get("generated", 0) for r in ok)), 4),
                   "candidates_requested": sum(r.get("requested", 0) for r in ok)},
        "stages": stages, "request_level_paired_violation_vs_templates": macro,
        "trade_offs": trade_off_frequencies(rows_by_stage, records, cfg.plausibility_drop_substantial),
        "small_pool": small_pool_analysis(records, rows_by_stage, n_boot, seed),
        "determinism": {"rerun_requests": len(rerun), "all_identical": all(rerun)},
        "records": records, "support_splits_used": list(support.splits_used)}
