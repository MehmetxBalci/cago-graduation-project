"""Synthetic fixture for V1.2 segment-aware category filtering (derived from the research test fixture; no real data needed).

Cells (TRAIN unless stated):
  women / trousers   44 eligible (original fixture)
  women / shorts      3 eligible (copies of the men / shorts garments)  -> category shared by women and men
  men   / shorts      3 eligible (original fixture)
  men   / trousers    2 TRAIN garments, both INELIGIBLE (unmapped material / not fully usable) -> TRAIN rows but not available
  kids  / dresses     2 TRAIN garments, both INELIGIBLE -> the segment `kids` has no available category (empty state)
  men   / dresses     eligible-looking garments in VAL and TEST only -> must never become available (no VAL/TEST fallback)
  baby  / skirts      VAL / TEST only -> `baby` is not a TRAIN segment at all
"""
from __future__ import annotations

import pandas as pd

from app.adapters import build_app_data
from app.tests.app_fixtures import CAPS, REP_ALL, VOCAB_DOC

_men_shorts = REP_ALL[(REP_ALL["split"] == "train") & (REP_ALL["target_segment"] == "men") & (REP_ALL["detail_category"] == "shorts")]
_any_train = REP_ALL[REP_ALL["split"] == "train"].head(2)


def _copy(rows: pd.DataFrame, tag: str, **values) -> pd.DataFrame:
    out = rows.copy()
    out["garment_id"] = [f"{tag}_{i}" for i in range(len(out))]
    out["parent_product_id"] = [f"p_{tag}_{i}" for i in range(len(out))]
    for k, v in values.items():
        out[k] = v
    return out


_extra = [
    _copy(_men_shorts, "ws", target_segment="women"),
    _copy(_any_train, "mt", target_segment="men", detail_category="trousers", has_unmapped_material=[True, False],
          is_fully_usable=[True, False]),
    _copy(_any_train, "kd", target_segment="kids", detail_category="dresses", is_fully_usable=False),
    _copy(_any_train, "mdv", target_segment="men", detail_category="dresses", split="val"),
    _copy(_any_train, "mdt", target_segment="men", detail_category="dresses", split="test"),
    _copy(_any_train, "bsv", target_segment="baby", detail_category="skirts", split="val"),
    _copy(_any_train, "bst", target_segment="baby", detail_category="skirts", split="test"),
]
REP_EXT_ALL = pd.concat([REP_ALL, *_extra], ignore_index=True)
REP_EXT_TRAIN = REP_EXT_ALL[REP_EXT_ALL["split"] == "train"].reset_index(drop=True)
CAPS_EXT = {"categories": {**CAPS["categories"], "dresses": {"controls": {}, "control_decisions": {}}}}
DATA_EXT = build_app_data(REP_EXT_TRAIN, VOCAB_DOC, CAPS_EXT)
EXPECTED_AVAILABLE = {"women": ["shorts", "trousers"], "men": ["shorts"], "kids": []}
