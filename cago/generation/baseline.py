"""Template Baseline Generator v1: clone ONE complete TRAIN garment, apply controlled mutations, validate, evaluate.

No component mixing, insertion, deletion or class mutation. No ML, no optimisation, no final scores.
"""
from __future__ import annotations

import json
import random
from collections import Counter
from dataclasses import dataclass
from typing import Any

import pandas as pd

from cago.generation.distance import template_distance, topology_preserved
from cago.generation.mutations import (MutationContext, MutationSettings, RepairError, clone_components, mutate_once,
                                       repair_forbidden)
from cago.generation.support_tables import SupportTables
from cago.generation.template_selector import Template, composition_signature, select_templates
from cago.oracle.engine import evaluate_garment
from cago.oracle.selection import make_component
from cago.preprocessing.ids import stable_hash
from cago.requirements.properties import build_profile, score_preferences
from cago.requirements.validation import RequirementContext, validate_candidate

ORACLE_FIELDS = ("sr1_violation", "sr1_reason", "sr2_violation", "sr2_fibre_count", "sr3_violation",
                 "sr3_trigger_materials", "sr4_violation", "sr5_violation", "sr5_hidden_component",
                 "sr5_trigger_materials", "violation_count", "any_violation", "explanation")


@dataclass(frozen=True)
class GenerationConfig:
    n_templates: int = 10
    mutations_per_template: int = 5          # candidates requested per template
    seed: int = 42
    min_mutations: int = 1                   # random mutations per candidate (forbidden repairs are extra)
    max_mutations: int = 3
    max_attempts: int = 25
    settings: MutationSettings = MutationSettings()
    w_sub: float = 1.0
    w_pct: float = 1.0


def public_components(components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Components without private helper keys."""
    return [{k: v for k, v in c.items() if not k.startswith("_")} for c in components]


def request_key(request: dict[str, Any]) -> str:
    core = {k: request[k] for k in ("target_segment", "detail_category", "hard_constraints", "soft_preferences")}
    return stable_hash(json.dumps(core, sort_keys=True, ensure_ascii=False), length=12)


def oracle_eval(candidate_id: str, colour: str | None, components: list[dict[str, Any]]) -> dict[str, Any]:
    comps = [make_component(c["component_id"], c["component_name_normalized"], c["component_class"],
                            [(m["material"], m["pct"]) for m in c["materials"]]) for c in components]
    row = evaluate_garment(candidate_id, colour, comps)
    return {k: row[k] for k in ORACLE_FIELDS}


def property_eval(request: dict[str, Any], components, colour, tags) -> dict[str, Any]:
    prof = build_profile(components, colour, tags)
    return score_preferences(request["soft_preferences"], prof, request["detail_category"])


def normalize_candidate(components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Representation ordering (pct desc, then name) of each component's materials; candidates themselves keep
    template slot order so that distance/log stay slot-aligned."""
    return [{**c, "materials": sorted(c["materials"], key=lambda m: (-m["pct"], m["material"]))} for c in components]


def generate_for_template(t: Template, request: dict[str, Any], support: SupportTables, ctx: RequirementContext,
                          cfg: GenerationConfig, rkey: str) -> tuple[list[dict[str, Any]], Counter, dict[str, int]]:
    forbidden = frozenset(request["hard_constraints"]["forbidden_materials"])
    soft = request["soft_preferences"]
    m = MutationContext(t.detail_category, support, forbidden, soft.get("preferred_dominant_material"), soft,
                        t.colour, frozenset(t.text_tags), cfg.settings)
    base = clone_components(t.components)
    t_sig = composition_signature(base)
    rejected: Counter = Counter()
    stats = {"attempts": 0}
    seen: set = set()
    out: list[dict[str, Any]] = []
    for serial in range(cfg.mutations_per_template):
        for attempt in range(cfg.max_attempts):
            stats["attempts"] += 1
            rng = random.Random(int(stable_hash(cfg.seed, rkey, t.garment_id, serial, attempt, length=16), 16))
            comps, log = clone_components(base), []
            try:
                log += repair_forbidden(comps, rng, m)
            except RepairError:
                rejected["unrepairable_forbidden_material"] += 1
                return out, rejected, stats          # deterministic failure: no admissible replacement exists
            k = rng.randint(cfg.min_mutations, cfg.max_mutations)
            for _ in range(k):
                e = mutate_once(comps, rng, m, len(log))
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
            if not topology_preserved(base, comps):
                rejected["topology_changed"] += 1
                continue
            sig = composition_signature(comps)
            if sig == t_sig:
                rejected["identical_to_template"] += 1
                continue
            if sig in seen:
                rejected["duplicate_candidate"] += 1
                continue
            seen.add(sig)
            cid = "cand_" + stable_hash(rkey, cfg.seed, t.garment_id, serial)
            pub = public_components(comps)
            out.append({
                "candidate_id": cid, "request_key": rkey, "template_garment_id": t.garment_id,
                "template_parent_product_id": t.parent_product_id, "template_split": t.split,
                "target_segment": t.target_segment, "detail_category": t.detail_category, "normalized_colour": t.colour,
                "components": pub, "mutation_log": log, "n_mutations": len(log),
                "n_forbidden_repairs": sum(e["reason"] == "forbidden_repair" for e in log),
                "hard_validation": {"passed": True, "issues": []},
                "template_distance": template_distance(public_components(base), pub, cfg.w_sub, cfg.w_pct),
                "oracle": oracle_eval(cid, t.colour, pub),
                "property_proxies": property_eval(request, pub, t.colour, t.text_tags),
            })
            break
        else:
            rejected["gave_up_after_max_attempts"] += 1
    return out, rejected, stats


def generate_baseline(request: dict[str, Any], rep: pd.DataFrame, support: SupportTables, ctx: RequirementContext,
                      cfg: GenerationConfig = GenerationConfig()) -> dict[str, Any]:
    """Generate candidates for one normalized request (output of validate_request(...).request)."""
    if tuple(support.splits_used) != ("train",):
        raise ValueError("support tables must be TRAIN-only")
    forbidden = frozenset(request["hard_constraints"]["forbidden_materials"])
    templates, pool = select_templates(rep, request, cfg.n_templates, cfg.seed, forbidden)
    rkey = request_key(request)
    cands, rejected, attempts, failed_templates = [], Counter(), 0, []
    for t in templates:
        c, rej, st = generate_for_template(t, request, support, ctx, cfg, rkey)
        cands += c
        rejected.update(rej)
        attempts += st["attempts"]
        if rej.get("unrepairable_forbidden_material"):
            failed_templates.append(t.garment_id)
    return {"request": request, "request_key": rkey, "templates": templates, "template_pool": pool,
            "candidates": cands, "rejected": dict(rejected), "attempts": attempts,
            "failed_templates": failed_templates, "config": {k: (v if k != "settings" else v.__dict__)
                                                             for k, v in cfg.__dict__.items()}}


def candidates_hash(cands: list[dict[str, Any]]) -> str:
    return stable_hash(json.dumps([[c["candidate_id"], c["components"], c["mutation_log"]] for c in cands],
                                  sort_keys=True, ensure_ascii=False), length=32)
