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
