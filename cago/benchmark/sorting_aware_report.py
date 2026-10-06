"""Markdown renderer for the VAL development comparison."""
from __future__ import annotations

import json
from typing import Any

LANG = ("Development comparison on VAL requests (TRAIN support only; TEST never used). Terminology: Sorting Compatibility (SR1-SR5 rule "
        "satisfaction), Intent Alignment, Dataset-relative Plausibility, constraint-based probabilistic generation with sorting-aware "
        "proposal/repair. Not a recyclability, sustainability or manufacturability measure; descriptive, no causal claim.")


def _t(rows, hdr) -> str:
    return "\n".join(["| " + " | ".join(hdr) + " |", "|" + "|".join("---" for _ in hdr) + "|", *["| " + " | ".join(str(x) for x in r) + " |" for r in rows]])


def _ci(p: dict, key="median_ci95") -> str:
    if not p.get("n_requests"):
        return "n/a"
    c = p[key]
    return f"{p['mean_diff']:+.3f} (median {c['point']:+.3f} [{c['lo']:+.3f}, {c['hi']:+.3f}], n={p['n_requests']})"


def render_comparison_md(o: dict[str, Any]) -> str:
    c, pv = o["coverage"], o["per_variant"]
    L = ["# CAGO sorting-aware generator - VAL development comparison", "", LANG, "",
         f"Requests {c['n_requests']} (invalid {len(c['invalid_requests'])}); cells {c['cells']}; categories {c['categories']}; segments {c['segments']}; types {c['types']}.", "",
         f"Fairness: identical template pool/selection across variants = {o['fairness']['identical_template_pool_and_selection_across_variants']}; "
         f"requested candidates {o['fairness']['candidates_requested_per_variant']}. {o['fairness']['mutation_attempt_budget_per_candidate']}. "
         f"Determinism re-run: {o['determinism']}.", "", "## Search / budget", "",
         _t([[n, v["search"]["candidates_generated"], v["search"]["generated_over_requested"], v["search"]["mutation_attempts"], v["search"]["unique_candidate_rate_mean"],
              v["search"]["oracle_full_evals"], v["search"]["fast_rule_evals"], v["search"]["repair_proposals_evaluated"], v["search"]["repair_acceptance_rate"],
              v["search"]["mean_seconds_per_request_informational"]] for n, v in pv.items()],
             ["variant", "generated", "gen/requested", "mutation attempts", "unique rate", "oracle full evals", "fast rule evals", "repair proposals", "repair acceptance", "sec/request (info)"]), "",
         "## Stage comparison (pooled rows)", ""]
    for stage in ("B_hard_valid_candidates", "C_pareto_front", "D_balanced", "E_sorting_focused", "F_intent_focused"):
        L += [f"### {stage}", "", _t([[n, v["stages"][stage].get("n_rows"), v["stages"][stage].get("violation_count", {}).get("pooled", {}).get("mean"),
                                       v["stages"][stage].get("zero_violation_rate_pooled"), json.dumps(v["stages"][stage].get("sr_rates")),
                                       v["stages"][stage].get("intent_0_100", {}).get("median"), v["stages"][stage].get("plausibility_0_100", {}).get("median"),
                                       v["stages"][stage].get("template_distance", {}).get("diagnostic_distance", {}).get("mean")] for n, v in pv.items() if v["stages"][stage].get("n_rows")],
                                     ["variant", "rows", "viol mean", "zero-viol", "SR1-SR5 rates", "intent median", "plaus median", "mean dist"]), ""]
    L += ["## Paired differences vs baseline (variant - A; request means; median CI over requests)", ""]
    for stage in ("B_hard_valid_candidates", "C_pareto_front", "E_sorting_focused", "D_balanced", "F_intent_focused"):
        L += [f"### {stage}", "", _t([[n, *(_ci(p[stage][m]) for m in ("violation_count", "zero_violation", "intent_0_1", "plausibility_0_1", "template_distance"))]
                                      for n, p in o["paired_vs_baseline"].items()], ["variant", "violation_count", "zero-violation share", "intent (0-1)", "plausibility (0-1)", "template distance"]), ""]
    L += ["## SR-specific effects: hard-valid pool rate differences (variant - A)", "",
          _t([[n, *(_ci(p["B_hard_valid_candidates"][f"{s}_rate"]) for s in ("SR1", "SR2", "SR3", "SR4", "SR5"))] for n, p in o["paired_vs_baseline"].items()],
             ["variant", "SR1", "SR2", "SR3", "SR4", "SR5"]), "",
          "Sorting-focused selection:", "", _t([[n, *(_ci(p["E_sorting_focused"][f"{s}_rate"]) for s in ("SR1", "SR2", "SR3", "SR4", "SR5"))] for n, p in o["paired_vs_baseline"].items()],
                                              ["variant", "SR1", "SR2", "SR3", "SR4", "SR5"]), "", "## Pareto / selection", "",
          _t([[n, v["pareto"]["front_size"]["median"], v["pareto"]["front_size_is_one_rate"], v["pareto"]["front_violation_levels_mean"], v["pareto"]["front_intent_range_mean"],
               v["pareto"]["front_plausibility_range_mean"], v["pareto"]["selection_role_duplicate_rate"], json.dumps(v["requests_without_zero_violation_candidate"])] for n, v in pv.items()],
             ["variant", "front median", "front==1", "front violation levels", "front intent range", "front plaus range", "role-duplicate rate", "no zero-viol candidate"]), "",
          "## Failure analysis and unresolved violations", ""]
    for n, v in pv.items():
        L += [f"**{n}** unresolved: {json.dumps(v['unresolved_after_generation'])}; failure counters: {json.dumps(v['failure_analysis'])}; rejected: {json.dumps(v['search']['rejected'])}", ""]
    L += ["## Small-pool stratification", ""]
    for b, cell in o["small_pool"].items():
        L += [f"### pool {b}: {cell['n_requests']} requests {cell['flag'] or ''}", ""]
        if cell["n_requests"]:
            L += [_t([[n, *(v[k] for k in ("generated_over_requested", "no_candidates_rate", "valid_pool_mean_violation", "valid_pool_zero_violation_rate", "sorting_focused_mean_violation",
                                           "balanced_mean_intent_0_100", "balanced_mean_plausibility_0_100", "unique_candidate_rate_mean", "front_size_is_one_rate", "repair_acceptance_rate",
                                           "no_train_supported_alternative", "unresolved_repairable_rate"))] for n, v in cell["variants"].items()],
                     ["variant", "gen/req", "no-cand", "valid viol", "valid zero", "sorting viol", "balanced intent", "balanced plaus", "unique", "front==1", "repair acc", "no alt", "unresolved"]), "",
                  "paired valid-pool violation vs A: " + json.dumps({n: _ci(p) for n, p in cell["paired_valid_pool_violation_vs_A"].items()}), ""]
    return "\n".join(L)
