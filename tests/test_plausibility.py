"""Dataset-relative plausibility tests."""
from __future__ import annotations

import math

import pytest

from cago.evaluation.config import EvaluationConfig
from cago.evaluation.plausibility import contextual_support, evaluate_plausibility, template_proximity
from cago.generation.support_tables import build_support_tables
from tests.synthetic_data import garment, make_rep, surface

CFG = EvaluationConfig()
REP = make_rep([garment(f"D{i}", f"pd{i}", "train", [("cotton", 60), ("polyester", 40)], [("polyester", 100)]) for i in range(8)])
SUP = build_support_tables(REP)
ZERO = {"n_substitutions": 0, "abs_pct_change_total": 0.0}


def comps(shell, lining=None):
    out = surface(shell)
    if lining:
        out.append({"component_id": "l", "source_component_index": 1, "component_class": "lining_component",
                    "component_name_normalized": "lining", "materials": [{"material": m, "pct": float(p)} for m, p in lining]})
    return out


def test_contextual_support_is_log_frequency_normalized():
    c = contextual_support(comps([("cotton", 55), ("polyester", 45)]), "trousers", SUP, CFG)
    n = SUP.combo_count("trousers", "surface_component", ["cotton", "polyester"])
    n_max = max(SUP.combos_by_category_class[("trousers", "surface_component")].values())
    assert n == 9 and n_max == 9 and c["score"] == pytest.approx(1.0)                        # most frequent combination
    rare = contextual_support(comps([("wool", 50), ("cotton", 50)]), "trousers", SUP, CFG)
    assert rare["components"][0]["support_count"] == 1
    assert rare["score"] == pytest.approx(math.log1p(1) / math.log1p(9)) and 0 < rare["score"] < 1
    assert rare["score"] < c["score"]                                                          # monotonic in support


def test_unseen_material_combination_gets_zero_exact_support():
    c = contextual_support(comps([("cotton", 50), ("nylon", 50)]), "trousers", SUP, CFG)      # both materials seen, combo never
    assert c["components"][0]["support_count"] == 0 and c["score"] == 0.0 and c["n_components_unseen_combination"] == 1
    assert "never observed" in c["components"][0]["evidence"]
    other_cat = contextual_support(comps([("cotton", 100)]), "shorts", SUP, CFG)              # context absent from TRAIN
    assert other_cat["score"] == 0.0 and other_cat["components"][0]["context_max_count"] == 0


def test_contextual_support_uses_train_only():
    assert SUP.splits_used == ("train",)
    silk = contextual_support(comps([("silk", 100)]), "trousers", SUP, CFG)                   # silk exists only in val/test rows
    assert silk["score"] == 0.0 and silk["components"][0]["support_count"] == 0
    # changing val/test rows cannot change the score
    rows = REP.to_dict("records")
    for r in rows:
        if r["split"] != "train":
            r["components"] = garment("Z", "pz", r["split"], [("cotton", 55), ("polyester", 45)], [("polyester", 100)])["components"]
    import pandas as pd
    sup2 = build_support_tables(pd.DataFrame(rows))
    assert contextual_support(comps([("silk", 100)]), "trousers", sup2, CFG)["score"] == 0.0
    bad = build_support_tables(REP)
    bad.splits_used = ("train", "val")
    with pytest.raises(ValueError):
        evaluate_plausibility(comps([("cotton", 100)]), "trousers", ZERO, bad, CFG)


def test_aggregate_over_components():
    c = comps([("cotton", 60), ("polyester", 40)], [("polyester", 100)])
    r = contextual_support(c, "trousers", SUP, CFG)
    assert len(r["components"]) == 2 and r["score"] == pytest.approx(sum(x["score"] for x in r["components"]) / 2)
    mn = contextual_support(c, "trousers", SUP, EvaluationConfig(context_aggregate="min"))
    assert mn["score"] == min(x["score"] for x in mn["components"])


def test_template_proximity_decreases_with_larger_mutations():
    prox = lambda n, a: template_proximity({"n_substitutions": n, "abs_pct_change_total": a}, CFG)["score"]
    assert prox(0, 0) == 1.0
    assert prox(0, 2) > prox(0, 10) > prox(0, 40)
    assert prox(0, 10) > prox(1, 10) > prox(2, 10) > prox(3, 10)
    assert prox(1, 0) > prox(2, 0)
    p = template_proximity({"n_substitutions": 1, "abs_pct_change_total": 10.0}, CFG)
    assert p["D"] == pytest.approx(1.1) and p["score"] == pytest.approx(math.exp(-0.5 * 1.1)) and p["n_substitutions"] == 1


def test_plausibility_combines_with_configurable_weights_and_keeps_raw_evidence():
    c = comps([("cotton", 55), ("polyester", 45)], [("polyester", 100)])
    dist = {"n_substitutions": 1, "abs_pct_change_total": 10.0}
    p = evaluate_plausibility(c, "trousers", dist, SUP, CFG)
    assert p["plausibility_raw"] == pytest.approx(0.5 * p["contextual_support"]["score"] + 0.5 * p["template_proximity"]["score"], abs=1e-5)
    assert p["plausibility_0_100"] == pytest.approx(100 * p["plausibility_raw"], abs=0.01)
    assert p["contextual_support"]["components"][0]["support_count"] >= 1 and p["template_proximity"]["abs_pct_change_total"] == 10.0
    w = evaluate_plausibility(c, "trousers", dist, SUP, EvaluationConfig(w_context=1.0, w_proximity=0.0))
    assert w["plausibility_raw"] == pytest.approx(w["contextual_support"]["score"], abs=1e-5)
    assert "manufacturab" in p["note"] and "not a guarantee" in p["note"]
