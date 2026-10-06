"""VAL-only development request construction for the sorting-aware generator study.

TEST rows are removed from the working representation before anything is built (`dev_view`); the frozen TEST benchmark
and Evaluation Validation V1 results are untouched and are NOT used for development decisions.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from cago.benchmark.benchmark_requests import TYPES, build_benchmark_requests
from cago.benchmark.perturbations import EvalGarment, load_eval_garments
from cago.generation.support_tables import SupportTables

DEV_SPLITS = ("train", "val")


def assert_dev_only(rep: pd.DataFrame) -> None:
    """Raise if any TEST row is present in a development working set."""
    bad = set(rep["split"].dropna().unique()) - set(DEV_SPLITS)
    if bad:
        raise ValueError(f"development pipeline must not contain splits {sorted(bad)}")


def dev_view(rep: pd.DataFrame) -> pd.DataFrame:
    """Representation restricted to TRAIN + VAL (TEST rows dropped)."""
    return rep[rep["split"].isin(DEV_SPLITS)].reset_index(drop=True)


def load_val_garments(rep_dev: pd.DataFrame, seed: int = 0) -> list[EvalGarment]:
    assert_dev_only(rep_dev)
    return load_eval_garments(rep_dev, "val", seed=seed, one_per_parent=False)


def build_val_requests(rep_dev: pd.DataFrame, support: SupportTables, seed: int = 0, types: tuple[str, ...] = TYPES,
                       max_requests: int | None = None) -> list[dict[str, Any]]:
    """Same construction philosophy as the frozen benchmark (no-preference / garment-derived / forbidden-material
    requests) but derived from held-out VAL garments."""
    assert_dev_only(rep_dev)
    if tuple(support.splits_used) != ("train",):
        raise ValueError("support tables must be TRAIN-only")
    return build_benchmark_requests(load_val_garments(rep_dev, seed), support, seed, types, max_requests)
