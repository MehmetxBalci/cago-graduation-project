# CAGO sorting-aware generator - VAL development comparison

Development comparison on VAL requests (TRAIN support only; TEST never used). Terminology: Sorting Compatibility (SR1-SR5 rule satisfaction), Intent Alignment, Dataset-relative Plausibility, constraint-based probabilistic generation with sorting-aware proposal/repair. Not a recyclability, sustainability or manufacturability measure; descriptive, no causal claim.

Requests 213 (invalid 0); cells 71; categories 23; segments {'baby': 24, 'kids': 66, 'men': 54, 'women': 69}; types {'no_pref': 71, 'derived_full': 71, 'derived_forbid': 71}.

Fairness: identical template pool/selection across variants = True; requested candidates {'A_baseline': 17040, 'B1_proposal_only': 17040, 'B2_repair_only': 17040, 'B3_proposal_plus_repair': 17040, 'B3_nondominated_local': 17040}. Baseline A max_attempts=25; Generator B max_proposal_attempts=25 (+ bounded repair steps, reported separately). Determinism re-run: {'rerun_requests': 5, 'all_identical': True}.

## Search / budget

| variant | generated | gen/requested | mutation attempts | unique rate | oracle full evals | fast rule evals | repair proposals | repair acceptance | sec/request (info) |
|---|---|---|---|---|---|---|---|---|---|
| A_baseline | 14545 | 0.8536 | 40000 | 0.9573 | 0 | 0 | 0 | None | 0.146 |
| B1_proposal_only | 14058 | 0.825 | 54121 | 1.0 | 0 | 1570703 | 0 | None | 0.3 |
| B2_repair_only | 13538 | 0.7945 | 70008 | 1.0 | 122532 | 287946 | 53924 | 0.4514 | 0.377 |
| B3_proposal_plus_repair | 13435 | 0.7884 | 69846 | 1.0 | 99274 | 2132203 | 30828 | 0.4036 | 0.475 |
| B3_nondominated_local | 13206 | 0.775 | 77435 | 1.0 | 139672 | 2540393 | 63637 | 0.3167 | 0.58 |

## Stage comparison (pooled rows)

### B_hard_valid_candidates

| variant | rows | viol mean | zero-viol | SR1-SR5 rates | intent median | plaus median | mean dist |
|---|---|---|---|---|---|---|---|
| A_baseline | 14545 | 1.273 | 0.2693 | {"SR1": 0.5711, "SR2": 0.1954, "SR3": 0.1799, "SR4": 0.1723, "SR5": 0.154} | 66.67 | 58.5 | 0.918 |
| B1_proposal_only | 14058 | 0.719 | 0.5049 | {"SR1": 0.2969, "SR2": 0.0876, "SR3": 0.0436, "SR4": 0.1717, "SR5": 0.1193} | 66.67 | 64.94 | 0.943 |
| B2_repair_only | 13538 | 0.505 | 0.6716 | {"SR1": 0.1461, "SR2": 0.0866, "SR3": 0.0236, "SR4": 0.1727, "SR5": 0.0756} | 75.0 | 67.67 | 1.08 |
| B3_proposal_plus_repair | 13435 | 0.405 | 0.7151 | {"SR1": 0.1054, "SR2": 0.0562, "SR3": 0.0115, "SR4": 0.1719, "SR5": 0.0599} | 66.67 | 67.27 | 1.062 |
| B3_nondominated_local | 13206 | 0.412 | 0.7056 | {"SR1": 0.1309, "SR2": 0.0526, "SR3": 0.0139, "SR4": 0.1687, "SR5": 0.0463} | 66.67 | 67.85 | 1.003 |

### C_pareto_front

| variant | rows | viol mean | zero-viol | SR1-SR5 rates | intent median | plaus median | mean dist |
|---|---|---|---|---|---|---|---|
| A_baseline | 570 | 0.733 | 0.5579 | {"SR1": 0.2719, "SR2": 0.1386, "SR3": 0.1649, "SR4": 0.1053, "SR5": 0.0526} | 80.0 | 91.97 | 0.243 |
| B1_proposal_only | 575 | 0.576 | 0.6504 | {"SR1": 0.233, "SR2": 0.113, "SR3": 0.0835, "SR4": 0.1026, "SR5": 0.0435} | 80.0 | 90.7 | 0.319 |
| B2_repair_only | 530 | 0.498 | 0.6981 | {"SR1": 0.2094, "SR2": 0.1075, "SR3": 0.0415, "SR4": 0.0962, "SR5": 0.0434} | 80.0 | 92.42 | 0.301 |
| B3_proposal_plus_repair | 536 | 0.465 | 0.7164 | {"SR1": 0.1847, "SR2": 0.0914, "SR3": 0.0448, "SR4": 0.1026, "SR5": 0.041} | 80.0 | 90.73 | 0.362 |
| B3_nondominated_local | 563 | 0.503 | 0.675 | {"SR1": 0.2256, "SR2": 0.0906, "SR3": 0.0337, "SR4": 0.1101, "SR5": 0.0426} | 80.0 | 90.51 | 0.365 |

### D_balanced

| variant | rows | viol mean | zero-viol | SR1-SR5 rates | intent median | plaus median | mean dist |
|---|---|---|---|---|---|---|---|
| A_baseline | 210 | 0.29 | 0.7524 | {"SR1": 0.1476, "SR2": 0.0333, "SR3": 0.0571, "SR4": 0.0381, "SR5": 0.0143} | 100.0 | 91.94 | 0.176 |
| B1_proposal_only | 210 | 0.205 | 0.8238 | {"SR1": 0.0952, "SR2": 0.0238, "SR3": 0.0333, "SR4": 0.0381, "SR5": 0.0143} | 100.0 | 91.16 | 0.246 |
| B2_repair_only | 210 | 0.229 | 0.8048 | {"SR1": 0.1048, "SR2": 0.0238, "SR3": 0.0429, "SR4": 0.0429, "SR5": 0.0143} | 100.0 | 92.56 | 0.224 |
| B3_proposal_plus_repair | 210 | 0.214 | 0.8143 | {"SR1": 0.1, "SR2": 0.0238, "SR3": 0.0381, "SR4": 0.0381, "SR5": 0.0143} | 100.0 | 91.16 | 0.233 |
| B3_nondominated_local | 210 | 0.21 | 0.8238 | {"SR1": 0.0952, "SR2": 0.019, "SR3": 0.0333, "SR4": 0.0429, "SR5": 0.019} | 100.0 | 91.53 | 0.255 |

### E_sorting_focused

| variant | rows | viol mean | zero-viol | SR1-SR5 rates | intent median | plaus median | mean dist |
|---|---|---|---|---|---|---|---|
| A_baseline | 210 | 0.071 | 0.9476 | {"SR1": 0.0286, "SR2": 0.019, "SR3": 0.0048, "SR4": 0.019, "SR5": 0.0} | 90.0 | 90.66 | 0.314 |
| B1_proposal_only | 210 | 0.014 | 0.9857 | {"SR1": 0.0, "SR2": 0.0, "SR3": 0.0048, "SR4": 0.0095, "SR5": 0.0} | 100.0 | 90.01 | 0.372 |
| B2_repair_only | 210 | 0.024 | 0.981 | {"SR1": 0.0048, "SR2": 0.0048, "SR3": 0.0, "SR4": 0.0143, "SR5": 0.0} | 100.0 | 90.7 | 0.36 |
| B3_proposal_plus_repair | 210 | 0.01 | 0.9905 | {"SR1": 0.0, "SR2": 0.0, "SR3": 0.0, "SR4": 0.0095, "SR5": 0.0} | 100.0 | 90.56 | 0.374 |
| B3_nondominated_local | 210 | 0.005 | 0.9952 | {"SR1": 0.0, "SR2": 0.0, "SR3": 0.0, "SR4": 0.0048, "SR5": 0.0} | 100.0 | 90.75 | 0.37 |

### F_intent_focused

| variant | rows | viol mean | zero-viol | SR1-SR5 rates | intent median | plaus median | mean dist |
|---|---|---|---|---|---|---|---|
| A_baseline | 140 | 0.429 | 0.6714 | {"SR1": 0.1786, "SR2": 0.0714, "SR3": 0.0929, "SR4": 0.0643, "SR5": 0.0214} | 100.0 | 87.83 | 0.332 |
| B1_proposal_only | 140 | 0.293 | 0.7786 | {"SR1": 0.1071, "SR2": 0.0429, "SR3": 0.0643, "SR4": 0.0643, "SR5": 0.0143} | 100.0 | 88.11 | 0.356 |
| B2_repair_only | 140 | 0.257 | 0.7929 | {"SR1": 0.1, "SR2": 0.0286, "SR3": 0.0643, "SR4": 0.0643, "SR5": 0.0} | 100.0 | 87.86 | 0.38 |
| B3_proposal_plus_repair | 140 | 0.25 | 0.7929 | {"SR1": 0.1, "SR2": 0.0286, "SR3": 0.0571, "SR4": 0.0643, "SR5": 0.0} | 100.0 | 87.95 | 0.4 |
| B3_nondominated_local | 140 | 0.25 | 0.7929 | {"SR1": 0.1, "SR2": 0.0214, "SR3": 0.0571, "SR4": 0.0714, "SR5": 0.0} | 100.0 | 87.34 | 0.408 |

## Paired differences vs baseline (variant - A; request means; median CI over requests)

### B_hard_valid_candidates

| variant | violation_count | zero-violation share | intent (0-1) | plausibility (0-1) | template distance |
|---|---|---|---|---|---|
| B1_proposal_only | -0.547 (median -0.461 [-0.500, -0.414], n=210) | +0.242 (median +0.238 [+0.224, +0.256], n=210) | -0.018 (median +0.000 [-0.006, +0.004], n=140) | +0.048 (median +0.045 [+0.042, +0.053], n=210) | +0.022 (median +0.015 [+0.005, +0.029], n=210) |
| B2_repair_only | -0.772 (median -0.730 [-0.784, -0.671], n=210) | +0.416 (median +0.435 [+0.391, +0.463], n=210) | +0.017 (median +0.013 [+0.007, +0.017], n=140) | +0.073 (median +0.068 [+0.060, +0.078], n=210) | +0.158 (median +0.151 [+0.125, +0.169], n=210) |
| B3_proposal_plus_repair | -0.858 (median -0.807 [-0.868, -0.743], n=210) | +0.454 (median +0.461 [+0.446, +0.493], n=210) | -0.007 (median +0.001 [-0.003, +0.012], n=140) | +0.069 (median +0.063 [+0.058, +0.073], n=210) | +0.138 (median +0.134 [+0.110, +0.151], n=210) |
| B3_nondominated_local | -0.849 (median -0.762 [-0.838, -0.719], n=210) | +0.444 (median +0.456 [+0.439, +0.485], n=210) | -0.011 (median +0.005 [+0.000, +0.013], n=140) | +0.078 (median +0.075 [+0.069, +0.082], n=210) | +0.083 (median +0.083 [+0.053, +0.101], n=210) |

### C_pareto_front

| variant | violation_count | zero-violation share | intent (0-1) | plausibility (0-1) | template distance |
|---|---|---|---|---|---|
| B1_proposal_only | -0.131 (median +0.000 [+0.000, +0.000], n=210) | +0.090 (median +0.000 [+0.000, +0.000], n=210) | -0.000 (median +0.000 [+0.000, +0.000], n=140) | -0.001 (median +0.000 [+0.000, +0.000], n=210) | +0.030 (median +0.000 [+0.000, +0.000], n=210) |
| B2_repair_only | -0.197 (median +0.000 [+0.000, +0.000], n=210) | +0.133 (median +0.000 [+0.000, +0.000], n=210) | +0.008 (median +0.000 [+0.000, +0.000], n=140) | +0.002 (median +0.000 [+0.000, +0.000], n=210) | +0.035 (median +0.000 [+0.000, +0.000], n=210) |
| B3_proposal_plus_repair | -0.224 (median +0.000 [-0.067, +0.000], n=210) | +0.147 (median +0.000 [+0.000, +0.061], n=210) | +0.007 (median +0.000 [+0.000, +0.000], n=140) | -0.003 (median +0.000 [+0.000, +0.000], n=210) | +0.054 (median +0.000 [+0.000, +0.000], n=210) |
| B3_nondominated_local | -0.187 (median +0.000 [+0.000, +0.000], n=210) | +0.115 (median +0.000 [+0.000, +0.000], n=210) | +0.006 (median +0.000 [+0.000, +0.000], n=140) | -0.003 (median +0.000 [+0.000, +0.000], n=210) | +0.042 (median +0.000 [+0.000, +0.000], n=210) |

### E_sorting_focused

| variant | violation_count | zero-violation share | intent (0-1) | plausibility (0-1) | template distance |
|---|---|---|---|---|---|
| B1_proposal_only | -0.057 (median +0.000 [+0.000, +0.000], n=210) | +0.038 (median +0.000 [+0.000, +0.000], n=210) | +0.028 (median +0.000 [+0.000, +0.000], n=140) | -0.005 (median +0.000 [+0.000, +0.000], n=210) | +0.059 (median +0.000 [+0.000, +0.000], n=210) |
| B2_repair_only | -0.048 (median +0.000 [+0.000, +0.000], n=210) | +0.033 (median +0.000 [+0.000, +0.000], n=210) | +0.029 (median +0.000 [+0.000, +0.000], n=140) | +0.000 (median +0.000 [+0.000, +0.000], n=210) | +0.047 (median +0.000 [+0.000, +0.000], n=210) |
| B3_proposal_plus_repair | -0.062 (median +0.000 [+0.000, +0.000], n=210) | +0.043 (median +0.000 [+0.000, +0.000], n=210) | +0.026 (median +0.000 [+0.000, +0.000], n=140) | -0.004 (median +0.000 [+0.000, +0.000], n=210) | +0.061 (median +0.000 [+0.000, +0.000], n=210) |
| B3_nondominated_local | -0.067 (median +0.000 [+0.000, +0.000], n=210) | +0.048 (median +0.000 [+0.000, +0.000], n=210) | +0.024 (median +0.000 [+0.000, +0.000], n=140) | -0.002 (median +0.000 [+0.000, +0.000], n=210) | +0.056 (median +0.000 [+0.000, +0.000], n=210) |

### D_balanced

| variant | violation_count | zero-violation share | intent (0-1) | plausibility (0-1) | template distance |
|---|---|---|---|---|---|
| B1_proposal_only | -0.086 (median +0.000 [+0.000, +0.000], n=210) | +0.071 (median +0.000 [+0.000, +0.000], n=210) | +0.004 (median +0.000 [+0.000, +0.000], n=140) | -0.004 (median +0.000 [+0.000, +0.000], n=210) | +0.070 (median +0.000 [+0.000, +0.000], n=210) |
| B2_repair_only | -0.062 (median +0.000 [+0.000, +0.000], n=210) | +0.052 (median +0.000 [+0.000, +0.000], n=210) | +0.009 (median +0.000 [+0.000, +0.000], n=140) | -0.000 (median +0.000 [+0.000, +0.000], n=210) | +0.048 (median +0.000 [+0.000, +0.000], n=210) |
| B3_proposal_plus_repair | -0.076 (median +0.000 [+0.000, +0.000], n=210) | +0.062 (median +0.000 [+0.000, +0.000], n=210) | +0.006 (median +0.000 [+0.000, +0.000], n=140) | -0.004 (median +0.000 [+0.000, +0.000], n=210) | +0.057 (median +0.000 [+0.000, +0.000], n=210) |
| B3_nondominated_local | -0.081 (median +0.000 [+0.000, +0.000], n=210) | +0.071 (median +0.000 [+0.000, +0.000], n=210) | +0.006 (median +0.000 [+0.000, +0.000], n=140) | -0.005 (median +0.000 [+0.000, +0.000], n=210) | +0.079 (median +0.000 [+0.000, +0.000], n=210) |

### F_intent_focused

| variant | violation_count | zero-violation share | intent (0-1) | plausibility (0-1) | template distance |
|---|---|---|---|---|---|
| B1_proposal_only | -0.136 (median +0.000 [+0.000, +0.000], n=140) | +0.107 (median +0.000 [+0.000, +0.000], n=140) | -0.004 (median +0.000 [+0.000, +0.000], n=140) | +0.006 (median +0.000 [+0.000, +0.000], n=140) | +0.024 (median +0.000 [+0.000, +0.000], n=140) |
| B2_repair_only | -0.171 (median +0.000 [+0.000, +0.000], n=140) | +0.121 (median +0.000 [+0.000, +0.000], n=140) | -0.006 (median +0.000 [+0.000, +0.000], n=140) | +0.009 (median +0.000 [+0.000, +0.000], n=140) | +0.048 (median +0.000 [+0.000, +0.000], n=140) |
| B3_proposal_plus_repair | -0.179 (median +0.000 [+0.000, +0.000], n=140) | +0.121 (median +0.000 [+0.000, +0.000], n=140) | -0.009 (median +0.000 [+0.000, +0.000], n=140) | +0.005 (median +0.000 [+0.000, +0.000], n=140) | +0.068 (median +0.000 [+0.000, +0.000], n=140) |
| B3_nondominated_local | -0.179 (median +0.000 [+0.000, +0.000], n=140) | +0.121 (median +0.000 [+0.000, +0.000], n=140) | -0.009 (median +0.000 [+0.000, +0.000], n=140) | +0.000 (median +0.000 [+0.000, +0.000], n=140) | +0.076 (median +0.000 [+0.000, +0.000], n=140) |

## SR-specific effects: hard-valid pool rate differences (variant - A)

| variant | SR1 | SR2 | SR3 | SR4 | SR5 |
|---|---|---|---|---|---|
| B1_proposal_only | -0.269 (median -0.263 [-0.279, -0.246], n=210) | -0.102 (median -0.056 [-0.076, -0.008], n=210) | -0.142 (median -0.087 [-0.110, -0.062], n=210) | -0.002 (median +0.000 [+0.000, +0.000], n=210) | -0.032 (median +0.000 [-0.018, +0.000], n=210) |
| B2_repair_only | -0.427 (median -0.443 [-0.474, -0.416], n=210) | -0.108 (median -0.075 [-0.100, -0.012], n=210) | -0.166 (median -0.106 [-0.132, -0.087], n=210) | -0.001 (median +0.000 [+0.000, +0.000], n=210) | -0.070 (median -0.021 [-0.038, +0.000], n=210) |
| B3_proposal_plus_repair | -0.463 (median -0.486 [-0.500, -0.459], n=210) | -0.134 (median -0.100 [-0.104, -0.025], n=210) | -0.176 (median -0.107 [-0.138, -0.087], n=210) | -0.001 (median +0.000 [+0.000, +0.000], n=210) | -0.084 (median -0.026 [-0.050, +0.000], n=210) |
| B3_nondominated_local | -0.439 (median -0.450 [-0.473, -0.425], n=210) | -0.137 (median -0.086 [-0.101, -0.054], n=210) | -0.174 (median -0.103 [-0.138, -0.087], n=210) | -0.003 (median +0.000 [+0.000, +0.000], n=210) | -0.097 (median -0.029 [-0.053, +0.000], n=210) |

Sorting-focused selection:

| variant | SR1 | SR2 | SR3 | SR4 | SR5 |
|---|---|---|---|---|---|
| B1_proposal_only | -0.029 (median +0.000 [+0.000, +0.000], n=210) | -0.019 (median +0.000 [+0.000, +0.000], n=210) | +0.000 (median +0.000 [+0.000, +0.000], n=210) | -0.009 (median +0.000 [+0.000, +0.000], n=210) | +0.000 (median +0.000 [+0.000, +0.000], n=210) |
| B2_repair_only | -0.024 (median +0.000 [+0.000, +0.000], n=210) | -0.014 (median +0.000 [+0.000, +0.000], n=210) | -0.005 (median +0.000 [+0.000, +0.000], n=210) | -0.005 (median +0.000 [+0.000, +0.000], n=210) | +0.000 (median +0.000 [+0.000, +0.000], n=210) |
| B3_proposal_plus_repair | -0.029 (median +0.000 [+0.000, +0.000], n=210) | -0.019 (median +0.000 [+0.000, +0.000], n=210) | -0.005 (median +0.000 [+0.000, +0.000], n=210) | -0.009 (median +0.000 [+0.000, +0.000], n=210) | +0.000 (median +0.000 [+0.000, +0.000], n=210) |
| B3_nondominated_local | -0.029 (median +0.000 [+0.000, +0.000], n=210) | -0.019 (median +0.000 [+0.000, +0.000], n=210) | -0.005 (median +0.000 [+0.000, +0.000], n=210) | -0.014 (median +0.000 [+0.000, +0.000], n=210) | +0.000 (median +0.000 [+0.000, +0.000], n=210) |

## Pareto / selection

| variant | front median | front==1 | front violation levels | front intent range | front plaus range | role-duplicate rate | no zero-viol candidate |
|---|---|---|---|---|---|---|---|
| A_baseline | 2.0 | 0.2571 | 1.781 | 0.2301 | 0.0808 | 0.9667 | {"count": 11, "n_requests": 210, "rate": 0.0524} |
| B1_proposal_only | 2.0 | 0.2762 | 1.671 | 0.2206 | 0.0755 | 0.9762 | {"count": 3, "n_requests": 210, "rate": 0.0143} |
| B2_repair_only | 2.0 | 0.3333 | 1.49 | 0.2037 | 0.0655 | 0.9714 | {"count": 4, "n_requests": 210, "rate": 0.019} |
| B3_proposal_plus_repair | 2.0 | 0.3429 | 1.51 | 0.2032 | 0.0684 | 0.9714 | {"count": 2, "n_requests": 210, "rate": 0.0095} |
| B3_nondominated_local | 2.0 | 0.319 | 1.581 | 0.2043 | 0.0748 | 0.9667 | {"count": 1, "n_requests": 210, "rate": 0.0048} |

## Failure analysis and unresolved violations

**A_baseline** unresolved: null; failure counters: {}; rejected: {"duplicate_candidate": 16923, "identical_to_template": 7132, "gave_up_after_max_attempts": 671, "no_applicable_mutation": 1400}

**B1_proposal_only** unresolved: {"candidates_final": 14058, "SR1": 4174, "SR2": 1232, "SR3": 613, "SR5": 1677, "SR4_immutable_violation": 2414, "candidates_with_unresolved_repairable": 5763}; failure counters: {}; rejected: {"duplicate_candidate": 28991, "identical_to_template": 9672, "gave_up_after_max_attempts": 1158, "no_applicable_mutation": 1400}

**B2_repair_only** unresolved: {"candidates_final": 13538, "SR1": 1978, "SR2": 1173, "SR3": 320, "SR5": 1024, "SR4_immutable_violation": 2338, "candidates_with_unresolved_repairable": 2887}; failure counters: {"accepted_repairs_introducing_other_violation": 43, "confirmed_fixed:SR1": 15322, "confirmed_fixed:SR2": 1915, "confirmed_fixed:SR3": 4320, "confirmed_fixed:SR5": 7518, "no_train_supported_alternative:SR1": 9, "no_train_supported_alternative:SR2": 9, "no_train_supported_alternative:SR5": 11, "proposals_introducing_other_violation": 2215, "repair_accepted": 24342, "repair_accepted:SR1": 12958, "repair_accepted:SR2": 1539, "repair_accepted:SR3": 3870, "repair_accepted:SR5": 5975, "repair_cycle_prevented": 36, "repair_rejected:intent_floor": 11729, "repair_rejected:no_violation_decrease": 11755, "repair_rejected:plausibility_floor": 6098}; rejected: {"duplicate_candidate": 35952, "identical_to_template": 19118, "gave_up_after_max_attempts": 1678, "no_applicable_mutation": 1400}

**B3_proposal_plus_repair** unresolved: {"candidates_final": 13435, "SR1": 1416, "SR2": 755, "SR3": 154, "SR5": 805, "SR4_immutable_violation": 2309, "candidates_with_unresolved_repairable": 2125}; failure counters: {"accepted_repairs_introducing_other_violation": 13, "confirmed_fixed:SR1": 4371, "confirmed_fixed:SR2": 518, "confirmed_fixed:SR3": 639, "confirmed_fixed:SR5": 7671, "no_train_supported_alternative:SR5": 1, "proposals_introducing_other_violation": 1741, "repair_accepted": 12443, "repair_accepted:SR1": 3942, "repair_accepted:SR2": 472, "repair_accepted:SR3": 605, "repair_accepted:SR5": 7424, "repair_cycle_prevented": 22, "repair_rejected:intent_floor": 5385, "repair_rejected:no_violation_decrease": 8491, "repair_rejected:plausibility_floor": 4509}; rejected: {"duplicate_candidate": 36646, "identical_to_template": 18365, "gave_up_after_max_attempts": 1781, "no_applicable_mutation": 1400}

**B3_nondominated_local** unresolved: {"candidates_final": 13206, "SR1": 1729, "SR2": 694, "SR3": 183, "SR5": 611, "SR4_immutable_violation": 2228, "candidates_with_unresolved_repairable": 2187}; failure counters: {"accepted_repairs_introducing_other_violation": 210, "confirmed_fixed:SR1": 3793, "confirmed_fixed:SR2": 371, "confirmed_fixed:SR3": 432, "confirmed_fixed:SR5": 9394, "no_train_supported_alternative:SR1": 85, "no_train_supported_alternative:SR2": 35, "no_train_supported_alternative:SR5": 512, "proposals_introducing_other_violation": 4690, "repair_accepted": 20154, "repair_accepted:SR1": 7024, "repair_accepted:SR2": 433, "repair_accepted:SR3": 541, "repair_accepted:SR5": 12156, "repair_cycle_prevented": 362, "repair_rejected:not_locally_nondominated": 43483}; rejected: {"duplicate_candidate": 38089, "identical_to_template": 24740, "gave_up_after_max_attempts": 2010, "no_applicable_mutation": 1400}

## Small-pool stratification

### pool <5: 9 requests SMALL POOL: interpret with caution

| variant | gen/req | no-cand | valid viol | valid zero | sorting viol | balanced intent | balanced plaus | unique | front==1 | repair acc | no alt | unresolved |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A_baseline | 0.1306 | 0.3333 | 0.787 | 0.3617 | 0 | 77.5 | 81.32 | 0.8643 | 0.6667 | None | 0 | None |
| B1_proposal_only | 0.0958 | 0.3333 | 0.478 | 0.5942 | 0 | 77.5 | 81.64 | 1.0 | 0.8333 | None | 0 | 0.3043 |
| B2_repair_only | 0.0778 | 0.3333 | 0.125 | 0.875 | 0 | 77.5 | 81.56 | 1.0 | 0.8333 | 0.9486 | 0 | 0.0 |
| B3_proposal_plus_repair | 0.0778 | 0.3333 | 0.125 | 0.875 | 0 | 77.5 | 81.64 | 1.0 | 0.8333 | 0.9111 | 0 | 0.0 |
| B3_nondominated_local | 0.0778 | 0.3333 | 0.125 | 0.875 | 0 | 77.5 | 81.64 | 1.0 | 0.8333 | 0.84 | 0 | 0.0 |

paired valid-pool violation vs A: {"B1_proposal_only": "-0.385 (median -0.350 [-0.688, -0.171], n=6)", "B2_repair_only": "-0.721 (median -0.658 [-1.062, -0.460], n=6)", "B3_proposal_plus_repair": "-0.721 (median -0.658 [-1.062, -0.460], n=6)", "B3_nondominated_local": "-0.721 (median -0.658 [-1.062, -0.460], n=6)"}

### pool 5-19: 12 requests SMALL POOL: interpret with caution

| variant | gen/req | no-cand | valid viol | valid zero | sorting viol | balanced intent | balanced plaus | unique | front==1 | repair acc | no alt | unresolved |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A_baseline | 0.2208 | 0.0 | 1.212 | 0.3019 | 0.083 | 77.08 | 81.87 | 1.0 | 0.3333 | None | 0 | None |
| B1_proposal_only | 0.2156 | 0.0 | 0.343 | 0.7536 | 0 | 81.25 | 81.85 | 1.0 | 0.5833 | None | 0 | 0.2464 |
| B2_repair_only | 0.2083 | 0.0 | 0.08 | 0.955 | 0 | 81.25 | 81.82 | 1.0 | 0.6667 | 0.6937 | 0 | 0.045 |
| B3_proposal_plus_repair | 0.2083 | 0.0 | 0.06 | 0.965 | 0 | 81.25 | 82.18 | 1.0 | 0.6667 | 0.5113 | 0 | 0.035 |
| B3_nondominated_local | 0.2083 | 0.0 | 0.06 | 0.965 | 0 | 81.25 | 82.06 | 1.0 | 0.6667 | 0.341 | 0 | 0.035 |

paired valid-pool violation vs A: {"B1_proposal_only": "-0.722 (median -0.917 [-1.000, -0.367], n=12)", "B2_repair_only": "-1.014 (median -1.042 [-1.333, -0.646], n=12)", "B3_proposal_plus_repair": "-1.028 (median -1.052 [-1.333, -0.646], n=12)", "B3_nondominated_local": "-1.028 (median -1.052 [-1.333, -0.646], n=12)"}

### pool 20-99: 39 requests 

| variant | gen/req | no-cand | valid viol | valid zero | sorting viol | balanced intent | balanced plaus | unique | front==1 | repair acc | no alt | unresolved |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A_baseline | 0.8071 | 0.0 | 1.154 | 0.2589 | 0 | 86.15 | 83.6 | 0.9303 | 0.2821 | None | 0 | None |
| B1_proposal_only | 0.7625 | 0.0 | 0.702 | 0.4754 | 0 | 84.23 | 83.77 | 1.0 | 0.2821 | None | 0 | 0.4107 |
| B2_repair_only | 0.7234 | 0.0 | 0.474 | 0.6535 | 0 | 86.15 | 84.9 | 1.0 | 0.3077 | 0.5377 | 0 | 0.2051 |
| B3_proposal_plus_repair | 0.7064 | 0.0 | 0.397 | 0.6878 | 0 | 84.23 | 84.57 | 1.0 | 0.3333 | 0.5527 | 0 | 0.1493 |
| B3_nondominated_local | 0.6696 | 0.0 | 0.363 | 0.7099 | 0 | 84.23 | 84.63 | 1.0 | 0.3333 | 0.4932 | 341 | 0.1163 |

paired valid-pool violation vs A: {"B1_proposal_only": "-0.436 (median -0.424 [-0.477, -0.335], n=39)", "B2_repair_only": "-0.654 (median -0.607 [-0.727, -0.585], n=39)", "B3_proposal_plus_repair": "-0.715 (median -0.692 [-0.808, -0.634], n=39)", "B3_nondominated_local": "-0.739 (median -0.746 [-0.827, -0.706], n=39)"}

### pool >=100: 153 requests 

| variant | gen/req | no-cand | valid viol | valid zero | sorting viol | balanced intent | balanced plaus | unique | front==1 | repair acc | no alt | unresolved |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A_baseline | 0.9576 | 0.0 | 1.303 | 0.2702 | 0.092 | 91.76 | 92.06 | 0.9644 | 0.2288 | None | 0 | None |
| B1_proposal_only | 0.9316 | 0.0 | 0.731 | 0.506 | 0.02 | 92.42 | 91.38 | 1.0 | 0.2288 | None | 0 | 0.4134 |
| B2_repair_only | 0.9007 | 0.0 | 0.521 | 0.6691 | 0.033 | 92.75 | 91.7 | 1.0 | 0.2941 | 0.4252 | 29 | 0.219 |
| B3_proposal_plus_repair | 0.8967 | 0.0 | 0.414 | 0.7152 | 0.013 | 92.75 | 91.28 | 1.0 | 0.3007 | 0.3603 | 1 | 0.163 |
| B3_nondominated_local | 0.8873 | 0.0 | 0.43 | 0.6991 | 0.007 | 92.75 | 91.05 | 1.0 | 0.268 | 0.2747 | 291 | 0.1783 |

paired valid-pool violation vs A: {"B1_proposal_only": "-0.568 (median -0.474 [-0.516, -0.415], n=153)", "B2_repair_only": "-0.784 (median -0.756 [-0.817, -0.695], n=153)", "B3_proposal_plus_repair": "-0.886 (median -0.838 [-0.876, -0.788], n=153)", "B3_nondominated_local": "-0.868 (median -0.792 [-0.851, -0.693], n=153)"}
