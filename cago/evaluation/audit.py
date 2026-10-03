"""Small candidate-evaluation audit (no candidate dumps)."""
from __future__ import annotations

from statistics import mean, median
from typing import Any

from cago.evaluation.candidate import RULES


def _dist(v: list[float]) -> dict[str, float | None]:
    if not v:
        return {"n": 0, "min": None, "median": None, "mean": None, "max": None}
    s = sorted(v)
    q = lambda p: s[min(len(s) - 1, int(p * (len(s) - 1) + 0.5))]
    return {"n": len(v), "min": round(s[0], 2), "p25": round(q(0.25), 2), "median": round(median(s), 2),
            "p75": round(q(0.75), 2), "mean": round(mean(s), 2), "max": round(s[-1], 2)}


def _sr_rates(evals: list[dict[str, Any]]) -> dict[str, float | None]:
    out = {r[:3].upper(): (round(100 * sum(bool(e["sorting"]["oracle"][r]) for e in evals) / len(evals), 2) if evals else None) for r in RULES}
    out["ANY"] = round(100 * sum(e["sorting"]["violation_count"] > 0 for e in evals) / len(evals), 2) if evals else None
    out["mean_violation_count"] = round(mean(e["sorting"]["violation_count"] for e in evals), 3) if evals else None
    return out


def audit_request(r: dict[str, Any], rerun_digest: str, drop_threshold: float) -> dict[str, Any]:
    req, ev, gen = r["request"], r["evaluation"], r["generation"]
    valid, tmpl = ev["valid"], ev["templates"]
    emap = {e["candidate_id"]: e for e in valid}
    front = [e for e in valid if e["is_pareto"]]
    selected = [emap[s["candidate_id"]] for s in r["selection"]["selections"]]
    used_templates = [tmpl[t.garment_id] for t in gen["templates"]]

    def vs_template(e):
        t = tmpl[e["template_garment_id"]]
        di = None if e["intent_alignment_raw"] is None or t["intent_alignment_raw"] is None else e["intent_alignment_raw"] - t["intent_alignment_raw"]
        dv = e["sorting"]["violation_count"] - t["sorting"]["violation_count"]
        dp = e["plausibility_raw"] - t["plausibility_raw"]
        return dv, di, dp

    def flags(pool):
        res = {"sorting_improves_intent_decreases": [], "intent_improves_sorting_worsens": [], "plausibility_falls_substantially": []}
        for e in pool:
            dv, di, dp = vs_template(e)
            if dv < 0 and di is not None and di < 0:
                res["sorting_improves_intent_decreases"].append(e["candidate_id"])
            if di is not None and di > 0 and dv > 0:
                res["intent_improves_sorting_worsens"].append(e["candidate_id"])
            if dp < -drop_threshold:
                res["plausibility_falls_substantially"].append(e["candidate_id"])
        return res

    fl_front, fl_sel = flags(front), flags(selected)
    unscorable = {}
    for e in valid:
        for u in e["intent"]["unscorable_preferences"]:
            unscorable.setdefault(f"{u['preference']}:{u['reason']}", 0)
            unscorable[f"{u['preference']}:{u['reason']}"] += 1
    active = sorted({p["preference"] for e in valid[:1] for p in e["intent"]["preferences"]})
    return {
        "request": {k: req[k] for k in ("target_segment", "detail_category", "hard_constraints", "soft_preferences", "warnings")},
        "generated": len(gen["candidates"]), "hard_valid": len(valid), "hard_excluded": ev["excluded"],
        "templates_used": len(gen["templates"]), "active_preferences": active,
        "unscorable_preferences": unscorable,
        "intent_0_100": _dist([100 * e["intent_alignment_raw"] for e in valid if e["intent_alignment_raw"] is not None]),
        "candidates_without_intent_score": sum(e["intent_alignment_raw"] is None for e in valid),
        "violation_count_distribution": {str(k): sum(e["sorting"]["violation_count"] == k for e in valid) for k in range(6)},
        "plausibility_0_100": _dist([100 * e["plausibility_raw"] for e in valid]),
        "pareto": {**r["pareto"], "front_ids": sorted(e["candidate_id"] for e in front)},
        "selections": [{"candidate_id": s["candidate_id"], "roles": s["roles"], "balanced_distance": s["balanced_distance"],
                        "template_garment_id": emap[s["candidate_id"]]["template_garment_id"],
                        "violation_count": emap[s["candidate_id"]]["sorting"]["violation_count"],
                        "sorting_compatibility_index_0_100": emap[s["candidate_id"]]["sorting"]["sorting_compatibility_index_0_100"],
                        "intent_0_100": None if emap[s["candidate_id"]]["intent_alignment_raw"] is None
                        else round(100 * emap[s["candidate_id"]]["intent_alignment_raw"], 2),
                        "plausibility_0_100": round(100 * emap[s["candidate_id"]]["plausibility_raw"], 2)} for s in r["selection"]["selections"]],
        "selection_notes": {"intent_focused_omitted": r["selection"].get("intent_focused_omitted"),
                            "multiple_roles_same_candidate": r["selection"].get("multiple_roles_same_candidate")},
        "sr_rates_pct": {"templates": _sr_rates(used_templates), "all_hard_valid_candidates": _sr_rates(valid),
                         "pareto_front": _sr_rates(front), "selected_designs": _sr_rates(selected)},
        "tradeoff_flags": {"pareto_front": {k: len(v) for k, v in fl_front.items()},
                           "selected": fl_sel, "front_size_is_one": len(front) == 1,
                           "plausibility_drop_threshold_pts": round(100 * drop_threshold, 1)},
        "deterministic_rerun_digest_equal": rerun_digest == r["digest"],
        "explanations": r["explanations"],
    }


def render_md(a: dict[str, Any]) -> str:
    L = ["# CAGO candidate evaluation + Pareto selection v1 - audit", "",
         "Indices: Intent = confidence-weighted preference alignment; Sorting = SR1-SR5 violation count (equal-weight rule-satisfaction "
         "index is reporting only); Plausibility = dataset-relative support/similarity (TRAIN only). None is a recyclability, "
         "sustainability or manufacturability measure.", "",
         f"Support tables: splits_used={a['support_splits_used']}; seed={a['seed']}.", "",
         "| request | generated | hard-valid | front | intent min/med/max | viol dist (0..5) | plaus med | deterministic |",
         "|---|---|---|---|---|---|---|---|"]
    for r in a["requests"]:
        q, i = r["request"], r["intent_0_100"]
        L.append(f"| {q['target_segment']}/{q['detail_category']} | {r['generated']} | {r['hard_valid']} | {r['pareto']['front_size']} "
                 f"({','.join(r['pareto']['dimensions'])}) | {i['min']}/{i['median']}/{i['max']} | "
                 f"{list(r['violation_count_distribution'].values())} | {r['plausibility_0_100']['median']} | {r['deterministic_rerun_digest_equal']} |")
    for r in a["requests"]:
        q = r["request"]
        L += ["", f"## {q['target_segment']} / {q['detail_category']}", "",
              f"hard: {q['hard_constraints']}; soft: { {k: v for k, v in q['soft_preferences'].items() if v is not None} }; "
              f"unscorable: {r['unscorable_preferences']}", "",
              "| role(s) | candidate | viol | sorting idx | intent | plausibility |", "|---|---|---|---|---|---|"]
        for s in r["selections"]:
            L.append(f"| {'+'.join(s['roles'])} | {s['candidate_id']} | {s['violation_count']} | {s['sorting_compatibility_index_0_100']} | "
                     f"{s['intent_0_100']} | {s['plausibility_0_100']} |")
        L += ["", f"SR rates % (templates / valid / front / selected): " + " / ".join(
            str({k: v for k, v in r['sr_rates_pct'][n].items() if k in ('SR1', 'SR2', 'SR3', 'SR4', 'SR5', 'ANY')})
            for n in ("templates", "all_hard_valid_candidates", "pareto_front", "selected_designs")), "",
              f"trade-off flags: {r['tradeoff_flags']}", ""]
        for e in r["explanations"]:
            L.append(f"**{'+'.join(e['roles'])}** `{e['candidate_id']}` (template `{e['template_garment_id']}`)")
            L += [f"- {s}" for s in e["statements"][:6]] + [f"- {t}" for t in e["trade_offs"]]
            L += [f"- mutation: {m['description']}" for m in e["mutations"][:4]]
            L.append("")
    L += ["## Edge cases", ""] + [f"- {x}" for x in a["edge_cases"]] + [""]
    return "\n".join(L)
