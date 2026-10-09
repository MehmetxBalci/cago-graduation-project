"""Report assembly (JSON), schema validation and thesis-oriented Markdown rendering for the final TEST evaluation.

Observed results (computed) are kept separate from interpretation; interpretation text in this module is limited to fixed
limitations that do not depend on the results.
"""
from __future__ import annotations

import json
from collections import Counter
from statistics import mean
from typing import Any

from cago.benchmark.final_test_runner import PRIMARY, STAGE_KEYS, analyze_pairs, breakdowns, conditions_check, costs, metric_maps, stage_pooled, trade_off_counts
from cago.benchmark.runner import pool_bin
from cago.benchmark.sorting_aware_comparison import small_pool
from cago.benchmark.statistics import describe
from cago.evaluation.config import EvaluationConfig

LANG = ("Terminology: SR1-SR5 Sorting Compatibility (violation count under the screening rules; zero violations does NOT mean recyclable), "
        "Intent Alignment, Dataset-relative Plausibility, constraint-based probabilistic generation with sorting-aware proposal/repair. "
        "Not a recyclability, sustainability or manufacturability measure.")
LIMITATIONS = [
    "Requests are derived from held-out TEST garments' observable properties; they are a benchmark of reproducing held-out intents, not real user requests.",
    "SR4 (colour == 'black') is immutable because colour is never mutated: no candidate of a black-template request can reach zero violations.",
    "Fit/length labels are inherited from the TRAIN template and are not re-derived after mutation; Intent saturates easily for derived requests.",
    "Dataset-relative Plausibility measures support/similarity to the TRAIN distribution only; it is not a manufacturability or quality guarantee.",
    "Equal requested budgets are not equal computation: B3 evaluates many more rules/Oracle calls per candidate.",
    "Uncertainty: percentile bootstrap, unadjusted for multiplicity; only P1-P5 are pre-specified primary outcomes. Requests of one cell share the TRAIN template pool (cell-clustered CIs are a sensitivity analysis).",
    "Wall-clock times are single-machine, informational, and not part of any statistical claim.",
    "Results describe this dataset, these V1 configurations and this request construction; they do not establish generalisation to other garment data or to physical sorting performance."]
REQUIRED_KEYS = ("report_version", "manifest", "integrity", "coverage", "conditions", "determinism", "stages", "generation_coverage", "paired",
                 "primary_outcomes", "breakdowns", "small_pool", "trade_offs", "costs", "failure_analysis", "examples", "limitations", "per_request", "invalid_requests")


def validate_report_schema(r: dict[str, Any]) -> list[str]:
    """Returns a list of schema problems ([] = consistent)."""
    p = [f"missing key: {k}" for k in REQUIRED_KEYS if k not in r]
    if p:
        return p
    if len(r["primary_outcomes"]) != len(PRIMARY):
        p.append("primary_outcomes length")
    for st in STAGE_KEYS:
        if st not in r["paired"]:
            p.append(f"paired missing stage {st}")
    for k in ("by_segment", "by_category", "by_request_type", "by_template_pool_bin"):
        if k not in r["breakdowns"]:
            p.append(f"breakdowns missing {k}")
    for k in ("no_candidate_requests", "no_zero_violation_requests", "unresolved_violations", "sr4_immutable", "diversity", "repair_side_effects", "baseline_outperforms_variant"):
        if k not in r["failure_analysis"]:
            p.append(f"failure_analysis missing {k}")
    if r["conditions"].get("identical_template_selection") is not True:
        p.append("conditions: template selection not identical")
    return p


def generation_coverage(raw) -> dict[str, Any]:
    out = {}
    for n in raw["names"]:
        rs = list(raw["recs"][n].values())
        gen = sum(r["generated"] for r in rs)
        uniq = sum(round((r["unique_candidate_rate"] or 0) * r["generated"]) for r in rs)
        out[n] = {"requests": len(rs), "candidates_requested": sum(r["requested"] for r in rs), "candidates_generated": gen,
                  "generated_over_requested": round(gen / max(1, sum(r["requested"] for r in rs)), 4), "unique_candidates": uniq,
                  "unique_candidate_rate": round(uniq / gen, 4) if gen else None, "hard_valid_candidates": sum(r["hard_valid"] for r in rs),
                  "hard_valid_rate": round(sum(r["hard_valid"] for r in rs) / max(1, gen), 4),
                  "requests_without_any_candidate": sum(r["hard_valid"] == 0 for r in rs),
                  "selection_availability": {st: sum(r["stages"][st] is not None for r in rs) for st in ("D_balanced", "E_sorting_focused", "F_intent_focused")},
                  "front_size": describe([r["front_size"] for r in rs if r["hard_valid"]], 2),
                  "front_size_is_one_share": round(sum(r["front_size"] == 1 for r in rs if r["hard_valid"]) / max(1, sum(bool(r["hard_valid"]) for r in rs)), 4),
                  "rejected_totals": dict(sum((Counter(r["rejected"]) for r in rs), Counter()))}
    return out


def failure_analysis(raw, baseline: str, variant: str) -> dict[str, Any]:
    ra, rb = raw["recs"][baseline], raw["recs"][variant]
    ids = sorted(set(ra) & set(rb))
    fa: dict[str, Any] = {}
    fa["no_candidate_requests"] = {n: [{"request_id": i, "pool": r["pool"], "rejected": r["rejected"]}
                                       for i, r in raw["recs"][n].items() if r["hard_valid"] == 0] for n in raw["names"]}
    nz = {n: {i for i, r in raw["recs"][n].items() if r["hard_valid"] and r["no_zero_violation_candidate"]} for n in raw["names"]}
    sr4_only = {i for i in nz[variant] if (rb[i]["stages"]["E_sorting_focused"] or {}).get("SR4_rate") == 1.0}
    fa["no_zero_violation_requests"] = {"baseline": len(nz[baseline]), "variant": len(nz[variant]), "both": len(nz[baseline] & nz[variant]),
                                        "variant_only": sorted(nz[variant] - nz[baseline])[:10], "n_variant_only": len(nz[variant] - nz[baseline]),
                                        "baseline_only": len(nz[baseline] - nz[variant]),
                                        "variant_requests_whose_sorting_focused_design_still_violates_SR4": len(sr4_only),
                                        "denominator_requests_with_candidates": {n: sum(bool(r["hard_valid"]) for r in raw["recs"][n].values()) for n in raw["names"]}}
    srch = Counter()
    for r in rb.values():
        srch.update(r["search"])
    fa["unresolved_violations"] = {"variant_final_candidates": srch.get("candidates_final", 0),
                                   **{f"{r}_unresolved": srch.get(f"unresolved:{r}", 0) for r in ("SR1", "SR2", "SR3", "SR5")},
                                   "candidates_with_unresolved_repairable": srch.get("candidates_with_unresolved_repairable", 0),
                                   "variant_no_train_supported_alternative": {k.split(":")[1]: v for k, v in srch.items() if k.startswith("no_train_supported_alternative")},
                                   "variant_repair_rejections": {k.split(":")[1]: v for k, v in srch.items() if k.startswith("repair_rejected")}}
    resid = {}
    for n in raw["names"]:
        pool = raw["rows"][n]["B_hard_valid_candidates"]
        nzr = [r for r in pool if r["vc"] > 0]
        resid[n] = {"candidates_with_violations": len(nzr), "only_SR4_remaining": sum(r["vc"] == 1 and r["sr"]["SR4"] for r in nzr),
                    "only_SR4_share_of_violating": round(sum(r["vc"] == 1 and r["sr"]["SR4"] for r in nzr) / len(nzr), 4) if nzr else None,
                    "SR4_violation_rate": round(sum(r["sr"]["SR4"] for r in pool) / len(pool), 4) if pool else None}
    fa["sr4_immutable"] = {"note": "colour is not mutated; SR4 can only be satisfied if the template colour is not 'black'", **resid,
                           "variant_sr4_immutable_candidates": srch.get("sr4_immutable_violation", 0)}
    fa["diversity"] = {n: {"unique_candidate_rate_mean": round(mean(r["unique_candidate_rate"] for r in raw["recs"][n].values() if r["unique_candidate_rate"] is not None), 4)
                           if any(r["unique_candidate_rate"] is not None for r in raw["recs"][n].values()) else None,
                           "requests_with_fewer_than_20_candidates": sum(0 < r["generated"] < 20 for r in raw["recs"][n].values()),
                           "duplicate_candidate_rejections": sum(r["rejected"].get("duplicate_candidate", 0) for r in raw["recs"][n].values()),
                           "identical_to_template_rejections": sum(r["rejected"].get("identical_to_template", 0) for r in raw["recs"][n].values()),
                           "front_violation_levels_mean": round(mean(r["front_violation_levels"] for r in raw["recs"][n].values() if r["hard_valid"]), 3)
                           if any(r["hard_valid"] for r in raw["recs"][n].values()) else None} for n in raw["names"]}
    fa["repair_side_effects"] = {"accepted_repairs_introducing_other_violation": srch.get("accepted_repairs_introducing_other_violation", 0),
                                 "repair_proposals_introducing_other_violation": srch.get("proposals_introducing_other_violation", 0),
                                 "repair_accepted": srch.get("repair_accepted", 0), "repair_proposals_evaluated": srch.get("repair_proposals_evaluated", 0),
                                 "examples": raw.get("repair_side_effect_examples", []), "examples_total": raw.get("repair_side_effect_examples_total", 0)}
    out_perf: dict[str, Any] = {}
    for st, m in (("B_hard_valid_candidates", "vc_mean"), ("E_sorting_focused", "vc_mean"), ("D_balanced", "intent_mean"), ("D_balanced", "plaus_mean")):
        a, b = metric_maps(ra, st)[m], metric_maps(rb, st)[m]
        both = [i for i in ids if a[i] is not None and b[i] is not None]
        sign = 1 if m == "vc_mean" else -1                      # >0 means the baseline is better
        worse = sorted(((sign * (b[i] - a[i]), i) for i in both if sign * (b[i] - a[i]) > 1e-9), reverse=True)
        out_perf[f"{st}:{m}"] = {"n_paired": len(both), "baseline_better": len(worse), "variant_better": sum(sign * (b[i] - a[i]) < -1e-9 for i in both),
                                 "equal": sum(abs(b[i] - a[i]) <= 1e-9 for i in both),
                                 "top_baseline_advantage": [{"request_id": i, "baseline": round(a[i], 4), "variant": round(b[i], 4), "pool": ra[i]["pool"],
                                                             "bin": pool_bin(ra[i]["pool"])} for _, i in worse[:6]]}
    fa["baseline_outperforms_variant"] = out_perf
    return fa


def per_request_table(raw, baseline: str, variant: str) -> list[dict[str, Any]]:
    out = []
    for rq in raw["valid_requests"]:
        i = rq["request_id"]
        row = {"request_id": i, "cell": rq["cell"], "type": rq["type"], "source_parent_product_id": rq["source_parent_product_id"],
               "pool": raw["recs"][baseline][i]["pool"]}
        for tag, n in (("A", baseline), ("B3", variant)):
            r = raw["recs"][n][i]
            s = r["stages"]
            g = lambda st, k, d=4: None if not s[st] or s[st][k] is None else round(s[st][k], d)
            row[tag] = {"generated": r["generated"], "hard_valid": r["hard_valid"], "front": r["front_size"], "pool_vc": g("B_hard_valid_candidates", "vc_mean"),
                        "pool_zero": g("B_hard_valid_candidates", "zero_share"), "sort_vc": g("E_sorting_focused", "vc_mean"),
                        "bal_vc": g("D_balanced", "vc_mean"), "bal_intent": g("D_balanced", "intent_mean"), "bal_plaus": g("D_balanced", "plaus_mean"),
                        "seconds": r["seconds_generation_and_evaluation"]}
        out.append(row)
    return out


def assemble_report(raw, coverage, integrity, manifest_info, n_boot: int, seed: int, ecfg: EvaluationConfig,
                    baseline: str = "A_baseline", variant: str = "B3_proposal_plus_repair", examples: dict[str, Any] | None = None) -> dict[str, Any]:
    paired = analyze_pairs(raw, baseline, variant, n_boot, seed)
    n_small = max(200, n_boot // 4)
    pool_key = lambda rq: pool_bin(raw["recs"][baseline][rq["request_id"]]["pool"])
    return {
        "report_version": 1, "manifest": manifest_info, "integrity": integrity, "coverage": coverage,
        "conditions": conditions_check(raw, baseline, variant, ecfg), "determinism": raw["determinism"],
        "stages": stage_pooled(raw, n_small, seed), "generation_coverage": generation_coverage(raw), "paired": paired,
        "primary_outcomes": [{"stage": st, "metric": m, "summary": paired[st][m]} for st, m in PRIMARY],
        "breakdowns": {"by_segment": breakdowns(raw, baseline, variant, lambda rq: rq["cell"][0], n_small, seed),
                       "by_category": breakdowns(raw, baseline, variant, lambda rq: rq["cell"][1], n_small, seed),
                       "by_request_type": breakdowns(raw, baseline, variant, lambda rq: rq["type"], n_small, seed),
                       "by_template_pool_bin": breakdowns(raw, baseline, variant, pool_key, n_small, seed)},
        "small_pool": small_pool(raw["recs"], raw["rows"], n_small, seed, baseline),
        "trade_offs": trade_off_counts(raw, ecfg.plausibility_drop_substantial), "costs": costs(raw, baseline, variant),
        "failure_analysis": failure_analysis(raw, baseline, variant), "examples": examples or {}, "limitations": LIMITATIONS,
        "per_request": per_request_table(raw, baseline, variant), "invalid_requests": raw["invalid"]}


# ---------------------------------------------------------------- markdown
def _t(rows, hdr) -> str:
    return "\n".join(["| " + " | ".join(hdr) + " |", "|" + "|".join("---" for _ in hdr) + "|", *["| " + " | ".join(str(x) for x in r) + " |" for r in rows]])


def _ci(s: dict[str, Any], grouping: str = "parent", stat: str = "mean") -> str:
    c = s.get("ci95", {}).get(grouping, {}).get(stat)
    return "n/a" if not c or c["lo"] is None else f"[{c['lo']:+.4f}, {c['hi']:+.4f}]"


def _fmt(s: dict[str, Any]) -> str:
    return "n/a" if s.get("mean_diff") is None else f"{s['mean_diff']:+.4f}"


def render_markdown(r: dict[str, Any]) -> str:
    cov, st, pv = r["coverage"], r["stages"], r["paired"]
    A, B = "A_baseline", "B3_proposal_plus_repair"
    L = ["# CAGO - Final held-out TEST evaluation: Generator A vs Generator B3", "", LANG, "",
         f"Frozen manifest digest: `{r['manifest']['digest']}` (verification ok = {r['manifest']['verification_ok']}; evaluation split = {r['manifest']['evaluation_split']}). "
         f"Determinism re-run identical: {r['determinism']['all_identical']} ({r['determinism']['checks']} checks).", "",
         "## 1. Integrity", "", "```json\n" + json.dumps(r["integrity"], indent=1, default=str) + "\n```", "",
         "## 2. Request coverage", "",
         f"Requests {cov['n_requests']} (run {r['conditions']['requests_run']}, invalid {len(r['invalid_requests'])}); cells {cov['cells']}; categories {cov['categories']}; "
         f"segments {cov['segments']}; types {cov['types']}; distinct held-out parents in derived requests {cov['distinct_held_out_parents_in_derived_requests']} "
         f"({cov['derived_requests']} derived requests; parents with >1 request {cov['parents_with_more_than_one_request']}; parent reuse across types {cov['requests_with_parent_reuse_across_types']}).", "",
         "Evaluation-split eligibility (nothing silently dropped): `" + json.dumps(cov["evaluation_split_eligibility"]) + "`", "",
         "## 3. Comparison conditions", "", "```json\n" + json.dumps(r["conditions"], indent=1) + "\n```", "", r["costs"]["fairness_statement"], "",
         "## 4. Generation coverage", "",
         _t([[n, v["candidates_requested"], v["candidates_generated"], v["generated_over_requested"], v["unique_candidates"], v["unique_candidate_rate"], v["hard_valid_rate"],
              v["requests_without_any_candidate"], json.dumps(v["selection_availability"]), v["front_size"]["median"], v["front_size_is_one_share"]] for n, v in r["generation_coverage"].items()],
             ["variant", "requested", "generated", "gen/req", "unique", "unique rate", "hard-valid rate", "requests w/o candidate", "selection availability (D/E/F)", "front median", "front==1"]), "",
         "## 5. Stage results (pooled rows; descriptive)", ""]
    ref = st["A_templates_reference"]
    L += [f"Stage A, original selected TRAIN templates: rows {ref['n_rows']}, violation mean {ref['violation_count']['pooled']['mean']}, zero-violation {ref['zero_violation_rate_pooled']}, "
          f"SR rates {json.dumps(ref['sr_rates'])}, intent median {ref['intent_0_100']['median']}, plausibility median {ref['plausibility_0_100']['median']}.", ""]
    for stage in STAGE_KEYS:
        L += [f"### {stage}", "", _t([[n, st[n][stage].get("n_rows"), st[n][stage]["violation_count"]["pooled"]["mean"] if st[n][stage].get("n_rows") else None,
                                       st[n][stage].get("zero_violation_rate_pooled"), json.dumps(st[n][stage].get("sr_rates")), st[n][stage].get("intent_0_100", {}).get("median"),
                                       st[n][stage].get("intent_0_100", {}).get("mean"), st[n][stage].get("plausibility_0_100", {}).get("median"),
                                       st[n][stage].get("plausibility_0_100", {}).get("mean"), st[n][stage].get("template_distance", {}).get("diagnostic_distance", {}).get("mean")]
                                      for n in (A, B)], ["variant", "rows", "viol mean", "zero-viol", "SR1-SR5", "intent med", "intent mean", "plaus med", "plaus mean", "mean dist"]), ""]
    L += ["## 6. Pre-specified primary outcomes (B3 - A; paired by request; 95% bootstrap CI)", "",
          _t([[f"{o['stage']} : {o['metric']}", o["summary"]["n_paired"], o["summary"]["only_baseline_available"], o["summary"]["only_variant_available"], o["summary"]["neither_available"],
               o["summary"].get("mean_baseline"), o["summary"].get("mean_variant"), _fmt(o["summary"]), _ci(o["summary"], "parent", "mean"), _ci(o["summary"], "cell", "mean"),
               _ci(o["summary"], "request", "mean"), o["summary"].get("median_diff"), _ci(o["summary"], "parent", "median"),
               f"{o['summary'].get('variant_lower')}/{o['summary'].get('equal')}/{o['summary'].get('variant_higher')}"] for o in r["primary_outcomes"]],
             ["outcome", "paired n", "only A", "only B3", "neither", "mean A", "mean B3", "mean diff", "CI parent-clustered", "CI cell-clustered", "CI request-level", "median diff", "median CI (parent)", "B3 lower/equal/higher"]), "",
          "Lower violation_count is better; higher Intent / Plausibility is better. Primary CI = parent-clustered.", "", "## 7. All paired differences (exploratory)", ""]
    for stage in STAGE_KEYS:
        L += [f"### {stage}", "", _t([[m, s["n_paired"], _fmt(s), s.get("median_diff"), _ci(s, "parent", "mean"), _ci(s, "cell", "mean"), f"{s.get('variant_lower')}/{s.get('equal')}/{s.get('variant_higher')}"]
                                      for m, s in pv[stage].items()], ["metric", "paired n", "mean diff", "median diff", "CI parent", "CI cell", "B3 lower/equal/higher"]), ""]
    L += ["## 8. Breakdowns (primary metrics; CI only when n >= 10)", ""]
    for g, title in (("by_segment", "segment"), ("by_request_type", "request type"), ("by_template_pool_bin", "eligible TRAIN template pool")):
        L += [f"### by {title}", "", _t([[k, c["n_requests"], *(f"{_fmt(c[f'{s}:{m}'])} {_ci(c[f'{s}:{m}'])}" for s, m in PRIMARY)] for k, c in r["breakdowns"][g].items()],
                                       ["group", "n", *[f"{s[:1]}:{m}" for s, m in PRIMARY]]), ""]
    L += ["### by category", "", _t([[k, c["n_requests"], *(_fmt(c[f"{s}:{m}"]) for s, m in PRIMARY)] for k, c in r["breakdowns"]["by_category"].items()],
                                  ["category", "n", *[f"{s[:1]}:{m}" for s, m in PRIMARY]]), "", "## 9. Small template pools", "",
          _t([[b, c["n_requests"], c["flag"] or "", *(f"{v['generated_over_requested']} / {v['no_candidates_rate']} / {v['valid_pool_mean_violation']} / {v['sorting_focused_mean_violation']}"
                                                         for v in (c["variants"][A], c["variants"][B]))] for b, c in r["small_pool"].items() if c["n_requests"]],
             ["pool bin", "requests", "flag", "A: gen/req / no-cand / pool viol / sorting viol", "B3: same"]), "", "## 10. Trade-offs vs own template", "",
          "```json\n" + json.dumps({n: {s: {k: v for k, v in c.items() if k != "n_rows"} for s, c in r["trade_offs"][n].items() if s in ('B_hard_valid_candidates', 'D_balanced', 'E_sorting_focused')} for n in (A, B)}, indent=0) + "\n```", "",
          "## 11. Computation and runtime", "", "```json\n" + json.dumps(r["costs"], indent=1) + "\n```", "", "## 12. Failure analysis (observed)", "",
          "```json\n" + json.dumps({k: v for k, v in r["failure_analysis"].items() if k != "repair_side_effects"}, indent=1, default=str) + "\n```", "",
          "Repair side effects: `" + json.dumps(r["failure_analysis"]["repair_side_effects"], default=str) + "`", "",
          "## 13. Reproducible examples", "", "```json\n" + json.dumps(r["examples"], indent=1, default=str)[:15000] + "\n```", "", "## 14. Limitations", ""]
    L += [f"- {x}" for x in r["limitations"]] + [""]
    return "\n".join(L)
