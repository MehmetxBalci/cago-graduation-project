"""Material mapping: supplied source table first, centralised manual overrides second, never silent."""
from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path
from typing import Any

from cago.config.materials import FAMILY_BY_CANONICAL, MANUAL_OVERRIDES
from cago.config.settings import SUPPORT_MATERIAL_TABLE

_WS = re.compile(r"\s+")


def material_key(raw: Any) -> str | None:
    """Lookup key: NFKC + casefold + whitespace collapse. Never used to alter material_raw."""
    if not isinstance(raw, str):
        return None
    s = _WS.sub(" ", unicodedata.normalize("NFKC", raw).casefold()).strip()
    return s or None


class MaterialMapper:
    """Maps raw material labels to (canonical, family, status).

    Statuses: mapped_source_canonical, mapped_source_alias, mapped_manual_override, unmapped, missing_material.
    Unmapped/missing -> canonical None, family 'unknown'.
    """

    def __init__(self, label_to_canonical: dict[str, str]) -> None:
        self.label_to_canonical = label_to_canonical
        self.canonical_names = set(label_to_canonical.values())
        # Override keys go through the same normalization as lookups (NFKC turns '™' into 'tm').
        self.overrides = {material_key(k): v for k, v in MANUAL_OVERRIDES.items()}

    @classmethod
    def from_support_dir(cls, support_dir: Path) -> "MaterialMapper":
        path = Path(support_dir) / SUPPORT_MATERIAL_TABLE
        mapping: dict[str, str] = {}
        with path.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                canon = row["canonical_material_name"].strip()
                mapping.setdefault(canon, canon)
                for label in row["raw_labels_joined"].split(" ; "):
                    key = material_key(label)
                    if key:
                        mapping[key] = canon
        return cls(mapping)

    def map(self, raw: Any) -> tuple[str | None, str, str]:
        key = material_key(raw)
        if key is None:
            return None, "unknown", "missing_material"
        canon = self.label_to_canonical.get(key)
        if canon is not None:
            status = "mapped_source_canonical" if key == canon else "mapped_source_alias"
            return canon, FAMILY_BY_CANONICAL.get(canon, "unknown"), status
        canon = self.overrides.get(key)
        if canon is not None:
            return canon, FAMILY_BY_CANONICAL.get(canon, "unknown"), "mapped_manual_override"
        return None, "unknown", "unmapped"
