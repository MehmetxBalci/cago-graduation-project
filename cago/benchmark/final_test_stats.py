"""Statistics for the final evaluation: request-level paired differences with request-, parent- and cell-clustered bootstrap."""
from __future__ import annotations

import math
import random
from statistics import mean, median
from typing import Any, Sequence

STATS = {"mean": mean, "median": median}


def cluster_bootstrap(values: Sequence[float], clusters: Sequence[str], stat: str = "mean", n_resamples: int = 2000,
                      seed: int = 0, level: float = 0.95, digits: int = 5) -> dict[str, Any]:
    """Percentile bootstrap that resamples whole CLUSTERS with replacement (requests of one cluster stay together).
    With singleton clusters this reduces to the ordinary request-level bootstrap. Deterministic for a seed."""
    if len(values) != len(clusters):
        raise ValueError("values and clusters must have equal length")
    groups: dict[str, list[float]] = {}
    for v, c in zip(values, clusters):
        groups.setdefault(c, []).append(float(v))
    keys = sorted(groups)
    if not keys:
        return {"n_requests": 0, "n_clusters": 0, "point": None, "lo": None, "hi": None, "level": level, "stat": stat, "n_resamples": n_resamples}
    f = STATS[stat]
    rng = random.Random(seed)
    k = len(keys)
    boots = []
    for _ in range(n_resamples):
        vals: list[float] = []
        for _ in range(k):
            vals += groups[keys[rng.randrange(k)]]
        boots.append(f(vals))
    boots.sort()
    a = (1 - level) / 2
    lo, hi = boots[int(a * (n_resamples - 1))], boots[int(math.ceil((1 - a) * (n_resamples - 1)))]
    allv = [v for g in groups.values() for v in g]
    return {"n_requests": len(allv), "n_clusters": k, "point": round(f(allv), digits), "lo": round(lo, digits), "hi": round(hi, digits),
            "level": level, "stat": stat, "n_resamples": n_resamples}


def paired_summary(a: dict[str, float | None], b: dict[str, float | None], universe: Sequence[str], clusters: dict[str, dict[str, str]],
                   n_boot: int = 2000, seed: int = 0, with_ci: bool = True, tol: float = 1e-9) -> dict[str, Any]:
    """Paired difference (b - a) over requests with BOTH values available; unavailable results are counted, never imputed.

    a, b: request_id -> value (None / missing = unavailable). universe: all requests that were run.
    """
    av = {i: v for i, v in a.items() if v is not None}
    bv = {i: v for i, v in b.items() if v is not None}
    both = sorted(set(av) & set(bv))
    diffs = [bv[i] - av[i] for i in both]
    out: dict[str, Any] = {"n_requests_total": len(universe), "n_paired": len(both), "only_baseline_available": len(set(av) - set(bv)),
                           "only_variant_available": len(set(bv) - set(av)), "neither_available": len(set(universe) - set(av) - set(bv))}
    if not diffs:
        return {**out, "mean_diff": None, "median_diff": None}
    out.update({"mean_baseline": round(mean(av[i] for i in both), 5), "mean_variant": round(mean(bv[i] for i in both), 5),
                "mean_diff": round(mean(diffs), 5), "median_diff": round(median(diffs), 5),
                "variant_lower": sum(d < -tol for d in diffs), "equal": sum(abs(d) <= tol for d in diffs), "variant_higher": sum(d > tol for d in diffs)})
    if with_ci:
        ci = {}
        for grouping in ("request", "parent", "cell"):
            cl = [(f"r:{i}" if grouping == "request" else clusters[i][grouping]) for i in both]
            ci[grouping] = {st: cluster_bootstrap(diffs, cl, st, n_boot, seed) for st in ("mean", "median")}
        out["ci95"] = ci
    return out
