"""Deterministic benchmark request construction.

Cells (target_segment x detail_category) come from clean TEST garments; every request is only a RAW user request.
Generation/support use TRAIN only. Derived requests copy observable properties of a held-out TEST garment
(dominant material, elastane bucket, colour, V1 fit/length labels), so each request has a realistic, checkable intent.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from cago.benchmark.intent_validation import primary_index
from cago.benchmark.perturbations import EvalGarment, public
from cago.generation.support_tables import SupportTables
from cago.preprocessing.ids import stable_hash
from cago.requirements.properties import build_profile, stretch_bucket

TYPES = ("no_pref", "derived_full", "derived_forbid")


def derived_preferences(g: EvalGarment, full: bool = True) -> dict[str, Any]:
    prof = build_profile(public(g.components), g.colour)
    prefs: dict[str, Any] = {}
    if prof.dominant:
        prefs["preferred_dominant_material"] = prof.dominant
    prefs["stretch"] = stretch_bucket(prof.elastane_pct)
    if full:
        if g.colour:
            prefs["colour"] = g.colour
        if g.fit_label:
            prefs["fit"] = g.fit_label
        if g.length_label:
            prefs["length_cut"] = g.length_label
    return prefs


def forbidden_candidate(g: EvalGarment, support: SupportTables) -> str | None:
    """Most frequent TRAIN material of the category that the held-out garment does not use (deterministic)."""
    used = {m["material"] for c in g.components for m in c["materials"]}
    cnt = support.materials_by_category.get(g.detail_category, Counter())
    for m in sorted(cnt, key=lambda k: (-cnt[k], k)):
        if m not in used:
            return m
    return None


def build_benchmark_requests(test_garments: list[EvalGarment], support: SupportTables, seed: int = 0,
                             types: tuple[str, ...] = TYPES, max_requests: int | None = None) -> list[dict[str, Any]]:
    """[{request_id, cell, type, source_test_garment, raw}] sorted by cell; reproducible for a seed."""
    cells: dict[tuple[str, str], list[EvalGarment]] = {}
    for g in test_garments:
        cells.setdefault((g.target_segment, g.detail_category), []).append(g)
    out = []
    for (seg, cat), gs in sorted(cells.items()):
        gs = sorted(gs, key=lambda g: stable_hash(seed, g.garment_id, length=16))
        for i, t in enumerate(types):
            g = gs[min(i, len(gs) - 1)] if t != "no_pref" else None
            raw: dict[str, Any] = {"target_segment": seg, "detail_category": cat}
            if t == "derived_full":
                raw.update(derived_preferences(g, True))
            elif t == "derived_forbid":
                raw.update(derived_preferences(g, False))
                f = forbidden_candidate(g, support)
                if f:
                    raw["forbidden_materials"] = [f]
            out.append({"request_id": f"{seg}|{cat}|{t}", "cell": [seg, cat], "type": t,
                        "source_test_garment": None if g is None else g.garment_id, "raw": raw})
    if max_requests is not None and len(out) > max_requests:
        out = sorted(sorted(out, key=lambda r: stable_hash(seed, r["request_id"], length=16))[:max_requests], key=lambda r: r["request_id"])
    return out
