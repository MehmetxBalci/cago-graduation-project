"""Generator B: Sorting-aware template + controlled mutation/repair generator (constraint-based probabilistic generation).

Same whole-garment-template philosophy as Baseline A: one TRAIN garment is cloned; only material identities and
percentages change. The frozen baseline generator is NOT modified and remains available as Baseline A.
Hard constraints are absolute; Intent / Plausibility protection and the acceptance policy gate every repair.
"""
from __future__ import annotations

import random
from collections import Counter
from typing import Any

import pandas as pd

from cago.evaluation.config import EvaluationConfig
from cago.evaluation.intent import evaluate_intent
from cago.evaluation.plausibility import evaluate_plausibility
from cago.generation.baseline import oracle_eval, public_components, request_key
from cago.generation.distance import template_distance, topology_preserved
from cago.generation.mutations import MutationContext, RepairError, clone_components, mutate_once, repair_forbidden
from cago.generation.support_tables import SupportTables
from cago.generation.template_selector import Template, composition_signature, select_templates
from cago.generation_sorting.config import IMMUTABLE_RULES, REPAIRABLE_RULES, SortingAwareGenerationConfig
from cago.generation_sorting.oracle_view import analyze
from cago.generation_sorting.policies import Snapshot, decide
from cago.generation_sorting.proposals import biased_mutate_once
from cago.generation_sorting.repairs import repair_proposals
from cago.generation_sorting.trace import make_step
from cago.preprocessing.ids import stable_hash
from cago.requirements.validation import RequirementContext, validate_candidate


def _mats(comp) -> list[tuple[str, float]]:
    return [(m["material"], m["pct"]) for m in comp["materials"]]


def repair_candidate(comps, log, base_pub, t: Template, request: dict[str, Any], support: SupportTables, ctx: RequirementContext,
                     cfg: SortingAwareGenerationConfig, ecfg: EvaluationConfig, counters: Counter, cid: str):
    """Bounded local repair of one hard-valid candidate. Returns (components, log, trace).

    Deterministic given the candidate: no randomness is used. Each evaluated proposal is traced (accepted or rejected).
    """
    forbidden = frozenset(request["hard_constraints"]["forbidden_materials"])
    soft, cat = request["soft_preferences"], t.detail_category

    def snap(components):
        pub = public_components(components)
        o = oracle_eval(cid, t.colour, pub)
        counters["oracle_full_evals"] += 1
        intent = evaluate_intent(soft, pub, t.colour, t.fit_label, t.length_label, t.text_tags, ecfg)["intent_alignment_raw"]
        plaus = evaluate_plausibility(pub, cat, template_distance(base_pub, pub), support, ecfg)["plausibility_raw"]
        counters["intent_evals"] += 1
        counters["plausibility_evals"] += 1
        ok = not validate_candidate(pub, sorted(forbidden), ctx) and topology_preserved(base_pub, pub)
        return Snapshot(int(o["violation_count"]), intent, plaus, ok), o

    trace: list[dict[str, Any]] = []
    visited = {composition_signature(comps)}
    before, o_before = snap(comps)
    for step in range(cfg.max_repair_steps):
        a = analyze(comps, t.colour, counters)
        viol = [r for r in cfg.allowed_rules() if a["flags"][r]]
        if not viol:
            break
        counters["repair_steps_started"] += 1
        props = repair_proposals(comps, a, cat, support, forbidden, cfg, log, t.colour, counters, step0=len(log))
        if not props:
            for r in viol:
                counters[f"no_train_supported_alternative:{r}"] += 1
            break
        accepted_one = False
        for p in props[:cfg.max_repair_proposals_per_step]:
            from cago.generation_sorting.oracle_view import reason_for
            sig = composition_signature(p.new_components)
            if sig in visited:
                counters["repair_cycle_prevented"] += 1
                continue
            after, o_after = snap(p.new_components)
            counters["repair_proposals_evaluated"] += 1
            ok, why, _ = decide(cfg.policy, before, after, cfg.preserve_intent_floor, cfg.preserve_plausibility_floor)
            ci = p.component_index
            trace.append(make_step(
                len(trace), p.rule, reason_for(p.rule, a), p.operation, {"index": ci, "name": comps[ci]["component_name_normalized"],
                                                                         "class": comps[ci]["component_class"]},
                _mats(comps[ci]), _mats(p.new_components[ci]), o_before, o_after, before.intent, after.intent, before.plaus,
                after.plaus, ok, why, p.entries))
            if trace[-1]["introduced_rules"]:
                counters["proposals_introducing_other_violation"] += 1
            if ok:
                counters["repair_accepted"] += 1
                counters[f"repair_accepted:{p.rule}"] += 1
                for r in trace[-1]["confirmed_fixed_rules"]:
                    counters[f"confirmed_fixed:{r}"] += 1
                if trace[-1]["introduced_rules"]:
                    counters["accepted_repairs_introducing_other_violation"] += 1
                comps, log = p.new_components, log + p.entries
                visited.add(sig)
                before, o_before = after, o_after
                accepted_one = True
                break
            counters[f"repair_rejected:{why}"] += 1
        if not accepted_one:
            break
    return comps, log, trace


def _account_unresolved(comps, t: Template, cfg: SortingAwareGenerationConfig, counters: Counter) -> None:
    flags = analyze(comps, t.colour)["flags"]
    for r in REPAIRABLE_RULES:
        if flags[r]:
            counters[f"unresolved:{r}" if r in cfg.allowed_rules() else f"not_attempted_rule_disabled:{r}"] += 1
    if flags["SR4"]:
        counters["sr4_immutable_violation"] += 1
    counters["candidates_final"] += 1
    counters["candidates_with_unresolved_repairable"] += any(flags[r] for r in cfg.allowed_rules())


def generate_for_template(t: Template, request: dict[str, Any], support: SupportTables, ctx: RequirementContext,
                          cfg: SortingAwareGenerationConfig, ecfg: EvaluationConfig, rkey: str, seen: set, counters: Counter,
                          rejected: Counter) -> tuple[list[dict[str, Any]], bool]:
    forbidden = frozenset(request["hard_constraints"]["forbidden_materials"])
    soft = request["soft_preferences"]
    m = MutationContext(t.detail_category, support, forbidden, soft.get("preferred_dominant_material"), soft, t.colour,
                        frozenset(t.text_tags), cfg.mutation_settings)
    base = clone_components(t.components)
    base_pub = public_components(base)
    t_sig = composition_signature(base)
    out: list[dict[str, Any]] = []
    for serial in range(cfg.candidates_per_template):
        for attempt in range(cfg.max_proposal_attempts):
            counters["mutation_attempts"] += 1
            rng = random.Random(int(stable_hash(cfg.seed, rkey, t.garment_id, serial, attempt, length=16), 16))   # same family as Baseline A
            comps, log = clone_components(base), []
            try:
                log += repair_forbidden(comps, rng, m)
            except RepairError:
                rejected["unrepairable_forbidden_material"] += 1
                return out, True
            k = rng.randint(cfg.min_mutations, cfg.max_mutations)
            for _ in range(k):
                e = (biased_mutate_once(comps, rng, m, len(log), cfg, counters) if cfg.sorting_aware_proposal
                     else mutate_once(comps, rng, m, len(log)))
                if e:
                    log.append(e)
            if not log:
                rejected["no_applicable_mutation"] += 1
                continue
            issues = validate_candidate(public_components(comps), sorted(forbidden), ctx)
            if issues:
                for i in issues:
                    rejected[f"hard_validation:{i.code}"] += 1
                continue
            if not topology_preserved(base_pub, public_components(comps)):
                rejected["topology_changed"] += 1
                continue
            pre = clone_components(comps)
            cid = "candB_" + stable_hash(rkey, cfg.seed, cfg.mode_name(), cfg.policy, t.garment_id, serial)
            trace: list[dict[str, Any]] = []
            if cfg.sorting_aware_repair:
                comps, log, trace = repair_candidate(comps, log, base_pub, t, request, support, ctx, cfg, ecfg, counters, cid)
            sig = composition_signature(comps)
            if sig == t_sig:
                rejected["identical_to_template"] += 1
                continue
            if sig in seen:
                rejected["duplicate_candidate"] += 1
                continue
            seen.add(sig)
            _account_unresolved(comps, t, cfg, counters)
            pub = public_components(comps)
            out.append({
                "candidate_id": cid, "request_key": rkey, "template_garment_id": t.garment_id,
                "template_parent_product_id": t.parent_product_id, "template_split": t.split, "target_segment": t.target_segment,
                "detail_category": t.detail_category, "normalized_colour": t.colour, "components": pub, "mutation_log": log,
                "n_mutations": len(log), "n_forbidden_repairs": sum(e["reason"] == "forbidden_repair" for e in log),
                "n_sorting_repairs": sum(bool(s["accepted"]) for s in trace), "hard_validation": {"passed": True, "issues": []},
                "template_distance": template_distance(base_pub, pub), "oracle": oracle_eval(cid, t.colour, pub),
                "generator": "B", "mode": cfg.mode_name(), "pre_repair_components": public_components(pre), "repair_trace": trace})
            break
        else:
            rejected["gave_up_after_max_attempts"] += 1
    return out, False


def generate_sorting_aware(request: dict[str, Any], rep: pd.DataFrame, support: SupportTables, ctx: RequirementContext,
                           cfg: SortingAwareGenerationConfig = SortingAwareGenerationConfig(),
                           ecfg: EvaluationConfig = EvaluationConfig()) -> dict[str, Any]:
    """Generate candidates for one normalized request (output of validate_request(...).request). Result layout is
    compatible with `cago.evaluation.candidate.evaluate_request_candidates`."""
    if tuple(support.splits_used) != ("train",):
        raise ValueError("support tables must be TRAIN-only")
    if cfg.policy not in ("STRICT_SORTING", "NONDOMINATED_LOCAL"):
        raise ValueError(f"unknown policy {cfg.policy!r}")
    forbidden = frozenset(request["hard_constraints"]["forbidden_materials"])
    templates, pool = select_templates(rep, request, cfg.n_templates, cfg.seed, forbidden)
    rkey = request_key(request)
    counters: Counter = Counter()
    rejected: Counter = Counter()
    seen: set = set()
    cands, failed = [], []
    for t in templates:
        c, was_failed = generate_for_template(t, request, support, ctx, cfg, ecfg, rkey, seen, counters, rejected)
        cands += c
        if was_failed:
            failed.append(t.garment_id)
    return {"request": request, "request_key": rkey, "templates": templates, "template_pool": pool, "candidates": cands,
            "rejected": dict(rejected), "attempts": counters["mutation_attempts"], "failed_templates": failed,
            "config": {"n_templates": cfg.n_templates, "mutations_per_template": cfg.candidates_per_template, "seed": cfg.seed,
                       "mode": cfg.mode_name(), "policy": cfg.policy}, "search": dict(counters)}
