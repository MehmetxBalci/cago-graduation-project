"""Pareto dominance, ranking and the three selections."""
from __future__ import annotations

import pytest

from cago.evaluation.config import EvaluationConfig
from cago.optimization.pareto import active_dimensions, dominates, non_dominated_ranks, pareto_sort
from cago.optimization.selection import balanced_distance, select_designs

CFG = EvaluationConfig()


def E(cid, v, intent, plaus):
    """intent / plaus are raw 0-1 (None allowed for intent)."""
    return {"candidate_id": cid, "intent_alignment_raw": intent, "plausibility_raw": plaus,
            "objectives": {"violation_count": v, "intent_loss": None if intent is None else round(1 - intent, 6),
                           "plausibility_loss": round(1 - plaus, 6)}}


def front(evals):
    s = pareto_sort(evals)
    return s


def test_dominance_definition():
    assert dominates((1, 1, 1), (2, 2, 2)) and dominates((1, 2, 3), (1, 2, 4))
    assert not dominates((1, 2, 3), (1, 2, 3))                       # equal: no strict improvement
    assert not dominates((1, 3, 3), (2, 2, 3)) and not dominates((2, 2, 3), (1, 3, 3))   # trade-off
    assert not dominates((1, 1), (0, 5))


def test_ranks_are_correct_fronts():
    pts = [(0, 0.5, 0.5), (1, 0.1, 0.1), (2, 0.9, 0.9), (1, 0.5, 0.5), (3, 1, 1)]
    r = non_dominated_ranks(pts)
    assert r == [0, 0, 2, 1, 3]            # p3 is dominated by p0; p2 by p3; p4 by p2 (successive fronts)
    assert non_dominated_ranks([]) == []


def test_identical_points_are_both_non_dominated_unless_deduplicated():
    pts = [(1, 0.2, 0.2), (1, 0.2, 0.2), (2, 0.5, 0.5)]
    assert non_dominated_ranks(pts) == [0, 0, 1]
    evals = [E("a", 1, 0.8, 0.8), E("b", 1, 0.8, 0.8)]
    assert pareto_sort(evals)["front_size"] == 2 and all(e["is_pareto"] for e in evals)


def test_float_noise_does_not_break_ties():
    evals = [E("a", 1, 0.8, 0.8), E("b", 1, 0.8 + 1e-15, 0.8)]
    assert pareto_sort(evals)["front_size"] == 2                      # rounded to 12 decimals before comparison


def test_intent_dimension_dropped_only_when_not_defined():
    none = [E("a", 1, None, 0.5), E("b", 0, None, 0.4)]
    dims, info = active_dimensions(none)
    assert dims == ["violation_count", "plausibility_loss"] and info["intent_dimension"] == "none_scorable"
    mixed = [E("a", 1, 0.5, 0.5), E("b", 0, None, 0.4)]
    assert active_dimensions(mixed)[1]["intent_dimension"] == "partially_scorable"
    full = [E("a", 1, 0.5, 0.5)]
    assert active_dimensions(full)[0] == ["violation_count", "intent_loss", "plausibility_loss"]
    # dropping intent changes the front: b (worse intent proxy None) is judged on the two remaining objectives
    s = pareto_sort(none)
    assert s["dimensions"] == ["violation_count", "plausibility_loss"] and s["front_size"] == 2


def _front_set():
    evals = [E("a", 0, 0.40, 0.60), E("b", 2, 0.95, 0.70), E("c", 1, 0.70, 0.90), E("d", 3, 0.50, 0.50), E("e", 1, 0.70, 0.50)]
    s = pareto_sort(evals)
    return evals, s


def test_pareto_front_membership():
    evals, s = _front_set()
    ids = {e["candidate_id"] for e in evals if e["is_pareto"]}
    assert ids == {"a", "b", "c"} and s["front_size"] == 3 and s["rank_counts"]["0"] == 3
    assert not next(e for e in evals if e["candidate_id"] == "d")["is_pareto"]


def test_three_selections_and_roles():
    evals, s = _front_set()
    sel = select_designs(evals, s["dimensions"], CFG)
    by = sel["by_role"]
    assert by["intent_focused"] == "b" and by["sorting_focused"] == "a"
    dist = {e["candidate_id"]: balanced_distance(e, s["dimensions"], CFG, [e for e in evals if e["is_pareto"]]) for e in evals if e["is_pareto"]}
    assert by["balanced"] == min(dist, key=lambda k: (round(dist[k], 12), k)) == "c"
    assert sorted(x["candidate_id"] for x in sel["selections"]) == ["a", "b", "c"]


def test_same_candidate_reports_multiple_roles_without_duplicates():
    evals = [E("a", 0, 0.9, 0.9), E("b", 1, 0.5, 0.5)]
    s = pareto_sort(evals)
    sel = select_designs(evals, s["dimensions"], CFG)
    assert len(sel["selections"]) == 1 and sel["selections"][0]["roles"] == ["balanced", "intent_focused", "sorting_focused"]
    assert sel["multiple_roles_same_candidate"]


def test_balanced_selection_is_deterministic_and_order_independent():
    evals, s = _front_set()
    first = select_designs(evals, s["dimensions"], CFG)["by_role"]
    rev = list(reversed(evals))
    assert select_designs(rev, s["dimensions"], CFG)["by_role"] == first
    tie = [E("z", 1, 0.5, 0.5), E("m", 1, 0.5, 0.5)]
    st = pareto_sort(tie)
    assert select_designs(tie, st["dimensions"], CFG)["by_role"]["balanced"] == "m"       # candidate_id tie-break
    mm = select_designs(evals, s["dimensions"], EvaluationConfig(balanced_normalization="front_minmax"))["by_role"]
    assert mm == select_designs(rev, s["dimensions"], EvaluationConfig(balanced_normalization="front_minmax"))["by_role"]


def test_intent_focused_tie_break_order():
    # same intent: lower violations first, then higher plausibility, then candidate_id
    evals = [E("c", 1, 0.8, 0.5), E("b", 1, 0.8, 0.9), E("a", 0, 0.8, 0.3), E("x", 2, 0.8, 0.99)]
    s = pareto_sort(evals)
    assert select_designs(evals, s["dimensions"], CFG)["by_role"]["intent_focused"] == "a"
    ev2 = [E("c", 1, 0.8, 0.9), E("b", 1, 0.8, 0.9), E("a", 1, 0.8, 0.5)]
    s2 = pareto_sort(ev2)
    assert select_designs(ev2, s2["dimensions"], CFG)["by_role"]["intent_focused"] == "b"   # plaus tie -> id
    ev3 = [E("b", 1, 0.8, 0.9), E("a", 1, 0.8, 0.7)]
    s3 = pareto_sort(ev3)
    assert select_designs(ev3, s3["dimensions"], CFG)["by_role"]["intent_focused"] == "b"   # higher plausibility wins


def test_sorting_focused_tie_break_order():
    evals = [E("c", 0, 0.5, 0.9), E("b", 0, 0.7, 0.2), E("a", 0, 0.7, 0.8), E("z", 1, 0.99, 0.99)]
    s = pareto_sort(evals)
    assert select_designs(evals, s["dimensions"], CFG)["by_role"]["sorting_focused"] == "a"   # intent tie -> plausibility
    ev2 = [E("b", 0, 0.7, 0.8), E("a", 0, 0.7, 0.8)]
    s2 = pareto_sort(ev2)
    assert select_designs(ev2, s2["dimensions"], CFG)["by_role"]["sorting_focused"] == "a"    # full tie -> id
    ev3 = [E("c", 0, 0.5, 0.9), E("b", 0, 0.7, 0.2)]
    assert select_designs(ev3, pareto_sort(ev3)["dimensions"], CFG)["by_role"]["sorting_focused"] == "b"   # higher intent first


def test_no_intent_score_omits_intent_focused_selection():
    evals = [E("a", 0, None, 0.5), E("b", 1, None, 0.9)]
    s = pareto_sort(evals)
    sel = select_designs(evals, s["dimensions"], CFG)
    assert sel["by_role"]["intent_focused"] is None and sel["intent_focused_omitted"]
    assert sel["by_role"]["sorting_focused"] == "a" and sel["by_role"]["balanced"] in {"a", "b"}


def test_empty_front():
    assert select_designs([], [], CFG)["selections"] == []
