"""Controlled-perturbation validation of the Dataset-relative Plausibility metric (measurement only: no thresholds are
fitted, monotonicity is never forced). Support statistics are TRAIN-only; TEST garments are evaluation examples."""
from __future__ import annotations

from typing import Any, Iterable, Sequence

from cago.benchmark.perturbations import LEVELS, EvalGarment, PerturbationConfig, perturb_garment
from cago.benchmark.statistics import bootstrap_ci, bootstrap_paired_ci, describe, ordering_accuracy, paired_differences, spearman
from cago.evaluation.config import EvaluationConfig
from cago.evaluation.plausibility import evaluate_plausibility
from cago.generation.support_tables import SupportTables
from cago.requirements.validation import RequirementContext

WEIGHTINGS = ((0.25, 0.75), (0.50, 0.50), (0.75, 0.25))          # (context, proximity)
HYPOTHESES = (("L0>=L1", "L0", "L1", False), ("L1>=L2", "L1", "L2", False), ("L0>=L2", "L0", "L2", False),
              ("L0>L4 (unsupported context scores lower)", "L0", "L4", True),
              ("L0>=L3 (descriptive)", "L0", "L3", False), ("L3>=L4 (descriptive)", "L3", "L4", False))


def _cfg(w: tuple[float, float]) -> EvaluationConfig:
    return EvaluationConfig(w_context=w[0], w_proximity=w[1])


def score_levels(garments: Sequence[EvalGarment], support: SupportTables, vocab_materials: Iterable[str],
                 ctx: RequirementContext, seed: int = 0, weightings=WEIGHTINGS,
                 pcfg: PerturbationConfig = PerturbationConfig()) -> list[dict[str, Any]]:
    """One row per (garment, level) with plausibility under every weighting + sub-scores + component-level evidence."""
    vocab = list(vocab_materials)
    rows = []
    for g in garments:
        base_ctx = None
        for lv, p in perturb_garment(g, support, vocab, ctx, seed, pcfg).items():
            by_w = {}
            for w in weightings:
                r = evaluate_plausibility(p["components"], g.detail_category, p["distance"], support, _cfg(w))
                by_w[f"{w[0]:.2f}/{w[1]:.2f}"] = r["plausibility_raw"]
            comps = r["contextual_support"]["components"]            # sub-scores do not depend on the weights
            base_ctx = comps if lv == "L0" else base_ctx
            changed = [] if lv in ("L0", "L1", "L2") else [p["info"]["component_index"]]
            # diagnostic (NOT part of the metric): does any slot exceed the largest TRAIN percentage for its material?
            out_range = any(support.pct_max(g.detail_category, c["component_class"], m["material"]) is not None
                            and m["pct"] > support.pct_max(g.detail_category, c["component_class"], m["material"]) + 1e-9
                            for c in p["components"] for m in c["materials"])
            rows.append({"garment_id": g.garment_id, "category": g.detail_category, "level": lv, "scores": by_w,
                         "contextual": r["contextual_support"]["score"], "proximity": r["template_proximity"]["score"],
                         "n_sub": p["distance"]["n_substitutions"], "abs_pct": p["distance"]["abs_pct_change_total"],
                         "hard_valid": p["hard_valid"], "pct_out_of_train_range": out_range,
                         "changed_component": None if not changed else {
                             "before_count": base_ctx[changed[0]]["support_count"], "after_count": comps[changed[0]]["support_count"],
                             "before_score": base_ctx[changed[0]]["score"], "after_score": comps[changed[0]]["score"],
                             "info": p["info"]}})
    return rows


def _by_level(rows, key) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {lv: {} for lv in LEVELS}
    for r in rows:
        out[r["level"]][r["garment_id"]] = key(r)
    return out


def _paired(lv: dict[str, dict[str, float]], hi: str, lo: str) -> tuple[list[float], list[float]]:
    ids = sorted(set(lv[hi]) & set(lv[lo]))
    return [lv[hi][i] for i in ids], [lv[lo][i] for i in ids]


def ordering_tests(rows, weight_key: str, n_boot: int, seed: int) -> dict[str, Any]:
    lv = _by_level(rows, lambda r: r["scores"][weight_key])
    out = {}
    for name, hi, lo, strict in HYPOTHESES:
        a, b = _paired(lv, hi, lo)
        acc = ordering_accuracy(a, b)
        out[name] = {**acc, "expected": "strictly higher" if strict else "higher or equal",
                     "expected_relation_share": acc["accuracy_strict"] if strict else acc["accuracy_non_strict"],
                     "median_paired_diff_x100": None if not a else round(100 * bootstrap_paired_ci(a, b, "median", n_boot, seed)["point"], 3),
                     "ci95_x100": None if not a else [round(100 * v, 3) for v in
                                                      (lambda c: (c["lo"], c["hi"]))(bootstrap_paired_ci(a, b, "median", n_boot, seed))],
                     "mean_paired_diff_x100": None if not a else round(100 * sum(paired_differences(a, b)) / len(a), 3)}
    ids = [i for i in lv["L0"] if all(i in lv[l] for l in ("L1", "L2"))]
    chain = [lv["L0"][i] >= lv["L1"][i] - 1e-9 and lv["L1"][i] >= lv["L2"][i] - 1e-9 for i in ids]
    ids4 = [i for i in lv["L0"] if i in lv["L4"]]
    out["chain L0>=L1>=L2 (per garment)"] = {"n": len(ids), "share": round(sum(chain) / len(chain), 4) if chain else None}
    out["L4<L0 (per garment)"] = {"n": len(ids4), "share": round(sum(lv["L4"][i] < lv["L0"][i] - 1e-9 for i in ids4) / len(ids4), 4) if ids4 else None}
    full = [i for i in ids if i in lv["L4"]]
    out["all expected (L0>=L1>=L2 and L4<L0)"] = {"n": len(full), "share": round(sum(
        lv["L0"][i] >= lv["L1"][i] - 1e-9 and lv["L1"][i] >= lv["L2"][i] - 1e-9 and lv["L4"][i] < lv["L0"][i] - 1e-9 for i in full) / len(full), 4) if full else None}
    return out


def distributions(rows, weight_key: str) -> dict[str, Any]:
    out = {}
    for lv in LEVELS:
        sel = [r for r in rows if r["level"] == lv]
        out[lv] = {"plausibility_0_100": describe([100 * r["scores"][weight_key] for r in sel], 2),
                   "contextual_support_0_1": describe([r["contextual"] for r in sel], 4),
                   "template_proximity_0_1": describe([r["proximity"] for r in sel], 4),
                   "distance": {"mean_n_substitutions": round(sum(r["n_sub"] for r in sel) / len(sel), 3) if sel else None,
                                "mean_abs_pct_change": round(sum(r["abs_pct"] for r in sel) / len(sel), 3) if sel else None},
                   "hard_valid_rate": round(sum(r["hard_valid"] for r in sel) / len(sel), 4) if sel else None,
                   "pct_out_of_train_range_rate_diagnostic": round(sum(r["pct_out_of_train_range"] for r in sel) / len(sel), 4) if sel else None}
    return out


def component_level_changes(rows) -> dict[str, Any]:
    out = {}
    for lv in ("L3", "L4"):
        ch = [r["changed_component"] for r in rows if r["level"] == lv and r["changed_component"]]
        if not ch:
            out[lv] = {"n": 0}
            continue
        d = [c["after_score"] - c["before_score"] for c in ch]
        out[lv] = {"n": len(ch), "mean_support_count_before": round(sum(c["before_count"] for c in ch) / len(ch), 2),
                   "mean_support_count_after": round(sum(c["after_count"] for c in ch) / len(ch), 2),
                   "share_support_decreased": round(sum(c["after_count"] < c["before_count"] for c in ch) / len(ch), 4),
                   "share_after_zero_support": round(sum(c["after_count"] == 0 for c in ch) / len(ch), 4),
                   "component_score_change": describe(d, 4)}
    z = [r for r in rows if r["level"] == "L4" and r["changed_component"]]
    out["L4_zero_support_substitution_share"] = round(sum(r["changed_component"]["info"].get("zero_support", False) for r in z) / len(z), 4) if z else None
    return out


def paired_contextual_change(rows) -> dict[str, Any]:
    """Is the contextual-support term itself sensitive to the perturbation? (paired against the garment's L0.)"""
    lv = _by_level(rows, lambda r: r["contextual"])
    out = {}
    for name in ("L1", "L2", "L3", "L4"):
        ids = sorted(set(lv["L0"]) & set(lv[name]))
        diffs = [lv[name][i] - lv["L0"][i] for i in ids]
        out[name] = {"n": len(ids), "share_unchanged": round(sum(abs(d) < 1e-9 for d in diffs) / len(diffs), 4) if diffs else None,
                     "max_abs_change": round(max((abs(d) for d in diffs), default=0.0), 4)}
    return out


def weight_sensitivity(rows, n_boot: int, seed: int) -> dict[str, Any]:
    keys = [f"{w[0]:.2f}/{w[1]:.2f}" for w in WEIGHTINGS]
    out: dict[str, Any] = {"weightings_context_over_proximity": keys, "default": "0.50/0.50", "per_weighting": {}}
    pooled = {k: [r["scores"][k] for r in rows] for k in keys}
    for k in keys:
        ot = ordering_tests(rows, k, n_boot, seed)
        out["per_weighting"][k] = {
            "ordering": {h: ot[h]["expected_relation_share"] for h in ot if "expected_relation_share" in ot[h]} | {
                h: ot[h]["share"] for h in ot if "share" in ot[h]},
            "score_spread": {lv: {"std": describe([100 * r["scores"][k] for r in rows if r["level"] == lv], 3)["std"],
                                  "iqr": (lambda d: None if d["p75"] is None else round(d["p75"] - d["p25"], 3))(
                                      describe([100 * r["scores"][k] for r in rows if r["level"] == lv], 3))} for lv in LEVELS},
            "median_by_level_x100": {lv: describe([100 * r["scores"][k] for r in rows if r["level"] == lv], 2)["median"] for lv in LEVELS}}
    out["ranking_spearman_pooled_items"] = {f"{a} vs {b}": spearman(pooled[a], pooled[b])
                                            for i, a in enumerate(keys) for b in keys[i + 1:]}
    return out


def run_plausibility_validation(garments, support, vocab_materials, ctx, seed=0, n_boot=1000, weightings=WEIGHTINGS,
                                pcfg=PerturbationConfig()) -> dict[str, Any]:
    rows = score_levels(garments, support, vocab_materials, ctx, seed, weightings, pcfg)
    d = "0.50/0.50"
    return {"n_test_garments": len(garments), "n_rows": len(rows), "support_splits_used": list(support.splits_used),
            "default_weighting": d, "levels_available": {lv: sum(r["level"] == lv for r in rows) for lv in LEVELS},
            "distributions_default_weighting": distributions(rows, d),
            "ordering_default_weighting": ordering_tests(rows, d, n_boot, seed),
            "component_level_contextual_changes": component_level_changes(rows),
            "paired_contextual_change_vs_L0": paired_contextual_change(rows),
            "weight_sensitivity": weight_sensitivity(rows, n_boot, seed)}, rows
