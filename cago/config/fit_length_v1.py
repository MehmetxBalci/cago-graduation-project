"""Frozen Fit/Length V1 vocabulary and decision thresholds (defined from the TRAIN-only text-evidence audit)."""

FIT_LABELS_V1 = ("slim", "regular", "relaxed", "oversized")
LENGTH_LABELS_V1 = ("standard", "long")

# Raw evidence families merged into V1 labels (kept visible in `fit_merged_from`; never separate ML labels).
FIT_MERGES = {"skinny": "slim", "loose": "relaxed"}
# Evidence families removed from V1 ML conditioning. Treated as unsupported evidence (never as a label).
LENGTH_EXCLUDED = ("cropped",)

# Legacy/removed UI values -> replacement hint (None = no replacement). The V1 requirement schema is STRICT:
# these values are rejected with code `removed_in_v1`; no silent alias normalisation.
REMOVED_V1_VALUES = {"fit": {"skinny": "slim", "loose": "relaxed"}, "length_cut": {"cropped": None}}

# Capability rule (TRAIN only): a control is exposed for a detail_category only if at least one V1 label of that
# control has >= this many TRAIN garments AND >= this many distinct TRAIN parent products.
MIN_CATEGORY_TRAIN_GARMENTS = 100
MIN_CATEGORY_TRAIN_PARENTS = 50

CONTROL_LABELS = {"fit": FIT_LABELS_V1, "length_cut": LENGTH_LABELS_V1}
CONTROL_LABEL_COLUMN = {"fit": "fit_label", "length_cut": "length_label"}
