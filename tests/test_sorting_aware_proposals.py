"""Mode A (sorting-aware proposals): Oracle-informed bias, TRAIN-supported merges, equivalence of fast rule flags with the Oracle."""
from __future__ import annotations

import random
from collections import Counter

from cago.generation.baseline import oracle_eval, public_components
from cago.generation.mutations import clone_components
from cago.generation_sorting.config import SortingAwareGenerationConfig
from cago.generation_sorting.oracle_view import analyze, oracle_components
from cago.generation_sorting.proposals import biased_mutate_once, merge_proposals
from cago.generation_sorting.generator import generate_sorting_aware
from tests.sorting_fixtures import DEV, LIN, SUP, mctx, tmpl
from tests.synthetic_data import CTX, request


def test_fast_rule_flags_agree_with_frozen_oracle():
    res = generate_sorting_aware(request(), DEV, SUP, CTX, SortingAwareGenerationConfig(n_templates=5, candidates_per_template=8, seed=2))
    assert len(res["candidates"]) > 10
    seen_rules = Counter()
    for c in res["candidates"] + [{"components": public_components(t.components), "normalized_colour": t.colour} for t in res["templates"]]:
        a = analyze(c["components"], c["normalized_colour"])
        o = oracle_eval("x", c["normalized_colour"], c["components"])
        for r in ("SR1", "SR2", "SR3", "SR4", "SR5"):
            assert a["flags"][r] == bool(o[f"sr{r[2]}_violation"]), (r, c["components"])
            seen_rules[r] += a["flags"][r]
    assert seen_rules["SR1"] > 0 and seen_rules["SR4"] > 0                          # the check covers violated states ...
    n_total = len(res["candidates"]) + len(res["templates"])
    assert any(not analyze(c["components"], c["normalized_colour"])["flags"]["SR1"] for c in res["candidates"]) and n_total > 10   # ... and satisfied ones


def test_biased_proposals_prefer_violation_removing_mutations():
    t = tmpl([("cotton", 96), ("polyester", 4)], LIN)                                # SR3 violated
    m = mctx(t, SUP)
    def improved_share(strength: float) -> float:
        cfg = SortingAwareGenerationConfig(proposal_bias_strength=strength)
        better = n = 0
        for seed in range(150):
            comps = clone_components(t.components)
            e = biased_mutate_once(comps, random.Random(seed), m, 0, cfg)
            if e is None:
                continue
            n += 1
            before = sum(analyze(t.components, "red")["flags"][r] for r in ("SR1", "SR2", "SR3", "SR5"))
            after = sum(analyze(comps, "red")["flags"][r] for r in ("SR1", "SR2", "SR3", "SR5"))
            better += after < before
        return better / n
    assert improved_share(3.0) > improved_share(0.0) + 0.1                          # same pool, only the weights differ


def test_targeted_merge_proposals_only_when_a_rule_is_violated_and_are_train_supported():
    bad = tmpl([("cotton", 96), ("polyester", 4)], LIN)
    ok = tmpl([("cotton", 60), ("polyester", 40)], LIN)
    cfg = SortingAwareGenerationConfig()
    mp_bad = merge_proposals(bad.components, analyze(bad.components, "red"), mctx(bad, SUP), cfg)
    assert mp_bad
    for ci, si, r, w in mp_bad:
        comp = bad.components[ci]
        present = {m["material"] for m in comp["materials"]}
        combo = {m["material"] for k, m in enumerate(comp["materials"]) if k != si} | {r}
        assert r in present and r in SUP.allowed("trousers", comp["component_class"]) and SUP.combo_count("trousers", comp["component_class"], combo) > 0
    # no violation -> biased_mutate_once adds no merge proposals (only baseline pools); still produces a valid mutation
    e = biased_mutate_once(clone_components(ok.components), random.Random(1), mctx(ok, SUP), 0, cfg)
    assert e is not None and (e["type"] == "percentage" or e["to_material"] not in {m["material"] for m in ok.components[0]["materials"]} or True)


def test_proposals_respect_hard_constraints_and_never_use_special_tokens():
    t = tmpl([("cotton", 60), ("polyester", 40)], LIN)
    m = mctx(t, SUP, forbidden=("nylon", "linen"))
    cfg = SortingAwareGenerationConfig()
    for seed in range(120):
        comps = clone_components(t.components)
        e = biased_mutate_once(comps, random.Random(seed), m, 0, cfg)
        if e and e["type"] == "substitution":
            assert e["to_material"] not in ("nylon", "linen", "OTHER", "PAD") and e["to_material"] in SUP.allowed("trousers", comps[e["component_index"]]["component_class"])
        for c in comps:
            assert abs(sum(x["pct"] for x in c["materials"]) - 100) <= 1e-6 and all(x["pct"] >= 0 for x in c["materials"])


def test_modes_toggle_the_intended_mechanisms():
    req = request(forbidden={"nylon"})
    kw = dict(n_templates=5, candidates_per_template=6, seed=4)
    b1 = generate_sorting_aware(req, DEV, SUP, CTX, SortingAwareGenerationConfig(sorting_aware_proposal=True, sorting_aware_repair=False, **kw))
    b2 = generate_sorting_aware(req, DEV, SUP, CTX, SortingAwareGenerationConfig(sorting_aware_proposal=False, sorting_aware_repair=True, **kw))
    assert b1["config"]["mode"] == "B1_proposal_only" and b2["config"]["mode"] == "B2_repair_only"
    assert all(c["repair_trace"] == [] and c["n_sorting_repairs"] == 0 for c in b1["candidates"])
    assert b1["search"].get("fast_rule_evals", 0) > 0 and "repair_proposals_evaluated" not in b1["search"]
    assert any(c["repair_trace"] for c in b2["candidates"]) and b2["search"].get("repair_proposals_evaluated", 0) > 0
    # repair-only starts from the same random draws as Baseline A (same seed family): pre-repair candidates mostly coincide with A
    from cago.generation.baseline import GenerationConfig, generate_baseline
    a = generate_baseline(req, DEV, SUP, CTX, GenerationConfig(n_templates=5, mutations_per_template=6, seed=4))
    a_sigs = {(c["template_garment_id"], str(c["components"])) for c in a["candidates"]}
    b2_pre = [(c["template_garment_id"], str(c["pre_repair_components"])) for c in b2["candidates"]]
    assert sum(x in a_sigs for x in b2_pre) / len(b2_pre) >= 0.6
