"""Compact audit of repair behaviour (trace aggregation, TRAIN-support checks, budget checks)."""
from __future__ import annotations

import json
from collections import Counter
from statistics import mean
from typing import Any

from cago.benchmark.statistics import describe
from cago.generation.support_tables import SupportTables
from cago.generation_sorting.oracle_view import RULES


def aggregate_traces(results: list[dict[str, Any]], support: SupportTables, cfg) -> dict[str, Any]:
    """Aggregate repair traces of several generated requests (each `res` from generate_sorting_aware)."""
    ops: dict[str, Counter] = {}
    rule_stats = {r: Counter() for r in RULES}
    rej = Counter()
    d_int, d_pl, dv = [], [], []
    leak_free = True
    n_traces = n_cands = n_with_repair = 0
    chain_ok = 0
    for res in results:
        for c in res["candidates"]:
            n_cands += 1
            tr = c["repair_trace"]
            n_with_repair += any(s["accepted"] for s in tr)
            for s in tr:
                n_traces += 1
                o = ops.setdefault(s["operation"], Counter())
                o["evaluated"] += 1
                o["accepted"] += bool(s["accepted"])
                o["claims_targeted_fix_confirmed"] += bool(s["claims_targeted_fix"])
                o["introduced_other_violation"] += bool(s["introduced_rules"])
                rr = rule_stats[s["targeted_rule"]]
                rr["evaluated"] += 1
                rr["accepted"] += bool(s["accepted"])
                rr["confirmed_fixed_targeted_rule"] += bool(s["claims_targeted_fix"])
                if not s["accepted"]:
                    rej[s["rejection_reason"]] += 1
                else:
                    if s["intent_delta"] is not None:
                        d_int.append(s["intent_delta"])
                    d_pl.append(s["plausibility_delta"])
                    dv.append(s["oracle_after"]["violation_count"] - s["oracle_before"]["violation_count"])
                cat, cls = c["detail_category"], s["component"]["class"]
                for (m, _), (m0, _) in zip(s["materials_after"], s["materials_before"]):
                    if m != m0 and s["operation"] != "revert_mutation_step" and m not in support.allowed(cat, cls):
                        leak_free = False
            if tr and all(isinstance(s["entries"], list) for s in tr):
                chain_ok += 1
    return {"candidates": n_cands, "candidates_with_accepted_repair": n_with_repair, "trace_steps": n_traces,
            "by_operation": {k: dict(v) for k, v in sorted(ops.items())}, "by_targeted_rule": {k: dict(v) for k, v in rule_stats.items() if v},
            "rejection_reasons": dict(rej), "accepted_repair_intent_delta": describe(d_int, 4), "accepted_repair_plausibility_delta": describe(d_pl, 4),
            "accepted_repair_violation_delta": describe(dv, 2),
            "all_proposed_repair_materials_train_supported": leak_free}


def render_generator_md(a: dict[str, Any]) -> str:
    L = ["# CAGO sorting-aware generator V1 - audit (development: TRAIN + VAL only)", "",
         "Terminology: Sorting Compatibility (SR1-SR5 rule satisfaction), Intent Alignment, Dataset-relative Plausibility; "
         "constraint-based probabilistic generation with sorting-aware proposal/repair. None of these is a recyclability, "
         "sustainability or manufacturability measure.", "",
         f"Working set splits: {a['development_splits']}; TEST rows present: {a['test_rows_in_working_set']}; support splits: {a['support_splits_used']}. "
         f"Requests audited: {a['n_requests']}. Config: `{json.dumps(a['config'])}`", "",
         f"Determinism (same seed, re-run identical): {a['determinism_identical']}. Budget respected: {a['budget_check']}", "",
         f"SR4 handling: {a['sr4_note']}", ""]
    for name, v in a["policies"].items():
        t = v["traces"]
        L += [f"## {name}", "", f"candidates {t['candidates']}; with accepted repair {t['candidates_with_accepted_repair']}; traced steps {t['trace_steps']}; "
              f"all proposed materials TRAIN-supported: {t['all_proposed_repair_materials_train_supported']}", "",
              "| operation | evaluated | accepted | confirmed targeted fix | introduced other violation |", "|---|---|---|---|---|"]
        L += [f"| {k} | {o['evaluated']} | {o['accepted']} | {o['claims_targeted_fix_confirmed']} | {o['introduced_other_violation']} |" for k, o in t["by_operation"].items()]
        L += ["", f"by targeted rule: {json.dumps(t['by_targeted_rule'])}", "", f"rejection reasons: {json.dumps(t['rejection_reasons'])}", "",
              f"accepted repair deltas - violations: {t['accepted_repair_violation_delta']}; intent: {t['accepted_repair_intent_delta']}; plausibility: {t['accepted_repair_plausibility_delta']}", "",
              f"search counters: {json.dumps(v['search_totals'])}", "", "### Example repair traces (entries omitted)", ""]
        for ex in v["examples"]:
            L.append(f"- `{ex['candidate_id']}`: " + "; ".join(
                f"[{s['step']}] {s['targeted_rule']}/{s['operation']} {'ACCEPT' if s['accepted'] else 'reject:' + str(s['rejection_reason'])} "
                f"vc {s['oracle_before']['violation_count']}->{s['oracle_after']['violation_count']} fixed={s['confirmed_fixed_rules']} introduced={s['introduced_rules']} "
                f"dIntent={s['intent_delta']} dPlaus={s['plausibility_delta']}" for s in ex["trace"][:4]))
        L.append("")
    return "\n".join(L)
