"""Deterministic, row-balanced group split by parent_product_id."""
from __future__ import annotations

import pandas as pd

from cago.config.settings import SPLIT_NAMES, SPLIT_RATIOS, SPLIT_SEED
from cago.preprocessing.ids import stable_hash


def assign_splits(garments: pd.DataFrame, ratios=SPLIT_RATIOS, seed: int = SPLIT_SEED) -> pd.DataFrame:
    """Order parent groups by sha256(seed|parent), then cut by cumulative garment-row share.

    All variants of a parent share one split. Non-null IDs of any scalar type are valid (grouped via str()); rows with a missing (None/NaN)
    parent_product_id each form their own group.
    """
    if abs(sum(ratios) - 1.0) > 1e-9:
        raise ValueError("split ratios must sum to 1")
    pid = garments["parent_product_id"].astype(object)
    gid = garments["garment_id"].astype(object)
    # Any non-null scalar ID (str/int/float) is a valid group key; only None/NaN are missing.
    group = pd.Series([("__missing__" + g) if pd.isna(p) else str(p) for p, g in zip(pid, gid)])
    sizes = group.value_counts()
    order = sorted(sizes.index, key=lambda g: stable_hash(seed, g, length=32))
    total = int(sizes.sum())
    cut1, cut2 = ratios[0] * total, (ratios[0] + ratios[1]) * total
    split_of: dict[str, str] = {}
    cum = 0
    for g in order:
        mid = cum + sizes[g] / 2
        split_of[g] = SPLIT_NAMES[0] if mid < cut1 else SPLIT_NAMES[1] if mid < cut2 else SPLIT_NAMES[2]
        cum += int(sizes[g])
    out = pd.DataFrame({
        "garment_id": gid.values,
        "parent_product_id": pid.values,
        "split": group.map(split_of).values,
    })
    assert_no_leakage(out)
    return out


def assert_no_leakage(mapping: pd.DataFrame) -> None:
    """Raise AssertionError if any parent_product_id appears in more than one split."""
    per_parent = mapping.dropna(subset=["parent_product_id"]).groupby("parent_product_id")["split"].nunique()
    leaked = per_parent[per_parent > 1]
    assert leaked.empty, f"parent-product leakage: {len(leaked)} parents span multiple splits"
