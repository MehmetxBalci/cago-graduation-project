# CAGO baseline benchmark (TRAIN-only generation, TEST-derived requests)

Terminology: Dataset-relative Plausibility (similarity/support relative to the TRAIN distribution; not a statement about production), Intent Alignment (preference-alignment index; not measured performance), SR1-SR5 Sorting Compatibility (equal-weight rule-satisfaction; not a recyclability or sustainability figure).

Requests 216 (ok 210, no valid candidates 6, invalid 0); cells 72; categories 23; segments {'baby': 27, 'kids': 69, 'men': 51, 'women': 69}; types {'no_pref': 72, 'derived_full': 72, 'derived_forbid': 72}; with soft preferences 144; with forbidden materials 72. Seed 0; bootstrap 1000. Determinism re-run: {'rerun_requests': 20, 'all_identical': True}.

Candidates: {'candidates_generated': 17831, 'hard_valid': 17831, 'hard_valid_rate': 1.0, 'candidates_requested': 21600}.

## Stage comparison (descriptive; pooled rows)

| stage | rows | requests | viol mean | viol median | zero-viol rate | SR1-SR5 rates | intent median | plaus median | mean dist |
|---|---|---|---|---|---|---|---|---|---|
| A_templates | 1905 | 210 | 1.06 | 1.0 | 0.4289 | {"SR1": 0.3927, "SR2": 0.21, "SR3": 0.1864, "SR4": 0.1664, "SR5": 0.105} | 80.0 | 90.44 | 0.0 |
| B_hard_valid_candidates | 17831 | 210 | 1.339 | 1.0 | 0.2535 | {"SR1": 0.5748, "SR2": 0.2253, "SR3": 0.2038, "SR4": 0.1721, "SR5": 0.1626} | 66.67 | 58.42 | 0.92 |
| C_pareto_front | 627 | 210 | 0.738 | 0.0 | 0.5726 | {"SR1": 0.2775, "SR2": 0.1324, "SR3": 0.1675, "SR4": 0.0909, "SR5": 0.0702} | 100.0 | 93.08 | 0.242 |
| D_balanced | 210 | 210 | 0.333 | 0.0 | 0.7476 | {"SR1": 0.1667, "SR2": 0.0476, "SR3": 0.0571, "SR4": 0.0286, "SR5": 0.0333} | 100.0 | 91.42 | 0.183 |
| E_sorting_focused | 210 | 210 | 0.11 | 0.0 | 0.9429 | {"SR1": 0.0429, "SR2": 0.0333, "SR3": 0.0143, "SR4": 0.019, "SR5": 0.0} | 80.0 | 90.43 | 0.306 |
| F_intent_focused | 140 | 140 | 0.471 | 0.0 | 0.6857 | {"SR1": 0.2, "SR2": 0.0786, "SR3": 0.1071, "SR4": 0.0643, "SR5": 0.0214} | 100.0 | 89.59 | 0.294 |

### Paired difference to own template (cluster bootstrap over requests; median [95% CI])

| stage | violations | intent pts | plausibility pts |
|---|---|---|---|
| B_hard_valid_candidates | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | -30.1401 [-31.0195, -29.1624] |
| C_pareto_front | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | -0.4976 [-0.8657, -0.4975] |
| D_balanced | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | -0.4975 [-0.4976, -0.4975] |
| E_sorting_focused | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | -0.7438 [-0.99, -0.4975] |
| F_intent_focused | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | -0.4975 [-0.99, -0.4975] |

### Request-level paired violation difference vs templates

```json
{"B_hard_valid_candidates": {"n_requests": 210, "mean_violation_minus_templates_per_request": {"n": 210, "point": 0.2745, "lo": 0.2337, "hi": 0.3211, "level": 0.95, "n_resamples": 1000, "stat": "median"}}, "C_pareto_front": {"n_requests": 210, "mean_violation_minus_templates_per_request": {"n": 210, "point": -0.5, "lo": -0.5667, "hi": -0.3833, "level": 0.95, "n_resamples": 1000, "stat": "median"}}, "D_balanced": {"n_requests": 210, "mean_violation_minus_templates_per_request": {"n": 210, "point": -0.7, "lo": -0.8, "hi": -0.6, "level": 0.95, "n_resamples": 1000, "stat": "median"}}, "E_sorting_focused": {"n_requests": 210, "mean_violation_minus_templates_per_request": {"n": 210, "point": -0.8571, "lo": -1.0, "hi": -0.7, "level": 0.95, "n_resamples": 1000, "stat": "median"}}, "F_intent_focused": {"n_requests": 140, "mean_violation_minus_templates_per_request": {"n": 140, "point": -0.55, "lo": -0.7, "hi": -0.35, "level": 0.95, "n_resamples": 1000, "stat": "median"}}}
```

## Trade-off frequencies (candidate vs its own template)

| stage | rows | sorting up & intent down | intent up & sorting down | sorting up & plaus drop>20.0 | all three improve |
|---|---|---|---|---|---|
| B_hard_valid_candidates | 17831 | 366/11869 (0.0308) | 240/11869 (0.0202) | 793/17831 (0.0445) | 5/11869 (0.0004) |
| C_pareto_front | 627 | 42/452 (0.0929) | 4/452 (0.0088) | 32/627 (0.051) | 1/452 (0.0022) |
| D_balanced | 210 | 1/140 (0.0071) | 1/140 (0.0071) | 2/210 (0.0095) | 1/140 (0.0071) |
| E_sorting_focused | 210 | 20/140 (0.1429) | 0/140 (0.0) | 15/210 (0.0714) | 1/140 (0.0071) |
| F_intent_focused | 140 | 0/140 (0.0) | 0/140 (0.0) | 7/140 (0.05) | 1/140 (0.0071) |

Requests without a zero-violation Pareto candidate: {'count': 12, 'n_requests': 210, 'rate': 0.0571}

## Small template pools

| pool bin | requests | cells | median pool | generated/requested | no-candidate rate | front==1 | template viol | sorting viol | sorting zero-viol | no zero-viol front | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|
| <5 | 9 | 3 | 0 | 0.0333 | 0.6667 | 0.3333 | 0 | 0 | 1.0 | 0.0 | SMALL POOL: interpret with caution |
| 5-19 | 15 | 5 | 11 | 0.246 | 0.0 | 0.4667 | 1.179 | 0.6 | 0.8 | 0.2 | SMALL POOL: interpret with caution |
| 20-99 | 39 | 13 | 66 | 0.7877 | 0.0 | 0.2308 | 0.826 | 0 | 1.0 | 0.0 |  |
| >=100 | 153 | 51 | 476 | 0.9386 | 0.0 | 0.2222 | 1.11 | 0.092 | 0.9412 | 0.0588 |  |

## Notes

- Requests are derived from held-out TEST garments (dominant material, elastane bucket, colour, V1 fit/length labels); all templates, support tables and generation are TRAIN-only.
- Stage rows are pooled over requests; request-level and cluster-bootstrap statistics are reported to avoid treating candidates as independent.
- Descriptive evaluation: no causal superiority claim; selected designs are Pareto-restricted subsets of the generated candidates.
