# CAGO sorting-aware generator V1 - audit (development: TRAIN + VAL only)

Terminology: Sorting Compatibility (SR1-SR5 rule satisfaction), Intent Alignment, Dataset-relative Plausibility; constraint-based probabilistic generation with sorting-aware proposal/repair. None of these is a recyclability, sustainability or manufacturability measure.

Working set splits: ['train', 'val']; TEST rows present: 0; support splits: ['train']. Requests audited: 43. Config: `{"n_templates": 10, "candidates_per_template": 8, "seed": 0, "min_mutations": 1, "max_mutations": 3, "max_proposal_attempts": 25, "sorting_aware_proposal": true, "sorting_aware_repair": true, "proposal_bias_strength": 2.0, "max_repair_steps": 3, "max_repair_proposals_per_step": 8, "allow_sr1_repair": true, "allow_sr2_repair": true, "allow_sr3_repair": true, "allow_sr5_repair": true, "allow_mutation_revert": true, "preserve_intent_floor": 0.15, "preserve_plausibility_floor": 0.15, "policy": "STRICT_SORTING"}`

Determinism (same seed, re-run identical): True. Budget respected: True

SR4 handling: SR4 (colour == 'black') is immutable in Generator B V1 because colour is not mutated; it is counted as 'sr4_immutable_violation', never as an unresolved repairable rule.

## B3 / STRICT_SORTING

candidates 2804; with accepted repair 635; traced steps 3230; all proposed materials TRAIN-supported: True

| operation | evaluated | accepted | confirmed targeted fix | introduced other violation |
|---|---|---|---|---|
| revert_mutation_step | 603 | 15 | 28 | 147 |
| sr1_supported_binary_pair | 838 | 93 | 838 | 109 |
| sr1_supported_slot_substitution | 699 | 277 | 443 | 93 |
| sr2_merge_fibre_into_existing_fibre | 661 | 107 | 362 | 22 |
| sr3_raise_minor_fibre_to_5pct | 64 | 45 | 54 | 0 |
| sr3_replace_minor_fibre_with_existing_fibre | 135 | 42 | 122 | 0 |
| sr5_lower_hidden_pct_to_5pct | 23 | 11 | 15 | 0 |
| sr5_substitute_hidden_with_surface_fibre | 207 | 70 | 168 | 0 |

by targeted rule: {"SR1": {"evaluated": 1828, "accepted": 375, "confirmed_fixed_targeted_rule": 1287}, "SR2": {"evaluated": 661, "accepted": 107, "confirmed_fixed_targeted_rule": 362}, "SR3": {"evaluated": 216, "accepted": 88, "confirmed_fixed_targeted_rule": 178}, "SR5": {"evaluated": 525, "accepted": 90, "confirmed_fixed_targeted_rule": 203}}

rejection reasons: {"plausibility_floor": 611, "no_violation_decrease": 1345, "intent_floor": 614}

accepted repair deltas - violations: {'n': 660, 'mean': -1.19, 'median': -1.0, 'std': 0.42, 'min': -3.0, 'p25': -1.0, 'p75': -1.0, 'max': -1.0}; intent: {'n': 441, 'mean': 0.0325, 'median': 0.0, 'std': 0.1216, 'min': 0.0, 'p25': 0.0, 'p75': 0.0, 'max': 0.6667}; plausibility: {'n': 660, 'mean': 0.0954, 'median': 0.0433, 'std': 0.1858, 'min': -0.1493, 'p25': -0.0398, 'p75': 0.2198, 'max': 0.8129}

search counters: {"candidates_final": 2804, "candidates_with_unresolved_repairable": 439, "confirmed_fixed:SR1": 850, "confirmed_fixed:SR2": 123, "confirmed_fixed:SR3": 130, "confirmed_fixed:SR5": 1049, "fast_rule_evals": 413009, "intent_evals": 18110, "mutation_attempts": 12748, "oracle_full_evals": 18110, "plausibility_evals": 18110, "proposals_introducing_other_violation": 394, "repair_accepted": 1999, "repair_accepted:SR1": 742, "repair_accepted:SR2": 115, "repair_accepted:SR3": 126, "repair_accepted:SR5": 1016, "repair_cycle_prevented": 2, "repair_proposals_evaluated": 5362, "repair_rejected:intent_floor": 908, "repair_rejected:no_violation_decrease": 1655, "repair_rejected:plausibility_floor": 800, "repair_steps_started": 2755, "sr4_immutable_violation": 510, "unresolved:SR1": 260, "unresolved:SR2": 177, "unresolved:SR3": 16, "unresolved:SR5": 202}

### Example repair traces (entries omitted)

- `candB_3489a1ceb3d90804`: [0] SR2/sr2_merge_fibre_into_existing_fibre ACCEPT vc 2->0 fixed=['SR1', 'SR2'] introduced=[] dIntent=None dPlaus=-0.025844
- `candB_ea9d0f12406f2d41`: [0] SR2/sr2_merge_fibre_into_existing_fibre ACCEPT vc 2->0 fixed=['SR1', 'SR2'] introduced=[] dIntent=None dPlaus=0.035706
- `candB_61dc86ffc20fed05`: [0] SR2/sr2_merge_fibre_into_existing_fibre ACCEPT vc 2->0 fixed=['SR1', 'SR2'] introduced=[] dIntent=None dPlaus=-0.014946
- `candB_2c01f3544d8267c7`: [0] SR2/sr2_merge_fibre_into_existing_fibre ACCEPT vc 2->0 fixed=['SR1', 'SR2'] introduced=[] dIntent=None dPlaus=-0.031544
- `candB_8d4e36046a94ceb8`: [0] SR1/sr1_supported_binary_pair ACCEPT vc 1->0 fixed=['SR1'] introduced=[] dIntent=None dPlaus=0.447578

## B3 / NONDOMINATED_LOCAL

candidates 2765; with accepted repair 611; traced steps 4122; all proposed materials TRAIN-supported: True

| operation | evaluated | accepted | confirmed targeted fix | introduced other violation |
|---|---|---|---|---|
| revert_mutation_step | 713 | 272 | 51 | 192 |
| sr1_supported_binary_pair | 913 | 76 | 913 | 156 |
| sr1_supported_slot_substitution | 1163 | 224 | 581 | 123 |
| sr2_merge_fibre_into_existing_fibre | 870 | 74 | 533 | 27 |
| sr3_raise_minor_fibre_to_5pct | 63 | 15 | 52 | 0 |
| sr3_replace_minor_fibre_with_existing_fibre | 112 | 22 | 95 | 1 |
| sr5_lower_hidden_pct_to_5pct | 35 | 1 | 29 | 0 |
| sr5_substitute_hidden_with_surface_fibre | 253 | 52 | 212 | 0 |

by targeted rule: {"SR1": {"evaluated": 2474, "accepted": 443, "confirmed_fixed_targeted_rule": 1500}, "SR2": {"evaluated": 870, "accepted": 74, "confirmed_fixed_targeted_rule": 533}, "SR3": {"evaluated": 213, "accepted": 51, "confirmed_fixed_targeted_rule": 154}, "SR5": {"evaluated": 565, "accepted": 168, "confirmed_fixed_targeted_rule": 279}}

rejection reasons: {"not_locally_nondominated": 3386}

accepted repair deltas - violations: {'n': 736, 'mean': -0.73, 'median': -1.0, 'std': 0.64, 'min': -3.0, 'p25': -1.0, 'p75': 0.0, 'max': 0.0}; intent: {'n': 509, 'mean': 0.0291, 'median': 0.0, 'std': 0.1105, 'min': 0.0, 'p25': 0.0, 'p75': 0.0, 'max': 0.6667}; plausibility: {'n': 736, 'mean': 0.1396, 'median': 0.0735, 'std': 0.1557, 'min': 0.0, 'p25': 0.0097, 'p75': 0.2313, 'max': 0.8129}

search counters: {"accepted_repairs_introducing_other_violation": 14, "candidates_final": 2765, "candidates_with_unresolved_repairable": 458, "confirmed_fixed:SR1": 704, "confirmed_fixed:SR2": 74, "confirmed_fixed:SR3": 73, "confirmed_fixed:SR5": 1323, "fast_rule_evals": 496505, "intent_evals": 25506, "mutation_attempts": 14121, "no_train_supported_alternative:SR1": 5, "no_train_supported_alternative:SR2": 5, "no_train_supported_alternative:SR5": 128, "oracle_full_evals": 25506, "plausibility_evals": 25506, "proposals_introducing_other_violation": 838, "repair_accepted": 3428, "repair_accepted:SR1": 1116, "repair_accepted:SR2": 86, "repair_accepted:SR3": 111, "repair_accepted:SR5": 2115, "repair_cycle_prevented": 46, "repair_proposals_evaluated": 11385, "repair_rejected:not_locally_nondominated": 7957, "repair_steps_started": 4916, "sr4_immutable_violation": 492, "unresolved:SR1": 335, "unresolved:SR2": 170, "unresolved:SR3": 33, "unresolved:SR5": 152}

### Example repair traces (entries omitted)

- `candB_7df8d2883de62304`: [0] SR2/sr2_merge_fibre_into_existing_fibre ACCEPT vc 2->0 fixed=['SR1', 'SR2'] introduced=[] dIntent=None dPlaus=0.035706
- `candB_60ba6b23face63b4`: [0] SR2/sr2_merge_fibre_into_existing_fibre reject:not_locally_nondominated vc 2->0 fixed=['SR1', 'SR2'] introduced=[] dIntent=None dPlaus=-0.014946; [1] SR2/sr2_merge_fibre_into_existing_fibre reject:not_locally_nondominated vc 2->0 fixed=['SR1', 'SR2'] introduced=[] dIntent=None dPlaus=-0.014946; [2] SR2/sr2_merge_fibre_into_existing_fibre reject:not_locally_nondominated vc 2->0 fixed=['SR1', 'SR2'] introduced=[] dIntent=None dPlaus=-0.321105; [3] SR2/sr2_merge_fibre_into_existing_fibre reject:not_locally_nondominated vc 2->0 fixed=['SR1', 'SR2'] introduced=[] dIntent=None dPlaus=-0.321105
- `candB_51365645630433d5`: [0] SR1/sr1_supported_binary_pair ACCEPT vc 1->0 fixed=['SR1'] introduced=[] dIntent=None dPlaus=0.447578
- `candB_7760a63931745fe2`: [0] SR1/sr1_supported_binary_pair reject:not_locally_nondominated vc 2->1 fixed=['SR1'] introduced=[] dIntent=None dPlaus=-0.038814; [1] SR1/sr1_supported_binary_pair ACCEPT vc 2->1 fixed=['SR1'] introduced=[] dIntent=None dPlaus=0.080513
- `candB_f9083cac10610035`: [0] SR3/sr3_replace_minor_fibre_with_existing_fibre ACCEPT vc 2->0 fixed=['SR1', 'SR3'] introduced=[] dIntent=None dPlaus=0.210698
