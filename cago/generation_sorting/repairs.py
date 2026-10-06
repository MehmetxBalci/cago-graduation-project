"""Rule-targeted repair proposals (SR1, SR2, SR3, SR5) built from the Oracle's own explanations.

Every material proposed comes from TRAIN support tables (same detail_category + component class), respects the TRAIN
percentage maximum for that material in that context and yields a material COMBINATION that was observed in TRAIN
(no fabricated combinations). Operations only change material identities / percentages inside existing components
(topology, component names, classes, slot count, colour and labels are preserved). SR4 is immutable (colour is not mutated).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from cago.generation.mutations import apply_percentage, apply_substitution, clone_components
from cago.generation.support_tables import SPECIAL_TOKENS, SupportTables
from cago.generation.template_selector import composition_signature
from cago.generation_sorting.config import SortingAwareGenerationConfig
from cago.generation_sorting.oracle_view import RULES, analyze, reason_for
from cago.oracle.config import SR1_BINARY, canon_material
from cago.oracle.rules import sorted_materials
from cago.preprocessing.ids import stable_hash

EPS = 1e-9


def _r9(x: float) -> float:
    return round(x, 9)


@dataclass
class RepairProposal:
    rule: str                       # rule that generated the proposal (first violated allowed rule for generic operations)
    operation: str
    component_index: int
    ops: list[tuple]                # ("sub", ci, slot, material) | ("pct", ci, from_slot, to_slot, delta)
    weight: float = 1.0
    new_components: list[dict[str, Any]] | None = None
    entries: list[dict[str, Any]] = field(default_factory=list)
    analysis_after: dict[str, Any] | None = None
    predicted_fixed: tuple[str, ...] = ()
    predicted_introduced: tuple[str, ...] = ()


def apply_ops(components, ops: list[tuple], step0: int, rule: str):
    """Apply primitive ops to a clone; returns (new_components, replayable log entries)."""
    comps = clone_components(components)
    entries = []
    for k, op in enumerate(ops):
        if op[0] == "sub":
            entries.append(apply_substitution(comps, op[1], op[2], op[3], step0 + k, f"sorting_repair:{rule}"))
        else:
            e = apply_percentage(comps, op[1], op[2], op[3], op[4], step0 + k)
            e["reason"] = f"sorting_repair:{rule}"
            entries.append(e)
    return comps, entries


def slot_substitutions(comp: dict[str, Any], si: int, category: str, support: SupportTables, forbidden,
                       require_observed_combo: bool = True) -> list[tuple[str, float]]:
    """TRAIN-supported replacements for one slot: [(material, weight)]. Present materials are allowed (merging into an
    existing fibre); the resulting distinct-material combination must have been observed in TRAIN."""
    cls, cur = comp["component_class"], comp["materials"][si]
    out = []
    for r in support.allowed(category, cls):
        if r == cur["material"] or r in forbidden or r.casefold() in SPECIAL_TOKENS:
            continue
        bound = support.pct_max(category, cls, r)
        if bound is None or cur["pct"] > bound + EPS:
            continue
        combo = {m["material"] for k, m in enumerate(comp["materials"]) if k != si} | {r}
        n_combo = support.combo_count(category, cls, combo)
        if require_observed_combo and n_combo == 0:
            continue
        out.append((r, math.sqrt(support.count(category, cls, r)) * (1.0 + math.log1p(n_combo))))
    return out


def _canons(comp) -> list[str | None]:
    return [canon_material(m["material"]) for m in comp["materials"]]


def _merge_ops(comps, ci, slots_by_fibre, category, support, forbidden, rule, operation, only_minor_below=None, a=None):
    """Replace a single-slot fibre by a material already present in the component (the Oracle aggregates duplicates,
    so the distinct fibre count drops by one)."""
    comp, out = comps[ci], []
    present = {m["material"] for m in comp["materials"]}
    for fibre, slots in slots_by_fibre:
        if len(slots) != 1:
            continue
        si = slots[0]
        for r, w in slot_substitutions(comp, si, category, support, forbidden):
            if r in present and canon_material(r) != fibre:
                out.append(RepairProposal(rule, operation, ci, [("sub", ci, si, r)], w))
    return out


def sr3_ops(comps, a, category, support, forbidden, cfg) -> list[RepairProposal]:
    ri = a["readable_index"]
    comp, mats, out = comps[ri], comps[ri]["materials"], []
    canons = _canons(comp)
    dom_canon = sorted_materials(a["readable"])[0][0]
    dom_slot = max((i for i in range(len(mats)) if canons[i] == dom_canon), key=lambda i: (mats[i]["pct"], -i))
    for t in a["sr3_triggers"]:
        c, p = t["material"], t["pct"]
        slots = [i for i in range(len(mats)) if canons[i] == c]
        s = max(slots, key=lambda i: (mats[i]["pct"], -i))
        delta = round(5.0 - p, 9)
        if delta > EPS and dom_slot not in slots and mats[dom_slot]["pct"] - delta >= 5.0 - EPS:
            cap = max(mats[s]["pct"], support.pct_max(category, comp["component_class"], mats[s]["material"]) or 0.0)
            if mats[s]["pct"] + delta <= cap + EPS:
                out.append(RepairProposal("SR3", "sr3_raise_minor_fibre_to_5pct", ri, [("pct", ri, dom_slot, s, delta)], 1.0))
    out += _merge_ops(comps, ri, [(t["material"], [i for i in range(len(mats)) if canons[i] == t["material"]]) for t in a["sr3_triggers"]],
                      category, support, forbidden, "SR3", "sr3_replace_minor_fibre_with_existing_fibre")
    return out


def sr2_ops(comps, a, category, support, forbidden, rule="SR2") -> list[RepairProposal]:
    ri = a["readable_index"]
    comp = comps[ri]
    canons = _canons(comp)
    dom = sorted_materials(a["readable"])[0][0]
    fibres = [(f, [i for i in range(len(canons)) if canons[i] == f]) for f, _ in sorted(a["readable"].items(), key=lambda kv: (kv[1], kv[0])) if f != dom]
    return _merge_ops(comps, ri, fibres, category, support, forbidden, rule, "sr2_merge_fibre_into_existing_fibre")


def sr1_ops(comps, a, category, support, forbidden, counters=None) -> list[RepairProposal]:
    ri = a["readable_index"]
    comp, mats = comps[ri], comps[ri]["materials"]
    out = []
    for si in range(len(mats)):
        for r, w in slot_substitutions(comp, si, category, support, forbidden):
            out.append(RepairProposal("SR1", "sr1_supported_slot_substitution", ri, [("sub", ri, si, r)], w))
    if len(mats) == 2:
        cls = comp["component_class"]
        pool = set(support.allowed(category, cls))
        for pair in sorted(sorted(p) for p in SR1_BINARY):
            X, Y = pair
            if not ({X, Y} <= pool) or {X, Y} & set(forbidden) or support.combo_count(category, cls, {X, Y}) == 0:
                continue
            for a0, a1 in ((X, Y), (Y, X)):
                if any(mats[k]["pct"] > (support.pct_max(category, cls, mat) or 0) + EPS for k, mat in enumerate((a0, a1))):
                    continue
                ops = [("sub", ri, k, mat) for k, mat in enumerate((a0, a1)) if mats[k]["material"] != mat]
                if len(ops) == 2:                       # single-slot cases are already covered above
                    out.append(RepairProposal("SR1", "sr1_supported_binary_pair", ri, ops, math.sqrt(support.count(category, cls, X) * support.count(category, cls, Y))))
    return out


def sr5_ops(comps, a, category, support, forbidden) -> list[RepairProposal]:
    hi = a["sr5_hidden_index"]
    comp, mats, out = comps[hi], comps[hi]["materials"], []
    canons = _canons(comp)
    surface = a["surface_set"]
    for t in a["sr5_triggers"]:
        slots = [i for i in range(len(mats)) if canons[i] == t["material"]]
        if len(slots) != 1:
            continue
        s = slots[0]
        for r, w in slot_substitutions(comp, s, category, support, forbidden):
            if canon_material(r) in surface:
                out.append(RepairProposal("SR5", "sr5_substitute_hidden_with_surface_fibre", hi, [("sub", hi, s, r)], w))
        delta = round(t["pct"] - 5.0, 9)
        if delta > EPS:
            for j in range(len(mats)):
                if j != s and canons[j] in surface:
                    cap = max(mats[j]["pct"], support.pct_max(category, comp["component_class"], mats[j]["material"]) or 0.0)
                    if mats[j]["pct"] + delta <= cap + EPS:
                        out.append(RepairProposal("SR5", "sr5_lower_hidden_pct_to_5pct", hi, [("pct", hi, s, j, delta)], 1.0))
    return out


def revert_ops(comps, log, forbidden, rule, limit: int = 3) -> list[RepairProposal]:
    """Inverse of the latest random mutation steps (restores the TRAIN template's own value). Forbidden-material repairs
    and earlier sorting repairs are never reverted."""
    out = []
    for e in reversed(log):
        if e.get("reason") is not None or len(out) >= limit:
            continue
        ci = e["component_index"]
        mats = comps[ci]["materials"]
        if e["type"] == "substitution":
            if mats[e["slot"]]["material"] == e["to_material"] and e["from_material"] not in forbidden:
                out.append(RepairProposal(rule, "revert_mutation_step", ci, [("sub", ci, e["slot"], e["from_material"])], 1.0))
        elif mats[e["to_slot"]]["pct"] - e["delta"] >= -EPS:
            out.append(RepairProposal(rule, "revert_mutation_step", ci, [("pct", ci, e["to_slot"], e["from_slot"], e["delta"])], 1.0))
    return out


def repair_proposals(comps, a, category: str, support: SupportTables, forbidden, cfg: SortingAwareGenerationConfig, log,
                     colour, counters=None, step0: int = 0) -> list[RepairProposal]:
    """Ranked proposals for the first violated, allowed rules. Each carries its Oracle look-ahead (fast rule evaluation):
    ranking = fewest remaining violations, then more confirmed-predicted fixes, then TRAIN weight, then a stable hash."""
    allowed = cfg.allowed_rules()
    viol = [r for r in allowed if a["flags"][r]]
    if not viol:
        return []
    props: list[RepairProposal] = []
    if a["readable_index"] is not None:
        if "SR3" in viol:
            props += sr3_ops(comps, a, category, support, forbidden, cfg)
        if "SR2" in viol:
            props += sr2_ops(comps, a, category, support, forbidden, "SR2")
        if "SR1" in viol:
            if a["sr1_reason"] == "more_than_two_fibres":
                props += sr2_ops(comps, a, category, support, forbidden, "SR1")
            elif a["sr1_reason"] in ("unsupported_mono", "unsupported_binary"):
                props += sr1_ops(comps, a, category, support, forbidden, counters)
    if "SR5" in viol and a["sr5_hidden_index"] is not None:
        props += sr5_ops(comps, a, category, support, forbidden)
    if cfg.allow_mutation_revert:
        props += revert_ops(comps, log, forbidden, viol[0])
    seen, ranked = set(), []
    base_flags = a["flags"]
    for p in props:
        p.new_components, p.entries = apply_ops(comps, p.ops, step0, p.rule)
        sig = composition_signature(p.new_components)
        if sig in seen:
            continue
        seen.add(sig)
        p.analysis_after = analyze(p.new_components, colour, counters)
        fa = p.analysis_after["flags"]
        p.predicted_fixed = tuple(r for r in RULES if base_flags[r] and not fa[r])
        p.predicted_introduced = tuple(r for r in RULES if fa[r] and not base_flags[r])
        ranked.append(p)
    ranked.sort(key=lambda p: (sum(p.analysis_after["flags"][r] for r in RULES), -len(p.predicted_fixed), -p.weight,
                               stable_hash(p.operation, p.ops, length=12)))
    return ranked


def explain_reason(rule: str, a: dict[str, Any]):
    return reason_for(rule, a)
