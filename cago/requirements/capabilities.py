"""Editable per-category capability table.

`category_capabilities.json` (in this package) is the source of truth and is meant to be edited by hand.
`generate_capabilities` only produces a first draft from the dataset's categories using DEFAULT_CONTROLS;
those defaults are design judgements (not data-derived) and are flagged for human review.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from cago.requirements.schema import CAPABILITY_FIELDS

CAPABILITIES_PATH = Path(__file__).with_name("category_capabilities.json")
_ORDER = CAPABILITY_FIELDS  # stretch, thermal_warmth, breathability, durability_wear, moisture_wicking, water_repellent, fit, length_cut


def _c(*enabled: str) -> dict[str, bool]:
    return {f: (f in enabled) for f in _ORDER}


# Draft capability defaults. Judgement calls; edit category_capabilities.json, not this table, once generated.
DEFAULT_CONTROLS: dict[str, dict[str, bool]] = {
    "bras_lingerie": _c("stretch", "breathability"),
    "dresses": _c("stretch", "thermal_warmth", "breathability", "fit", "length_cut"),
    "jeans": _c("stretch", "breathability", "durability_wear", "fit", "length_cut"),
    "joggers": _c("stretch", "thermal_warmth", "breathability", "durability_wear", "moisture_wicking", "fit", "length_cut"),
    "jumpsuits_overalls": _c("stretch", "thermal_warmth", "breathability", "durability_wear", "fit", "length_cut"),
    "leggings": _c("stretch", "thermal_warmth", "breathability", "moisture_wicking", "fit", "length_cut"),
    "outerwear_coat": _c("thermal_warmth", "breathability", "durability_wear", "water_repellent", "fit", "length_cut"),
    "outerwear_gilet": _c("thermal_warmth", "breathability", "durability_wear", "water_repellent", "fit"),
    "outerwear_jacket": _c("stretch", "thermal_warmth", "breathability", "durability_wear", "water_repellent", "fit", "length_cut"),
    "set": _c("stretch", "thermal_warmth", "breathability", "fit"),
    "shirt_blouse": _c("stretch", "breathability", "fit", "length_cut"),
    "shorts": _c("stretch", "breathability", "durability_wear", "moisture_wicking", "fit", "length_cut"),
    "skirts": _c("stretch", "breathability", "fit", "length_cut"),
    "sleepwear_homewear": _c("stretch", "thermal_warmth", "breathability", "fit", "length_cut"),
    "socks_hosiery": _c("stretch", "thermal_warmth", "breathability", "durability_wear", "moisture_wicking"),
    "sweater_cardigan": _c("stretch", "thermal_warmth", "breathability", "fit", "length_cut"),
    "sweatshirt_hoodie": _c("stretch", "thermal_warmth", "breathability", "fit", "length_cut"),
    "swimwear": _c("stretch", "moisture_wicking"),
    "tank_camisole_vest": _c("stretch", "breathability", "moisture_wicking", "fit", "length_cut"),
    "top_generic": _c("stretch", "thermal_warmth", "breathability", "moisture_wicking", "fit", "length_cut"),
    "trousers": _c("stretch", "thermal_warmth", "breathability", "durability_wear", "water_repellent", "fit", "length_cut"),
    "tshirt_polo": _c("stretch", "breathability", "moisture_wicking", "fit", "length_cut"),
    "underwear_bottoms": _c("stretch", "breathability", "moisture_wicking"),
}
# Categories whose draft rows are least certain; surfaced in the representation audit for human review.
REVIEW_CATEGORIES = ("set", "top_generic", "sleepwear_homewear", "jumpsuits_overalls", "swimwear")


def generate_capabilities(category_to_parent: dict[str, str], source: str) -> dict[str, Any]:
    """Draft table covering exactly the given categories. Categories lacking a default get ALL controls disabled."""
    cats = {}
    for cat in sorted(category_to_parent):
        controls = DEFAULT_CONTROLS.get(cat)
        cats[cat] = {"parent_category": category_to_parent[cat],
                     "controls": dict(controls) if controls else _c(),
                     "needs_review": cat in REVIEW_CATEGORIES or controls is None}
    return {"version": 1, "source": source,
            "always_available": ["forbidden_materials", "preferred_dominant_material", "colour"],
            "note": "Draft derived from dataset categories + design judgement; edit controls freely. "
                    "A disabled control makes the request field ignored with a 'control_not_available' warning.",
            "categories": cats}


def load_capabilities(path: Path = CAPABILITIES_PATH) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as fh:
        return json.load(fh)


def save_capabilities(caps: dict[str, Any], path: Path = CAPABILITIES_PATH) -> None:
    Path(path).write_text(json.dumps(caps, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def controls_for(caps: dict[str, Any], category: str) -> dict[str, bool]:
    return caps["categories"][category]["controls"]


def coverage_report(caps: dict[str, Any], dataset_categories: Iterable[str]) -> dict[str, Any]:
    ds, cp = set(dataset_categories), set(caps.get("categories", {}))
    return {"dataset_categories": len(ds), "capability_categories": len(cp),
            "missing_in_capabilities": sorted(ds - cp), "extra_in_capabilities": sorted(cp - ds)}


# ---------------------------------------------------------------- TRAIN-evidence revision (Fit/Length V1)
def fit_length_support(rep) -> dict[str, dict[str, dict[str, dict[str, int]]]]:
    """TRAIN-only support: {detail_category: {control: {label: {garments, parents}}}} for the V1 labels.

    `rep` needs columns split, detail_category, parent_product_id, fit_label, length_label. VAL/TEST rows are ignored.
    """
    from cago.config.fit_length_v1 import CONTROL_LABEL_COLUMN, CONTROL_LABELS
    tr = rep[rep["split"] == "train"]
    out: dict[str, dict[str, dict[str, dict[str, int]]]] = {}
    for cat in sorted(rep["detail_category"].dropna().unique()):
        sub = tr[tr["detail_category"] == cat]
        out[cat] = {}
        for ctrl, labels in CONTROL_LABELS.items():
            col = CONTROL_LABEL_COLUMN[ctrl]
            out[cat][ctrl] = {lab: {"garments": int((sub[col] == lab).sum()),
                                    "parents": int(sub.loc[sub[col] == lab, "parent_product_id"].nunique())}
                              for lab in labels}
    return out


def is_supported(label_support: dict[str, dict[str, int]], min_garments: int | None = None,
                 min_parents: int | None = None) -> bool:
    from cago.config.fit_length_v1 import MIN_CATEGORY_TRAIN_GARMENTS, MIN_CATEGORY_TRAIN_PARENTS
    mg = MIN_CATEGORY_TRAIN_GARMENTS if min_garments is None else min_garments
    mp = MIN_CATEGORY_TRAIN_PARENTS if min_parents is None else min_parents
    return any(v["garments"] >= mg and v["parents"] >= mp for v in label_support.values())


def revise_capabilities(caps: dict[str, Any], support: dict[str, Any], min_garments: int | None = None,
                        min_parents: int | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Disable `fit` / `length_cut` where TRAIN support is insufficient (disable-only, idempotent).

    A control stays enabled only if it was enabled AND >=1 V1 label has the minimum TRAIN support. Controls that
    are disabled by design but have support are listed for human review and are NOT auto-enabled.
    """
    import copy
    from cago.config.fit_length_v1 import (CONTROL_LABELS, FIT_LABELS_V1, LENGTH_LABELS_V1, MIN_CATEGORY_TRAIN_GARMENTS,
                                           MIN_CATEGORY_TRAIN_PARENTS)
    mg = MIN_CATEGORY_TRAIN_GARMENTS if min_garments is None else min_garments
    mp = MIN_CATEGORY_TRAIN_PARENTS if min_parents is None else min_parents
    new = copy.deepcopy(caps)
    changes: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    for cat, entry in new["categories"].items():
        sup = support.get(cat, {})
        entry["fit_length_support_train"] = {c: sup.get(c, {l: {"garments": 0, "parents": 0} for l in CONTROL_LABELS[c]})
                                             for c in CONTROL_LABELS}
        entry["fit_length_supported_labels"] = {      # informational (not enforced): labels meeting the TRAIN thresholds
            ctrl: [l for l, v in entry["fit_length_support_train"][ctrl].items()
                   if v["garments"] >= mg and v["parents"] >= mp] for ctrl in CONTROL_LABELS}
        decisions = entry.setdefault("control_decisions", {})
        for ctrl in CONTROL_LABELS:
            supported = is_supported(entry["fit_length_support_train"][ctrl], mg, mp)
            on = entry["controls"].get(ctrl, False)
            if on and supported:
                decisions[ctrl] = "enabled"
            elif on:
                entry["controls"][ctrl] = False
                decisions[ctrl] = "disabled_insufficient_train_support"
                changes.append({"category": cat, "control": ctrl, "from": True, "to": False,
                                "train_support": entry["fit_length_support_train"][ctrl]})
            else:
                decisions[ctrl] = decisions.get(ctrl) if decisions.get(ctrl) == "disabled_insufficient_train_support" \
                    else "disabled_by_design"
                if supported and decisions[ctrl] == "disabled_by_design":
                    review.append({"category": cat, "control": ctrl, "train_support": entry["fit_length_support_train"][ctrl]})
    prev = {(c["category"], c["control"]): c for c in caps.get("fit_length_v1", {}).get("changes", [])}
    for c in changes:
        prev[(c["category"], c["control"])] = c
    new["fit_length_v1"] = {
        "basis": "TRAIN split only (val/test never used)",
        "rule": "a control stays enabled only if previously enabled AND >=1 V1 label has >= min_garments train garments "
                "and >= min_parents distinct train parent products; disable-only; supported-but-disabled controls are "
                "listed for human review",
        "thresholds": {"min_garments": mg, "min_parents": mp},
        "labels": {"fit": list(FIT_LABELS_V1), "length_cut": list(LENGTH_LABELS_V1)},
        "changes": sorted(prev.values(), key=lambda c: (c["category"], c["control"])),
        "supported_but_disabled_by_design": review,
    }
    return new, changes
