"""Three user-facing selections from the Pareto front. No design is ever called universally best."""
from __future__ import annotations

import math
from typing import Any, Sequence

from cago.evaluation.config import EvaluationConfig


def _r(x: float | None, d: int = 12) -> float:
    return round(x, d) if x is not None else float("-inf")


def balanced_distance(e: dict[str, Any], dims: Sequence[str], cfg: EvaluationConfig, front: list[dict[str, Any]]) -> float:
    """Euclidean distance to the ideal point after normalisation.

    fixed (default): violations / max_violations; the two losses are already in [0, 1]; ideal = origin.
    front_minmax: min-max over the Pareto front (a constant objective contributes 0).
    """
    comps = []
    for d in dims:
        v = float(e["objectives"][d])
        if cfg.balanced_normalization == "front_minmax":
            vals = [float(f["objectives"][d]) for f in front]
            lo, hi = min(vals), max(vals)
            comps.append(0.0 if hi == lo else (v - lo) / (hi - lo))
        else:
            comps.append(v / cfg.max_violations if d == "violation_count" else v)
    return math.sqrt(sum(c * c for c in comps))


def _key_balanced(e, dist, d):
    return (_r(dist, d), e["objectives"]["violation_count"], -_r(e["intent_alignment_raw"], d),
            -_r(e["plausibility_raw"], d), e["candidate_id"])


def select_designs(evals: list[dict[str, Any]], dims: Sequence[str], cfg: EvaluationConfig = EvaluationConfig()) -> dict[str, Any]:
    """Balanced / Intent-focused / Sorting-focused designs among rank-0 candidates (evaluations carry is_pareto)."""
    d = cfg.objective_decimals
    front = sorted((e for e in evals if e["is_pareto"]), key=lambda e: e["candidate_id"])
    if not front:
        return {"selections": [], "by_role": {}, "front_size": 0}
    picks: dict[str, dict[str, Any] | None] = {}
    # A) Balanced: closest to ideal; ties: fewer violations, higher intent, higher plausibility, candidate_id
    dist = {e["candidate_id"]: balanced_distance(e, dims, cfg, front) for e in front}
    picks["balanced"] = min(front, key=lambda e: _key_balanced(e, dist[e["candidate_id"]], d))
    # B) Intent-focused: max intent; ties: lower violations, higher plausibility, candidate_id
    with_intent = [e for e in front if e["intent_alignment_raw"] is not None]
    picks["intent_focused"] = min(with_intent, key=lambda e: (-_r(e["intent_alignment_raw"], d), e["objectives"]["violation_count"],
                                                              -_r(e["plausibility_raw"], d), e["candidate_id"])) if with_intent else None
    # C) Sorting-focused: min violations; ties: higher intent, higher plausibility, candidate_id
    picks["sorting_focused"] = min(front, key=lambda e: (e["objectives"]["violation_count"], -_r(e["intent_alignment_raw"], d),
                                                         -_r(e["plausibility_raw"], d), e["candidate_id"]))
    roles: dict[str, list[str]] = {}
    for role, e in picks.items():
        if e is not None:
            roles.setdefault(e["candidate_id"], []).append(role)
    sel = [{"candidate_id": cid, "roles": rs, "balanced_distance": round(dist[cid], 6)} for cid, rs in sorted(roles.items())]
    return {"selections": sel, "by_role": {r: (e["candidate_id"] if e else None) for r, e in picks.items()},
            "front_size": len(front), "intent_focused_omitted": picks["intent_focused"] is None,
            "multiple_roles_same_candidate": any(len(s["roles"]) > 1 for s in sel),
            "balanced_normalization": cfg.balanced_normalization}
