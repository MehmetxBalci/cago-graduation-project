"""TRAIN-only support tables for the template baseline generator.

Only components made entirely of vocabulary materials (ml_token == material, i.e. never OTHER/PAD/unmapped) are
counted, so every material these tables can offer is a real, in-vocabulary material observed in TRAIN.
VAL/TEST rows are never read.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable

import numpy as np
import pandas as pd

TRAIN = "train"
SPECIAL_TOKENS = frozenset({"pad", "other"})


def to_py(v: Any) -> Any:
    """Recursively convert numpy containers/scalars (as read from parquet) to plain Python."""
    if isinstance(v, np.ndarray):
        return [to_py(x) for x in v.tolist()]
    if isinstance(v, (list, tuple)):
        return [to_py(x) for x in v]
    if isinstance(v, dict):
        return {k: to_py(x) for k, x in v.items()}
    if isinstance(v, np.generic):
        return v.item()
    return v


def clean_component(comp: dict[str, Any]) -> bool:
    """True if every material is a physical, in-vocabulary material (no None/OTHER/PAD)."""
    mats, toks = comp["materials"], comp["ml_tokens"]
    return bool(mats) and all(m is not None and t == m and str(m).casefold() not in SPECIAL_TOKENS
                              for m, t in zip(mats, toks))


@dataclass
class SupportTables:
    """Counts observed in TRAIN garments only."""
    splits_used: tuple[str, ...] = (TRAIN,)
    n_train_garments: int = 0
    n_components_used: int = 0
    n_components_skipped_non_vocab: int = 0
    materials_by_category: dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))
    materials_by_category_class: dict[tuple[str, str], Counter] = field(default_factory=lambda: defaultdict(Counter))
    combos_by_category_class: dict[tuple[str, str], Counter] = field(default_factory=lambda: defaultdict(Counter))
    pct_values: dict[tuple[str, str, str], list[float]] = field(default_factory=lambda: defaultdict(list))
    _pct_stats: dict[tuple[str, str, str], dict[str, float]] = field(default_factory=dict, repr=False)

    # -- queries
    def allowed(self, category: str, component_class: str) -> list[str]:
        """Materials observed in TRAIN for this category + component class, most frequent first (name tie-break)."""
        c = self.materials_by_category_class.get((category, component_class), Counter())
        return sorted(c, key=lambda m: (-c[m], m))

    def count(self, category: str, component_class: str, material: str) -> int:
        return self.materials_by_category_class.get((category, component_class), Counter()).get(material, 0)

    def pct_max(self, category: str, component_class: str, material: str) -> float | None:
        s = self._pct_stats.get((category, component_class, material))
        return None if s is None else s["max"]

    def combo_count(self, category: str, component_class: str, materials: Iterable[str]) -> int:
        return self.combos_by_category_class.get((category, component_class), Counter()).get(frozenset(materials), 0)

    def finalize(self) -> "SupportTables":
        self._pct_stats = {k: {"n": len(v), "min": float(min(v)), "p50": float(np.percentile(v, 50)),
                               "p95": float(np.percentile(v, 95)), "max": float(max(v))}
                           for k, v in sorted(self.pct_values.items())}
        return self

    def summary(self) -> dict[str, Any]:
        return {"splits_used": list(self.splits_used), "n_train_garments": self.n_train_garments,
                "n_components_used": self.n_components_used,
                "n_components_skipped_non_vocab": self.n_components_skipped_non_vocab,
                "categories": len(self.materials_by_category),
                "category_class_cells": len(self.materials_by_category_class),
                "distinct_materials": len({m for c in self.materials_by_category.values() for m in c}),
                "distinct_combinations": sum(len(c) for c in self.combos_by_category_class.values()),
                "pct_stat_cells": len(self._pct_stats)}


def build_support_tables(rep: pd.DataFrame) -> SupportTables:
    """Build the tables from representation rows whose split == 'train' (everything else is ignored)."""
    tr = rep[rep["split"] == TRAIN]
    t = SupportTables(n_train_garments=len(tr))
    for cat, comps in zip(tr["detail_category"], tr["components"]):
        for c in comps:
            c = to_py(c)
            if not clean_component(c):
                t.n_components_skipped_non_vocab += 1
                continue
            cls = c["component_class"]
            t.n_components_used += 1
            t.materials_by_category_class[(cat, cls)].update(c["materials"])
            t.materials_by_category[cat].update(c["materials"])
            t.combos_by_category_class[(cat, cls)][frozenset(c["materials"])] += 1
            for m, p in zip(c["materials"], c["percentages"]):
                t.pct_values[(cat, cls, m)].append(float(p))
    return t.finalize()
