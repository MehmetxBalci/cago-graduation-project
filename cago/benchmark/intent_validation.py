"""Controlled-experiment validation of Intent Alignment scoring BEHAVIOUR (direction, exactness, isolation).
This validates the scoring function, not measured garment performance."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Callable

from cago.benchmark.perturbations import EvalGarment, public
from cago.config.fit_length_v1 import FIT_LABELS_V1, LENGTH_LABELS_V1
from cago.evaluation.config import EvaluationConfig
from cago.evaluation.intent import evaluate_intent
from cago.preprocessing.ids import stable_hash
from cago.requirements.properties import build_profile, stretch_bucket

EPS = 1e-9
INDEPENDENT = ("colour", "fit", "length_cut")
FUNCTIONAL_ALL = {"thermal_warmth": "heavy", "breathability": "high", "durability_wear": "reinforced",
                  "moisture_wicking": True, "water_repellent": True, "stretch": "low"}
CFG = EvaluationConfig()


@dataclass
class Case:
    soft: dict[str, Any]
    components: list[dict[str, Any]]
    colour: str | None
    fit_label: str | None = None
    length_label: str | None = None
    text_tags: tuple[str, ...] = ()
    meta: dict[str, Any] = field(default_factory=dict)


def sats(c: Case, cfg: EvaluationConfig = CFG) -> dict[str, float | None]:
    r = evaluate_intent(c.soft, c.components, c.colour, c.fit_label, c.length_label, c.text_tags, cfg)
    return {p["preference"]: p["satisfaction_0_1"] for p in r["preferences"]}


def direction(a: float | None, b: float | None) -> str:
    if a is None or b is None:
        return "unscorable"
    return "increase" if b > a + EPS else "decrease" if b < a - EPS else "unchanged"


def primary_index(components) -> int:
    return next((i for i, c in enumerate(components) if c["component_class"] == "surface_component"), 0)


def base_case(g: EvalGarment, include=("colour", "fit", "length_cut"), extra: dict | None = None) -> Case:
    soft: dict[str, Any] = {}
    if "colour" in include and g.colour:
        soft["colour"] = g.colour
    if "fit" in include and g.fit_label:
        soft["fit"] = g.fit_label
    if "length_cut" in include and g.length_label:
        soft["length_cut"] = g.length_label
    soft.update(extra or {})
    return Case(soft, public(g.components), g.colour, g.fit_label, g.length_label, g.text_tags)


def with_(c: Case, **kw) -> Case:
    d = copy.deepcopy(c)
    for k, v in kw.items():
        setattr(d, k, v)
    return d


# ---------------------------------------------------------------- variants
def shift_material(c: Case, frm: str, to: str) -> Case | None:
    comps = copy.deepcopy(c.components)
    p = comps[primary_index(comps)]
    if any(m["material"] == to for m in p["materials"]):
        return None
    slot = next((m for m in p["materials"] if m["material"] == frm), None)
    if slot is None:
        return None
    slot["material"] = to
    return with_(c, components=comps)


def add_text(c: Case, tag: str) -> Case | None:
    """Add a text-evidence tag; None when the garment already carries it (nothing would change)."""
    return None if tag in c.text_tags else with_(c, text_tags=tuple(sorted(set(c.text_tags) | {tag})))


def add_component(c: Case, name: str, cls: str, material: str) -> Case:
    comps = copy.deepcopy(c.components)
    comps.append({"component_id": f"synthetic_{name}", "source_component_index": len(comps), "component_class": cls,
                  "component_name_normalized": name, "materials": [{"material": material, "pct": 100.0}]})
    return with_(c, components=comps)


def has_component(c: Case, name: str) -> bool:
    """Evidence already present? coating -> coating component; padding -> any filling component."""
    prof = build_profile(c.components)
    return prof.coating_present if name == "coating" else prof.filling_present if name == "padding" else \
        any(x["component_name_normalized"] == name for x in c.components)


# ---------------------------------------------------------------- generic comparison
def compare(name: str, gid: str, base: Case, var: Case, target: str, expected: str, coupling: bool = False) -> dict[str, Any]:
    sb, sv = sats(base), sats(var)
    t0, t1 = sb.get(target), sv.get(target)
    obs = direction(t0, t1)
    changed = {p: [sb[p], sv.get(p)] for p in sb if direction(sb[p], sv.get(p)) not in ("unchanged",)}
    rec = {"experiment": name, "garment_id": gid, "target": target, "expected": expected, "observed": obs,
           "passed": obs == expected, "target_before": t0, "target_after": t1,
           "affected": sorted(changed), "unintended": sorted(p for p in changed if p != target)}
    if coupling:
        b6, v6 = with_(base, soft={**base.soft, **FUNCTIONAL_ALL}), with_(var, soft={**var.soft, **FUNCTIONAL_ALL})
        s6b, s6v = sats(b6), sats(v6)
        rec["coupled_functional_changes"] = sorted(p for p in FUNCTIONAL_ALL if p != target and p in s6b
                                                   and direction(s6b[p], s6v.get(p)) not in ("unchanged", "unscorable"))
    return rec


def exact_check(name: str, gid: str, case: Case, target: str, expected: float | None) -> dict[str, Any]:
    got = sats(case).get(target)
    ok = (got is None and expected is None) or (got is not None and expected is not None and abs(got - expected) <= EPS)
    return {"experiment": name, "garment_id": gid, "target": target, "expected": expected, "observed": got, "passed": ok,
            "target_before": None, "target_after": got, "affected": [], "unintended": []}


def _pick(seq: list, seed: str):
    return seq[int(stable_hash(seed, length=8), 16) % len(seq)] if seq else None


def _other(label: str, labels: tuple[str, ...], gid: str) -> str:
    return _pick([l for l in labels if l != label], gid + label)


# ---------------------------------------------------------------- experiment families
def stretch_threshold_checks() -> list[dict[str, Any]]:
    recs = []
    table = {"none": lambda e: e <= 1e-9, "low": lambda e: 1e-9 < e <= 2.0, "high": lambda e: e > 2.0}
    for e in (0.0, 0.5, 2.0, 2.01, 5.0):
        comps = [{"component_id": "s", "source_component_index": 0, "component_class": "surface_component",
                  "component_name_normalized": "shell", "materials": [{"material": "cotton", "pct": 100.0 - e}] +
                  ([{"material": "elastane", "pct": e}] if e else [])}]
        for want, rule in table.items():
            case = Case({"stretch": want, "colour": "black", "preferred_dominant_material": "cotton"}, comps, "black")
            r = exact_check(f"stretch_threshold(elastane={e:g}%,request={want})", "synthetic", case, "stretch", 1.0 if rule(e) else 0.0)
            ind = sats(case)
            r["unintended"] = [p for p in ("colour", "preferred_dominant_material") if ind[p] != 1.0]
            recs.append(r)
    return recs


def dominant_experiments(gs: list[EvalGarment], vocab: list[str]) -> list[dict[str, Any]]:
    recs = []
    for g in gs:
        prof = build_profile(public(g.components), g.colour)
        D = prof.dominant
        if not D:
            continue
        stretch = {"stretch": stretch_bucket(prof.elastane_pct)}
        base = base_case(g, extra={"preferred_dominant_material": D, **stretch})
        recs.append(exact_check("dominant_material_original_matches", g.garment_id, base, "preferred_dominant_material", 1.0))
        pi = primary_index(base.components)
        pm = base.components[pi]["materials"]
        if D != "elastane":
            repl = _pick([m for m in vocab if m not in prof.primary_shares and m != "elastane"], g.garment_id + "dom")
            if repl:
                comps = copy.deepcopy(base.components)
                slot = next(m for m in comps[pi]["materials"] if m["material"] == D)
                slot["material"] = repl
                recs.append(compare("dominant_substitution", g.garment_id, base, with_(base, components=comps),
                                    "preferred_dominant_material", "decrease"))
        order = sorted(range(len(pm)), key=lambda i: (-pm[i]["pct"], pm[i]["material"]))
        distinct = len({m["material"] for m in pm}) == len(pm)       # duplicate names are aggregated by the metric
        if distinct and len(pm) >= 2 and pm[order[0]]["pct"] - pm[order[1]]["pct"] >= 1.0 and "elastane" not in (pm[order[0]]["material"], pm[order[1]]["material"]):
            comps = copy.deepcopy(base.components)
            a, b = comps[pi]["materials"][order[0]], comps[pi]["materials"][order[1]]
            a["pct"], b["pct"] = b["pct"], a["pct"]
            recs.append(compare("dominant_percentage_swap", g.garment_id, base, with_(base, components=comps),
                                "preferred_dominant_material", "decrease"))
    return recs


def stretch_real_experiments(gs: list[EvalGarment]) -> list[dict[str, Any]]:
    recs = []
    for g in gs:
        prof = build_profile(public(g.components), g.colour)
        base = base_case(g, extra={"stretch": stretch_bucket(prof.elastane_pct)})
        recs.append(exact_check("stretch_original_bucket_matches", g.garment_id, base, "stretch", 1.0))
        pm = base.components[primary_index(base.components)]["materials"]
        el = next((m for m in pm if m["material"] == "elastane"), None)
        dom = max(pm, key=lambda m: m["pct"])
        if el and 0 < el["pct"] <= 2.0 and dom["material"] != "elastane" and dom["pct"] - 3.0 > 10:
            comps = copy.deepcopy(base.components)
            pmv = comps[primary_index(comps)]["materials"]
            next(m for m in pmv if m["material"] == "elastane")["pct"] += 3.0
            next(m for m in pmv if m["material"] == dom["material"])["pct"] -= 3.0
            recs.append(compare("elastane_shift_low_to_high", g.garment_id, base, with_(base, components=comps), "stretch", "decrease"))
    return recs


def label_experiments(gs: list[EvalGarment]) -> list[dict[str, Any]]:
    recs = []
    for g in gs:
        for pref, label, src, labels, kw in (("fit", g.fit_label, g.fit_source, FIT_LABELS_V1, "fit_label"),
                                             ("length_cut", g.length_label, g.length_source, LENGTH_LABELS_V1, "length_label")):
            name = "fit" if pref == "fit" else "length"
            if label is None:
                case = Case({pref: labels[0]}, public(g.components), g.colour, g.fit_label, g.length_label)
                recs.append(exact_check(f"{name}_unlabeled_is_unscorable_not_zero", g.garment_id, case, pref, None))
                continue
            if src != "structured":
                continue
            match = base_case(g, extra={"preferred_dominant_material": build_profile(public(g.components)).dominant})
            match.soft[pref] = label
            recs.append(exact_check(f"{name}_exact_match", g.garment_id, match, pref, 1.0))
            mismatch = with_(match, soft={**match.soft, pref: _other(label, labels, g.garment_id)})
            recs.append(compare(f"{name}_mismatch_supported_label", g.garment_id, match, mismatch, pref, "decrease"))
    return recs


def colour_experiments(gs: list[EvalGarment]) -> list[dict[str, Any]]:
    recs = []
    colours = sorted({g.colour for g in gs if g.colour})
    for g in gs:
        if not g.colour:
            continue
        prof = build_profile(public(g.components), g.colour)
        base = base_case(g, extra={"preferred_dominant_material": prof.dominant, "stretch": stretch_bucket(prof.elastane_pct)})
        recs.append(exact_check("colour_exact_match", g.garment_id, base, "colour", 1.0))
        other = _pick([c for c in colours if c != g.colour], g.garment_id + "col")
        if other:
            recs.append(compare("colour_changed", g.garment_id, base, with_(base, colour=other), "colour", "decrease"))
    return recs


def functional_experiments(gs: list[EvalGarment]) -> list[dict[str, Any]]:
    """Controlled evidence addition/removal. pre(sat) keeps headroom so a strict direction is testable."""
    recs = []
    specs: list[tuple[str, str, Any, str, Callable[[Case], Case | None], Callable[[float | None], bool], bool]] = [
        # name, pref, value, expected, variant(base)->variant, pre(base_sat), reverse
        ("water_text_evidence_added", "water_repellent", True, "increase", lambda c: add_text(c, "water_resistant"), lambda s: s is not None and s <= 0.7, False),
        ("water_coating_added", "water_repellent", True, "increase", lambda c: None if has_component(c, "coating") else add_component(c, "coating", "surface_component", "polyurethane"), lambda s: s is not None and s <= 0.7, False),
        ("water_coating_removed", "water_repellent", True, "decrease", lambda c: None if has_component(c, "coating") else add_component(c, "coating", "surface_component", "polyurethane"), lambda s: True, True),
        ("moisture_cotton_to_polyester", "moisture_wicking", True, "increase", lambda c: shift_material(c, "cotton", "polyester"), lambda s: s is not None and s <= 0.9, False),
        ("moisture_polyester_to_cotton", "moisture_wicking", True, "decrease", lambda c: shift_material(c, "polyester", "cotton"), lambda s: s is not None and s >= 0.1, False),
        ("moisture_text_quick_dry_added", "moisture_wicking", True, "increase", lambda c: add_text(c, "quick_dry"), lambda s: s is not None and s <= 0.8, False),
        ("thermal_heavy_cotton_to_wool", "thermal_warmth", "heavy", "increase", lambda c: shift_material(c, "cotton", "wool"), lambda s: s is not None and s <= 0.8, False),
        ("thermal_light_wool_to_cotton", "thermal_warmth", "light", "increase", lambda c: shift_material(c, "wool", "cotton"), lambda s: s is not None and s <= 0.9, False),
        ("thermal_heavy_filling_added", "thermal_warmth", "heavy", "increase", lambda c: None if has_component(c, "padding") else add_component(c, "padding", "filling_component", "polyester"), lambda s: s is not None and s <= 0.8, False),
        ("thermal_light_filling_added", "thermal_warmth", "light", "decrease", lambda c: None if has_component(c, "padding") else add_component(c, "padding", "filling_component", "polyester"), lambda s: s is not None and s >= 0.2, False),
        ("breathability_polyester_to_cotton", "breathability", "high", "increase", lambda c: shift_material(c, "polyester", "cotton"), lambda s: s is not None and s <= 0.9, False),
        ("breathability_coating_added", "breathability", "high", "decrease", lambda c: None if has_component(c, "coating") else add_component(c, "coating", "surface_component", "polyurethane"), lambda s: s is not None and s >= 0.3, False),
        ("breathability_filling_added", "breathability", "high", "decrease", lambda c: None if has_component(c, "padding") else add_component(c, "padding", "filling_component", "polyester"), lambda s: s is not None and s >= 0.3, False),
        ("durability_cotton_to_nylon", "durability_wear", "reinforced", "increase", lambda c: shift_material(c, "cotton", "nylon"), lambda s: s is not None and s <= 0.9, False),
        ("durability_text_ripstop_added", "durability_wear", "reinforced", "increase", lambda c: add_text(c, "ripstop"), lambda s: s is not None and s <= 0.8, False),
    ]
    for g in gs:
        for name, pref, value, expected, make, pre, reverse in specs:
            base = base_case(g, extra={pref: value})
            var = make(base)
            if var is None:
                continue
            if reverse:                                  # evidence REMOVAL: start from the garment WITH the evidence
                base, var = var, base
                # headroom is required on the state WITHOUT the added evidence (the proxy saturates at 1)
                if not (lambda s: s is not None and s <= 0.7)(sats(var).get(pref)):
                    continue
            elif not pre(sats(base).get(pref)):
                continue
            recs.append(compare(name, g.garment_id, base, var, pref, expected, coupling=True))
    return recs


def isolation_experiment_names() -> set[str]:
    return {"colour_changed", "fit_mismatch_supported_label", "length_mismatch_supported_label", "dominant_substitution",
            "dominant_percentage_swap", "elastane_shift_low_to_high"}


def summarize(records: list[dict[str, Any]], max_failures: int = 3) -> dict[str, Any]:
    by: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        by.setdefault(r["experiment"].split("(")[0] if r["experiment"].startswith("stretch_threshold") else r["experiment"], []).append(r)
    out = {}
    for name, rs in sorted(by.items()):
        obs: dict[str, int] = {}
        aff: dict[str, int] = {}
        unint: dict[str, int] = {}
        coupled: dict[str, int] = {}
        for r in rs:
            obs[str(r["observed"])] = obs.get(str(r["observed"]), 0) + 1
            for p in r["affected"]:
                aff[p] = aff.get(p, 0) + 1
            for p in r["unintended"]:
                unint[p] = unint.get(p, 0) + 1
            for p in r.get("coupled_functional_changes", []):
                coupled[p] = coupled.get(p, 0) + 1
        n_unint = sum(bool(r["unintended"]) for r in rs)
        out[name] = {"n_cases": len(rs), "expected": rs[0]["expected"] if not name.startswith("stretch_threshold") else "exact table value",
                     "observed_counts": obs, "pass_rate": round(sum(r["passed"] for r in rs) / len(rs), 4),
                     "status": "PASS" if all(r["passed"] for r in rs) else "FAIL", "affected_subcomponents": aff,
                     "unintended_changes": unint, "cases_with_unintended_change": n_unint,
                     "isolation_accuracy": round(1 - n_unint / len(rs), 4), "coupled_functional_changes": coupled,
                     "failures": [{"garment_id": r["garment_id"], "experiment": r["experiment"], "expected": r["expected"],
                                   "observed": r["observed"]} for r in rs if not r["passed"]][:max_failures]}
    iso = [r for r in records if r["experiment"] in isolation_experiment_names()]
    out["_isolation_overall"] = {"experiments": sorted(isolation_experiment_names()), "n_cases": len(iso),
                                 "isolation_accuracy": round(sum(not r["unintended"] for r in iso) / len(iso), 4) if iso else None,
                                 "intended_direction_and_isolated": round(sum(r["passed"] and not r["unintended"] for r in iso) / len(iso), 4) if iso else None}
    return out


def run_intent_validation(gs: list[EvalGarment], vocab: list[str]) -> dict[str, Any]:
    recs = (stretch_threshold_checks() + dominant_experiments(gs, vocab) + stretch_real_experiments(gs) + label_experiments(gs)
            + colour_experiments(gs) + functional_experiments(gs))
    summ = summarize(recs)
    exps = [v for k, v in summ.items() if not k.startswith("_")]
    return {"n_garments": len(gs), "n_cases": len(recs), "experiments": summ,
            "overall": {"experiments": len(exps), "experiments_passing": sum(e["status"] == "PASS" for e in exps),
                        "case_pass_rate": round(sum(r["passed"] for r in recs) / len(recs), 4)},
            "note": "validates scoring behaviour on controlled manipulations; not measured garment performance"}
