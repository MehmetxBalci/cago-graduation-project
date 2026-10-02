"""Centralised material configuration: family taxonomy and manual overrides.

`material_family` is a CAGO-derived taxonomy, NOT source ground truth.
Families: natural_plant, natural_animal, synthetic, regenerated_cellulosic,
leather, metal, other, unknown.
"""

# canonical material (from the supplied source mapping table) -> CAGO family.
FAMILY_BY_CANONICAL: dict[str, str] = {
    **{m: "synthetic" for m in (
        "nylon", "polyester", "elastane", "acrylic", "modacrylic", "elastodiene", "elastomultiester",
        "polyethylene", "polypropylene", "polyurethane", "tpu", "tpe", "eva", "ptfe", "polycarbonate",
        "polystyrene", "pbt", "pctg", "abs", "mabs", "pom", "pmma")},
    **{m: "natural_plant" for m in ("cotton", "linen", "hemp", "jute", "ramie")},
    **{m: "natural_animal" for m in ("wool", "cashmere", "alpaca", "mohair", "silk", "down", "feather")},
    # JUDGEMENT CALL: acetate/triacetate are semi-synthetic cellulose esters.
    **{m: "regenerated_cellulosic" for m in (
        "viscose", "modal", "lyocell", "cupro", "cellulose", "acetate", "triacetate")},
    **{m: "leather" for m in ("leather", "suede")},
    # JUDGEMENT CALL: metallised_fibre is a textile fibre but metal-dominated for sorting purposes.
    **{m: "metal" for m in ("metal", "steel", "iron", "brass", "zinc", "copper", "metallised_fibre")},
    **{m: "other" for m in ("paper", "glass", "pearl", "wax", "textile", "rubber", "latex", "silicone", "resin")},
    "unspecified_material": "unknown",
}

# Manual overrides: normalized raw label -> canonical. Reported with status
# `mapped_manual_override`. Restricted to brand/origin/trademark qualifiers whose base material
# is explicit in the label. Anything that changes meaning (recycled/reprocessed, alloys, wood,
# foams, "yak wool") is deliberately left UNMAPPED for human decision.
MANUAL_OVERRIDES: dict[str, str] = {
    "lyocell™ modal": "modal",        # TENCEL(TM) Modal
    "lyocell™ lyocell": "lyocell",    # TENCEL(TM) Lyocell
    "european linen™": "linen",
    "european linen ™": "linen",
    "australian wool": "wool",
    "sheep leather": "leather",
    "lamb leather": "leather",
    "cow leather": "leather",
    "goat leather": "leather",
    "goat suede": "suede",
    "polyethylene terephthalate": "polyester",  # PET; source table already maps label 'pet'
}
