"""Single configuration point for Candidate Evaluation + Pareto Selection v1.

Nothing here is a physical claim: weights are reporting/aggregation choices that can be tuned or ablated.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# preference -> (confidence class, confidence weight)
INTENT_CONFIDENCE: dict[str, tuple[str, float]] = {
    "preferred_dominant_material": ("exact", 1.00),
    "colour": ("exact", 1.00),
    "fit": ("exact", 1.00),                 # label carried by the template (not re-derived after mutation)
    "length_cut": ("exact", 1.00),
    "stretch": ("strong_proxy", 1.00),      # elastane percentage
    "thermal_warmth": ("moderate_proxy", 0.75),
    "moisture_wicking": ("moderate_proxy", 0.75),
    "water_repellent": ("moderate_proxy", 0.75),
    "breathability": ("heuristic_proxy", 0.50),
    "durability_wear": ("heuristic_proxy", 0.50),
}

# Explicit proxy-score [-1, 1] -> satisfaction [0, 1] transforms.
#   affine_signed : satisfaction = (proxy + 1) / 2          (use when -1 means 'clearly contradicts the request')
#   clipped_reward: satisfaction = clamp(proxy, 0, 1)       (use for reward-only proxies where 0 = 'no supporting
#                   evidence'; the affine map would score 'no evidence' as 0.5, i.e. half satisfied)
PROXY_TRANSFORM: dict[str, str] = {
    "stretch": "affine_signed", "thermal_warmth": "clipped_reward", "breathability": "clipped_reward",
    "durability_wear": "clipped_reward", "moisture_wicking": "clipped_reward", "water_repellent": "clipped_reward",
}

# Requested values that mean "no special preference": reported as active but NOT scored.
NEUTRAL_VALUES: dict[str, str] = {"thermal_warmth": "standard", "breathability": "standard", "durability_wear": "standard"}

INTENT_ORDER = ("preferred_dominant_material", "stretch", "thermal_warmth", "breathability", "durability_wear",
                "moisture_wicking", "water_repellent", "fit", "length_cut", "colour")


@dataclass(frozen=True)
class EvaluationConfig:
    # --- intent
    confidence: dict = field(default_factory=lambda: dict(INTENT_CONFIDENCE))
    transform: dict = field(default_factory=lambda: dict(PROXY_TRANSFORM))
    satisfied_min: float = 0.99               # satisfaction >= this -> "satisfied"
    not_satisfied_max: float = 0.01           # satisfaction <= this -> "not satisfied", in between -> "partial"
    dominant_tie_tolerance: float = 1e-9
    # --- plausibility (dataset-relative; NOT manufacturability)
    w_context: float = 0.5
    w_proximity: float = 0.5
    context_aggregate: str = "mean"           # mean | min over active components
    prox_w_sub: float = 1.0                   # distance D = prox_w_sub*n_substitutions + prox_w_pct*abs_pct_change/100
    prox_w_pct: float = 1.0
    prox_decay: float = 0.5                   # proximity = exp(-prox_decay * D)
    plausibility_drop_substantial: float = 0.20   # reporting threshold (raw 0-1) vs template
    # --- pareto / selection
    max_violations: int = 5
    objective_decimals: int = 12              # objective values are rounded before comparisons (float-noise ties)
    balanced_normalization: str = "fixed"     # fixed: violations/5, losses already in [0,1] | front_minmax
