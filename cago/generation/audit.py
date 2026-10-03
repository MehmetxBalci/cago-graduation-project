"""Small baseline audit (no huge candidate dumps)."""
from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any

from cago.generation.baseline import candidates_hash, oracle_eval, public_components
from cago.generation.support_tables import SPECIAL_TOKENS, SupportTables
from cago.generation.template_selector import Template

RULES = ("sr1_violation", "sr2_violation", "sr3_violation", "sr4_violation", "sr5_violation", "any_violation")


def _rates(rows: list[dict[str, Any]]) -> dict[str, float | None]:
    return {r: (round(100 * sum(bool(x[r]) for x in rows) / len(rows), 2) if rows else None) for r in RULES}


def _stat(v: list[float]) -> dict[str, float | None]:
    return {"mean": round(mean(v), 4), "min": round(min(v), 4), "max": round(max(v), 4)} if v else {"mean": None, "min": None, "max": None}


def audit_request(res: dict[str, Any], rerun_hash: str | None = None, n_examples: int = 2) -> dict[str, Any]:
    cands: list[dict[str, Any]] = res["candidates"]
    templates: list[Template] = res["templates"]
    tmap = {t.garment_id: t for t in templates}
    forbidden = set(res["request"]["hard_constraints"]["forbidden_materials"])
    t_or = [oracle_eval(t.garment_id, t.colour, public_components(t.components)) for t in templates]
    mats = [m["material"] for c in cands for comp in c["components"] for m in comp["materials"]]
    sums_ok = all(abs(sum(m["pct"] for m in comp["materials"]) - 100) <= 1e-6 for c in cands for comp in c["components"])
    nonneg = all(m["pct"] >= 0 for c in cands for comp in c["components"] for m in comp["materials"])
    changed = Counter()
    by_id = {t.garment_id: oracle for t, oracle in zip(templates, t_or)}
    for c in cands:
        for r in RULES[:-1]:
            changed[r] += c["oracle"][r] != by_id[c["template_garment_id"]][r]
    d = [c["template_distance"] for c in cands]
    return {
        "request": {k: res["request"][k] for k in ("target_segment", "detail_category", "hard_constraints",
                                                    "soft_preferences", "warnings")},
        "request_key": res["request_key"], "template_pool": res["template_pool"],
        "templates_selected": [{"garment_id": t.garment_id, "parent_product_id": t.parent_product_id,
                                "n_forbidden_slots": t.n_forbidden_slots, "rank_score_diagnostic": round(t.rank_score, 4)}
                               for t in templates],
        "generation": {"candidates_requested": res["config"]["n_templates"] * res["config"]["mutations_per_template"],
                       "candidates_generated": len(cands), "attempts": res["attempts"], "rejected": res["rejected"],
                       "failed_templates_unrepairable": res["failed_templates"],
                       "mutation_types": dict(Counter(e["type"] for c in cands for e in c["mutation_log"])),
                       "forbidden_repairs": sum(c["n_forbidden_repairs"] for c in cands),
                       "mean_mutations_per_candidate": round(mean([c["n_mutations"] for c in cands]), 3) if cands else None},
        "hard_constraints": {
            "all_candidates_passed_validation": all(c["hard_validation"]["passed"] for c in cands),
            "forbidden_material_occurrences": sum(m in forbidden for m in mats),
            "pad_or_other_occurrences": sum(str(m).casefold() in SPECIAL_TOKENS for m in mats),
            "all_component_sums_100_within_1e-6": sums_ok, "all_percentages_non_negative": nonneg,
            "all_templates_from_train": all(t.split == "train" for t in templates)},
        "template_distance_diagnostic": {
            "diagnostic_distance": _stat([x["diagnostic_distance"] for x in d]),
            "n_substitutions": _stat([x["n_substitutions"] for x in d]),
            "abs_pct_change_total": _stat([x["abs_pct_change_total"] for x in d]),
            "note": "diagnostic only; not a plausibility score"},
        "oracle_sr1_sr5": {"template_rates_pct": _rates(t_or), "candidate_rates_pct": _rates([c["oracle"] for c in cands]),
                           "candidates_whose_flag_differs_from_template": dict(changed)},
        "property_proxies_diagnostic": {
            "candidate_diagnostic_mean_score": _stat([c["property_proxies"]["diagnostic_mean_score"] for c in cands
                                                      if c["property_proxies"]["diagnostic_mean_score"] is not None]),
            "note": "diagnostic only; not the Intent Alignment Score"},
        "deterministic_rerun_hash_equal": None if rerun_hash is None else rerun_hash == candidates_hash(cands),
        "examples": [{"candidate_id": c["candidate_id"], "template_garment_id": c["template_garment_id"],
                      "mutation_log": c["mutation_log"], "template_distance": {k: c["template_distance"][k] for k in
                                                                               ("n_substitutions", "abs_pct_change_total", "diagnostic_distance")},
                      "oracle_any_violation": c["oracle"]["any_violation"],
                      "components": [{"name": comp["component_name_normalized"],
                                      "materials": [(m["material"], m["pct"]) for m in comp["materials"]]}
                                     for comp in c["components"]]} for c in cands[:n_examples]],
    }


def render_markdown(a: dict[str, Any]) -> str:
    L = ["# CAGO template baseline generator v1 - audit", "",
         f"Seed {a['config']['seed']}; templates/request {a['config']['n_templates']}; candidates/template "
         f"{a['config']['mutations_per_template']}; mutations/candidate {a['config']['min_mutations']}-{a['config']['max_mutations']}.", "",
         "Support tables (TRAIN only): " + str(a["support_tables"]), "",
         f"Leakage: templates from non-train splits = {a['leakage']['templates_not_from_train']}; "
         f"support splits_used = {a['support_tables']['splits_used']}.", "",
         "| request | eligible tmpl | selected | candidates | forbidden occ. | PAD/OTHER occ. | sums 100 | mean dist | ANY tmpl% | ANY cand% | deterministic |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in a["requests"]:
        q, g, h = r["request"], r["generation"], r["hard_constraints"]
        L.append(f"| {q['target_segment']}/{q['detail_category']} | {r['template_pool']['eligible_templates']} | "
                 f"{r['template_pool']['selected']} | {g['candidates_generated']}/{g['candidates_requested']} | "
                 f"{h['forbidden_material_occurrences']} | {h['pad_or_other_occurrences']} | "
                 f"{h['all_component_sums_100_within_1e-6']} | {r['template_distance_diagnostic']['diagnostic_distance']['mean']} | "
                 f"{r['oracle_sr1_sr5']['template_rates_pct']['any_violation']} | "
                 f"{r['oracle_sr1_sr5']['candidate_rates_pct']['any_violation']} | {r['deterministic_rerun_hash_equal']} |")
    for r in a["requests"]:
        q = r["request"]
        L += ["", f"## {q['target_segment']} / {q['detail_category']}", "",
              f"hard: {q['hard_constraints']}; soft (non-null): { {k: v for k, v in q['soft_preferences'].items() if v is not None} }; "
              f"warnings: {[w['code'] for w in q['warnings']]}", "",
              f"pool: {r['template_pool']}", "", f"generation: {r['generation']}", "",
              f"oracle: {r['oracle_sr1_sr5']}", ""]
        for e in r["examples"]:
            L.append(f"- `{e['candidate_id']}` from `{e['template_garment_id']}` dist={e['template_distance']} "
                     f"log={[(x['type'], x['reason'], x['from_material'], x['to_material']) for x in e['mutation_log']]}")
    L += ["", "## Edge cases", ""] + [f"- {e}" for e in a["edge_cases"]] + [""]
    return "\n".join(L)
