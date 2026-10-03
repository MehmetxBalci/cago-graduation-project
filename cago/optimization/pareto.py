"""Deterministic non-dominated sorting. All objectives are MINIMISED; no objective is ever collapsed into a weight."""
from __future__ import annotations

from typing import Any, Sequence

DIMENSIONS = ("violation_count", "intent_loss", "plausibility_loss")


def dominates(a: Sequence[float], b: Sequence[float]) -> bool:
    """A dominates B iff A is no worse in every objective and strictly better in at least one."""
    return all(x <= y for x, y in zip(a, b)) and any(x < y for x, y in zip(a, b))


def non_dominated_ranks(points: Sequence[Sequence[float]]) -> list[int]:
    """Rank 0 = non-dominated front; rank k = front after removing ranks < k. Identical points share a rank
    (neither dominates the other), so duplicates are all kept unless the caller deduplicates explicitly."""
    n = len(points)
    ranks = [-1] * n
    remaining = list(range(n))
    r = 0
    while remaining:
        front = [i for i in remaining if not any(dominates(points[j], points[i]) for j in remaining if j != i)]
        for i in front:
            ranks[i] = r
        remaining = [i for i in remaining if ranks[i] < 0]
        r += 1
    return ranks


def active_dimensions(evals: Sequence[dict[str, Any]]) -> tuple[list[str], dict[str, Any]]:
    """Objective dimensions for ONE request. intent_loss is dropped when it is not defined for every candidate
    (no scorable preference at all -> 'none_scorable'; some candidates unscorable -> 'partially_scorable')."""
    n_intent = sum(e["objectives"]["intent_loss"] is not None for e in evals)
    dims = ["violation_count", "plausibility_loss"]
    info = {"intent_dimension": "active", "n_with_intent": n_intent}
    if evals and n_intent == len(evals):
        dims = ["violation_count", "intent_loss", "plausibility_loss"]
    else:
        info["intent_dimension"] = "none_scorable" if n_intent == 0 else "partially_scorable"
    return dims, info


def objective_vector(e: dict[str, Any], dims: Sequence[str], decimals: int = 12) -> tuple[float, ...]:
    return tuple(round(float(e["objectives"][d]), decimals) for d in dims)


def pareto_sort(evals: list[dict[str, Any]], decimals: int = 12) -> dict[str, Any]:
    """Annotate each evaluation (in place) with pareto_rank / is_pareto and return summary."""
    dims, info = active_dimensions(evals)
    ranks = non_dominated_ranks([objective_vector(e, dims, decimals) for e in evals])
    for e, r in zip(evals, ranks):
        e["pareto_rank"], e["is_pareto"] = r, r == 0
    front = [e for e in evals if e["is_pareto"]]
    return {"dimensions": dims, **info, "n_candidates": len(evals), "front_size": len(front),
            "rank_counts": {str(k): ranks.count(k) for k in sorted(set(ranks))}}
