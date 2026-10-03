# CAGO template baseline generator v1 - audit

Seed 42; templates/request 10; candidates/template 5; mutations/candidate 1-3.

Support tables (TRAIN only): {'splits_used': ['train'], 'n_train_garments': 33265, 'n_components_used': 46734, 'n_components_skipped_non_vocab': 247, 'categories': 23, 'category_class_cells': 158, 'distinct_materials': 22, 'distinct_combinations': 1775, 'pct_stat_cells': 817}

Leakage: templates from non-train splits = 0; support splits_used = ['train'].

| request | eligible tmpl | selected | candidates | forbidden occ. | PAD/OTHER occ. | sums 100 | mean dist | ANY tmpl% | ANY cand% | deterministic |
|---|---|---|---|---|---|---|---|---|---|---|
| women/trousers | 1868 | 10 | 50/50 | 0 | 0 | True | 0.9436 | 100.0 | 88.0 | True |
| men/tshirt_polo | 944 | 10 | 50/50 | 0 | 0 | True | 0.8896 | 90.0 | 88.0 | True |
| women/dresses | 2418 | 10 | 50/50 | 0 | 0 | True | 0.9836 | 70.0 | 94.0 | True |
| men/outerwear_jacket | 391 | 10 | 50/50 | 0 | 0 | True | 1.264 | 90.0 | 84.0 | True |
| kids/sweatshirt_hoodie | 767 | 10 | 44/50 | 0 | 0 | True | 0.7568 | 10.0 | 40.91 | True |
| men/set | 6 | 3 | 15/50 | 0 | 0 | True | 1.9773 | 66.67 | 100.0 | True |
| baby/trousers | 2 | 1 | 5/50 | 0 | 0 | True | 0.816 | 0.0 | 60.0 | True |

## women / trousers

hard: {'forbidden_materials': ['polyester']}; soft (non-null): {'preferred_dominant_material': 'linen', 'stretch': 'low', 'breathability': 'high', 'fit': 'relaxed', 'length_cut': 'long'}; warnings: []

pool: {'train_garments_in_cell': 1876, 'eligible_templates': 1868, 'ineligible_reasons': {'non_vocab_material_token': 8}, 'selected': 10, 'selected_distinct_parents': 10, 'requested': 10, 'pool_smaller_than_requested': False, 'selected_requiring_forbidden_repair': 0}

generation: {'candidates_requested': 50, 'candidates_generated': 50, 'attempts': 56, 'rejected': {'duplicate_candidate': 3, 'identical_to_template': 3}, 'failed_templates_unrepairable': [], 'mutation_types': {'substitution': 64, 'percentage': 40}, 'forbidden_repairs': 0, 'mean_mutations_per_candidate': 2.08}

oracle: {'template_rates_pct': {'sr1_violation': 90.0, 'sr2_violation': 30.0, 'sr3_violation': 40.0, 'sr4_violation': 0.0, 'sr5_violation': 0.0, 'any_violation': 100.0}, 'candidate_rates_pct': {'sr1_violation': 86.0, 'sr2_violation': 30.0, 'sr3_violation': 32.0, 'sr4_violation': 0.0, 'sr5_violation': 6.0, 'any_violation': 88.0}, 'candidates_whose_flag_differs_from_template': {'sr1_violation': 10, 'sr2_violation': 0, 'sr3_violation': 4, 'sr4_violation': 0, 'sr5_violation': 3}}

- `cand_ebe86a68d29d3202` from `g_ffc6e2061355f436` dist={'n_substitutions': 1, 'abs_pct_change_total': 10.0, 'diagnostic_distance': 1.1} log=[('substitution', None, 'viscose', 'cotton'), ('percentage', None, 'wool', 'linen')]
- `cand_4eee410a98739838` from `g_ffc6e2061355f436` dist={'n_substitutions': 1, 'abs_pct_change_total': 2.0, 'diagnostic_distance': 1.02} log=[('substitution', None, 'wool', 'acrylic'), ('substitution', None, 'acrylic', 'cotton'), ('percentage', None, 'viscose', 'linen')]

## men / tshirt_polo

hard: {'forbidden_materials': []}; soft (non-null): {'stretch': 'low', 'moisture_wicking': True}; warnings: []

pool: {'train_garments_in_cell': 944, 'eligible_templates': 944, 'ineligible_reasons': {}, 'selected': 10, 'selected_distinct_parents': 10, 'requested': 10, 'pool_smaller_than_requested': False, 'selected_requiring_forbidden_repair': 0}

generation: {'candidates_requested': 50, 'candidates_generated': 50, 'attempts': 73, 'rejected': {'identical_to_template': 6, 'duplicate_candidate': 17}, 'failed_templates_unrepairable': [], 'mutation_types': {'substitution': 54, 'percentage': 50}, 'forbidden_repairs': 0, 'mean_mutations_per_candidate': 2.08}

oracle: {'template_rates_pct': {'sr1_violation': 80.0, 'sr2_violation': 60.0, 'sr3_violation': 70.0, 'sr4_violation': 30.0, 'sr5_violation': 0.0, 'any_violation': 90.0}, 'candidate_rates_pct': {'sr1_violation': 80.0, 'sr2_violation': 60.0, 'sr3_violation': 62.0, 'sr4_violation': 30.0, 'sr5_violation': 0.0, 'any_violation': 88.0}, 'candidates_whose_flag_differs_from_template': {'sr1_violation': 4, 'sr2_violation': 0, 'sr3_violation': 4, 'sr4_violation': 0, 'sr5_violation': 0}}

- `cand_9137024b1703bfd2` from `g_c5d5c0b2998e0a2e` dist={'n_substitutions': 1, 'abs_pct_change_total': 10.0, 'diagnostic_distance': 1.1} log=[('substitution', None, 'lyocell', 'viscose'), ('substitution', None, 'viscose', 'nylon'), ('percentage', None, 'polyester', 'wool')]
- `cand_732a9e7773d72d43` from `g_c5d5c0b2998e0a2e` dist={'n_substitutions': 0, 'abs_pct_change_total': 2.0, 'diagnostic_distance': 0.02} log=[('percentage', None, 'lyocell', 'elastane')]

## women / dresses

hard: {'forbidden_materials': []}; soft (non-null): {}; warnings: []

pool: {'train_garments_in_cell': 2426, 'eligible_templates': 2418, 'ineligible_reasons': {'non_vocab_material_token': 7, 'unmapped_material': 1}, 'selected': 10, 'selected_distinct_parents': 10, 'requested': 10, 'pool_smaller_than_requested': False, 'selected_requiring_forbidden_repair': 0}

generation: {'candidates_requested': 50, 'candidates_generated': 50, 'attempts': 63, 'rejected': {'duplicate_candidate': 10, 'identical_to_template': 3}, 'failed_templates_unrepairable': [], 'mutation_types': {'percentage': 40, 'substitution': 67}, 'forbidden_repairs': 0, 'mean_mutations_per_candidate': 2.14}

oracle: {'template_rates_pct': {'sr1_violation': 50.0, 'sr2_violation': 0.0, 'sr3_violation': 0.0, 'sr4_violation': 50.0, 'sr5_violation': 10.0, 'any_violation': 70.0}, 'candidate_rates_pct': {'sr1_violation': 64.0, 'sr2_violation': 0.0, 'sr3_violation': 4.0, 'sr4_violation': 50.0, 'sr5_violation': 38.0, 'any_violation': 94.0}, 'candidates_whose_flag_differs_from_template': {'sr1_violation': 11, 'sr2_violation': 0, 'sr3_violation': 2, 'sr4_violation': 0, 'sr5_violation': 16}}

- `cand_49ed05a87908b3e8` from `g_fb57e9b60fbecf19` dist={'n_substitutions': 0, 'abs_pct_change_total': 6.0, 'diagnostic_distance': 0.06} log=[('percentage', None, 'lyocell', 'polyester'), ('percentage', None, 'lyocell', 'polyester')]
- `cand_c26e54aaccc168a5` from `g_fb57e9b60fbecf19` dist={'n_substitutions': 2, 'abs_pct_change_total': 10.0, 'diagnostic_distance': 2.1} log=[('substitution', None, 'polyester', 'nylon'), ('substitution', None, 'lyocell', 'cotton'), ('percentage', None, 'cotton', 'nylon')]

## men / outerwear_jacket

hard: {'forbidden_materials': ['down', 'feather']}; soft (non-null): {'water_repellent': True}; warnings: []

pool: {'train_garments_in_cell': 404, 'eligible_templates': 391, 'ineligible_reasons': {'non_vocab_material_token': 10, 'unmapped_material': 3}, 'selected': 10, 'selected_distinct_parents': 10, 'requested': 10, 'pool_smaller_than_requested': False, 'selected_requiring_forbidden_repair': 0}

generation: {'candidates_requested': 50, 'candidates_generated': 50, 'attempts': 59, 'rejected': {'identical_to_template': 2, 'duplicate_candidate': 7}, 'failed_templates_unrepairable': [], 'mutation_types': {'substitution': 90, 'percentage': 5}, 'forbidden_repairs': 0, 'mean_mutations_per_candidate': 1.9}

oracle: {'template_rates_pct': {'sr1_violation': 20.0, 'sr2_violation': 10.0, 'sr3_violation': 10.0, 'sr4_violation': 30.0, 'sr5_violation': 70.0, 'any_violation': 90.0}, 'candidate_rates_pct': {'sr1_violation': 32.0, 'sr2_violation': 10.0, 'sr3_violation': 10.0, 'sr4_violation': 30.0, 'sr5_violation': 78.0, 'any_violation': 84.0}, 'candidates_whose_flag_differs_from_template': {'sr1_violation': 12, 'sr2_violation': 0, 'sr3_violation': 0, 'sr4_violation': 0, 'sr5_violation': 16}}

- `cand_6439c5074c07e817` from `g_862cbe5c905a5093` dist={'n_substitutions': 1, 'abs_pct_change_total': 0.0, 'diagnostic_distance': 1.0} log=[('substitution', None, 'nylon', 'polyester'), ('substitution', None, 'polyester', 'cotton')]
- `cand_72e1877b352780b4` from `g_862cbe5c905a5093` dist={'n_substitutions': 2, 'abs_pct_change_total': 0.0, 'diagnostic_distance': 2.0} log=[('substitution', None, 'nylon', 'polyester'), ('substitution', None, 'polyester', 'leather'), ('substitution', None, 'polyester', 'cotton')]

## kids / sweatshirt_hoodie

hard: {'forbidden_materials': ['acrylic']}; soft (non-null): {'thermal_warmth': 'heavy'}; warnings: []

pool: {'train_garments_in_cell': 767, 'eligible_templates': 767, 'ineligible_reasons': {}, 'selected': 10, 'selected_distinct_parents': 10, 'requested': 10, 'pool_smaller_than_requested': False, 'selected_requiring_forbidden_repair': 0}

generation: {'candidates_requested': 50, 'candidates_generated': 44, 'attempts': 210, 'rejected': {'duplicate_candidate': 105, 'identical_to_template': 61, 'gave_up_after_max_attempts': 6}, 'failed_templates_unrepairable': [], 'mutation_types': {'substitution': 38, 'percentage': 44}, 'forbidden_repairs': 0, 'mean_mutations_per_candidate': 1.864}

oracle: {'template_rates_pct': {'sr1_violation': 10.0, 'sr2_violation': 10.0, 'sr3_violation': 10.0, 'sr4_violation': 0.0, 'sr5_violation': 0.0, 'any_violation': 10.0}, 'candidate_rates_pct': {'sr1_violation': 36.36, 'sr2_violation': 11.36, 'sr3_violation': 11.36, 'sr4_violation': 0.0, 'sr5_violation': 9.09, 'any_violation': 40.91}, 'candidates_whose_flag_differs_from_template': {'sr1_violation': 11, 'sr2_violation': 0, 'sr3_violation': 0, 'sr4_violation': 0, 'sr5_violation': 4}}

- `cand_13e03d25dd7cdfc6` from `g_cf29e6669bf3edac` dist={'n_substitutions': 1, 'abs_pct_change_total': 0.0, 'diagnostic_distance': 1.0} log=[('substitution', None, 'polyester', 'cotton')]
- `cand_7fc566e2a8012bde` from `g_cf29e6669bf3edac` dist={'n_substitutions': 1, 'abs_pct_change_total': 0.0, 'diagnostic_distance': 1.0} log=[('substitution', None, 'polyester', 'wool')]

## men / set

hard: {'forbidden_materials': ['cotton', 'polyester']}; soft (non-null): {}; warnings: []

pool: {'train_garments_in_cell': 6, 'eligible_templates': 6, 'ineligible_reasons': {}, 'selected': 3, 'selected_distinct_parents': 3, 'requested': 10, 'pool_smaller_than_requested': True, 'selected_requiring_forbidden_repair': 3}

generation: {'candidates_requested': 50, 'candidates_generated': 15, 'attempts': 15, 'rejected': {}, 'failed_templates_unrepairable': [], 'mutation_types': {'substitution': 38, 'percentage': 14}, 'forbidden_repairs': 25, 'mean_mutations_per_candidate': 3.467}

oracle: {'template_rates_pct': {'sr1_violation': 33.33, 'sr2_violation': 33.33, 'sr3_violation': 66.67, 'sr4_violation': 0.0, 'sr5_violation': 0.0, 'any_violation': 66.67}, 'candidate_rates_pct': {'sr1_violation': 100.0, 'sr2_violation': 33.33, 'sr3_violation': 60.0, 'sr4_violation': 0.0, 'sr5_violation': 0.0, 'any_violation': 100.0}, 'candidates_whose_flag_differs_from_template': {'sr1_violation': 10, 'sr2_violation': 0, 'sr3_violation': 1, 'sr4_violation': 0, 'sr5_violation': 0}}

- `cand_f4773d721857f631` from `g_90dc20e62daf9311` dist={'n_substitutions': 1, 'abs_pct_change_total': 0.0, 'diagnostic_distance': 1.0} log=[('substitution', 'forbidden_repair', 'cotton', 'viscose'), ('percentage', None, 'viscose', 'elastane'), ('substitution', None, 'viscose', 'nylon'), ('percentage', None, 'elastane', 'nylon')]
- `cand_9aebe5ee21754df1` from `g_90dc20e62daf9311` dist={'n_substitutions': 2, 'abs_pct_change_total': 0.0, 'diagnostic_distance': 2.0} log=[('substitution', 'forbidden_repair', 'cotton', 'viscose'), ('substitution', None, 'viscose', 'wool'), ('substitution', None, 'elastane', 'nylon')]

## baby / trousers

hard: {'forbidden_materials': []}; soft (non-null): {}; warnings: []

pool: {'train_garments_in_cell': 2, 'eligible_templates': 2, 'ineligible_reasons': {}, 'selected': 1, 'selected_distinct_parents': 1, 'requested': 10, 'pool_smaller_than_requested': True, 'selected_requiring_forbidden_repair': 0}

generation: {'candidates_requested': 50, 'candidates_generated': 5, 'attempts': 5, 'rejected': {}, 'failed_templates_unrepairable': [], 'mutation_types': {'substitution': 7, 'percentage': 3}, 'forbidden_repairs': 0, 'mean_mutations_per_candidate': 2}

oracle: {'template_rates_pct': {'sr1_violation': 0.0, 'sr2_violation': 0.0, 'sr3_violation': 0.0, 'sr4_violation': 0.0, 'sr5_violation': 0.0, 'any_violation': 0.0}, 'candidate_rates_pct': {'sr1_violation': 60.0, 'sr2_violation': 0.0, 'sr3_violation': 0.0, 'sr4_violation': 0.0, 'sr5_violation': 0.0, 'any_violation': 60.0}, 'candidates_whose_flag_differs_from_template': {'sr1_violation': 3, 'sr2_violation': 0, 'sr3_violation': 0, 'sr4_violation': 0, 'sr5_violation': 0}}

- `cand_0a89db275630b1da` from `g_102c257f10841fe0` dist={'n_substitutions': 1, 'abs_pct_change_total': 6.0, 'diagnostic_distance': 1.06} log=[('substitution', None, 'elastane', 'viscose'), ('percentage', None, 'cotton', 'viscose'), ('percentage', None, 'cotton', 'viscose')]
- `cand_9ac07526a27c53fa` from `g_102c257f10841fe0` dist={'n_substitutions': 1, 'abs_pct_change_total': 0.0, 'diagnostic_distance': 1.0} log=[('substitution', None, 'cotton', 'viscose')]

## Edge cases

- kids/sweatshirt_hoodie: 44/50 candidates generated; rejections {'duplicate_candidate': 105, 'identical_to_template': 61, 'gave_up_after_max_attempts': 6}
- men/set: only 3 templates available (requested 10)
- men/set: 15/50 candidates generated; rejections {}
- baby/trousers: only 1 templates available (requested 10)
- baby/trousers: 5/50 candidates generated; rejections {}
