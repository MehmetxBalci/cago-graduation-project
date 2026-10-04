"""Controlled perturbations of held-out (TEST) garments for metric validation.

TEST garments are only EVALUATION EXAMPLES. Every reference/support statistic stays TRAIN-only (SupportTables).
Component topology (components, order, class/name, material count) is always preserved.

Levels:  L0 original | L1 small percentage move | L2 larger percentage move | L3 one controlled supported
substitution | L4 one contextually unusual substitution (zero / very low TRAIN support for category + class).
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Iterable

import pandas as pd

from cago.generation.distance import template_distance, topology_preserved
from cago.generation.mutations import apply_percentage, apply_substitution, clone_components
from cago.generation.support_tables import SPECIAL_TOKENS, SupportTables, to_py
from cago.generation.template_selector import ineligibility_reason, template_components
from cago.preprocessing.ids import stable_hash
from cago.requirements.validation import RequirementContext, validate_candidate

LEVELS = ("L0", "L1", "L2", "L3", "L4")


@dataclass(frozen=True)
class PerturbationConfig:
    l1_delta: float = 1.0               # percentage points moved at L1 (per multi-material component)
    l2_max_delta: float = 10.0          # upper bound of the L2 move
    l2_min_delta: float = 2.0           # L2 must exceed L1; smaller feasible moves are skipped
    min_pct: float = 0.5                # a source slot never drops below this (material stays present)
    l3_top_k: int = 5                   # L3 picks among the K most frequent TRAIN materials for the context
    l4_low_support_max: int = 2         # 'very low' TRAIN support when no zero-support material exists


@dataclass
class EvalGarment:
    garment_id: str
    parent_product_id: Any
    target_segment: str
    detail_category: str
    colour: str | None
    fit_label: str | None
    fit_source: str | None
    length_label: str | None
    length_source: str | None
    text_tags: tuple[str, ...]
    components: list[dict[str, Any]]


def _nn(v: Any) -> Any:
    """pandas missing values (None/NaN) -> None."""
    return None if v is None or (isinstance(v, float) and v != v) else v


def load_eval_garments(rep: pd.DataFrame, split: str = "test", n: int | None = None, seed: int = 0,
                       one_per_parent: bool = True) -> list[EvalGarment]:
    """Clean (template-eligible) garments of ONE split, deterministically ordered by sha256(seed, garment_id)."""
    sub = rep[rep["split"] == split]
    rows = sorted(sub.itertuples(index=False), key=lambda r: stable_hash(seed, r.garment_id, length=16))
    out, parents = [], set()
    for r in rows:
        comps = template_components(r.components)
        if ineligibility_reason(r, comps):
            continue
        if one_per_parent and r.parent_product_id in parents:
            continue
        parents.add(r.parent_product_id)
        out.append(EvalGarment(r.garment_id, r.parent_product_id, r.target_segment, r.detail_category, _nn(r.normalized_colour),
                               _nn(r.fit_label), _nn(getattr(r, "fit_label_source", None)), _nn(r.length_label),
                               _nn(getattr(r, "length_label_source", None)), tuple(to_py(r.text_evidence_tags)), comps))
        if n is not None and len(out) >= n:
            break
    return out


def public(components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{k: v for k, v in c.items() if not k.startswith("_")} for c in components]


def _rng(seed: int, gid: str, level: str) -> random.Random:
    return random.Random(int(stable_hash(seed, gid, level, length=16), 16))


def perturb_percentages(components, level: str, rng: random.Random, cfg: PerturbationConfig):
    """L1/L2: move percentage points between materials inside every multi-material component. Returns (components, n_moves)."""
    comps = clone_components(components)
    moves = 0
    for ci, c in enumerate(comps):
        mats = c["materials"]
        if len(mats) < 2:
            continue
        if level == "L1":
            srcs = [i for i, m in enumerate(mats) if m["pct"] >= cfg.l1_delta + cfg.min_pct]
            if not srcs:
                continue
            i, d = srcs[rng.randrange(len(srcs))], cfg.l1_delta
        else:
            i = max(range(len(mats)), key=lambda k: (mats[k]["pct"], -k))
            d = min(cfg.l2_max_delta, float(int((mats[i]["pct"] - cfg.min_pct) * 2) / 2))
            if d < cfg.l2_min_delta:
                continue
        dsts = [j for j in range(len(mats)) if j != i]
        apply_percentage(comps, ci, i, dsts[rng.randrange(len(dsts))], d, moves)
        moves += 1
    return (comps, moves) if moves else (None, 0)


def _slots(components) -> list[tuple[int, int]]:
    return [(ci, si) for ci, c in enumerate(components) for si in range(len(c["materials"]))]


def substitute_supported(components, category: str, support: SupportTables, rng: random.Random, cfg: PerturbationConfig):
    """L3: replace one slot by one of the K most frequent TRAIN materials of its (category, class) context (pct <= TRAIN max)."""
    props = []
    for ci, si in _slots(components):
        c = components[ci]
        present = {m["material"] for m in c["materials"]}
        pool = [r for r in support.allowed(category, c["component_class"]) if r not in present
                and r.casefold() not in SPECIAL_TOKENS][:cfg.l3_top_k]
        for r in pool:
            bound = support.pct_max(category, c["component_class"], r)
            if bound is not None and c["materials"][si]["pct"] <= bound + 1e-9:
                props.append((ci, si, r))
    if not props:
        return None, None
    ci, si, r = props[rng.randrange(len(props))]
    comps = clone_components(components)
    apply_substitution(comps, ci, si, r, 0)
    return comps, {"component_index": ci, "slot": si, "to_material": r,
                   "train_support_count": support.count(category, comps[ci]["component_class"], r)}


def substitute_unusual(components, category: str, support: SupportTables, vocab_materials: Iterable[str],
                       rng: random.Random, cfg: PerturbationConfig):
    """L4: replace one slot by a globally valid vocabulary material with ZERO (else very low) TRAIN support for the
    (category, component class) context. Returns (None, None) when no such material exists."""
    vocab = sorted(m for m in vocab_materials if m.casefold() not in SPECIAL_TOKENS)
    zero, low = [], []
    for ci, si in _slots(components):
        c = components[ci]
        present = {m["material"] for m in c["materials"]}
        for r in vocab:
            if r in present:
                continue
            n = support.count(category, c["component_class"], r)
            (zero if n == 0 else low if n <= cfg.l4_low_support_max else []).append((ci, si, r, n))
    pool = zero or low
    if not pool:
        return None, None
    ci, si, r, n = pool[rng.randrange(len(pool))]
    comps = clone_components(components)
    apply_substitution(comps, ci, si, r, 0)
    return comps, {"component_index": ci, "slot": si, "to_material": r, "train_support_count": n, "zero_support": n == 0}


def perturb_garment(g: EvalGarment, support: SupportTables, vocab_materials: Iterable[str], ctx: RequirementContext,
                    seed: int = 0, cfg: PerturbationConfig = PerturbationConfig()) -> dict[str, dict[str, Any]]:
    """{level: {components, distance, info, hard_valid}} for the levels applicable to this garment."""
    cat, base = g.detail_category, g.components
    out: dict[str, dict[str, Any]] = {}

    def add(level, comps, info):
        pub, orig = public(comps), public(base)
        assert topology_preserved(orig, pub)
        out[level] = {"components": pub, "distance": template_distance(orig, pub), "info": info,
                      "hard_valid": not validate_candidate(pub, [], ctx)}

    add("L0", clone_components(base), {})
    for lv in ("L1", "L2"):
        comps, moves = perturb_percentages(base, lv, _rng(seed, g.garment_id, lv), cfg)
        if comps:
            add(lv, comps, {"components_changed": moves})
    comps, info = substitute_supported(base, cat, support, _rng(seed, g.garment_id, "L3"), cfg)
    if comps:
        add("L3", comps, info)
    comps, info = substitute_unusual(base, cat, support, vocab_materials, _rng(seed, g.garment_id, "L4"), cfg)
    if comps:
        add("L4", comps, info)
    return out
