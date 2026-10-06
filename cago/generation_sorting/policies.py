"""Deterministic acceptance policies for sorting repairs (kept separate; objectives are never collapsed into a scalar)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cago.generation_sorting.config import NONDOMINATED_LOCAL, POLICIES, STRICT_SORTING
from cago.optimization.pareto import dominates

EPS = 1e-9


@dataclass(frozen=True)
class Snapshot:
    """Evaluation of one composition: SR violation count, Intent (raw 0-1 or None), Plausibility (raw 0-1), hard validity."""
    vc: int
    intent: float | None
    plaus: float
    hard_ok: bool = True


def objective_vector(s: Snapshot, with_intent: bool, decimals: int = 12) -> tuple[float, ...]:
    v = [float(s.vc)]
    if with_intent:
        v.append(1.0 - s.intent)
    v.append(1.0 - s.plaus)
    return tuple(round(x, decimals) for x in v)


def decide(policy: str, before: Snapshot, after: Snapshot, intent_floor: float | None,
           plaus_floor: float | None) -> tuple[bool, str | None, dict[str, Any]]:
    """(accepted, rejection_reason, details).

    STRICT_SORTING: hard constraints pass AND violation_count decreases AND the Intent / Plausibility floors pass
    (max allowed drop per repair, raw units; Intent floor skipped when Intent is null).
    NONDOMINATED_LOCAL: hard constraints pass AND `after` dominates `before` over (violation_count, Intent loss when
    Intent exists, Plausibility loss).
    """
    if policy not in POLICIES:
        raise ValueError(f"unknown policy {policy!r}")
    d_intent = None if before.intent is None or after.intent is None else after.intent - before.intent
    d_plaus = after.plaus - before.plaus
    details = {"intent_delta": d_intent, "plausibility_delta": d_plaus, "violation_delta": after.vc - before.vc}
    if not after.hard_ok:
        return False, "hard_invalid", details
    if policy == STRICT_SORTING:
        if after.vc >= before.vc:
            return False, "no_violation_decrease", details
        if intent_floor is not None and d_intent is not None and -d_intent > intent_floor + EPS:
            return False, "intent_floor", details
        if plaus_floor is not None and -d_plaus > plaus_floor + EPS:
            return False, "plausibility_floor", details
        return True, None, details
    with_intent = before.intent is not None and after.intent is not None
    if dominates(objective_vector(after, with_intent), objective_vector(before, with_intent)):
        return True, None, details
    worse = [n for n, bad in (("violation_count", after.vc > before.vc), ("intent", with_intent and after.intent < before.intent - EPS),
                              ("plausibility", after.plaus < before.plaus - EPS)) if bad]
    return False, "not_locally_nondominated", {**details, "worse_in": worse}
