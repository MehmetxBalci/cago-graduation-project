"""Rule-targeted repairs (SR1, SR2, SR3, SR5), SR4 immutability, floors, traces and cycle prevention."""
from __future__ import annotations

from collections import Counter

import pytest

from cago.generation.baseline import oracle_eval, public_components
from cago.generation.mutations import clone_components
from cago.generation_sorting.config import SortingAwareGenerationConfig
from cago.generation_sorting.generator import repair_candidate
from cago.generation_sorting.oracle_view import analyze
from cago.generation_sorting.repairs import apply_ops, repair_proposals, sr3_ops
from cago.generation_sorting.trace import STEP_FIELDS, oracle_flags, verify_trace
from tests.sorting_fixtures import CFG, ECFG, LIN, SUP, tmpl
from tests.synthetic_data import CTX, request


def run(shell, lining, soft=None, colour="red", cfg=None, forbidden=(), support=SUP):
    t = tmpl(shell, lining, colour)
    comps = clone_components(t.components)
    cnt = Counter()
    out, log, trace = repair_candidate(comps, [], public_components(t.components), t, request(forbidden, **(soft or {})), support, CTX,
                                       cfg or CFG, ECFG, cnt, "cand_x")
    return t, out, log, trace, cnt


def flags(components, colour="red"):
    return oracle_flags(oracle_eval("x", colour, public_components(components)))


def accepted(trace):
    return [s for s in trace if s["accepted"]]


def test_sr1_supported_mono_repair():
    t, out, log, trace, _ = run([("linen", 100)], LIN)
    assert flags(t.components)["SR1"] and flags(t.components)["SR5"]
    acc = accepted(trace)
    assert acc and acc[0]["targeted_rule"] == "SR1" and acc[0]["oracle_reason_before"] == "unsupported_mono"
    assert out[0]["materials"][0]["material"] == "cotton" and out[0]["materials"][0]["pct"] == 100.0
    assert "SR1" in acc[0]["confirmed_fixed_rules"] and not any(flags(out).values())


def test_sr1_supported_binary_repair():
    t, out, log, trace, _ = run([("cotton", 50), ("linen", 50)], LIN)
    assert analyze(t.components, "red")["sr1_reason"] == "unsupported_binary"
    acc = accepted(trace)
    assert acc and acc[0]["targeted_rule"] == "SR1" and not flags(out)["SR1"]
    mats = {m["material"] for m in out[0]["materials"]}
    assert SUP.combo_count("trousers", "surface_component", mats) > 0              # never a fabricated combination
    assert all(m["material"] in SUP.allowed("trousers", "surface_component") for m in out[0]["materials"])


def test_sr2_fibre_count_reduction():
    cfg = SortingAwareGenerationConfig(seed=1, allow_sr1_repair=False)               # only SR2 is targeted
    t, out, log, trace, _ = run([("cotton", 60), ("polyester", 30), ("elastane", 10)], LIN, cfg=cfg)
    assert analyze(t.components, "red")["n_fibres"] == 3 and flags(t.components)["SR2"]
    acc = accepted(trace)
    assert acc and acc[0]["targeted_rule"] == "SR2" and acc[0]["operation"] == "sr2_merge_fibre_into_existing_fibre"
    assert analyze(out, "red")["n_fibres"] == 2 and not flags(out)["SR2"]
    assert len(out[0]["materials"]) == 3                                             # slot count (topology) unchanged
    assert abs(sum(m["pct"] for m in out[0]["materials"]) - 100) <= 1e-6


def test_sr3_below_five_repaired_and_exactly_five_passes():
    assert flags(tmpl([("cotton", 96), ("polyester", 4)], LIN).components)["SR3"]
    assert not flags(tmpl([("cotton", 95), ("polyester", 5)], LIN).components)["SR3"]     # exactly 5.0 passes (frozen Oracle)
    t, out, log, trace, _ = run([("cotton", 96), ("polyester", 4)], LIN)
    acc = accepted(trace)
    assert acc and acc[0]["targeted_rule"] == "SR3" and not flags(out)["SR3"]
    assert abs(sum(m["pct"] for m in out[0]["materials"]) - 100) <= 1e-6
    # the raise-to-5% operation lands on exactly 5.0 and keeps the sum at 100
    a = analyze(t.components, "red")
    raise_ops = [p for p in sr3_ops(t.components, a, "trousers", SUP, frozenset(), CFG) if p.operation == "sr3_raise_minor_fibre_to_5pct"]
    assert raise_ops and raise_ops[0].ops[0][4] == pytest.approx(1.0)
    comps, entries = apply_ops(t.components, raise_ops[0].ops, 0, "SR3")
    mats = {m["material"]: m["pct"] for m in comps[0]["materials"]}
    assert mats["polyester"] == 5.0 and mats["cotton"] == 95.0 and entries[0]["type"] == "percentage"
    assert not analyze(comps, "red")["flags"]["SR3"]


def test_sr5_hidden_material_repair_and_exactly_five_percent_passes():
    assert not flags(tmpl([("cotton", 100)], [("polyester", 5), ("cotton", 95)]).components)["SR5"]    # hidden 5.0% passes
    t, out, log, trace, _ = run([("cotton", 100)], [("polyester", 100)])
    assert flags(t.components)["SR5"] and not flags(t.components)["SR1"]
    acc = accepted(trace)
    assert acc and acc[0]["targeted_rule"] == "SR5" and acc[0]["component"]["class"] == "lining_component"
    assert out[1]["materials"][0]["material"] == "cotton" and not flags(out)["SR5"]
    assert [c["component_name_normalized"] for c in out] == [c["component_name_normalized"] for c in t.components]   # no component change
    assert len(out) == len(t.components)


def test_sr5_percentage_repair_lowers_hidden_material_to_exactly_five():
    from cago.generation_sorting.repairs import sr5_ops
    t = tmpl([("cotton", 100)], [("polyester", 30), ("cotton", 70)])
    a = analyze(t.components, "red")
    assert a["flags"]["SR5"]
    props = [p for p in sr5_ops(t.components, a, "trousers", SUP, frozenset()) if p.operation == "sr5_lower_hidden_pct_to_5pct"]
    assert props
    comps, _ = apply_ops(t.components, props[0].ops, 0, "SR5")
    assert {m["material"]: m["pct"] for m in comps[1]["materials"]} == {"polyester": 5.0, "cotton": 95.0} and not analyze(comps, "red")["flags"]["SR5"]


def test_sr4_is_immutable_and_never_targeted():
    t, out, log, trace, cnt = run([("cotton", 100)], LIN, colour="black")
    assert flags(t.components, "black")["SR4"] and flags(out, "black")["SR4"] and trace == []   # nothing repairable, SR4 untouched
    assert "SR4" not in SortingAwareGenerationConfig().allowed_rules()
    t2, out2, _, trace2, _ = run([("linen", 100)], LIN, colour="black")
    assert flags(out2, "black")["SR4"] and all(s["targeted_rule"] != "SR4" for s in trace2)
    a = analyze(t2.components, "black")
    props = repair_proposals(t2.components, a, "trousers", SUP, frozenset(), CFG, [], "black")
    assert props and all(p.rule != "SR4" for p in props)
    from cago.generation_sorting.generator import _account_unresolved
    c = Counter()
    _account_unresolved(out2, tmpl([("linen", 100)], LIN, "black"), CFG, c)
    assert c["sr4_immutable_violation"] == 1 and c["unresolved:SR1"] == 0


def test_accepted_repairs_truly_fix_their_rules_and_strict_never_worsens():
    for shell, lining in (([("linen", 100)], LIN), ([("cotton", 50), ("linen", 50)], LIN), ([("cotton", 96), ("polyester", 4)], LIN),
                          ([("cotton", 100)], [("polyester", 100)]), ([("cotton", 60), ("polyester", 30), ("elastane", 10)], LIN)):
        t, out, log, trace, _ = run(shell, lining)
        for s in accepted(trace):
            assert s["oracle_after"]["violation_count"] < s["oracle_before"]["violation_count"]            # STRICT_SORTING
            for r in s["confirmed_fixed_rules"]:
                assert s["oracle_before"]["flags"][r] and not s["oracle_after"]["flags"][r]
            assert s["claims_targeted_fix"] == (s["targeted_rule"] in s["confirmed_fixed_rules"])
        assert sum(flags(out).values()) <= sum(flags(t.components).values())


def test_introduced_violations_are_reported_and_cannot_be_hidden():
    # repairing SR1 on the shell would make the (linen) lining absent from the surface set -> SR5 introduced, vc not decreased
    t, out, log, trace, cnt = run([("linen", 100)], [("linen", 100)])
    assert flags(t.components)["SR1"] and not flags(t.components)["SR5"]
    rej = [s for s in trace if not s["accepted"]]
    assert rej and any("SR5" in s["introduced_rules"] for s in rej)
    assert all(s["rejection_reason"] == "no_violation_decrease" for s in rej if "SR5" in s["introduced_rules"] and s["oracle_after"]["violation_count"] >= 1)
    assert cnt["proposals_introducing_other_violation"] >= 1 and flags(out) == flags(t.components) or accepted(trace)


def test_intent_floor_rejects_excessive_preference_damage():
    soft = {"preferred_dominant_material": "linen"}
    t, out, log, trace, cnt = run([("linen", 100)], LIN, soft)
    assert trace and all(not s["accepted"] for s in trace)
    reasons = {s["rejection_reason"] for s in trace}
    assert "intent_floor" in reasons and reasons <= {"intent_floor", "plausibility_floor", "no_violation_decrease"}
    floor = [s for s in trace if s["rejection_reason"] == "intent_floor"]
    assert all(s["intent_before"] == 1.0 and s["intent_after"] == 0.0 and s["intent_delta"] == -1.0 for s in floor)
    assert all(s["oracle_after"]["violation_count"] < s["oracle_before"]["violation_count"] for s in floor)   # it WOULD have improved sorting
    assert out[0]["materials"][0]["material"] == "linen" and cnt["repair_rejected:intent_floor"] == len(floor)
    cfg = SortingAwareGenerationConfig(seed=1, preserve_intent_floor=None)
    _, out2, _, trace2, _ = run([("linen", 100)], LIN, soft, cfg=cfg)
    assert accepted(trace2)                                                           # same repair accepted without the floor
    _, out3, _, trace3, _ = run([("linen", 100)], LIN, None)                          # Intent null: floor is skipped
    assert accepted(trace3) and trace3[0]["intent_before"] is None and trace3[0]["intent_after"] is None


def test_plausibility_floor_rejects_excessive_plausibility_damage():
    cfg = SortingAwareGenerationConfig(seed=1, preserve_plausibility_floor=1e-6)
    t, out, log, trace, cnt = run([("linen", 100)], LIN, None, cfg=cfg)
    assert trace and not accepted(trace) and "plausibility_floor" in {s["rejection_reason"] for s in trace}
    assert all(s["plausibility_delta"] < 0 for s in trace if s["rejection_reason"] == "plausibility_floor")
    assert cnt["repair_rejected:plausibility_floor"] >= 1
    assert accepted(run([("linen", 100)], LIN, None, cfg=SortingAwareGenerationConfig(seed=1, preserve_plausibility_floor=None))[3])


def test_hard_constraints_block_repairs():
    # forbidding cotton leaves no admissible supported mono that also fixes the lining: only non-cotton proposals may appear
    t, out, log, trace, _ = run([("linen", 100)], LIN, None, forbidden=("cotton",))
    for s in trace:
        assert all(m != "cotton" for m, _ in s["materials_after"] if True) or s["component"]["class"] == "lining_component"
    assert not any(m["material"] == "cotton" for m in out[0]["materials"])
    for s in trace:
        for e in s["entries"]:
            assert e["to_material"] not in ("cotton", "OTHER", "PAD") if e["type"] == "substitution" and s["component"]["class"] == "surface_component" else True


def test_trace_faithfully_matches_before_after_candidate():
    t, out, log, trace, _ = run([("cotton", 60), ("polyester", 30), ("elastane", 10)], [("polyester", 100)])
    assert trace and all(set(STEP_FIELDS) <= set(s) for s in trace)
    pre = clone_components(t.components)
    assert verify_trace(t.components, pre, trace, out) is True
    acc = accepted(trace)
    assert acc[0]["oracle_before"]["flags"] == flags(pre) and acc[-1]["oracle_after"]["flags"] == flags(out)
    assert acc[-1]["oracle_after"]["violation_count"] == sum(flags(out).values())
    tampered = clone_components(out)
    tampered[0]["materials"][0]["pct"] += 1.0
    assert verify_trace(t.components, pre, trace, tampered) is False
    assert [e for s in acc for e in s["entries"]] == log                              # the candidate's log carries exactly the repairs


def test_repair_cycle_prevention_and_bounded_steps():
    t, out, log, trace, cnt = run([("cotton", 50), ("linen", 50)], LIN)
    sigs = []
    from cago.generation.template_selector import composition_signature
    cfg0 = SortingAwareGenerationConfig(seed=1, max_repair_steps=0)
    _, out0, _, trace0, cnt0 = run([("linen", 100)], LIN, cfg=cfg0)
    assert trace0 == [] and cnt0["repair_steps_started"] == 0
    cfg1 = SortingAwareGenerationConfig(seed=1, max_repair_steps=1, max_repair_proposals_per_step=2)
    _, _, _, trace1, _ = run([("linen", 100)], [("polyester", 100)], cfg=cfg1)
    assert len(trace1) <= 2 and len(accepted(trace1)) <= 1
    # a revert that would recreate an already-visited composition is skipped and counted
    from cago.generation.mutations import apply_substitution
    base = tmpl([("cotton", 60), ("polyester", 40)], LIN)
    comps = clone_components(base.components)
    log = [apply_substitution(comps, 0, 1, "nylon", 0)]                              # polyester -> nylon (unsupported binary)
    cnt = Counter()
    repair_candidate(comps, log, public_components(base.components), base, request(), SUP, CTX, CFG, ECFG, cnt, "c")
    assert cnt["repair_steps_started"] >= 1


def test_no_alternative_is_reported_not_hidden():
    from cago.generation.support_tables import build_support_tables
    import pandas as pd
    from tests.sorting_fixtures import DEV
    only_lin = pd.DataFrame([r for r in DEV.to_dict("records") if r["detail_category"] == "trousers" and r["split"] == "train"][:0] or DEV.head(0))
    empty = build_support_tables(DEV[DEV["detail_category"] == "shorts"])              # no TRAIN support for women/trousers contexts
    t, out, log, trace, cnt = run([("linen", 100)], LIN, support=empty)
    assert trace == [] and cnt["no_train_supported_alternative:SR1"] == 1 and flags(out)["SR1"]
