"""Central pipeline settings. Reference values are sanity checks only, never used in processing."""

PCT_TOLERANCE_LOW: float = 99.0
PCT_TOLERANCE_HIGH: float = 101.0
# Generated candidates must sum to 100 within numerical tolerance (source data keeps the 99-101 tolerance above).
CANDIDATE_PCT_SUM_ABS_TOL: float = 1e-6

SPLIT_RATIOS: tuple[float, float, float] = (0.70, 0.15, 0.15)  # train, val, test
SPLIT_SEED: int = 42
SPLIT_NAMES: tuple[str, str, str] = ("train", "val", "test")

SUPPORT_MATERIAL_TABLE = "4_material_normalization_table.csv"
SUPPORT_COMPONENT_TABLE = "6_component_name_summary_table.csv"

REQUIRED_GARMENT_FIELDS = (
    "parent_product_id", "brand", "region", "gender_section", "parent_category",
    "detail_category", "variant_colour", "composition_assignment_type", "components_structured",
)
REQUIRED_COMPONENT_FIELDS = ("component_path_raw", "component_name_norm", "component_class", "materials")

# User-supplied figures from a previous independent audit: (value, absolute tolerance).
# Used ONLY to print a discrepancy table in the audit. Processing never depends on them.
REFERENCE_AUDIT: dict[str, tuple[int, int]] = {
    "garments": (47522, 0),
    "unique_parent_products": (35860, 0),
    "exact_black_variants": (6515, 0),
    "components": (67500, 50),
    "material_occurrences": (118800, 50),
}
