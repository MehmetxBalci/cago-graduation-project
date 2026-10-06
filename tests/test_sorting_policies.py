"""Acceptance policies: STRICT_SORTING and NONDOMINATED_LOCAL."""
from __future__ import annotations

import pytest

from cago.generation_sorting.policies import Snapshot, decide, objective_vector

S = Snapshot


def strict(b, a, i=0.15, p=0.15):
    return decide("STRICT_SORTING", b, a, i, p)


def local(b, a):
    return decide("NONDOMINATED_LOCAL", b, a, None, None)


def test_strict_requires_violation_decrease():
    ok, why, _ = strict(S(2, 0.8, 0.9), S(1, 0.8, 0.9))
    assert ok and why is None
    for after in (S(2, 0.9, 0.95), S(3, 0.9, 0.95)):                          # improved intent/plaus but no sorting gain
        ok, why, _ = strict(S(2, 0.8, 0.9), after)
        assert not ok and why == "no_violation_decrease"


def test_strict_floors_use_max_allowed_drop_and_skip_null_intent():
    assert strict(S(2, 0.8, 0.9), S(1, 0.66, 0.9))[0]                        # drop 0.14 <= 0.15
    ok, why, d = strict(S(2, 0.8, 0.9), S(1, 0.64, 0.9))
    assert not ok and why == "intent_floor" and d["intent_delta"] == pytest.approx(-0.16)
    ok, why, _ = strict(S(2, 0.8, 0.9), S(1, 0.8, 0.74))
    assert not ok and why == "plausibility_floor"
    assert strict(S(2, None, 0.9), S(1, None, 0.9))[0]                       # Intent null: no Intent floor
    assert strict(S(2, 0.8, 0.9), S(1, 0.0, 0.0), i=None, p=None)[0]         # floors disabled
    assert strict(S(2, 0.8, 0.9), S(1, 0.2, 0.9), i=0.7)[0] is True          # configurable amount


def test_hard_invalid_is_always_rejected():
    for pol in ("STRICT_SORTING", "NONDOMINATED_LOCAL"):
        ok, why, _ = decide(pol, S(3, 0.5, 0.5), S(0, 0.9, 0.9, hard_ok=False), None, None)
        assert not ok and why == "hard_invalid"


def test_nondominated_local_dominance_correctness():
    b = S(2, 0.8, 0.8)
    assert local(b, S(1, 0.8, 0.8))[0]                                       # strictly better sorting, others equal
    assert local(b, S(2, 0.9, 0.8))[0] and local(b, S(2, 0.8, 0.9))[0]       # strictly better in one, equal elsewhere
    assert local(b, S(1, 0.9, 0.9))[0]
    ok, why, d = local(b, S(1, 0.8, 0.7))
    assert not ok and why == "not_locally_nondominated" and d["worse_in"] == ["plausibility"]
    ok, why, d = local(b, S(0, 0.5, 0.8))
    assert not ok and d["worse_in"] == ["intent"]
    assert not local(b, b)[0]                                                # identical: no strict improvement
    assert not local(b, S(3, 0.9, 0.9))[0]                                   # worse sorting
    # Intent null: dominance is judged over (violation_count, plausibility loss) only
    assert local(S(2, None, 0.8), S(1, None, 0.8))[0] and not local(S(2, None, 0.8), S(1, None, 0.7))[0]


def test_policies_are_distinct_and_not_collapsed_to_a_scalar():
    b, a = S(2, 0.8, 0.9), S(1, 0.8, 0.8)                                    # sorting up, plausibility down by 0.1
    assert strict(b, a)[0] is True and local(b, a)[0] is False
    assert objective_vector(a, True) == (1.0, 0.2, pytest.approx(0.2)) or len(objective_vector(a, True)) == 3
    assert len(objective_vector(a, False)) == 2
    with pytest.raises(ValueError):
        decide("WEIGHTED_SUM", b, a, None, None)
