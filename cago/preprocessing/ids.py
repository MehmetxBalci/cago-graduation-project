"""Deterministic identifiers (sha256-based; never Python's salted hash())."""
from __future__ import annotations

import hashlib
from collections import Counter
from typing import Any, Sequence


def stable_hash(*parts: Any, length: int = 16) -> str:
    """Hex digest of the parts joined with a unit separator."""
    payload = "\x1f".join("" if p is None else str(p) for p in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def make_garment_ids(keys: Sequence[tuple]) -> tuple[list[str], int]:
    """One ID per row from a content key. Duplicate keys get an occurrence suffix in the hash input.

    Returns (ids, n_rows_with_duplicate_key).
    """
    seen: Counter = Counter()
    ids: list[str] = []
    dup_rows = 0
    for key in keys:
        occ = seen[key]
        seen[key] += 1
        if occ:
            dup_rows += 1
        ids.append("g_" + (stable_hash(*key) if occ == 0 else stable_hash(*key, f"dup{occ}")))
    return ids, dup_rows


def make_component_id(garment_id: str, component_index: int, component_path_raw: Any) -> str:
    return "c_" + stable_hash(garment_id, component_index, component_path_raw)
