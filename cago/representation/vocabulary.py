"""ML material vocabulary fitted on TRAIN garments only. Oracle canonicalization is separate and untouched."""
from __future__ import annotations

from typing import Any, Iterable

import pandas as pd

from cago.config.materials import FAMILY_BY_CANONICAL

SPECIAL_TOKENS = ("PAD", "OTHER")
OTHER = "OTHER"
DEFAULT_MIN_COUNT = 30          # train material occurrences; see threshold_sweep in the vocabulary/audit
SWEEP = (1, 5, 10, 20, 30, 50, 100, 200, 500)
NEVER_IN_VOCAB = frozenset({"unspecified_material"})   # source placeholder, not a material: always OTHER
FIT_SPLIT = "train"


def fit_vocabulary(material_rows: pd.DataFrame, split_map: pd.DataFrame, min_count: int = DEFAULT_MIN_COUNT,
                   known_names: Iterable[str] = (), aliases: dict[str, str] | None = None,
                   component_rows: pd.DataFrame | None = None) -> dict[str, Any]:
    """Fit the vocabulary using ONLY rows whose garment is in the train split.

    material_rows: columns garment_id, material_canonical (usable-component material occurrences; None = unmapped).
    split_map: columns garment_id, split. Materials seen only in val/test (or known only from `known_names`) -> OTHER.
    """
    if min_count < 1:
        raise ValueError("min_count must be >= 1")
    train_ids = set(split_map.loc[split_map["split"] == FIT_SPLIT, "garment_id"])
    tr = material_rows[material_rows["garment_id"].isin(train_ids)]
    mapped = tr.dropna(subset=["material_canonical"])
    occ = mapped["material_canonical"].value_counts()
    gar = mapped.groupby("material_canonical")["garment_id"].nunique()
    names = sorted(set(known_names) | set(occ.index))

    keep = [m for m in occ.index if occ[m] >= min_count and m not in NEVER_IN_VOCAB]
    keep.sort(key=lambda m: (-int(occ[m]), m))
    tokens = [*SPECIAL_TOKENS, *keep]

    table, c2t = [], {}
    for m in sorted(names, key=lambda x: (-int(occ.get(x, 0)), x)):
        n = int(occ.get(m, 0))
        if m in keep:
            tok, why = m, "in_vocab"
        elif m in NEVER_IN_VOCAB:
            tok, why = OTHER, "unspecified_source_label"
        elif n == 0:
            tok, why = OTHER, "unseen_in_train"
        else:
            tok, why = OTHER, "rare_in_train"
        c2t[m] = tok
        table.append({"material_canonical": m, "material_family": FAMILY_BY_CANONICAL.get(m, "unknown"),
                      "train_occurrences": n, "train_garments": int(gar.get(m, 0)), "ml_token": tok,
                      "token_reason": why})
    vocab = {
        "version": 1, "fit_split": FIT_SPLIT, "min_count": int(min_count),
        "n_train_garments": len(train_ids), "n_train_material_occurrences": int(len(tr)),
        "train_unmapped_occurrences": int(tr["material_canonical"].isna().sum()),
        "special_tokens": list(SPECIAL_TOKENS), "tokens": tokens,
        "token_to_id": {t: i for i, t in enumerate(tokens)}, "vocabulary_size": len(tokens),
        "unmapped_source_material_token": OTHER,
        "canonical_to_token": c2t,
        "threshold_sweep": {str(t): int(sum(1 for m in occ.index if occ[m] >= t and m not in NEVER_IN_VOCAB))
                            for t in SWEEP},
        "count_table": table,
        "material_aliases": {k: v for k, v in sorted((aliases or {}).items()) if v in c2t and k != v},
    }
    if component_rows is not None:
        ctr = component_rows[component_rows["garment_id"].isin(train_ids)]
        vocab["component_classes"] = sorted(ctr["component_class"].dropna().unique())
        vocab["component_names"] = sorted(ctr["component_name_normalized"].dropna().unique())
    return vocab


def token_for(canonical: str | None, vocab: dict[str, Any]) -> str:
    """ML token for a canonical material. Unmapped (None) and unknown names -> OTHER."""
    if canonical is None:
        return OTHER
    return vocab["canonical_to_token"].get(canonical, OTHER)


def token_reason(canonical: str | None, vocab: dict[str, Any]) -> str:
    if canonical is None:
        return "unmapped_source_material"
    t = vocab["canonical_to_token"].get(canonical)
    if t is None:
        return "unknown_to_vocabulary"
    return next((r["token_reason"] for r in vocab["count_table"] if r["material_canonical"] == canonical), "in_vocab")


def mapping_table(vocab: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(vocab["count_table"])
