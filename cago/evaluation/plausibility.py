"""Dataset-relative plausibility (TRAIN distribution only). NOT manufacturability or a guarantee of any kind.

A) contextual support: for each active component, how often its exact material COMBINATION occurs in TRAIN for the
   same (detail_category, component_class):  score = log(1 + n) / log(1 + n_max_in_context)  in [0, 1]
   (n = 0 -> 0, never fabricated). Aggregated over components (mean by default; min configurable).
B) template proximity: proximity = exp(-decay * D),  D = w_sub * n_substitutions + w_pct * abs_pct_change_total / 100.
Plausibility = w_context * A + w_proximity * B  (default 0.5 / 0.5); reported x100 together with raw evidence.
"""
from __future__ import annotations

import math
from typing import Any

from cago.evaluation.config import EvaluationConfig
from cago.generation.support_tables import SupportTables

FORMULA = ("contextual = log(1+n)/log(1+n_max) per component (0 if unseen); proximity = exp(-decay*D), "
           "D = w_sub*n_substitutions + w_pct*abs_pct_change/100; plausibility = w_ctx*contextual + w_prox*proximity")
NOTE = ("dataset-relative support/similarity to the TRAIN distribution; not a guarantee of manufacturability")


def contextual_support(components: list[dict[str, Any]], category: str, support: SupportTables,
                       cfg: EvaluationConfig = EvaluationConfig()) -> dict[str, Any]:
    per = []
    for c in components:
        cls = c["component_class"]
        combo = frozenset(m["material"] for m in c["materials"])
        cell = support.combos_by_category_class.get((category, cls), {})
        n = int(cell.get(combo, 0)) if cell else 0
        n_max = int(max(cell.values())) if cell else 0
        score = math.log1p(n) / math.log1p(n_max) if n > 0 and n_max > 0 else 0.0
        per.append({"component_name": c["component_name_normalized"], "component_class": cls,
                    "materials": sorted(combo), "support_count": n, "context_max_count": n_max,
                    "context_distinct_combinations": len(cell), "score": round(score, 6),
                    "evidence": ("exact combination never observed in TRAIN for this context" if n == 0
                                 else f"observed {n}x in TRAIN (context max {n_max})")})
    scores = [p["score"] for p in per]
    agg = (min(scores) if cfg.context_aggregate == "min" else sum(scores) / len(scores)) if scores else 0.0
    return {"score": round(agg, 6), "aggregate": cfg.context_aggregate, "components": per,
            "n_components_unseen_combination": sum(p["support_count"] == 0 for p in per)}


def template_proximity(distance: dict[str, Any], cfg: EvaluationConfig = EvaluationConfig()) -> dict[str, Any]:
    n_sub, absp = distance["n_substitutions"], distance["abs_pct_change_total"]
    d = cfg.prox_w_sub * n_sub + cfg.prox_w_pct * absp / 100.0
    return {"score": round(math.exp(-cfg.prox_decay * d), 6), "D": round(d, 6), "n_substitutions": n_sub,
            "abs_pct_change_total": absp, "decay": cfg.prox_decay,
            "formula": f"exp(-{cfg.prox_decay} * ({cfg.prox_w_sub}*n_sub + {cfg.prox_w_pct}*abs_pct/100))"}


def evaluate_plausibility(components: list[dict[str, Any]], category: str, distance: dict[str, Any],
                          support: SupportTables, cfg: EvaluationConfig = EvaluationConfig()) -> dict[str, Any]:
    if tuple(support.splits_used) != ("train",):
        raise ValueError("plausibility support must be TRAIN-only")
    ctx = contextual_support(components, category, support, cfg)
    prox = template_proximity(distance, cfg)
    raw = cfg.w_context * ctx["score"] + cfg.w_proximity * prox["score"]
    return {"plausibility_raw": round(raw, 6), "plausibility_0_100": round(100 * raw, 2),
            "contextual_support": ctx, "template_proximity": prox,
            "weights": {"context": cfg.w_context, "proximity": cfg.w_proximity}, "formula": FORMULA, "note": NOTE}
