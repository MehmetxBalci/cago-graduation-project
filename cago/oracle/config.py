"""CAGO Oracle v1 baseline configuration (Li & Walther 2026, SR1-SR5 'central' settings).

Material canonicalization mirrors the published rule implementation
(`01_evaluate_sorting_rules_frozen.py::canon_material`). It is intentionally separate from the
preprocessing `material_canonical` mapping: the published rules also fold cashmere/alpaca/mohair into wool.
"""

SR1_MONO: frozenset[str] = frozenset({"acrylic", "cotton", "nylon", "polyester", "viscose", "wool"})
SR1_BINARY: frozenset[frozenset[str]] = frozenset({
    frozenset({"acrylic", "cotton"}), frozenset({"acrylic", "wool"}), frozenset({"cotton", "elastane"}),
    frozenset({"cotton", "polyester"}), frozenset({"elastane", "polyester"}), frozenset({"polyester", "viscose"}),
})
SR3_THRESHOLD_PCT: float = 5.0   # violation iff non-dominant pct < threshold (5.0 itself passes)
SR5_THRESHOLD_PCT: float = 5.0   # violation iff hidden pct > threshold (5.0 itself passes)
SR4_BLACK: str = "black"

SURFACE_CLASS = "surface_component"
COATING_NAME = "coating"
HIDDEN_CLASSES: frozenset[str] = frozenset({"lining_component", "filling_component"})
HIDDEN_NAMES: frozenset[str] = frozenset({
    "lining", "body_lining", "hood_lining", "sleeve_lining", "skirt_lining", "cup_lining", "inner_layer",
    "interlining", "inner_pants", "petticoat", "filling", "padding", "body_filling", "upper_body_filling",
    "under_body_filling", "down_proof_fabric",
})

_CANON_SINGLE = {"spandex": "elastane", "lycra": "elastane", "rayon": "viscose", "flax": "linen",
                 "naia": "acetate", "supima": "cotton", "pp": "polypropylene", "tencel modal": "modal"}
_CANON_SETS = (
    ({"polyamide", "pa", "pa6", "pa66"}, "nylon"),
    ({"merino", "merino wool", "cashmere", "alpaca", "mohair"}, "wool"),
    ({"tencel", "tencel lyocell"}, "lyocell"),
    ({"pet", "pes", "repreve"}, "polyester"),
)


def canon_material(raw) -> str | None:
    """Published-rule canonicalization: strip+lower, then fixed synonym folding. Blank/None -> None."""
    if raw is None:
        return None
    m = str(raw).strip().lower()
    if not m:
        return None
    for members, target in _CANON_SETS:
        if m in members:
            return target
    return _CANON_SINGLE.get(m, m)


# Published baseline counts (Li & Walther 2026) for the authoritative 47,522-record dataset.
# Used ONLY by the reproduction audit; never used by the rules.
PUBLISHED_N: int = 47_522
PUBLISHED_COUNTS: dict[str, int] = {"SR1": 17_303, "SR2": 9_504, "SR3": 8_228, "SR4": 6_515, "SR5": 3_878, "ANY": 23_908}
