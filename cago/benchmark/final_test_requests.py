"""Final TEST evaluation: split integrity checks and deterministic held-out request construction.

Role of TEST-derived information (documented, and the only role TEST data may play):
  * TEST (target_segment, detail_category) cells define WHICH requests are asked.
  * TEST garments' observable properties (dominant material, elastane bucket, colour, V1 fit/length labels) define the
    preferences of 'derived' requests. A TEST garment's composition is NEVER a generation template and never enters
    any TRAIN support statistic; generators receive TRAIN rows only.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd

from cago.benchmark.benchmark_requests import derived_preferences, forbidden_candidate
from cago.benchmark.perturbations import EvalGarment, load_eval_garments
from cago.generation.support_tables import SupportTables
from cago.generation.template_selector import ineligibility_reason, template_components
from cago.preprocessing.ids import stable_hash

SPLITS = ("train", "val", "test")
TYPES = ("no_pref", "derived_full", "derived_forbid")


def check_split_integrity(rep: pd.DataFrame, split_map: pd.DataFrame | None = None) -> dict[str, Any]:
    """Parent-product and garment leakage between TRAIN / VAL / TEST (all overlaps must be zero)."""
    parents = {s: set(rep.loc[rep["split"] == s, "parent_product_id"].dropna()) for s in SPLITS}
    gids = {s: set(rep.loc[rep["split"] == s, "garment_id"]) for s in SPLITS}
    pairs = [("train", "val"), ("train", "test"), ("val", "test")]
    out: dict[str, Any] = {
        "parents_per_split": {s: len(parents[s]) for s in SPLITS}, "garments_per_split": {s: len(gids[s]) for s in SPLITS},
        "parent_overlap": {f"{a}&{b}": len(parents[a] & parents[b]) for a, b in pairs},
        "garment_overlap": {f"{a}&{b}": len(gids[a] & gids[b]) for a, b in pairs},
        "garment_id_unique": bool(rep["garment_id"].is_unique), "unknown_splits": sorted(set(rep["split"].dropna()) - set(SPLITS)),
        "null_parent_rows": int(rep["parent_product_id"].isna().sum())}
    if split_map is not None:
        m = dict(zip(split_map["garment_id"], split_map["split"]))
        out["split_mapping_consistent_with_representation"] = all(m.get(g) == s for g, s in zip(rep["garment_id"], rep["split"]))
    out["ok"] = (not any(out["parent_overlap"].values()) and not any(out["garment_overlap"].values()) and out["garment_id_unique"]
                 and not out["unknown_splits"] and out.get("split_mapping_consistent_with_representation", True))
    return out


def assert_split_integrity(rep: pd.DataFrame, split_map: pd.DataFrame | None = None) -> dict[str, Any]:
    r = check_split_integrity(rep, split_map)
    if not r["ok"]:
        raise ValueError(f"split/parent leakage detected: {r}")
    return r


def generation_view(rep: pd.DataFrame) -> pd.DataFrame:
    """The ONLY representation generators may see: TRAIN rows (no VAL, no TEST)."""
    return rep[rep["split"] == "train"].reset_index(drop=True)


def eligibility_audit(rep: pd.DataFrame, split: str) -> dict[str, Any]:
    """Which garments of the evaluation split can define derived preferences (clean compositions) - nothing is silently dropped."""
    sub = rep[rep["split"] == split]
    reasons: Counter = Counter()
    ok_parents: set = set()
    for r in sub.itertuples(index=False):
        why = ineligibility_reason(r, template_components(r.components))
        reasons[why or "eligible"] += 1
        if not why:
            ok_parents.add(r.parent_product_id)
    cells_all = {(s, c) for s, c in zip(sub["target_segment"], sub["detail_category"])}
    cells_ok = {(s, c) for s, c, p in zip(sub["target_segment"], sub["detail_category"], sub["parent_product_id"]) if p in ok_parents}
    return {"garments": len(sub), "parents": int(sub["parent_product_id"].nunique()), "by_reason": dict(reasons),
            "eligible_parents": len(ok_parents), "cells": len(cells_all), "cells_with_eligible_garment": len(cells_ok),
            "cells_without_eligible_garment": sorted("|".join(c) for c in cells_all - cells_ok)}


def build_final_test_requests(rep_eval: pd.DataFrame, support: SupportTables, split: str = "test", seed: int = 0,
                              k_per_type: int = 3) -> list[dict[str, Any]]:
    """Deterministic requests for an evaluation split (`rep_eval` is the FULL representation; only the split's observable
    properties are read). Per (segment, category) cell: 1 no-preference request (for EVERY cell of the split), and up to
    `k_per_type` derived_full + `k_per_type` derived_forbid requests from distinct held-out parent products (disjoint
    parent sets across the two types when enough parents exist; documented reuse otherwise)."""
    if tuple(support.splits_used) != ("train",):
        raise ValueError("support tables must be TRAIN-only")
    garments = load_eval_garments(rep_eval, split, seed=seed, one_per_parent=True)
    by_cell: dict[tuple[str, str], list[EvalGarment]] = {}
    for g in garments:
        by_cell.setdefault((g.target_segment, g.detail_category), []).append(g)
    sub = rep_eval[rep_eval["split"] == split]
    cells = sorted({(s, c) for s, c in zip(sub["target_segment"], sub["detail_category"])})
    out: list[dict[str, Any]] = []
    for seg, cat in cells:
        gs = by_cell.get((seg, cat), [])               # already ordered by sha256(seed, garment_id)
        base = {"target_segment": seg, "detail_category": cat}
        out.append({"request_id": f"{seg}|{cat}|no_pref", "cell": [seg, cat], "type": "no_pref", "source_garment_id": None,
                    "source_parent_product_id": None, "parent_reused_across_types": False, "raw": dict(base)})
        full = gs[:k_per_type]
        forb = gs[k_per_type:2 * k_per_type]
        reused = False
        if not forb:
            forb, reused = gs[:k_per_type], bool(gs)
        for t, lst in (("derived_full", full), ("derived_forbid", forb)):
            for g in lst:
                raw = dict(base)
                raw.update(derived_preferences(g, t == "derived_full"))
                if t == "derived_forbid":
                    f = forbidden_candidate(g, support)
                    if f:
                        raw["forbidden_materials"] = [f]
                out.append({"request_id": f"{seg}|{cat}|{t}|{g.garment_id}", "cell": [seg, cat], "type": t, "source_garment_id": g.garment_id,
                            "source_parent_product_id": g.parent_product_id, "parent_reused_across_types": bool(reused and t == "derived_forbid"),
                            "raw": raw})
    return out


def cluster_ids(requests: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    """request_id -> {'parent': ..., 'cell': ...}. Derived requests cluster by their held-out parent product; no-preference
    requests (no parent) form singleton parent clusters named after their cell."""
    out = {}
    for r in requests:
        cell = "|".join(r["cell"])
        out[r["request_id"]] = {"parent": f"parent:{r['source_parent_product_id']}" if r["source_parent_product_id"] is not None
                                else f"nopref:{cell}", "cell": f"cell:{cell}"}
    return out


def coverage_report(requests: list[dict[str, Any]], eval_audit: dict[str, Any]) -> dict[str, Any]:
    parents = [r["source_parent_product_id"] for r in requests if r["source_parent_product_id"] is not None]
    return {"n_requests": len(requests), "cells": len({tuple(r["cell"]) for r in requests}),
            "categories": len({r["cell"][1] for r in requests}), "segments": dict(Counter(r["cell"][0] for r in requests)),
            "by_category": dict(sorted(Counter(r["cell"][1] for r in requests).items())),
            "types": dict(Counter(r["type"] for r in requests)), "distinct_held_out_parents_in_derived_requests": len(set(parents)),
            "derived_requests": len(parents), "parents_with_more_than_one_request": sum(v > 1 for v in Counter(parents).values()),
            "requests_with_parent_reuse_across_types": sum(r["parent_reused_across_types"] for r in requests),
            "evaluation_split_eligibility": eval_audit,
            "request_ids_digest": stable_hash([r["request_id"] for r in requests], length=16)}
