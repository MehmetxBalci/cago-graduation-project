# CAGO evaluation validation (controlled perturbations)

Terminology: Dataset-relative Plausibility (similarity/support relative to the TRAIN distribution; not a statement about production), Intent Alignment (preference-alignment index; not measured performance), SR1-SR5 Sorting Compatibility (equal-weight rule-satisfaction; not a recyclability or sustainability figure).

TEST garments used as evaluation examples only: 600. Support splits used: ['train']. Seed 1, bootstrap 1000 resamples.

## 1. Plausibility by perturbation level (weighting 0.50/0.50)

| level | n | median | mean | ctx median | prox median | mean #subst | mean abs pct | hard-valid |
|---|---|---|---|---|---|---|---|---|
| L0 | 600 | 94.04 | 90.39 | 0.8807 | 1.0 | 0.0 | 0.0 | 0.9983 |
| L1 | 423 | 90.58 | 87.06 | 0.8283 | 0.99 | 0.0 | 2.312 | 1.0 |
| L2 | 423 | 85.55 | 82.22 | 0.8283 | 0.9048 | 0.0 | 23.121 | 1.0 |
| L3 | 600 | 54.4 | 51.54 | 0.4814 | 0.6065 | 1.0 | 0.0 | 0.9983 |
| L4 | 600 | 30.33 | 38.03 | 0.0 | 0.6065 | 1.0 | 0.0 | 0.9983 |

### Expected ordering (paired by garment)

| hypothesis | n | share satisfying | ties | median diff (pts) | 95% CI |
|---|---|---|---|---|---|
| L0>=L1 | 423 | 1.0 | 0.0 | 0.5 | [0.5, 0.5] |
| L1>=L2 | 423 | 1.0 | 0.0 | 4.26 | [4.26, 4.26] |
| L0>=L2 | 423 | 1.0 | 0.0 | 4.76 | [4.76, 4.76] |
| L0>L4 (unsupported context scores lower) | 600 | 1.0 | 0.0 | 52.69 | [47.03, 54.48] |
| L0>=L3 (descriptive) | 600 | 0.985 | 0.0 | 39.02 | [36.4, 40.3] |
| L3>=L4 (descriptive) | 600 | 0.98 | 0.2817 | 9.19 | [7.81, 11.4] |
| chain L0>=L1>=L2 (per garment) | 423 | 1.0 |  |  |  |
| L4<L0 (per garment) | 600 | 1.0 |  |  |  |
| all expected (L0>=L1>=L2 and L4<L0) | 423 | 1.0 |  |  |  |

### Component-level contextual support

```json
{"L3": {"n": 600, "mean_support_count_before": 359.31, "mean_support_count_after": 47.94, "share_support_decreased": 0.8983, "share_after_zero_support": 0.3117, "component_score_change": {"n": 600, "mean": -0.4728, "median": -0.4547, "std": 0.3582, "min": -1.0, "p25": -0.7735, "p75": -0.2404, "max": 1.0}}, "L4": {"n": 600, "mean_support_count_before": 348.2, "mean_support_count_after": 0.0, "share_support_decreased": 0.98, "share_after_zero_support": 1.0, "component_score_change": {"n": 600, "mean": -0.8052, "median": -0.9017, "std": 0.2503, "min": -1.0, "p25": -1.0, "p75": -0.6731, "max": 0.0}}, "L4_zero_support_substitution_share": 1.0}
```

## 2. Weight sensitivity (context/proximity)

| weighting | ordering shares | median by level |
|---|---|---|
| 0.25/0.75 | {"L0>=L1": 1.0, "L1>=L2": 1.0, "L0>=L2": 1.0, "L0>L4 (unsupported context scores lower)": 1.0, "L0>=L3 (descriptive)": 1.0, "L3>=L4 (descriptive)": 0.98, "chain L0>=L1>=L2 (per garment)": 1.0, "L4<L0 (per garment)": 1.0, "all expected (L0>=L1>=L2 and L4<L0)": 1.0} | {"L0": 97.02, "L1": 94.76, "L2": 86.48, "L3": 57.53, "L4": 45.49} |
| 0.50/0.50 | {"L0>=L1": 1.0, "L1>=L2": 1.0, "L0>=L2": 1.0, "L0>L4 (unsupported context scores lower)": 1.0, "L0>=L3 (descriptive)": 0.985, "L3>=L4 (descriptive)": 0.98, "chain L0>=L1>=L2 (per garment)": 1.0, "L4<L0 (per garment)": 1.0, "all expected (L0>=L1>=L2 and L4<L0)": 1.0} | {"L0": 94.04, "L1": 90.58, "L2": 85.55, "L3": 54.4, "L4": 30.33} |
| 0.75/0.25 | {"L0>=L1": 1.0, "L1>=L2": 1.0, "L0>=L2": 1.0, "L0>L4 (unsupported context scores lower)": 1.0, "L0>=L3 (descriptive)": 0.9617, "L3>=L4 (descriptive)": 0.98, "chain L0>=L1>=L2 (per garment)": 1.0, "L4<L0 (per garment)": 1.0, "all expected (L0>=L1>=L2 and L4<L0)": 1.0} | {"L0": 91.06, "L1": 86.76, "L2": 84.19, "L3": 51.27, "L4": 15.16} |

Spread (std / IQR by level): {"0.25/0.75": {"L0": {"std": 5.749, "iqr": 7.668}, "L1": {"std": 6.052, "iqr": 9.289}, "L2": {"std": 6.317, "iqr": 9.07}, "L3": {"std": 7.742, "iqr": 14.061}, "L4": {"std": 5.796, "iqr": 9.806}}, "0.50/0.50": {"L0": {"std": 11.498, "iqr": 15.336}, "L1": {"std": 12.148, "iqr": 19.051}, "L2": {"std": 12.056, "iqr": 16.805}, "L3": {"std": 15.484, "iqr": 28.121}, "L4": {"std": 11.591, "iqr": 19.612}}, "0.75/0.25": {"L0": {"std": 17.247, "iqr": 23.004}, "L1": {"std": 18.249, "iqr": 28.595}, "L2": {"std": 18.158, "iqr": 27.898}, "L3": {"std": 23.226, "iqr": 42.182}, "L4": {"std": 17.387, "iqr": 29.418}}}

Pooled-item Spearman between weightings: {"0.25/0.75 vs 0.50/0.50": 0.98407, "0.25/0.75 vs 0.75/0.25": 0.950974, "0.50/0.50 vs 0.75/0.25": 0.988264}

## 3-4. Intent Alignment validation + isolation

Cases: 11030; experiments passing: 29/29; case pass rate 1.0.

| experiment | n | expected | observed | pass rate | status | affected | unintended | isolation |
|---|---|---|---|---|---|---|---|---|
| breathability_coating_added | 381 | decrease | {"decrease": 381} | 1.0 | PASS | {"breathability": 381} | {} | 1.0 |
| breathability_filling_added | 381 | decrease | {"decrease": 381} | 1.0 | PASS | {"breathability": 381} | {} | 1.0 |
| breathability_polyester_to_cotton | 181 | increase | {"increase": 181} | 1.0 | PASS | {"breathability": 181} | {} | 1.0 |
| colour_changed | 600 | decrease | {"decrease": 600} | 1.0 | PASS | {"colour": 600} | {} | 1.0 |
| colour_exact_match | 600 | 1.0 | {"1.0": 600} | 1.0 | PASS | {} | {} | 1.0 |
| dominant_material_original_matches | 600 | 1.0 | {"1.0": 600} | 1.0 | PASS | {} | {} | 1.0 |
| dominant_percentage_swap | 236 | decrease | {"decrease": 236} | 1.0 | PASS | {"preferred_dominant_material": 236} | {} | 1.0 |
| dominant_substitution | 599 | decrease | {"decrease": 599} | 1.0 | PASS | {"preferred_dominant_material": 599} | {} | 1.0 |
| durability_cotton_to_nylon | 294 | increase | {"increase": 294} | 1.0 | PASS | {"durability_wear": 294} | {} | 1.0 |
| durability_text_ripstop_added | 569 | increase | {"increase": 569} | 1.0 | PASS | {"durability_wear": 569} | {} | 1.0 |
| elastane_shift_low_to_high | 51 | decrease | {"decrease": 51} | 1.0 | PASS | {"stretch": 51} | {} | 1.0 |
| fit_exact_match | 464 | 1.0 | {"1.0": 464} | 1.0 | PASS | {} | {} | 1.0 |
| fit_mismatch_supported_label | 464 | decrease | {"decrease": 464} | 1.0 | PASS | {"fit": 464} | {} | 1.0 |
| fit_unlabeled_is_unscorable_not_zero | 129 | None | {"None": 129} | 1.0 | PASS | {} | {} | 1.0 |
| length_exact_match | 308 | 1.0 | {"1.0": 308} | 1.0 | PASS | {} | {} | 1.0 |
| length_mismatch_supported_label | 308 | decrease | {"decrease": 308} | 1.0 | PASS | {"length_cut": 308} | {} | 1.0 |
| length_unlabeled_is_unscorable_not_zero | 292 | None | {"None": 292} | 1.0 | PASS | {} | {} | 1.0 |
| moisture_cotton_to_polyester | 219 | increase | {"increase": 219} | 1.0 | PASS | {"moisture_wicking": 219} | {} | 1.0 |
| moisture_polyester_to_cotton | 181 | decrease | {"decrease": 181} | 1.0 | PASS | {"moisture_wicking": 181} | {} | 1.0 |
| moisture_text_quick_dry_added | 449 | increase | {"increase": 449} | 1.0 | PASS | {"moisture_wicking": 449} | {} | 1.0 |
| stretch_original_bucket_matches | 600 | 1.0 | {"1.0": 600} | 1.0 | PASS | {} | {} | 1.0 |
| stretch_threshold | 15 | exact table value | {"1.0": 5, "0.0": 10} | 1.0 | PASS | {} | {} | 1.0 |
| thermal_heavy_cotton_to_wool | 310 | increase | {"increase": 310} | 1.0 | PASS | {"thermal_warmth": 310} | {} | 1.0 |
| thermal_heavy_filling_added | 581 | increase | {"increase": 581} | 1.0 | PASS | {"thermal_warmth": 581} | {} | 1.0 |
| thermal_light_filling_added | 396 | decrease | {"decrease": 396} | 1.0 | PASS | {"thermal_warmth": 396} | {} | 1.0 |
| thermal_light_wool_to_cotton | 40 | increase | {"increase": 40} | 1.0 | PASS | {"thermal_warmth": 40} | {} | 1.0 |
| water_coating_added | 597 | increase | {"increase": 597} | 1.0 | PASS | {"water_repellent": 597} | {} | 1.0 |
| water_coating_removed | 597 | decrease | {"decrease": 597} | 1.0 | PASS | {"water_repellent": 597} | {} | 1.0 |
| water_text_evidence_added | 588 | increase | {"increase": 588} | 1.0 | PASS | {"water_repellent": 588} | {} | 1.0 |

Isolation overall: {"experiments": ["colour_changed", "dominant_percentage_swap", "dominant_substitution", "elastane_shift_low_to_high", "fit_mismatch_supported_label", "length_mismatch_supported_label"], "n_cases": 2258, "isolation_accuracy": 1.0, "intended_direction_and_isolated": 1.0}

## Questionable / notable metric behaviour

- Contextual support is combination-based, so L1/L2 percentage perturbations leave it exactly unchanged for every garment (paired, max change 0): the L0>=L1>=L2 ordering is produced entirely by the template-proximity term and holds by construction.
- Percentages are not part of the contextual term: share of garments with a slot above the TRAIN maximum for its material is 0.0083 (L0) / 0.026 (L1) / 0.0331 (L2) and is not penalised by contextual support.
- L0>=L3 (descriptive): expected relation holds for 0.985 of pairs (a supported substitution can raise contextual support when the original combination is rare in TRAIN).
- L3>=L4 (descriptive): expected relation holds for 0.980 of pairs (an L3 'supported' substitution can still create a combination unseen in TRAIN, so it can tie with or fall below L4).
- Weighting changes the L0>=L3 ordering share: 0.25/0.75: 1.0, 0.50/0.50: 0.985, 0.75/0.25: 0.9617 (more context weight -> more cases where the substituted garment outscores the original).
- Functional proxies are coupled through shared materials/components (legitimate, but a single manipulation moves several requested properties at once); other proxies changed per experiment (counts): {"breathability_coating_added": {"water_repellent": 381, "durability_wear": 2, "moisture_wicking": 2}, "breathability_filling_added": {"thermal_warmth": 381}, "breathability_polyester_to_cotton": {"moisture_wicking": 181, "water_repellent": 162, "durability_wear": 14}, "durability_cotton_to_nylon": {"breathability": 294, "moisture_wicking": 294, "water_repellent": 275}, "moisture_cotton_to_polyester": {"breathability": 219, "water_repellent": 212, "durability_wear": 10}, "moisture_polyester_to_cotton": {"breathability": 181, "water_repellent": 162, "durability_wear": 14}, "thermal_heavy_cotton_to_wool": {"breathability": 310, "durability_wear": 85}, "thermal_heavy_filling_added": {"breathability": 402}, "thermal_light_filling_added": {"breathability": 396}, "thermal_light_wool_to_cotton": {"breathability": 40, "durability_wear": 23}, "water_coating_added": {"breathability": 402, "durability_wear": 3, "moisture_wicking": 10}, "water_coating_removed": {"breathability": 402, "durability_wear": 3, "moisture_wicking": 10}}
- Proxies saturate at satisfaction 1 (e.g. water_repellent after two strong evidence items), so further evidence cannot increase the score; the experiments therefore require headroom (preconditions) before testing a strict direction.
- Duplicate material names inside a component are aggregated by the metric (as in the Oracle): a percentage swap between two slots of the same material does not change dominance; such garments are excluded from the swap experiment.
