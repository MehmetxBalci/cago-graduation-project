"""Markdown renderers + data-driven 'questionable behaviour' flags for the validation / benchmark reports."""
from __future__ import annotations

import json
from typing import Any

LANG = ("Terminology: Dataset-relative Plausibility (similarity/support relative to the TRAIN distribution; not a statement about "
        "production), Intent Alignment (preference-alignment index; not measured performance), SR1-SR5 Sorting Compatibility "
        "(equal-weight rule-satisfaction; not a recyclability or sustainability figure).")


def _t(rows, hdr) -> str:
    return "\n".join(["| " + " | ".join(hdr) + " |", "|" + "|".join("---" for _ in hdr) + "|",
                      *["| " + " | ".join(str(x) for x in r) + " |" for r in rows]])


def questionable_flags(pl: dict[str, Any], it: dict[str, Any]) -> list[str]:
    out = []
    d = pl["distributions_default_weighting"]
    pc = pl["paired_contextual_change_vs_L0"]
    if pc["L1"]["share_unchanged"] == 1.0 and pc["L2"]["share_unchanged"] == 1.0:
        out.append("Contextual support is combination-based, so L1/L2 percentage perturbations leave it exactly unchanged for every garment "
                   "(paired, max change 0): the L0>=L1>=L2 ordering is produced entirely by the template-proximity term and holds by construction.")
    r = [d[l]["pct_out_of_train_range_rate_diagnostic"] for l in ("L0", "L1", "L2")]
    out.append(f"Percentages are not part of the contextual term: share of garments with a slot above the TRAIN maximum for its material "
               f"is {r[0]} (L0) / {r[1]} (L1) / {r[2]} (L2) and is not penalised by contextual support.")
    o = pl["ordering_default_weighting"]
    msg = {"L0>=L3 (descriptive)": "a supported substitution can raise contextual support when the original combination is rare in TRAIN",
           "L3>=L4 (descriptive)": "an L3 'supported' substitution can still create a combination unseen in TRAIN, so it can tie with or fall below L4"}
    for name, why in msg.items():
        if o[name]["n"] and o[name]["expected_relation_share"] < 1:
            out.append(f"{name}: expected relation holds for {o[name]['expected_relation_share']:.3f} of pairs ({why}).")
    w = pl["weight_sensitivity"]["per_weighting"]
    out.append("Weighting changes the L0>=L3 ordering share: " + ", ".join(f"{k}: {v['ordering']['L0>=L3 (descriptive)']}" for k, v in w.items())
               + " (more context weight -> more cases where the substituted garment outscores the original).")
    if o["L0>L4 (unsupported context scores lower)"]["expected_relation_share"] < 1:
        out.append("L4 scored >= L0 for some garments.")
    coupled = {}
    for k, v in it["experiments"].items():
        if k.startswith("_"):
            continue
        if v["status"] != "PASS":
            out.append(f"Intent experiment '{k}' FAILED ({v['pass_rate']}): {v['failures']}")
        if v["coupled_functional_changes"]:
            coupled[k] = v["coupled_functional_changes"]
    if coupled:
        out.append("Functional proxies are coupled through shared materials/components (legitimate, but a single manipulation moves several "
                   "requested properties at once); other proxies changed per experiment (counts): " + json.dumps(coupled))
    out.append("Proxies saturate at satisfaction 1 (e.g. water_repellent after two strong evidence items), so further evidence cannot increase "
               "the score; the experiments therefore require headroom (preconditions) before testing a strict direction.")
    out.append("Duplicate material names inside a component are aggregated by the metric (as in the Oracle): a percentage swap between two "
               "slots of the same material does not change dominance; such garments are excluded from the swap experiment.")
    return out


def render_validation_md(a: dict[str, Any]) -> str:
    pl, it = a["plausibility"], a["intent"]
    L = ["# CAGO evaluation validation (controlled perturbations)", "", LANG, "",
         f"TEST garments used as evaluation examples only: {pl['n_test_garments']}. Support splits used: {pl['support_splits_used']}. "
         f"Seed {a['seed']}, bootstrap {a['n_bootstrap']} resamples.", "", "## 1. Plausibility by perturbation level (weighting 0.50/0.50)", ""]
    d = pl["distributions_default_weighting"]
    L += [_t([[lv, d[lv]["plausibility_0_100"]["n"], d[lv]["plausibility_0_100"]["median"], d[lv]["plausibility_0_100"]["mean"],
               d[lv]["contextual_support_0_1"]["median"], d[lv]["template_proximity_0_1"]["median"],
               d[lv]["distance"]["mean_n_substitutions"], d[lv]["distance"]["mean_abs_pct_change"], d[lv]["hard_valid_rate"]] for lv in d],
              ["level", "n", "median", "mean", "ctx median", "prox median", "mean #subst", "mean abs pct", "hard-valid"]), "",
          "### Expected ordering (paired by garment)", "",
          _t([[k, v["n"], v.get("expected_relation_share", v.get("share")), v.get("tie_share", ""), v.get("median_paired_diff_x100", ""), v.get("ci95_x100", "")]
              for k, v in pl["ordering_default_weighting"].items()], ["hypothesis", "n", "share satisfying", "ties", "median diff (pts)", "95% CI"]), "",
          "### Component-level contextual support", "", "```json\n" + json.dumps(pl["component_level_contextual_changes"]) + "\n```", "",
          "## 2. Weight sensitivity (context/proximity)", ""]
    ws = pl["weight_sensitivity"]
    L += [_t([[k, json.dumps(v["ordering"]), json.dumps(v["median_by_level_x100"])] for k, v in ws["per_weighting"].items()],
             ["weighting", "ordering shares", "median by level"]), "",
          "Spread (std / IQR by level): " + json.dumps({k: v["score_spread"] for k, v in ws["per_weighting"].items()}), "",
          "Pooled-item Spearman between weightings: " + json.dumps(ws["ranking_spearman_pooled_items"]), "",
          "## 3-4. Intent Alignment validation + isolation", "", f"Cases: {it['n_cases']}; experiments passing: {it['overall']['experiments_passing']}/{it['overall']['experiments']}; "
          f"case pass rate {it['overall']['case_pass_rate']}.", "",
          _t([[k, v["n_cases"], v["expected"], json.dumps(v["observed_counts"]), v["pass_rate"], v["status"], json.dumps(v["affected_subcomponents"]),
               json.dumps(v["unintended_changes"]), v["isolation_accuracy"]] for k, v in it["experiments"].items() if not k.startswith("_")],
              ["experiment", "n", "expected", "observed", "pass rate", "status", "affected", "unintended", "isolation"]), "",
          "Isolation overall: " + json.dumps(it["experiments"]["_isolation_overall"]), "", "## Questionable / notable metric behaviour", ""]
    L += [f"- {x}" for x in a["questionable_behaviour"]] + [""]
    return "\n".join(L)


def render_benchmark_md(b: dict[str, Any]) -> str:
    c = b["coverage"]
    L = ["# CAGO baseline benchmark (TRAIN-only generation, TEST-derived requests)", "", LANG, "",
         f"Requests {c['n_requests']} (ok {c['n_ok']}, no valid candidates {c['n_no_valid_candidates']}, invalid {c['n_invalid']}); cells {c['cells']}; "
         f"categories {c['categories']}; segments {c['segments']}; types {c['types']}; with soft preferences {c['requests_with_soft_preferences']}; "
         f"with forbidden materials {c['requests_with_forbidden_materials']}. Seed {b['seed']}; bootstrap {b['n_bootstrap']}. Determinism re-run: {b['determinism']}.", "",
         f"Candidates: {b['totals']}.", "", "## Stage comparison (descriptive; pooled rows)", ""]
    st = b["stages"]
    L += [_t([[s, v.get("n_rows"), v.get("n_requests"), v["violation_count"]["pooled"]["mean"], v["violation_count"]["pooled"]["median"],
               v["zero_violation_rate_pooled"], json.dumps(v["sr_rates"]), v["intent_0_100"]["median"], v["plausibility_0_100"]["median"],
               v["template_distance"]["diagnostic_distance"]["mean"]] for s, v in st.items() if v.get("n_rows")],
              ["stage", "rows", "requests", "viol mean", "viol median", "zero-viol rate", "SR1-SR5 rates", "intent median", "plaus median", "mean dist"]), "",
          "### Paired difference to own template (cluster bootstrap over requests; median [95% CI])", "",
          _t([[s, *(f"{v['paired_vs_own_template'][k]['point']} [{v['paired_vs_own_template'][k]['lo']}, {v['paired_vs_own_template'][k]['hi']}]"
                    if v.get("paired_vs_own_template", {}).get(k, {}).get("n") else "n/a"
                    for k in ("violation_count_minus_template", "intent_points_minus_template", "plausibility_points_minus_template"))]
              for s, v in st.items() if s != "A_templates" and v.get("n_rows")], ["stage", "violations", "intent pts", "plausibility pts"]), "",
          "### Request-level paired violation difference vs templates", "", "```json\n" + json.dumps(b["request_level_paired_violation_vs_templates"]) + "\n```", "",
          "## Trade-off frequencies (candidate vs its own template)", ""]
    t = b["trade_offs"]
    L += [_t([[s, v["n_rows"], *(f"{v[k]['count']}/{v[k]['defined_n']} ({v[k]['rate']})" for k in ("sorting_up_intent_down", "intent_up_sorting_down", "sorting_up_plaus_drop", "all_three_improve"))]
              for s, v in t["per_stage"].items()], ["stage", "rows", "sorting up & intent down", "intent up & sorting down",
                                                    f"sorting up & plaus drop>{t['plausibility_drop_threshold_points']}", "all three improve"]), "",
          f"Requests without a zero-violation Pareto candidate: {t['requests_without_zero_violation_pareto_candidate']}", "", "## Small template pools", "",
          _t([[k, v["n_requests"], v["n_cells"], v["eligible_pool_median"], v["candidates_generated_over_requested"], v["no_candidates_rate"],
               v["front_size_is_one_rate"], v["template_mean_violation"], v["sorting_focused_mean_violation"], v["sorting_focused_zero_violation_rate"],
               v["no_zero_violation_pareto_rate"], v["flag"] or ""] for k, v in b["small_pool"].items()],
              ["pool bin", "requests", "cells", "median pool", "generated/requested", "no-candidate rate", "front==1", "template viol", "sorting viol",
               "sorting zero-viol", "no zero-viol front", "flag"]), "", "## Notes", ""] + [f"- {x}" for x in b["notes"]] + [""]
    return "\n".join(L)
