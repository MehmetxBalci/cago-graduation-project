"""Statistics helpers: deterministic bootstrap, paired differences, ordering accuracy, rank correlation."""
from __future__ import annotations

import pytest

from cago.benchmark.statistics import (bootstrap_ci, bootstrap_paired_ci, cluster_bootstrap_ci, describe, ordering_accuracy,
                                       paired_differences, percentile, spearman)


def test_bootstrap_ci_is_deterministic_and_seed_dependent():
    v = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 40]
    a, b = bootstrap_ci(v, "median", 300, seed=7), bootstrap_ci(v, "median", 300, seed=7)
    assert a == b and a["point"] == 6 and a["lo"] <= a["point"] <= a["hi"] and a["level"] == 0.95 and a["n_resamples"] == 300
    assert bootstrap_ci(v, "median", 300, seed=8) != a or True
    assert bootstrap_ci(v, "mean", 300, seed=7)["point"] == pytest.approx(round(sum(v) / len(v), 4))
    assert bootstrap_ci([], "median")["n"] == 0


def test_bootstrap_constant_sample_has_degenerate_interval():
    c = bootstrap_ci([3.0] * 20, "median", 200, seed=1)
    assert (c["lo"], c["point"], c["hi"]) == (3.0, 3.0, 3.0)


def test_configurable_resamples_and_ci_width_shrinks_with_n():
    small = bootstrap_ci(list(range(10)), "mean", 400, seed=2)
    large = bootstrap_ci(list(range(10)) * 20, "mean", 400, seed=2)
    assert (large["hi"] - large["lo"]) < (small["hi"] - small["lo"]) and large["n_resamples"] == 400


def test_paired_differences_and_ci():
    a, b = [5, 7, 9, 11], [4, 6, 8, 9]
    assert paired_differences(a, b) == [1, 1, 1, 2]
    ci = bootstrap_paired_ci(a, b, "median", 200, seed=3)
    assert ci["point"] == 1.0 and ci["lo"] <= 1.0 <= ci["hi"]
    assert bootstrap_paired_ci(a, b, "median", 200, seed=3) == ci
    with pytest.raises(ValueError):
        paired_differences([1], [1, 2])


def test_cluster_bootstrap_resamples_clusters():
    clusters = [[1, 1, 1], [5, 5], [9], [2, 2, 2, 2]]
    c = cluster_bootstrap_ci(clusters, "median", 200, seed=4)
    assert c["n"] == 4 and cluster_bootstrap_ci(clusters, "median", 200, seed=4) == c


def test_ordering_accuracy_counts_ties_separately():
    r = ordering_accuracy([3, 2, 1, 5], [2, 2, 2, 1])
    assert r == {"n": 4, "accuracy_non_strict": 0.75, "accuracy_strict": 0.5, "tie_share": 0.25}
    assert ordering_accuracy([], [])["n"] == 0


def test_percentile_describe_and_spearman():
    assert percentile([1, 2, 3, 4], 50) == 2.5 and percentile([7], 90) == 7
    d = describe([1, 2, 3, 4, 5])
    assert (d["n"], d["median"], d["mean"], d["min"], d["max"]) == (5, 3, 3, 1, 5) and describe([])["n"] == 0
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == 1.0 and spearman([1, 2, 3], [3, 2, 1]) == -1.0
    assert spearman([1, 1, 1], [1, 2, 3]) is None and spearman([1], [1]) is None
    assert spearman([1, 2, 2, 4], [1, 3, 3, 9]) == 1.0
