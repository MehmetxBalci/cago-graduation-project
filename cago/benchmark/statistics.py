"""Small, deterministic statistics helpers (medians, bootstrap CIs, paired differences, rank correlation)."""
from __future__ import annotations

import math
import random
from statistics import mean, median, pstdev
from typing import Callable, Sequence


def percentile(values: Sequence[float], p: float) -> float:
    """Linear-interpolation percentile, p in [0, 100]."""
    s = sorted(values)
    if not s:
        raise ValueError("empty sample")
    k = (len(s) - 1) * p / 100.0
    lo, hi = math.floor(k), math.ceil(k)
    return float(s[lo] if lo == hi else s[lo] + (s[hi] - s[lo]) * (k - lo))


def describe(values: Sequence[float], digits: int = 4) -> dict[str, float | int | None]:
    v = [float(x) for x in values]
    if not v:
        return {"n": 0, "mean": None, "median": None, "std": None, "min": None, "p25": None, "p75": None, "max": None}
    r = lambda x: round(x, digits)
    return {"n": len(v), "mean": r(mean(v)), "median": r(median(v)), "std": r(pstdev(v)), "min": r(min(v)),
            "p25": r(percentile(v, 25)), "p75": r(percentile(v, 75)), "max": r(max(v))}


STATS: dict[str, Callable[[Sequence[float]], float]] = {"median": median, "mean": mean}


def bootstrap_ci(values: Sequence[float], stat: str = "median", n_resamples: int = 1000, seed: int = 0,
                 level: float = 0.95, digits: int = 4) -> dict[str, float | int | None]:
    """Percentile bootstrap CI of a statistic of one sample. Deterministic for a given seed."""
    v = [float(x) for x in values]
    if not v:
        return {"n": 0, "point": None, "lo": None, "hi": None, "level": level, "n_resamples": n_resamples}
    f = STATS[stat]
    rng = random.Random(seed)
    n = len(v)
    boots = sorted(f([v[rng.randrange(n)] for _ in range(n)]) for _ in range(n_resamples))
    a = (1 - level) / 2
    lo, hi = boots[int(a * (n_resamples - 1))], boots[int(math.ceil((1 - a) * (n_resamples - 1)))]
    return {"n": n, "point": round(f(v), digits), "lo": round(lo, digits), "hi": round(hi, digits), "level": level,
            "n_resamples": n_resamples, "stat": stat}


def paired_differences(a: Sequence[float], b: Sequence[float]) -> list[float]:
    """Element-wise a - b for paired samples (same length)."""
    if len(a) != len(b):
        raise ValueError("paired samples must have equal length")
    return [float(x) - float(y) for x, y in zip(a, b)]


def bootstrap_paired_ci(a: Sequence[float], b: Sequence[float], stat: str = "median", n_resamples: int = 1000,
                        seed: int = 0, level: float = 0.95) -> dict[str, float | int | None]:
    """Bootstrap CI of the paired difference (a - b)."""
    return bootstrap_ci(paired_differences(a, b), stat, n_resamples, seed, level)


def cluster_bootstrap_ci(cluster_values: Sequence[Sequence[float]], stat: str = "median", n_resamples: int = 1000,
                         seed: int = 0, level: float = 0.95) -> dict[str, float | int | None]:
    """CI for the median/mean of per-cluster medians (clusters = e.g. benchmark requests); resamples clusters."""
    reps = [median(c) for c in cluster_values if len(c)]
    return bootstrap_ci(reps, stat, n_resamples, seed, level)


def ordering_accuracy(higher: Sequence[float], lower: Sequence[float], tol: float = 1e-9) -> dict[str, float | int | None]:
    """For paired samples: share with higher >= lower (non-strict), share with higher > lower (strict), tie share."""
    n = len(higher)
    if n != len(lower):
        raise ValueError("paired samples must have equal length")
    if n == 0:
        return {"n": 0, "accuracy_non_strict": None, "accuracy_strict": None, "tie_share": None}
    ge = sum(h >= l - tol for h, l in zip(higher, lower))
    gt = sum(h > l + tol for h, l in zip(higher, lower))
    tie = sum(abs(h - l) <= tol for h, l in zip(higher, lower))
    return {"n": n, "accuracy_non_strict": round(ge / n, 4), "accuracy_strict": round(gt / n, 4), "tie_share": round(tie / n, 4)}


def _ranks(x: Sequence[float]) -> list[float]:
    order = sorted(range(len(x)), key=lambda i: x[i])
    ranks = [0.0] * len(x)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and x[order[j + 1]] == x[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return ranks


def spearman(x: Sequence[float], y: Sequence[float]) -> float | None:
    """Spearman rank correlation (average ranks for ties); None if undefined."""
    if len(x) != len(y) or len(x) < 2:
        return None
    rx, ry = _ranks(x), _ranks(y)
    mx, my = mean(rx), mean(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx, vy = sum((a - mx) ** 2 for a in rx), sum((b - my) ** 2 for b in ry)
    return None if vx == 0 or vy == 0 else round(cov / math.sqrt(vx * vy), 6)
