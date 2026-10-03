"""User-request schema: field names, enums, and result containers (no ML, no LLM parsing)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cago.config.fit_length_v1 import FIT_LABELS_V1, LENGTH_LABELS_V1, REMOVED_V1_VALUES  # noqa: F401

REQUIRED_FIELDS = ("target_segment", "detail_category")  # values: source gender_section (women/men/kids/baby)
HARD_FIELDS = ("forbidden_materials",)
FUNCTIONAL_FIELDS = ("stretch", "thermal_warmth", "breathability", "durability_wear",
                     "moisture_wicking", "water_repellent")
SOFT_FIELDS = ("preferred_dominant_material", *FUNCTIONAL_FIELDS, "fit", "length_cut", "colour")
ALL_FIELDS = (*REQUIRED_FIELDS, *HARD_FIELDS, *SOFT_FIELDS)

# Fields whose availability depends on detail_category (see category_capabilities.json).
CAPABILITY_FIELDS = (*FUNCTIONAL_FIELDS, "fit", "length_cut")

ENUMS: dict[str, tuple[str, ...]] = {
    "stretch": ("none", "low", "high"),
    "thermal_warmth": ("light", "standard", "heavy"),
    "breathability": ("standard", "high"),
    "durability_wear": ("standard", "reinforced"),
    "fit": FIT_LABELS_V1,              # V1: skinny -> slim, loose -> relaxed (merged upstream; rejected here)
    "length_cut": LENGTH_LABELS_V1,    # V1: cropped removed
}
TRUE_ONLY_FIELDS = ("moisture_wicking", "water_repellent")   # allowed values: True or None


@dataclass(frozen=True)
class Issue:
    """Validation error or warning."""
    code: str
    field: str | tuple[str, ...] | None
    message: str

    def to_dict(self) -> dict[str, Any]:
        f = list(self.field) if isinstance(self.field, tuple) else self.field
        return {"code": self.code, "field": f, "message": self.message}


@dataclass
class RequirementResult:
    """Outcome of validating one request. `request` is None when there are errors."""
    ok: bool
    request: dict[str, Any] | None
    errors: list[Issue] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)

    def error_codes(self) -> list[str]:
        return [e.code for e in self.errors]

    def warning_codes(self) -> list[str]:
        return [w["code"] for w in self.warnings]
