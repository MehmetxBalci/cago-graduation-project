# CAGO - Final held-out TEST evaluation: Generator A vs Generator B3

Terminology: SR1-SR5 Sorting Compatibility (violation count under the screening rules; zero violations does NOT mean recyclable), Intent Alignment, Dataset-relative Plausibility, constraint-based probabilistic generation with sorting-aware proposal/repair. Not a recyclability, sustainability or manufacturability measure.

Frozen manifest digest: `37645a68f848099bbc3176d836155b91cd05d20a17ec4c15f6eba6ccaf629551` (verification ok = True; evaluation split = test). Determinism re-run identical: True (20 checks).

## 1. Integrity

```json
{
 "split_integrity": {
  "parents_per_split": {
   "train": 25126,
   "val": 5348,
   "test": 5386
  },
  "garments_per_split": {
   "train": 33265,
   "val": 7128,
   "test": 7129
  },
  "parent_overlap": {
   "train&val": 0,
   "train&test": 0,
   "val&test": 0
  },
  "garment_overlap": {
   "train&val": 0,
   "train&test": 0,
   "val&test": 0
  },
  "garment_id_unique": true,
  "unknown_splits": [],
  "null_parent_rows": 0,
  "split_mapping_consistent_with_representation": true,
  "ok": true
 },
 "generator_input_splits": [
  "train"
 ],
 "support_splits_used": [
  "train"
 ],
 "support_train_garments": 33265,
 "evaluation_split": "test",
 "templates_all_from_train": true
}
```

## 2. Request coverage

Requests 469 (run 469, invalid 0); cells 72; categories 23; segments {'baby': 37, 'kids': 157, 'men': 114, 'women': 161}; types {'no_pref': 72, 'derived_full': 199, 'derived_forbid': 198}; distinct held-out parents in derived requests 381 (397 derived requests; parents with >1 request 16; parent reuse across types 16).

Evaluation-split eligibility (nothing silently dropped): `{"garments": 7129, "parents": 5386, "by_reason": {"eligible": 7088, "non_vocab_material_token": 29, "unmapped_material": 12}, "eligible_parents": 5349, "cells": 72, "cells_with_eligible_garment": 72, "cells_without_eligible_garment": []}`

## 3. Comparison conditions

```json
{
 "requests_in_both": 469,
 "requests_run": 469,
 "identical_template_selection": true,
 "identical_eligible_pool_size": true,
 "identical_requested_budget": true,
 "identical_evaluation_config": true,
 "evaluation_config_fields": [
  "balanced_normalization",
  "confidence",
  "context_aggregate",
  "dominant_tie_tolerance",
  "max_violations",
  "not_satisfied_max",
  "objective_decimals",
  "plausibility_drop_substantial",
  "prox_decay",
  "prox_w_pct",
  "prox_w_sub",
  "satisfied_min",
  "transform",
  "w_context",
  "w_proximity"
 ]
}
```

Requested candidates, template pool, template selection, seed, attempt limit and evaluation are identical. Computational cost is NOT equal: Generator B3 performs additional Oracle-guided rule evaluations, Oracle calls and Intent/Plausibility evaluations for repairs (see ratios).

## 4. Generation coverage

| variant | requested | generated | gen/req | unique | unique rate | hard-valid rate | requests w/o candidate | selection availability (D/E/F) | front median | front==1 |
|---|---|---|---|---|---|---|---|---|---|---|
| A_baseline | 37520 | 33178 | 0.8843 | 31779 | 0.9578 | 1.0 | 8 | {"D_balanced": 461, "E_sorting_focused": 461, "F_intent_focused": 391} | 3.0 | 0.2408 |
| B3_proposal_plus_repair | 37520 | 30598 | 0.8155 | 30598 | 1.0 | 1.0 | 8 | {"D_balanced": 461, "E_sorting_focused": 461, "F_intent_focused": 391} | 2.0 | 0.2777 |

## 5. Stage results (pooled rows; descriptive)

Stage A, original selected TRAIN templates: rows 4357, violation mean 1.042, zero-violation 0.4319, SR rates {"SR1": 0.3888, "SR2": 0.2061, "SR3": 0.1873, "SR4": 0.1678, "SR5": 0.0918}, intent median 80.0, plausibility median 90.38.

### B_hard_valid_candidates

| variant | rows | viol mean | zero-viol | SR1-SR5 | intent med | intent mean | plaus med | plaus mean | mean dist |
|---|---|---|---|---|---|---|---|---|---|
| A_baseline | 33178 | 1.325 | 0.2562 | {"SR1": 0.5702, "SR2": 0.2172, "SR3": 0.2049, "SR4": 0.172, "SR5": 0.1604} | 66.67 | 68.76 | 58.05 | 59.07 | 0.908 |
| B3_proposal_plus_repair | 30598 | 0.435 | 0.6971 | {"SR1": 0.1133, "SR2": 0.0642, "SR3": 0.0228, "SR4": 0.1722, "SR5": 0.0629} | 66.67 | 68.25 | 67.26 | 66.15 | 1.05 |

### C_pareto_front

| variant | rows | viol mean | zero-viol | SR1-SR5 | intent med | intent mean | plaus med | plaus mean | mean dist |
|---|---|---|---|---|---|---|---|---|---|
| A_baseline | 1344 | 0.7 | 0.5692 | {"SR1": 0.2582, "SR2": 0.1205, "SR3": 0.1421, "SR4": 0.1109, "SR5": 0.0685} | 80.0 | 79.42 | 89.89 | 86.68 | 0.279 |
| B3_proposal_plus_repair | 1359 | 0.528 | 0.6696 | {"SR1": 0.1928, "SR2": 0.0964, "SR3": 0.0603, "SR4": 0.1141, "SR5": 0.0648} | 80.0 | 79.2 | 89.2 | 86.34 | 0.361 |

### D_balanced

| variant | rows | viol mean | zero-viol | SR1-SR5 | intent med | intent mean | plaus med | plaus mean | mean dist |
|---|---|---|---|---|---|---|---|---|---|
| A_baseline | 461 | 0.377 | 0.6963 | {"SR1": 0.1605, "SR2": 0.0412, "SR3": 0.0781, "SR4": 0.0542, "SR5": 0.0434} | 100.0 | 90.59 | 90.58 | 88.36 | 0.193 |
| B3_proposal_plus_repair | 461 | 0.275 | 0.7787 | {"SR1": 0.0933, "SR2": 0.0325, "SR3": 0.0651, "SR4": 0.0521, "SR5": 0.0325} | 100.0 | 90.17 | 90.79 | 88.24 | 0.265 |

### E_sorting_focused

| variant | rows | viol mean | zero-viol | SR1-SR5 | intent med | intent mean | plaus med | plaus mean | mean dist |
|---|---|---|---|---|---|---|---|---|---|
| A_baseline | 461 | 0.102 | 0.9414 | {"SR1": 0.0347, "SR2": 0.0325, "SR3": 0.0108, "SR4": 0.0239, "SR5": 0.0} | 100.0 | 82.95 | 88.27 | 84.99 | 0.336 |
| B3_proposal_plus_repair | 461 | 0.035 | 0.9761 | {"SR1": 0.0065, "SR2": 0.0065, "SR3": 0.0043, "SR4": 0.0174, "SR5": 0.0} | 100.0 | 84.52 | 88.26 | 85.0 | 0.402 |

### F_intent_focused

| variant | rows | viol mean | zero-viol | SR1-SR5 | intent med | intent mean | plaus med | plaus mean | mean dist |
|---|---|---|---|---|---|---|---|---|---|
| A_baseline | 391 | 0.414 | 0.7187 | {"SR1": 0.156, "SR2": 0.0742, "SR3": 0.0921, "SR4": 0.0716, "SR5": 0.0205} | 100.0 | 92.88 | 87.95 | 84.3 | 0.314 |
| B3_proposal_plus_repair | 391 | 0.307 | 0.7775 | {"SR1": 0.1125, "SR2": 0.0435, "SR3": 0.0742, "SR4": 0.0665, "SR5": 0.0102} | 100.0 | 92.35 | 87.83 | 84.94 | 0.369 |

## 6. Pre-specified primary outcomes (B3 - A; paired by request; 95% bootstrap CI)

| outcome | paired n | only A | only B3 | neither | mean A | mean B3 | mean diff | CI parent-clustered | CI cell-clustered | CI request-level | median diff | median CI (parent) | B3 lower/equal/higher |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B_hard_valid_candidates : vc_mean | 461 | 0 | 0 | 8 | 1.29816 | 0.42108 | -0.8771 | [-0.9167, -0.8397] | [-0.9347, -0.8201] | [-0.9145, -0.8404] | -0.79872 | [-0.8659, -0.7478] | 456/5/0 |
| E_sorting_focused : vc_mean | 461 | 0 | 0 | 8 | 0.10195 | 0.03471 | -0.0673 | [-0.1007, -0.0389] | [-0.1375, -0.0171] | [-0.0998, -0.0369] | 0 | [+0.0000, +0.0000] | 18/443/0 |
| B_hard_valid_candidates : zero_share | 461 | 0 | 0 | 8 | 0.26792 | 0.70842 | +0.4405 | [+0.4229, +0.4578] | [+0.4115, +0.4678] | [+0.4235, +0.4582] | 0.44595 | [+0.4278, +0.4583] | 0/14/447 |
| D_balanced : intent_mean | 391 | 0 | 0 | 78 | 0.90593 | 0.90171 | -0.0042 | [-0.0112, +0.0018] | [-0.0112, +0.0019] | [-0.0111, +0.0021] | 0.0 | [+0.0000, +0.0000] | 8/378/5 |
| D_balanced : plaus_mean | 461 | 0 | 0 | 8 | 0.88357 | 0.88239 | -0.0012 | [-0.0054, +0.0032] | [-0.0059, +0.0039] | [-0.0055, +0.0027] | 0.0 | [+0.0000, +0.0000] | 67/308/86 |

Lower violation_count is better; higher Intent / Plausibility is better. Primary CI = parent-clustered.

## 7. All paired differences (exploratory)

### B_hard_valid_candidates

| metric | paired n | mean diff | median diff | CI parent | CI cell | B3 lower/equal/higher |
|---|---|---|---|---|---|---|
| vc_mean | 461 | -0.8771 | -0.79872 | [-0.9167, -0.8397] | [-0.9347, -0.8201] | 456/5/0 |
| zero_share | 461 | +0.4405 | 0.44595 | [+0.4229, +0.4578] | [+0.4115, +0.4678] | 0/14/447 |
| SR1_rate | 461 | -0.4531 | -0.46411 | [-0.4683, -0.4382] | [-0.4772, -0.4281] | 455/6/0 |
| SR2_rate | 461 | -0.1492 | -0.1 | [-0.1663, -0.1332] | [-0.1761, -0.1245] | 284/170/7 |
| SR3_rate | 461 | -0.1833 | -0.10667 | [-0.2027, -0.1640] | [-0.2168, -0.1515] | 371/89/1 |
| SR4_rate | 461 | -0.0001 | 0.0 | [-0.0023, +0.0020] | [-0.0032, +0.0032] | 66/272/123 |
| SR5_rate | 461 | -0.0914 | -0.03947 | [-0.1033, -0.0803] | [-0.1154, -0.0682] | 270/187/4 |
| intent_mean | 391 | -0.0053 | 0.0 | [-0.0133, +0.0020] | [-0.0166, +0.0048] | 189/9/193 |
| plaus_mean | 461 | +0.0675 | 0.06492 | [+0.0632, +0.0718] | [+0.0591, +0.0753] | 32/3/426 |
| dist_mean | 461 | +0.1425 | 0.1455 | [+0.1306, +0.1542] | [+0.1208, +0.1620] | 63/7/391 |

### C_pareto_front

| metric | paired n | mean diff | median diff | CI parent | CI cell | B3 lower/equal/higher |
|---|---|---|---|---|---|---|
| vc_mean | 461 | -0.1705 | 0.0 | [-0.2028, -0.1391] | [-0.2269, -0.1211] | 184/242/35 |
| zero_share | 461 | +0.1098 | 0.0 | [+0.0900, +0.1295] | [+0.0849, +0.1369] | 37/246/178 |
| SR1_rate | 461 | -0.0546 | 0.0 | [-0.0697, -0.0398] | [-0.0742, -0.0353] | 106/331/24 |
| SR2_rate | 461 | -0.0201 | 0.0 | [-0.0316, -0.0083] | [-0.0410, -0.0026] | 37/406/18 |
| SR3_rate | 461 | -0.0743 | 0.0 | [-0.0899, -0.0594] | [-0.0979, -0.0539] | 95/362/4 |
| SR4_rate | 461 | -0.0129 | 0.0 | [-0.0241, -0.0032] | [-0.0255, -0.0016] | 47/386/28 |
| SR5_rate | 461 | -0.0086 | 0.0 | [-0.0152, -0.0024] | [-0.0167, -0.0016] | 28/413/20 |
| intent_mean | 391 | +0.0050 | 0.0 | [-0.0043, +0.0136] | [-0.0069, +0.0159] | 62/243/86 |
| plaus_mean | 461 | -0.0000 | 0.0 | [-0.0046, +0.0042] | [-0.0068, +0.0059] | 134/187/140 |
| dist_mean | 461 | +0.0528 | 0.0 | [+0.0354, +0.0709] | [+0.0251, +0.0833] | 107/209/145 |

### D_balanced

| metric | paired n | mean diff | median diff | CI parent | CI cell | B3 lower/equal/higher |
|---|---|---|---|---|---|---|
| vc_mean | 461 | -0.1019 | 0 | [-0.1354, -0.0697] | [-0.1398, -0.0646] | 45/413/3 |
| zero_share | 461 | +0.0824 | 0.0 | [+0.0563, +0.1092] | [+0.0483, +0.1177] | 2/419/40 |
| SR1_rate | 461 | -0.0673 | 0.0 | [-0.0925, -0.0449] | [-0.0984, -0.0381] | 32/428/1 |
| SR2_rate | 461 | -0.0087 | 0.0 | [-0.0195, +0.0022] | [-0.0177, -0.0021] | 5/455/1 |
| SR3_rate | 461 | -0.0130 | 0.0 | [-0.0261, -0.0022] | [-0.0248, -0.0022] | 7/453/1 |
| SR4_rate | 461 | -0.0022 | 0.0 | [-0.0108, +0.0044] | [-0.0107, +0.0044] | 2/458/1 |
| SR5_rate | 461 | -0.0109 | 0.0 | [-0.0218, +0.0000] | [-0.0240, +0.0000] | 6/454/1 |
| intent_mean | 391 | -0.0042 | 0.0 | [-0.0112, +0.0018] | [-0.0112, +0.0019] | 8/378/5 |
| plaus_mean | 461 | -0.0012 | 0.0 | [-0.0054, +0.0032] | [-0.0059, +0.0039] | 67/308/86 |
| dist_mean | 461 | +0.0722 | 0.0 | [+0.0454, +0.0992] | [+0.0341, +0.1110] | 59/325/77 |

### E_sorting_focused

| metric | paired n | mean diff | median diff | CI parent | CI cell | B3 lower/equal/higher |
|---|---|---|---|---|---|---|
| vc_mean | 461 | -0.0673 | 0 | [-0.1007, -0.0389] | [-0.1375, -0.0171] | 18/443/0 |
| zero_share | 461 | +0.0347 | 0.0 | [+0.0195, +0.0523] | [+0.0108, +0.0693] | 0/445/16 |
| SR1_rate | 461 | -0.0282 | 0.0 | [-0.0436, -0.0150] | [-0.0628, -0.0043] | 13/448/0 |
| SR2_rate | 461 | -0.0260 | 0.0 | [-0.0412, -0.0130] | [-0.0602, -0.0022] | 12/449/0 |
| SR3_rate | 461 | -0.0065 | 0.0 | [-0.0151, +0.0000] | [-0.0151, +0.0000] | 3/458/0 |
| SR4_rate | 461 | -0.0065 | 0.0 | [-0.0152, +0.0000] | [-0.0152, +0.0000] | 3/458/0 |
| SR5_rate | 461 | +0.0000 | 0.0 | [+0.0000, +0.0000] | [+0.0000, +0.0000] | 0/461/0 |
| intent_mean | 391 | +0.0158 | 0.0 | [+0.0052, +0.0261] | [+0.0042, +0.0277] | 5/361/25 |
| plaus_mean | 461 | +0.0001 | 0.0 | [-0.0098, +0.0091] | [-0.0130, +0.0116] | 49/279/133 |
| dist_mean | 461 | +0.0662 | 0.0 | [+0.0291, +0.1056] | [+0.0181, +0.1173] | 82/319/60 |

### F_intent_focused

| metric | paired n | mean diff | median diff | CI parent | CI cell | B3 lower/equal/higher |
|---|---|---|---|---|---|---|
| vc_mean | 391 | -0.1074 | 0 | [-0.1509, -0.0662] | [-0.1521, -0.0659] | 31/358/2 |
| zero_share | 391 | +0.0588 | 0.0 | [+0.0378, +0.0831] | [+0.0365, +0.0833] | 0/368/23 |
| SR1_rate | 391 | -0.0435 | 0.0 | [-0.0639, -0.0254] | [-0.0653, -0.0231] | 17/374/0 |
| SR2_rate | 391 | -0.0307 | 0.0 | [-0.0488, -0.0153] | [-0.0509, -0.0130] | 12/379/0 |
| SR3_rate | 391 | -0.0179 | 0.0 | [-0.0328, -0.0052] | [-0.0312, -0.0073] | 7/384/0 |
| SR4_rate | 391 | -0.0051 | 0.0 | [-0.0129, +0.0000] | [-0.0128, +0.0000] | 2/389/0 |
| SR5_rate | 391 | -0.0102 | 0.0 | [-0.0253, +0.0026] | [-0.0229, +0.0000] | 6/383/2 |
| intent_mean | 391 | -0.0053 | 0.0 | [-0.0100, -0.0017] | [-0.0096, -0.0017] | 7/384/0 |
| plaus_mean | 391 | +0.0065 | 0.0 | [-0.0015, +0.0146] | [-0.0013, +0.0137] | 46/257/88 |
| dist_mean | 391 | +0.0546 | 0.0 | [+0.0200, +0.0877] | [+0.0143, +0.0939] | 50/282/59 |

## 8. Breakdowns (primary metrics; CI only when n >= 10)

### by segment

| group | n | B:vc_mean | E:vc_mean | B:zero_share | D:intent_mean | D:plaus_mean |
|---|---|---|---|---|---|---|
| baby | 37 | -0.7509 [-0.9241, -0.5363] | -0.0312 [-0.1071, +0.0000] | +0.4553 [+0.3262, +0.5536] | +0.0000 [+0.0000, +0.0000] | +0.0221 [+0.0050, +0.0431] |
| kids | 157 | -0.8441 [-0.9080, -0.7770] | -0.0828 [-0.1410, -0.0256] | +0.4845 [+0.4586, +0.5118] | -0.0103 [-0.0239, +0.0032] | -0.0036 [-0.0107, +0.0035] |
| men | 114 | -0.8582 [-0.9303, -0.7800] | -0.0721 [-0.1532, -0.0090] | +0.4082 [+0.3705, +0.4438] | -0.0010 [-0.0158, +0.0084] | -0.0021 [-0.0090, +0.0043] |
| women | 161 | -0.9473 [-1.0077, -0.8876] | -0.0559 [-0.1056, -0.0124] | +0.4169 [+0.3887, +0.4425] | -0.0012 [-0.0097, +0.0097] | -0.0029 [-0.0111, +0.0047] |

### by request type

| group | n | B:vc_mean | E:vc_mean | B:zero_share | D:intent_mean | D:plaus_mean |
|---|---|---|---|---|---|---|
| derived_forbid | 198 | -0.8911 [-0.9516, -0.8308] | -0.0718 [-0.1282, -0.0308] | +0.4712 [+0.4458, +0.4955] | -0.0026 [-0.0128, +0.0051] | -0.0029 [-0.0084, +0.0027] |
| derived_full | 199 | -0.8681 [-0.9336, -0.8059] | -0.0816 [-0.1378, -0.0357] | +0.4114 [+0.3850, +0.4393] | -0.0059 [-0.0159, +0.0031] | -0.0034 [-0.0106, +0.0043] |
| no_pref | 72 | -0.8632 [-0.9415, -0.7841] | -0.0143 [-0.0429, +0.0000] | +0.4366 [+0.4016, +0.4695] | n/a n/a | +0.0097 [+0.0025, +0.0175] |

### by eligible TRAIN template pool

| group | n | B:vc_mean | E:vc_mean | B:zero_share | D:intent_mean | D:plaus_mean |
|---|---|---|---|---|---|---|
| 20-99 | 80 | -0.7188 [-0.7772, -0.6547] | +0.0000 [+0.0000, +0.0000] | +0.4003 [+0.3644, +0.4324] | -0.0144 [-0.0379, +0.0028] | +0.0132 [+0.0026, +0.0252] |
| 5-19 | 21 | -0.7956 [-1.0479, -0.5507] | -0.0476 [-0.1579, +0.0000] | +0.4175 [+0.2998, +0.5171] | +0.0000 [+0.0000, +0.0000] | +0.0185 [+0.0062, +0.0355] |
| <5 | 11 | -0.9167 [-1.0625, -0.6250] | +0.0000 [+0.0000, +0.0000] | +0.7500 [+0.6250, +0.8125] | +0.0000 [+0.0000, +0.0000] | +0.1081 [+0.0000, +0.1621] |
| >=100 | 357 | -0.9170 [-0.9635, -0.8734] | -0.0840 [-0.1232, -0.0476] | +0.4483 [+0.4305, +0.4676] | -0.0022 [-0.0092, +0.0042] | -0.0065 [-0.0114, -0.0022] |

### by category

| category | n | B:vc_mean | E:vc_mean | B:zero_share | D:intent_mean | D:plaus_mean |
|---|---|---|---|---|---|---|
| bras_lingerie | 10 | -1.0956 | +0.0000 | +0.3426 | +0.0000 | +0.0013 |
| dresses | 14 | -1.0018 | -0.0714 | +0.5164 | +0.0000 | +0.0120 |
| jeans | 21 | -0.8863 | +0.0000 | +0.4779 | +0.0111 | -0.0256 |
| joggers | 21 | -0.8244 | +0.0000 | +0.4220 | +0.0389 | -0.0270 |
| jumpsuits_overalls | 19 | -0.6209 | +0.0000 | +0.3810 | +0.0000 | +0.0015 |
| leggings | 22 | -0.9795 | +0.0000 | +0.4009 | +0.0000 | +0.0036 |
| outerwear_coat | 21 | -0.7017 | +0.0000 | +0.4015 | -0.0278 | +0.0109 |
| outerwear_gilet | 20 | -0.8604 | +0.0000 | +0.3666 | -0.0392 | +0.0231 |
| outerwear_jacket | 21 | -0.8603 | -0.0476 | +0.4004 | +0.0000 | -0.0054 |
| set | 14 | -0.6237 | +0.0000 | +0.4677 | +0.0000 | +0.0169 |
| shirt_blouse | 21 | -0.9791 | +0.0000 | +0.6290 | +0.0000 | -0.0258 |
| shorts | 24 | -0.8115 | +0.0000 | +0.5134 | -0.0167 | -0.0181 |
| skirts | 19 | -0.8994 | +0.0000 | +0.5014 | -0.0208 | +0.0067 |
| sleepwear_homewear | 28 | -0.8824 | +0.0000 | +0.5037 | +0.0000 | +0.0152 |
| socks_hosiery | 24 | -1.0691 | -1.0000 | +0.2042 | -0.0333 | -0.0102 |
| sweater_cardigan | 21 | -0.8999 | -0.1429 | +0.3963 | +0.0000 | +0.0001 |
| sweatshirt_hoodie | 21 | -0.6384 | +0.0000 | +0.3855 | +0.0000 | +0.0016 |
| swimwear | 21 | -0.9103 | +0.0000 | +0.4379 | -0.0185 | -0.0027 |
| tank_camisole_vest | 21 | -0.8511 | +0.0000 | +0.4736 | +0.0111 | +0.0065 |
| top_generic | 14 | -0.9300 | +0.0000 | +0.5299 | +0.0000 | +0.0077 |
| trousers | 24 | -1.1668 | -0.0833 | +0.5226 | +0.0000 | +0.0003 |
| tshirt_polo | 24 | -0.9488 | +0.0000 | +0.5037 | +0.0000 | +0.0027 |
| underwear_bottoms | 24 | -0.7582 | +0.0000 | +0.3656 | +0.0000 | -0.0053 |

## 9. Small template pools

| pool bin | requests | flag | A: gen/req / no-cand / pool viol / sorting viol | B3: same |
|---|---|---|---|---|
| <5 | 11 | SMALL POOL: interpret with caution | 0.0273 / 0.7273 / 0.917 / 0 | 0.0273 / 0.7273 / 0 / 0 |
| 5-19 | 21 | SMALL POOL: interpret with caution | 0.2726 / 0.0 / 1.33 / 0.429 | 0.2607 / 0.0 / 0.505 / 0.381 |
| 20-99 | 80 |  | 0.8533 / 0.0 / 1.153 / 0 | 0.7394 / 0.0 / 0.418 / 0 |
| >=100 | 357 |  | 0.9536 / 0.0 / 1.36 / 0.106 | 0.8895 / 0.0 / 0.438 / 0.022 |

## 10. Trade-offs vs own template

```json
{
"A_baseline": {
"B_hard_valid_candidates": {
"sorting_up_intent_down": {
"count": 726,
"defined_n": 28322,
"rate": 0.0256
},
"intent_up_sorting_down": {
"count": 514,
"defined_n": 28322,
"rate": 0.0181
},
"sorting_up_plaus_drop": {
"count": 1259,
"defined_n": 33178,
"rate": 0.0379
},
"all_three_improve": {
"count": 27,
"defined_n": 28322,
"rate": 0.001
}
},
"D_balanced": {
"sorting_up_intent_down": {
"count": 3,
"defined_n": 391,
"rate": 0.0077
},
"intent_up_sorting_down": {
"count": 5,
"defined_n": 391,
"rate": 0.0128
},
"sorting_up_plaus_drop": {
"count": 5,
"defined_n": 461,
"rate": 0.0108
},
"all_three_improve": {
"count": 2,
"defined_n": 391,
"rate": 0.0051
}
},
"E_sorting_focused": {
"sorting_up_intent_down": {
"count": 46,
"defined_n": 391,
"rate": 0.1176
},
"intent_up_sorting_down": {
"count": 0,
"defined_n": 391,
"rate": 0.0
},
"sorting_up_plaus_drop": {
"count": 28,
"defined_n": 461,
"rate": 0.0607
},
"all_three_improve": {
"count": 2,
"defined_n": 391,
"rate": 0.0051
}
}
},
"B3_proposal_plus_repair": {
"B_hard_valid_candidates": {
"sorting_up_intent_down": {
"count": 4642,
"defined_n": 26148,
"rate": 0.1775
},
"intent_up_sorting_down": {
"count": 118,
"defined_n": 26148,
"rate": 0.0045
},
"sorting_up_plaus_drop": {
"count": 5723,
"defined_n": 30598,
"rate": 0.187
},
"all_three_improve": {
"count": 147,
"defined_n": 26148,
"rate": 0.0056
}
},
"D_balanced": {
"sorting_up_intent_down": {
"count": 10,
"defined_n": 391,
"rate": 0.0256
},
"intent_up_sorting_down": {
"count": 6,
"defined_n": 391,
"rate": 0.0153
},
"sorting_up_plaus_drop": {
"count": 15,
"defined_n": 461,
"rate": 0.0325
},
"all_three_improve": {
"count": 8,
"defined_n": 391,
"rate": 0.0205
}
},
"E_sorting_focused": {
"sorting_up_intent_down": {
"count": 44,
"defined_n": 391,
"rate": 0.1125
},
"intent_up_sorting_down": {
"count": 0,
"defined_n": 391,
"rate": 0.0
},
"sorting_up_plaus_drop": {
"count": 41,
"defined_n": 461,
"rate": 0.0889
},
"all_three_improve": {
"count": 8,
"defined_n": 391,
"rate": 0.0205
}
}
}
}
```

## 11. Computation and runtime

```json
{
 "A_baseline": {
  "requests": 469,
  "candidates_requested": 37520,
  "candidates_generated": 33178,
  "generated_over_requested": 0.8843,
  "mutation_attempts": 94936,
  "oracle_calls_generation_phase": 33178,
  "oracle_calls_evaluation_phase_templates": 4357,
  "fast_rule_evals": 0,
  "repair_proposals_evaluated": 0,
  "repair_accepted": 0,
  "intent_evals_in_repair": 0,
  "plausibility_evals_in_repair": 0,
  "seconds_generation_only_total": 84.34,
  "seconds_generation_and_evaluation_total": 90.35,
  "seconds_per_request_mean": 0.1926
 },
 "B3_proposal_plus_repair": {
  "requests": 469,
  "candidates_requested": 37520,
  "candidates_generated": 30598,
  "generated_over_requested": 0.8155,
  "mutation_attempts": 165525,
  "oracle_calls_generation_phase": 270059,
  "oracle_calls_evaluation_phase_templates": 4357,
  "fast_rule_evals": 4997473,
  "repair_proposals_evaluated": 78736,
  "repair_accepted": 32970,
  "intent_evals_in_repair": 239461,
  "plausibility_evals_in_repair": 239461,
  "seconds_generation_only_total": 254.98,
  "seconds_generation_and_evaluation_total": 260.89,
  "seconds_per_request_mean": 0.5563
 },
 "ratios_variant_over_baseline": {
  "mutation_attempts": 1.744,
  "oracle_calls_generation_phase": 8.14,
  "seconds_generation_only_total": 3.023,
  "seconds_generation_and_evaluation_total": 2.888,
  "candidates_generated": 0.922
 },
 "fairness_statement": "Requested candidates, template pool, template selection, seed, attempt limit and evaluation are identical. Computational cost is NOT equal: Generator B3 performs additional Oracle-guided rule evaluations, Oracle calls and Intent/Plausibility evaluations for repairs (see ratios).",
 "timing_note": "wall-clock seconds measured per request inside one worker process; informational only"
}
```

## 12. Failure analysis (observed)

```json
{
 "no_candidate_requests": {
  "A_baseline": [
   {
    "request_id": "baby|skirts|no_pref",
    "pool": 0,
    "rejected": {}
   },
   {
    "request_id": "baby|skirts|derived_full|g_8f5bcacfc0a243be",
    "pool": 0,
    "rejected": {}
   },
   {
    "request_id": "baby|skirts|derived_full|g_6e318e461d13aa7d",
    "pool": 0,
    "rejected": {}
   },
   {
    "request_id": "baby|skirts|derived_forbid|g_8f5bcacfc0a243be",
    "pool": 0,
    "rejected": {}
   },
   {
    "request_id": "baby|skirts|derived_forbid|g_6e318e461d13aa7d",
    "pool": 0,
    "rejected": {}
   },
   {
    "request_id": "men|leggings|no_pref",
    "pool": 0,
    "rejected": {}
   },
   {
    "request_id": "men|leggings|derived_full|g_9aefaa391d6e2763",
    "pool": 0,
    "rejected": {}
   },
   {
    "request_id": "men|leggings|derived_forbid|g_9aefaa391d6e2763",
    "pool": 0,
    "rejected": {}
   }
  ],
  "B3_proposal_plus_repair": [
   {
    "request_id": "baby|skirts|no_pref",
    "pool": 0,
    "rejected": {}
   },
   {
    "request_id": "baby|skirts|derived_full|g_8f5bcacfc0a243be",
    "pool": 0,
    "rejected": {}
   },
   {
    "request_id": "baby|skirts|derived_full|g_6e318e461d13aa7d",
    "pool": 0,
    "rejected": {}
   },
   {
    "request_id": "baby|skirts|derived_forbid|g_8f5bcacfc0a243be",
    "pool": 0,
    "rejected": {}
   },
   {
    "request_id": "baby|skirts|derived_forbid|g_6e318e461d13aa7d",
    "pool": 0,
    "rejected": {}
   },
   {
    "request_id": "men|leggings|no_pref",
    "pool": 0,
    "rejected": {}
   },
   {
    "request_id": "men|leggings|derived_full|g_9aefaa391d6e2763",
    "pool": 0,
    "rejected": {}
   },
   {
    "request_id": "men|leggings|derived_forbid|g_9aefaa391d6e2763",
    "pool": 0,
    "rejected": {}
   }
  ]
 },
 "no_zero_violation_requests": {
  "baseline": 27,
  "variant": 11,
  "both": 11,
  "variant_only": [],
  "n_variant_only": 0,
  "baseline_only": 16,
  "variant_requests_whose_sorting_focused_design_still_violates_SR4": 8,
  "denominator_requests_with_candidates": {
   "A_baseline": 461,
   "B3_proposal_plus_repair": 461
  }
 },
 "unresolved_violations": {
  "variant_final_candidates": 30598,
  "SR1_unresolved": 3466,
  "SR2_unresolved": 1965,
  "SR3_unresolved": 699,
  "SR5_unresolved": 1925,
  "candidates_with_unresolved_repairable": 5205,
  "variant_no_train_supported_alternative": {
   "SR5": 2
  },
  "variant_repair_rejections": {
   "intent_floor": 15183,
   "plausibility_floor": 10053,
   "no_violation_decrease": 20530
  }
 },
 "sr4_immutable": {
  "note": "colour is not mutated; SR4 can only be satisfied if the template colour is not 'black'",
  "A_baseline": {
   "candidates_with_violations": 24677,
   "only_SR4_remaining": 1491,
   "only_SR4_share_of_violating": 0.0604,
   "SR4_violation_rate": 0.172
  },
  "B3_proposal_plus_repair": {
   "candidates_with_violations": 9267,
   "only_SR4_remaining": 4062,
   "only_SR4_share_of_violating": 0.4383,
   "SR4_violation_rate": 0.1722
  },
  "variant_sr4_immutable_candidates": 5268
 },
 "diversity": {
  "A_baseline": {
   "unique_candidate_rate_mean": 0.9586,
   "requests_with_fewer_than_20_candidates": 12,
   "duplicate_candidate_rejections": 40026,
   "identical_to_template_rejections": 16932,
   "front_violation_levels_mean": 1.772
  },
  "B3_proposal_plus_repair": {
   "unique_candidate_rate_mean": 1.0,
   "requests_with_fewer_than_20_candidates": 12,
   "duplicate_candidate_rejections": 81201,
   "identical_to_template_rejections": 48926,
   "front_violation_levels_mean": 1.605
  }
 },
 "baseline_outperforms_variant": {
  "B_hard_valid_candidates:vc_mean": {
   "n_paired": 461,
   "baseline_better": 0,
   "variant_better": 456,
   "equal": 5,
   "top_baseline_advantage": []
  },
  "E_sorting_focused:vc_mean": {
   "n_paired": 461,
   "baseline_better": 0,
   "variant_better": 18,
   "equal": 443,
   "top_baseline_advantage": []
  },
  "D_balanced:intent_mean": {
   "n_paired": 391,
   "baseline_better": 8,
   "variant_better": 5,
   "equal": 378,
   "top_baseline_advantage": [
    {
     "request_id": "men|socks_hosiery|derived_forbid|g_5a8e0711ccce6963",
     "baseline": 1.0,
     "variant": 0.5,
     "pool": 313,
     "bin": ">=100"
    },
    {
     "request_id": "kids|socks_hosiery|derived_forbid|g_26c20a6036b2b6d7",
     "baseline": 1.0,
     "variant": 0.5,
     "pool": 393,
     "bin": ">=100"
    },
    {
     "request_id": "kids|outerwear_coat|derived_full|g_8739e866e8af1957",
     "baseline": 1.0,
     "variant": 0.5,
     "pool": 50,
     "bin": "20-99"
    },
    {
     "request_id": "kids|outerwear_gilet|derived_full|g_bea76f7c20804652",
     "baseline": 0.6667,
     "variant": 0.3333,
     "pool": 68,
     "bin": "20-99"
    },
    {
     "request_id": "women|swimwear|derived_full|g_453558eafb554700",
     "baseline": 1.0,
     "variant": 0.6667,
     "pool": 616,
     "bin": ">=100"
    },
    {
     "request_id": "women|shorts|derived_full|g_21a80eb18f5575d7",
     "baseline": 1.0,
     "variant": 0.6667,
     "pool": 522,
     "bin": ">=100"
    }
   ]
  },
  "D_balanced:plaus_mean": {
   "n_paired": 461,
   "baseline_better": 67,
   "variant_better": 86,
   "equal": 308,
   "top_baseline_advantage": [
    {
     "request_id": "women|socks_hosiery|derived_full|g_1019caf347474963",
     "baseline": 0.9524,
     "variant": 0.6497,
     "pool": 427,
     "bin": ">=100"
    },
    {
     "request_id": "women|swimwear|derived_full|g_6bb13269cfdb3f64",
     "baseline": 0.9662,
     "variant": 0.6838,
     "pool": 616,
     "bin": ">=100"
    },
    {
     "request_id": "kids|shirt_blouse|derived_full|g_ed3d4ff09f1cbb98",
     "baseline": 0.8741,
     "variant": 0.6461,
     "pool": 541,
     "bin": ">=100"
    },
    {
     "request_id": "kids|jeans|derived_full|g_dc3d2bf76a4e03d3",
     "baseline": 0.9303,
     "variant": 0.7325,
     "pool": 476,
     "bin": ">=100"
    },
    {
     "request_id": "men|jeans|derived_full|g_7280af7405b89e7b",
     "baseline": 0.995,
     "variant": 0.8033,
     "pool": 297,
     "bin": ">=100"
    },
    {
     "request_id": "kids|joggers|derived_full|g_e54d0003af83f66d",
     "baseline": 0.8614,
     "variant": 0.6696,
     "pool": 468,
     "bin": ">=100"
    }
   ]
  }
 }
}
```

Repair side effects: `{"accepted_repairs_introducing_other_violation": 26, "repair_proposals_introducing_other_violation": 3968, "repair_accepted": 32970, "repair_proposals_evaluated": 78736, "examples": [{"request_id": "men|outerwear_jacket|derived_forbid|g_b1a99827320c4511", "candidate_id": "candB_cd1f259724b3c43b", "operation": "sr2_merge_fibre_into_existing_fibre", "targeted_rule": "SR2", "confirmed_fixed_rules": ["SR1", "SR2"], "introduced_rules": ["SR5"], "violations_before_after": [2, 1], "intent_delta": 0.0, "plausibility_delta": -0.118388}, {"request_id": "men|outerwear_jacket|derived_forbid|g_b1a99827320c4511", "candidate_id": "candB_c6bdb2469c5df0ea", "operation": "sr2_merge_fibre_into_existing_fibre", "targeted_rule": "SR2", "confirmed_fixed_rules": ["SR1", "SR2"], "introduced_rules": ["SR5"], "violations_before_after": [2, 1], "intent_delta": 0.0, "plausibility_delta": -0.113708}, {"request_id": "men|outerwear_jacket|derived_forbid|g_b1a99827320c4511", "candidate_id": "candB_8ce8a2c0a32d9b46", "operation": "sr2_merge_fibre_into_existing_fibre", "targeted_rule": "SR2", "confirmed_fixed_rules": ["SR1", "SR2"], "introduced_rules": ["SR5"], "violations_before_after": [3, 2], "intent_delta": 0.0, "plausibility_delta": -0.105957}, {"request_id": "men|outerwear_jacket|derived_forbid|g_b1a99827320c4511", "candidate_id": "candB_1aaf73ce621b25d9", "operation": "sr2_merge_fibre_into_existing_fibre", "targeted_rule": "SR2", "confirmed_fixed_rules": ["SR1", "SR2"], "introduced_rules": ["SR5"], "violations_before_after": [2, 1], "intent_delta": 0.0, "plausibility_delta": -0.1172}, {"request_id": "men|underwear_bottoms|no_pref", "candidate_id": "candB_b13dd909a1947402", "operation": "sr2_merge_fibre_into_existing_fibre", "targeted_rule": "SR2", "confirmed_fixed_rules": ["SR1", "SR2"], "introduced_rules": ["SR5"], "violations_before_after": [2, 1], "intent_delta": null, "plausibility_delta": -0.133679}, {"request_id": "men|underwear_bottoms|derived_full|g_3695e12083ba1784", "candidate_id": "candB_a55046959c81ce1c", "operation": "sr2_merge_fibre_into_existing_fibre", "targeted_rule": "SR2", "confirmed_fixed_rules": ["SR1", "SR2"], "introduced_rules": ["SR5"], "violations_before_after": [2, 1], "intent_delta": 0.0, "plausibility_delta": -0.129822}], "examples_total": 23}`

## 13. Reproducible examples

```json
{
 "reproduction_command": "python scripts/run_final_test_evaluation.py --reproduce-request '<request_id>'",
 "selected_requests": {
  "largest_B3_improvement_pool_violation": {
   "request_id": "men|outerwear_jacket|derived_forbid|g_b1a99827320c4511",
   "request": {
    "hard": {
     "forbidden_materials": [
      "cotton"
     ]
    },
    "soft": {
     "preferred_dominant_material": "polyester",
     "stretch": "low"
    }
   },
   "variants": {
    "A_baseline": {
     "template_pool": 391,
     "generated": 80,
     "front_size": 4,
     "designs": {
      "balanced": {
       "candidate_id": "cand_0586115109cdcbc0",
       "template_garment_id": "g_fc0f6f69dc0cf991",
       "violation_count": 2,
       "sr_violations": {
        "SR1": false,
        "SR2": false,
        "SR3": true,
        "SR4": false,
        "SR5": true
       },
       "intent_0_100": 100.0,
       "plausibility_0_100": 89.98,
       "template_distance": {
        "n_substitutions": 0,
        "abs_pct_change_total": 2.0,
        "diagnostic_distance": 0.02
       },
       "components": [
        [
         "shell",
         [
          [
           "polyester",
           99.0
          ],
          [
           "elastane",
           1.0
          ]
         ]
        ],
        [
         "lining",
         [
          [
           "polyester",
           52.0
          ],
          [
           "viscose",
           48.0
          ]
         ]
        ],
        [
         "sleeve_lining",
         [
          [
           "polyester",
           100.0
          ]
         ]
        ]
       ],
       "mutations": [
        "Moved 1 percentage points from elastane (2% -> 1%) to polyester (98% -> 99%) in component 'shell'"
       ]
      },
      "intent_focused": {
       "candidate_id": "cand_0586115109cdcbc0",
       "template_garment_id": "g_fc0f6f69dc0cf991",
       "violation_count": 2,
       "sr_violations": {
        "SR1": false,
        "SR2": false,
        "SR3": true,
        "SR4": false,
        "SR5": true
       },
       "intent_0_100": 100.0,
       "plausibility_0_100": 89.98,
       "template_distance": {
        "n_substitutions": 0,
        "abs_pct_change_total": 2.0,
        "diagnostic_distance": 0.02
       },
       "components": [
        [
         "shell",
         [
          [
           "polyester",
           99.0
          ],
          [
           "elastane",
           1.0
          ]
         ]
        ],
        [
         "lining",
         [
          [
           "polyester",
           52.0
          ],
          [
           "viscose",
           48.0
          ]
         ]
        ],
        [
         "sleeve_lining",
         [
          [
           "polyester",
           100.0
          ]
         ]
        ]
       ],
       "mutations": [
        "Moved 1 percentage points from elastane (2% -> 1%) to polyester (98% -> 99%) in component 'shell'"
       ]
      },
      "sorting_focused": {
       "candidate_id": "cand_541b077a2f1b3419",
       "template_garment_id": "g_fc0f6f69dc0cf991",
       "violation_count": 1,
       "sr_violations": {
        "SR1": false,
        "SR2": false,
        "SR3": true,
        "SR4": false,
        "SR5": false
       },
       "intent_0_100": 50.0,
       "plausibility_0_100": 64.55,
       "template_distance": {
        "n_substitutions": 1,
        "abs_pct_change_total": 20.0,
        "diagnostic_distance": 1.2
       },
       "components": [
        [
         "shell",
         [
          [
           "polyester",
           98.0
          ],
          [
           "viscose",
           2.0
          ]
         ]
        ],
        [
         "lining",
         [
          [
           "polyester",
           42.0
          ],
          [
           "viscose",
           58.0
          ]
         ]
        ],
        [
         "sleeve_lining",
         [
          [
           "polyester",
           100.0
          ]
         ]
        ]
       ],
       "mutations": [
        "Substituted elastane with viscose in component 'shell' (slot at 2%)",
        "Moved 10 percentage points from polyester (52% -> 42%) to viscose (48% -> 58%) in component 'lining'"
       ]
      }
     },
     "explanation_statements": {
      "cand_0586115109cdcbc0": [
       "Preference 'preferred_dominant_material=polyester' satisfied: polyester is the highest-percentage material of the primary component ('polyester' at 99%).",
       "Preference 'stretch=low' satisfied: proxy 'stretch=low' scored 1 from composition/text evidence (elastane=1%; bucket=low)."
      ],
      "cand_541b077a2f1b3419": [
       "SR5 is no longer violated compared with the template (confirmed: undoing mutation step(s) [0] restores the template's SR5 result).",
       "Preference 'preferred_dominant_material=polyester' satisfied: polyester is the highest-percentage material of the primary component ('polyester' at 98%).",
       "Preference 'stretch=low' not fully satisfied (satisfaction 0): proxy 'stretch=low' scored -1 from composition/text evidence (elastane=0%; bucket=none)."
      ]
     }
    },
    "B3_proposal_plus_repair": {
     "template_pool": 391,
     "generated": 80,
     "front_size": 4,
     "designs": {
      "balanced": {
       "candidate_id": "candB_98a8b782998723b8",
       "template_garment_id": "g_fc0f6f69dc0cf991",
       "violation_count": 1,
       "sr_violations": {
        "SR1": false,
        "SR2": false,
        "SR3": true,
        "SR4": false,
        "SR5": false
       },
       "intent_0_100": 100.0,
       "plausibility_0_100": 76.11,
       "template_distance": {
        "n_substitutions": 1,
        "abs_pct_change_total": 2.0,
        "diagnostic_distance": 1.02
       },
       "components": [
        [
         "shell",
         [
          [
           "polyester",
           99.0
          ],
          [
           "elastane",
           1.0
          ]
         ]
        ],
        [
         "lining",
         [
          [
           "polyester",
           52.0
          ],
          [
           "polyester",
           48.0
          ]
         ]
        ],
        [
         "sleeve_lining",
         [
          [
           "polyester",
           100.0
          ]
         ]
        ]
       ],
       "mutations": [
        "Moved 1 percentage points from elastane (2% -> 1%) to polyester (98% -> 99%) in component 'shell'",
        "Substituted viscose with polyester in component 'lining' (slot at 48%)"
       ]
      },
      "intent_focused": {
       "candidate_id": "candB_98a8b782998723b8",
       "template_garment_id": "g_fc0f6f69dc0cf991",
       "violation_count": 1,
       "sr_violations": {
        "SR1": false,
        "SR2": false,
        "SR3": true,
        "SR4": false,
        "SR5": false
       },
       "intent_0_100": 100.0,
       "plausibility_0_100": 76.11,
       "template_distance": {
        "n_substitutions": 1,
        "abs_pct_change_total": 2.0,
        "diagnostic_distance": 1.02
       },
       "components": [
        [
         "shell",
         [
          [
           "polyester",
           99.0
          ],
          [
           "elastane",
           1.0
          ]
         ]
        ],
        [
         "lining",
         [
          [
           "polyester",
           52.0
          ],
          [
           "polyester",
           48.0
          ]
         ]
        ],
        [
         "sleeve_lining",
         [
          [
           "polyester",
           100.0
          ]
         ]
        ]
       ],
       "mutations": [
        "Moved 1 percentage points from elastane (2% -> 1%) to polyester (98% -> 99%) in component 'shell'",
        "Substituted viscose with polyester in component 'lining' (slot at 48%)"
       ]
      },
      "sorting_focused": {
       "candidate_id": "candB_22c1868a8c724ce3",
       "template_garment_id": "g_fc0f6f69dc0cf991",
       "violation_count": 0,
       "sr_violations": {
        "SR1": false,
        "SR2": false,
        "SR3": false,
        "SR4": false,
        "SR5": false
       },
       "intent_0_100": 50.0,
       "plausibility_0_100": 75.23,
       "template_distance": {
        "n_substitutions": 1,
        "abs_pct_change_total": 8.0,
        "diagnostic_distance": 1.08
       },
       "components": [
        [
         "shell",
         [
          [
           "polyester",
           94.0
          ],
          [
           "elastane",
           6.0
          ]
         ]
        ],
        [
         "lining",
         [
          [
           "polyester",
           52.0
          ],
          [
           "polyester",
           48.0
          ]
         ]
        ],
        [
         "sleeve_lining",
         [
          [
           "polyester",
           100.0
          ]
         ]
        ]
       ],
       "mutations": [
        "Substituted viscose with polyester in component 'lining' (slot at 48%)",
        "Moved 5 percentage points from polyester (98% -> 93%) to elastane (2% -> 7%) in component 'shell'",
        "Moved 1 percentage points from elastane (7% -> 6%) to polyester (93% -> 94%) in component 'shell'"
       ]
      }
     },
     "explanation_statements": {
      "candB_22c1868a8c724ce3": [
       "SR3 is no longer violated compared with the template (confirmed: undoing mutation step(s) [1] restores the template's SR3 result).",
       "SR5 is no longer violated compared with the template (confirmed: undoing mutation step(s) [0] restores the template's SR5 result).",
       "Preference 'preferred_dominant_material=polyester' satisfied: polyester is the highest-percentage material of the primary component ('polyester' at 94%).",
       "Preference 'stretch=low' not fully satisfied (satisfaction 0): proxy 'stretch=low' scored -1 from composition/text evidence (elastane=6%; bucket=high)."
      ],
      "candB_98a8b782998723b8": [
       "SR5 is no longer violated compared with the template (confirmed: undoing mutation step(s) [1] restores the template's SR5 result).",
       "Preference 'preferred_dominant_material=polyester' satisfied: polyester is the highest-percentage material of the primary component ('polyester' at 99%).",
       "Preference 'stretch=low' satisfied: proxy 'stretch=low' scored 1 from composition/text evidence (elastane=1%; bucket=low)."
      ]
     }
    }
   }
  },
  "small_template_pool": {
   "request_id": "baby|trousers|derived_forbid|g_fbaeaffc844337c6",
   "request": {
    "hard": {
     "forbidden_materials": [
      "elastane"
     ]
    },
    "soft": {
     "preferred_dominant_material": "cotton",
     "stretch": "none"
    }
   },
   "variants": {
    "A_baseline": {
     "template_pool": 2,
     "generated": 8,
     "front_size": 2,
     "designs": {
      "balanced": {
       "candidate_id": "cand_39f044d4fc05b840",
       "template_garment_id": "g_102c257f10841fe0",
       "violation_count": 0,
       "sr_violations": {
        "SR1": false,
        "SR2": false,
        "SR3": false,
        "SR4": false,
        "SR5": false
       },
       "intent_0_100": 100.0,
       "plausibility_0_100": 62.51,
       "template_distance": {
        "n_substitutions": 1,
        "abs_pct_change_total": 10.0,
        "diagnostic_distance": 1.1
       },
       "components": [
        [
         "main",
         [
          [
           "cotton",
           90.0
          ],
          [
           "polyester",
           10.0
          ]
         ]
        ]
       ],
       "mutations": [
        "Substituted elastane with linen in component 'main' (slot at 5%) (forbidden-material repair)",
        "Substituted linen with polyester in component 'main' (slot at 5%)",
        "Moved 5 percentage points from cotton (95% -> 90%) to polyester (5% -> 10%) in component 'main'"
       ]
      },
      "intent_focused": {
       "candidate_id": "cand_39f044d4fc05b840",
       "template_garment_id": "g_102c257f10841fe0",
       "violation_count": 0,
       "sr_violations": {
        "SR1": false,
        "SR2": false,
        "SR3": false,
        "SR4": false,
        "SR5": false
       },
       "intent_0_100": 100.0,
       "plausibility_0_100": 62.51,
       "template_distance": {
        "n_substitutions": 1,
        "abs_pct_change_total": 10.0,
        "diagnostic_distance": 1.1
       },
       "components": [
        [
         "main",
         [
          [
           "cotton",
           90.0
          ],
          [
           "polyester",
           10.0
          ]
         ]
        ]
       ],
       "mutations": [
        "Substituted elastane with linen in component 'main' (slot at 5%) (forbidden-material repair)",
        "Substituted linen with polyester in component 'main' (slot at 5%)",
        "Moved 5 percentage points from cotton (95% -> 90%) to polyester (5% -> 10%) in component 'main'"
       ]
      },
      "sorting_focused": {
       "candidate_id": "cand_39f044d4fc05b840",
       "template_garment_id": "g_102c257f10841fe0",
       "violation_count": 0,
       "sr_violations": {
        "SR1": false,
        "SR2": false,
        "SR3": false,
        "SR4": false,
        "SR5": false
       },
       "intent_0_100": 100.0,
       "plausibility_0_100": 62.51,
       "template_distance": {
        "n_substitutions": 1,
        "abs_pct_change_total": 10.0,
        "diagnostic_distance": 1.1
       },
       "components": [
        [
         "main",
         [
          [
           "cotton",
           90.0
          ],
          [
           "polyester",
           10.0
          ]
         ]
        ]
       ],
       "mutations": [
        "Substituted elastane with linen in component 'main' (slot at 5%) (forbidden-material repair)",
        "Substituted linen with polyester in component 'main' (slot at 5%)",
        "Moved 5 percentage points from cotton (95% -> 90%) to polyester (5% -> 10%) in component 'main'"
       ]
      }
     },
     "explanation_statements": {
      "cand_39f044d4fc05b840": [
       "Preference 'preferred_dominant_material=cotton' satisfied: cotton is the highest-percentage material of the primary component ('cotton' at 90%).",
       "Preference 'stretch=none' satisfied: proxy 'stretch=none' scored 1 from composition/text evidence (elastane=0%; bucket=none)."
      ]
     }
    },
    "B3_proposal_plus_repair": {
     "template_pool": 2,
     "generated": 8,
     "front_size": 1,
     "designs": {
      "balanced": {
       "candidate_id": "candB_f6fd39176c98e64b",
       "template_garment_id": "g_102c257f10841fe0",
       "violation_count": 0,
       "sr_violations": {
        "SR1": false,
        "SR2": false,
        "SR3": false,
        "SR4": false,
        "SR5": false
       },
       "intent_0_100": 100.0,
       "plausibility_0_100": 79.46,
       "template_distance": {
        "n_substitutions": 1,
        "abs_pct_change_total": 0.0,
        "diagnostic_distance": 1.0
       },
       "components": [
     
```

## 14. Limitations

- Requests are derived from held-out TEST garments' observable properties; they are a benchmark of reproducing held-out intents, not real user requests.
- SR4 (colour == 'black') is immutable because colour is never mutated: no candidate of a black-template request can reach zero violations.
- Fit/length labels are inherited from the TRAIN template and are not re-derived after mutation; Intent saturates easily for derived requests.
- Dataset-relative Plausibility measures support/similarity to the TRAIN distribution only; it is not a manufacturability or quality guarantee.
- Equal requested budgets are not equal computation: B3 evaluates many more rules/Oracle calls per candidate.
- Uncertainty: percentile bootstrap, unadjusted for multiplicity; only P1-P5 are pre-specified primary outcomes. Requests of one cell share the TRAIN template pool (cell-clustered CIs are a sensitivity analysis).
- Wall-clock times are single-machine, informational, and not part of any statistical claim.
- Results describe this dataset, these V1 configurations and this request construction; they do not establish generalisation to other garment data or to physical sorting performance.
