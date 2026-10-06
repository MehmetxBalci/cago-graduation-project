"""Configuration for Sorting-Aware Candidate Generator V1 (Generator B). Every probability/limit is configurable.

Development rules: only TRAIN statistics and VAL development requests are used; TEST is never read.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from cago.generation.mutations import MutationSettings

STRICT_SORTING = "STRICT_SORTING"
NONDOMINATED_LOCAL = "NONDOMINATED_LOCAL"
POLICIES = (STRICT_SORTING, NONDOMINATED_LOCAL)
REPAIRABLE_RULES = ("SR1", "SR2", "SR3", "SR5")
IMMUTABLE_RULES = ("SR4",)          # colour is not mutated in Generator B V1 -> SR4 cannot be repaired by fibre mutation


@dataclass(frozen=True)
class SortingAwareGenerationConfig:
    # --- budget (kept equal to Baseline A for the fair comparison)
    n_templates: int = 10
    candidates_per_template: int = 8
    seed: int = 42
    min_mutations: int = 1
    max_mutations: int = 3
    max_proposal_attempts: int = 25            # per candidate slot, as in Baseline A
    # --- modes (both can be on)
    sorting_aware_proposal: bool = True
    sorting_aware_repair: bool = True
    proposal_bias_strength: float = 2.0        # proposal weight *= exp(strength * (repairable violations removed - added))
    # --- repair
    max_repair_steps: int = 3
    max_repair_proposals_per_step: int = 8
    allow_sr1_repair: bool = True
    allow_sr2_repair: bool = True
    allow_sr3_repair: bool = True
    allow_sr5_repair: bool = True
    allow_mutation_revert: bool = True         # inverse of a random mutation step (restores the TRAIN template's own value)
    # --- protection (raw 0-1 units; None disables a floor). Not tuned on TEST.
    preserve_intent_floor: float | None = 0.15
    preserve_plausibility_floor: float | None = 0.15
    policy: str = STRICT_SORTING
    # --- reused frozen settings
    mutation_settings: MutationSettings = field(default_factory=MutationSettings)

    def allowed_rules(self) -> tuple[str, ...]:
        flags = {"SR1": self.allow_sr1_repair, "SR2": self.allow_sr2_repair, "SR3": self.allow_sr3_repair, "SR5": self.allow_sr5_repair}
        return tuple(r for r in REPAIRABLE_RULES if flags[r])

    def mode_name(self) -> str:
        return {(True, False): "B1_proposal_only", (False, True): "B2_repair_only", (True, True): "B3_proposal_plus_repair",
                (False, False): "B0_no_sorting_awareness"}[(self.sorting_aware_proposal, self.sorting_aware_repair)]


MODE_CONFIGS = {
    "B1": {"sorting_aware_proposal": True, "sorting_aware_repair": False},
    "B2": {"sorting_aware_proposal": False, "sorting_aware_repair": True},
    "B3": {"sorting_aware_proposal": True, "sorting_aware_repair": True},
}
