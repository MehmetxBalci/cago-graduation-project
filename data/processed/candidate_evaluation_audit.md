# CAGO candidate evaluation + Pareto selection v1 - audit

Indices: Intent = confidence-weighted preference alignment; Sorting = SR1-SR5 violation count (equal-weight rule-satisfaction index is reporting only); Plausibility = dataset-relative support/similarity (TRAIN only). None is a recyclability, sustainability or manufacturability measure.

Support tables: splits_used=['train']; seed=42.

| request | generated | hard-valid | front | intent min/med/max | viol dist (0..5) | plaus med | deterministic |
|---|---|---|---|---|---|---|---|
| women/trousers | 80 | 80 | 3 (violation_count,intent_loss,plausibility_loss) | 32.11/55.56/77.78 | [9, 43, 6, 18, 4, 0] | 53.27 | True |
| men/tshirt_polo | 80 | 80 | 3 (violation_count,intent_loss,plausibility_loss) | 0.0/40.45/94.0 | [0, 18, 13, 37, 12, 0] | 48.93 | True |
| women/dresses | 80 | 80 | 2 (violation_count,plausibility_loss) | None/None/None | [6, 37, 31, 6, 0, 0] | 63.39 | True |
| women/dresses | 80 | 80 | 1 (violation_count,intent_loss,plausibility_loss) | 100.0/100.0/100.0 | [19, 43, 15, 3, 0, 0] | 55.77 | True |
| men/outerwear_jacket | 79 | 79 | 8 (violation_count,intent_loss,plausibility_loss) | 0.0/42.0/82.0 | [8, 36, 30, 5, 0, 0] | 63.6 | True |
| kids/sweatshirt_hoodie | 80 | 80 | 9 (violation_count,intent_loss,plausibility_loss) | 63.57/63.57/100.0 | [45, 30, 5, 0, 0, 0] | 55.18 | True |
| men/set | 24 | 24 | 2 (violation_count,intent_loss,plausibility_loss) | 0.0/100.0/100.0 | [0, 12, 5, 7, 0, 0] | 18.39 | True |
| baby/trousers | 8 | 8 | 2 (violation_count,intent_loss,plausibility_loss) | 0.0/0.0/100.0 | [5, 3, 0, 0, 0, 0] | 91.62 | True |

## women / trousers

hard: {'forbidden_materials': ['polyester']}; soft: {'preferred_dominant_material': 'linen', 'stretch': 'low', 'breathability': 'high', 'fit': 'relaxed', 'length_cut': 'long'}; unscorable: {}

| role(s) | candidate | viol | sorting idx | intent | plausibility |
|---|---|---|---|---|---|
| sorting_focused | cand_5a59c50e23dcc75f | 0 | 100.0 | 55.56 | 79.46 |
| balanced+intent_focused | cand_abd13c7861b91537 | 1 | 80.0 | 77.78 | 91.03 |

SR rates % (templates / valid / front / selected): {'SR1': 90.0, 'SR2': 30.0, 'SR3': 40.0, 'SR4': 0.0, 'SR5': 0.0, 'ANY': 100.0} / {'SR1': 86.25, 'SR2': 30.0, 'SR3': 35.0, 'SR4': 0.0, 'SR5': 5.0, 'ANY': 88.75} / {'SR1': 33.33, 'SR2': 0.0, 'SR3': 33.33, 'SR4': 0.0, 'SR5': 0.0, 'ANY': 66.67} / {'SR1': 50.0, 'SR2': 0.0, 'SR3': 0.0, 'SR4': 0.0, 'SR5': 0.0, 'ANY': 50.0}

trade-off flags: {'pareto_front': {'sorting_improves_intent_decreases': 1, 'intent_improves_sorting_worsens': 0, 'plausibility_falls_substantially': 0}, 'selected': {'sorting_improves_intent_decreases': ['cand_5a59c50e23dcc75f'], 'intent_improves_sorting_worsens': [], 'plausibility_falls_substantially': []}, 'front_size_is_one': False, 'plausibility_drop_threshold_pts': 20.0}

**sorting_focused** `cand_5a59c50e23dcc75f` (template `g_16f303f35bedc6f2`)
- SR1 is no longer violated compared with the template (confirmed: undoing mutation step(s) [2] restores the template's SR1 result).
- Preference 'breathability=high' satisfied: proxy 'breathability=high' scored 1 from composition/text evidence (breathable_fibre_share=1.00).
- Preference 'fit=relaxed' satisfied: template fit label 'relaxed' matches requested 'relaxed'.
- Preference 'length_cut=long' satisfied: template length_cut label 'long' matches requested 'long'.
- Preference 'preferred_dominant_material=linen' not fully satisfied (satisfaction 0): linen is not the highest-percentage material of the primary component ('cotton' at 100%).
- Preference 'stretch=low' not fully satisfied (satisfaction 0): proxy 'stretch=low' scored -1 from composition/text evidence (elastane=0%; bucket=none).
- Sorting rule violations: template 1 -> candidate 0 (-1).
- Intent alignment index: template 77.8 -> candidate 55.6 (-22.2 points).
- Dataset-relative plausibility index: template 78.3 -> candidate 79.5 (+1.2 points).
- Trade-off: sorting rule violations decreased while intent alignment decreased relative to the template.
- mutation: Substituted linen with lyocell in component 'main' (slot at 100%)
- mutation: Substituted lyocell with linen in component 'main' (slot at 100%)
- mutation: Substituted linen with cotton in component 'main' (slot at 100%)

**balanced+intent_focused** `cand_abd13c7861b91537` (template `g_18a9798a474bfa64`)
- Preference 'preferred_dominant_material=linen' satisfied: linen is the highest-percentage material of the primary component ('linen' at 56%).
- Preference 'breathability=high' satisfied: proxy 'breathability=high' scored 1 from composition/text evidence (breathable_fibre_share=1.00).
- Preference 'fit=relaxed' satisfied: template fit label 'relaxed' matches requested 'relaxed'.
- Preference 'length_cut=long' satisfied: template length_cut label 'long' matches requested 'long'.
- Preference 'stretch=low' not fully satisfied (satisfaction 0): proxy 'stretch=low' scored -1 from composition/text evidence (elastane=0%; bucket=none).
- Sorting rule violations: template 1 -> candidate 1 (+0).
- Intent alignment index: template 77.8 -> candidate 77.8 (+0.0 points).
- Dataset-relative plausibility index: template 91.5 -> candidate 91.0 (-0.5 points).
- mutation: Moved 1 percentage points from viscose (45% -> 44%) to linen (55% -> 56%) in component 'shell'


## men / tshirt_polo

hard: {'forbidden_materials': []}; soft: {'stretch': 'low', 'moisture_wicking': True, 'colour': 'black'}; unscorable: {}

| role(s) | candidate | viol | sorting idx | intent | plausibility |
|---|---|---|---|---|---|
| intent_focused | cand_588c755ec6e47da4 | 4 | 20.0 | 94.0 | 51.18 |
| balanced+sorting_focused | cand_7b61a0b81a320483 | 1 | 80.0 | 63.64 | 87.7 |

SR rates % (templates / valid / front / selected): {'SR1': 60.0, 'SR2': 60.0, 'SR3': 70.0, 'SR4': 60.0, 'SR5': 0.0, 'ANY': 100.0} / {'SR1': 72.5, 'SR2': 60.0, 'SR3': 61.25, 'SR4': 60.0, 'SR5': 0.0, 'ANY': 100.0} / {'SR1': 33.33, 'SR2': 33.33, 'SR3': 66.67, 'SR4': 100.0, 'SR5': 0.0, 'ANY': 100.0} / {'SR1': 50.0, 'SR2': 50.0, 'SR3': 50.0, 'SR4': 100.0, 'SR5': 0.0, 'ANY': 100.0}

trade-off flags: {'pareto_front': {'sorting_improves_intent_decreases': 0, 'intent_improves_sorting_worsens': 0, 'plausibility_falls_substantially': 0}, 'selected': {'sorting_improves_intent_decreases': [], 'intent_improves_sorting_worsens': [], 'plausibility_falls_substantially': []}, 'front_size_is_one': False, 'plausibility_drop_threshold_pts': 20.0}

**intent_focused** `cand_588c755ec6e47da4` (template `g_c5d5c0b2998e0a2e`)
- Preference 'stretch=low' satisfied: proxy 'stretch=low' scored 1 from composition/text evidence (elastane=2%; bucket=low).
- Preference 'colour=black' satisfied: candidate colour 'black' matches requested 'black' (exact match).
- Preference 'moisture_wicking=True' not fully satisfied (satisfaction 0.78): proxy 'moisture_wicking=True' scored 0.78 from composition/text evidence (polyester_nylon_share=0.78).
- Sorting rule violations: template 4 -> candidate 4 (+0).
- Intent alignment index: template 92.4 -> candidate 94.0 (+1.6 points).
- Dataset-relative plausibility index: template 54.6 -> candidate 51.2 (-3.4 points).
- mutation: Moved 2 percentage points from wool (9% -> 7%) to polyester (72% -> 74%) in component 'main'
- mutation: Moved 5 percentage points from wool (7% -> 2%) to polyester (74% -> 79%) in component 'main'
- mutation: Moved 1 percentage points from polyester (79% -> 78%) to elastane (1% -> 2%) in component 'main'

**balanced+sorting_focused** `cand_7b61a0b81a320483` (template `g_ae652a0e3cb8b6c6`)
- Preference 'moisture_wicking=True' satisfied: proxy 'moisture_wicking=True' scored 1 from composition/text evidence (polyester_nylon_share=0.91; text:quick_dry).
- Preference 'colour=black' satisfied: candidate colour 'black' matches requested 'black' (exact match).
- Preference 'stretch=low' not fully satisfied (satisfaction 0): proxy 'stretch=low' scored -1 from composition/text evidence (elastane=9%; bucket=high).
- Sorting rule violations: template 1 -> candidate 1 (+0).
- Intent alignment index: template 63.6 -> candidate 63.6 (+0.0 points).
- Dataset-relative plausibility index: template 88.2 -> candidate 87.7 (-0.5 points).
- mutation: Moved 1 percentage points from polyester (92% -> 91%) to elastane (8% -> 9%) in component 'main'
- mutation: Substituted polyester with cotton in component 'main' (slot at 91%)
- mutation: Substituted cotton with polyester in component 'main' (slot at 91%)


## women / dresses

hard: {'forbidden_materials': []}; soft: {}; unscorable: {}

| role(s) | candidate | viol | sorting idx | intent | plausibility |
|---|---|---|---|---|---|
| balanced+sorting_focused | cand_239ee2e649fa9d14 | 0 | 100.0 | None | 91.58 |

SR rates % (templates / valid / front / selected): {'SR1': 50.0, 'SR2': 0.0, 'SR3': 0.0, 'SR4': 50.0, 'SR5': 10.0, 'ANY': 70.0} / {'SR1': 58.75, 'SR2': 0.0, 'SR3': 2.5, 'SR4': 50.0, 'SR5': 35.0, 'ANY': 92.5} / {'SR1': 50.0, 'SR2': 0.0, 'SR3': 0.0, 'SR4': 0.0, 'SR5': 50.0, 'ANY': 50.0} / {'SR1': 0.0, 'SR2': 0.0, 'SR3': 0.0, 'SR4': 0.0, 'SR5': 0.0, 'ANY': 0.0}

trade-off flags: {'pareto_front': {'sorting_improves_intent_decreases': 0, 'intent_improves_sorting_worsens': 0, 'plausibility_falls_substantially': 0}, 'selected': {'sorting_improves_intent_decreases': [], 'intent_improves_sorting_worsens': [], 'plausibility_falls_substantially': []}, 'front_size_is_one': False, 'plausibility_drop_threshold_pts': 20.0}

**balanced+sorting_focused** `cand_239ee2e649fa9d14` (template `g_4a754cb4ae6c270e`)
- Sorting rule violations: template 0 -> candidate 0 (+0).
- Dataset-relative plausibility index: template 93.1 -> candidate 91.6 (-1.5 points).
- mutation: Moved 1 percentage points from cotton (42% -> 41%) to polyester (58% -> 59%) in component 'shell'
- mutation: Moved 2 percentage points from cotton (41% -> 39%) to polyester (59% -> 61%) in component 'shell'


## women / dresses

hard: {'forbidden_materials': []}; soft: {'thermal_warmth': 'standard', 'fit': 'slim', 'length_cut': 'long'}; unscorable: {'thermal_warmth:neutral_value': 80}

| role(s) | candidate | viol | sorting idx | intent | plausibility |
|---|---|---|---|---|---|
| balanced+intent_focused+sorting_focused | cand_154c000f9de65c55 | 0 | 100.0 | 100.0 | 93.09 |

SR rates % (templates / valid / front / selected): {'SR1': 20.0, 'SR2': 10.0, 'SR3': 20.0, 'SR4': 20.0, 'SR5': 0.0, 'ANY': 50.0} / {'SR1': 52.5, 'SR2': 10.0, 'SR3': 10.0, 'SR4': 20.0, 'SR5': 10.0, 'ANY': 76.25} / {'SR1': 0.0, 'SR2': 0.0, 'SR3': 0.0, 'SR4': 0.0, 'SR5': 0.0, 'ANY': 0.0} / {'SR1': 0.0, 'SR2': 0.0, 'SR3': 0.0, 'SR4': 0.0, 'SR5': 0.0, 'ANY': 0.0}

trade-off flags: {'pareto_front': {'sorting_improves_intent_decreases': 0, 'intent_improves_sorting_worsens': 0, 'plausibility_falls_substantially': 0}, 'selected': {'sorting_improves_intent_decreases': [], 'intent_improves_sorting_worsens': [], 'plausibility_falls_substantially': []}, 'front_size_is_one': True, 'plausibility_drop_threshold_pts': 20.0}

**balanced+intent_focused+sorting_focused** `cand_154c000f9de65c55` (template `g_08e1d7557a08e23b`)
- Preference 'fit=slim' satisfied: template fit label 'slim' matches requested 'slim'.
- Preference 'length_cut=long' satisfied: template length_cut label 'long' matches requested 'long'.
- Preference 'thermal_warmth=standard' could not be scored (neutral_value).
- Sorting rule violations: template 0 -> candidate 0 (+0).
- Intent alignment index: template 100.0 -> candidate 100.0 (+0.0 points).
- Dataset-relative plausibility index: template 94.1 -> candidate 93.1 (-1.0 points).
- mutation: Substituted elastane with nylon in component 'shell' (slot at 11%)
- mutation: Moved 2 percentage points from polyester (89% -> 87%) to nylon (11% -> 13%) in component 'shell'
- mutation: Substituted nylon with elastane in component 'shell' (slot at 13%)


## men / outerwear_jacket

hard: {'forbidden_materials': ['down', 'feather']}; soft: {'durability_wear': 'reinforced', 'water_repellent': True}; unscorable: {}

| role(s) | candidate | viol | sorting idx | intent | plausibility |
|---|---|---|---|---|---|
| balanced+intent_focused+sorting_focused | cand_e56eb461d22e7c6d | 0 | 100.0 | 82.0 | 63.92 |

SR rates % (templates / valid / front / selected): {'SR1': 10.0, 'SR2': 0.0, 'SR3': 0.0, 'SR4': 30.0, 'SR5': 70.0, 'ANY': 80.0} / {'SR1': 27.85, 'SR2': 0.0, 'SR3': 1.27, 'SR4': 30.38, 'SR5': 81.01, 'ANY': 89.87} / {'SR1': 12.5, 'SR2': 0.0, 'SR3': 0.0, 'SR4': 12.5, 'SR5': 75.0, 'ANY': 75.0} / {'SR1': 0.0, 'SR2': 0.0, 'SR3': 0.0, 'SR4': 0.0, 'SR5': 0.0, 'ANY': 0.0}

trade-off flags: {'pareto_front': {'sorting_improves_intent_decreases': 1, 'intent_improves_sorting_worsens': 0, 'plausibility_falls_substantially': 3}, 'selected': {'sorting_improves_intent_decreases': [], 'intent_improves_sorting_worsens': [], 'plausibility_falls_substantially': ['cand_e56eb461d22e7c6d']}, 'front_size_is_one': False, 'plausibility_drop_threshold_pts': 20.0}

**balanced+intent_focused+sorting_focused** `cand_e56eb461d22e7c6d` (template `g_e35286f9dcff0e91`)
- SR5 is no longer violated compared with the template (confirmed: undoing mutation step(s) [0] restores the template's SR5 result).
- Preference 'durability_wear=reinforced' satisfied: proxy 'durability_wear=reinforced' scored 1 from composition/text evidence (nylon_share=1.00).
- Preference 'water_repellent=True' not fully satisfied (satisfaction 0.7): proxy 'water_repellent=True' scored 0.7 from composition/text evidence (text:water_resistant; supporting:synthetic_shell).
- Sorting rule violations: template 1 -> candidate 0 (-1).
- Intent alignment index: template 82.0 -> candidate 82.0 (+0.0 points).
- Dataset-relative plausibility index: template 93.8 -> candidate 63.9 (-29.9 points).
- mutation: Substituted polyester with nylon in component 'inner_layer' (slot at 100%)


## kids / sweatshirt_hoodie

hard: {'forbidden_materials': ['acrylic']}; soft: {'thermal_warmth': 'heavy', 'fit': 'oversized'}; unscorable: {}

| role(s) | candidate | viol | sorting idx | intent | plausibility |
|---|---|---|---|---|---|
| balanced+sorting_focused | cand_290bdf070eb3038e | 0 | 100.0 | 63.57 | 99.5 |
| intent_focused | cand_6308d497a94f3454 | 2 | 60.0 | 100.0 | 52.44 |

SR rates % (templates / valid / front / selected): {'SR1': 0.0, 'SR2': 0.0, 'SR3': 0.0, 'SR4': 0.0, 'SR5': 0.0, 'ANY': 0.0} / {'SR1': 40.0, 'SR2': 0.0, 'SR3': 0.0, 'SR4': 0.0, 'SR5': 10.0, 'ANY': 43.75} / {'SR1': 33.33, 'SR2': 0.0, 'SR3': 0.0, 'SR4': 0.0, 'SR5': 11.11, 'ANY': 33.33} / {'SR1': 50.0, 'SR2': 0.0, 'SR3': 0.0, 'SR4': 0.0, 'SR5': 50.0, 'ANY': 50.0}

trade-off flags: {'pareto_front': {'sorting_improves_intent_decreases': 0, 'intent_improves_sorting_worsens': 3, 'plausibility_falls_substantially': 3}, 'selected': {'sorting_improves_intent_decreases': [], 'intent_improves_sorting_worsens': ['cand_6308d497a94f3454'], 'plausibility_falls_substantially': ['cand_6308d497a94f3454']}, 'front_size_is_one': False, 'plausibility_drop_threshold_pts': 20.0}

**balanced+sorting_focused** `cand_290bdf070eb3038e` (template `g_d67a7bc7c475a683`)
- Preference 'fit=oversized' satisfied: template fit label 'oversized' matches requested 'oversized'.
- Preference 'thermal_warmth=heavy' not fully satisfied (satisfaction 0.15): proxy 'thermal_warmth=heavy' scored 0.15 from composition/text evidence (wool_acrylic_share=0.00; text:brushed).
- Sorting rule violations: template 0 -> candidate 0 (+0).
- Intent alignment index: template 63.6 -> candidate 63.6 (+0.0 points).
- Dataset-relative plausibility index: template 100.0 -> candidate 99.5 (-0.5 points).
- mutation: Moved 1 percentage points from polyester (20% -> 19%) to cotton (80% -> 81%) in component 'shell'

**intent_focused** `cand_6308d497a94f3454` (template `g_d67a7bc7c475a683`)
- SR1 is newly violated compared with the template (confirmed: undoing mutation step(s) [1] restores the template's SR1 result).
- SR5 is newly violated compared with the template (confirmed: undoing mutation step(s) [1] restores the template's SR5 result).
- Preference 'thermal_warmth=heavy' satisfied: proxy 'thermal_warmth=heavy' scored 1 from composition/text evidence (wool_acrylic_share=0.90; text:brushed).
- Preference 'fit=oversized' satisfied: template fit label 'oversized' matches requested 'oversized'.
- Sorting rule violations: template 0 -> candidate 2 (+2).
- Intent alignment index: template 63.6 -> candidate 100.0 (+36.4 points).
- Dataset-relative plausibility index: template 100.0 -> candidate 52.4 (-47.6 points).
- Trade-off: intent alignment increased while sorting rule violations increased relative to the template.
- mutation: Moved 5 percentage points from polyester (20% -> 15%) to cotton (80% -> 85%) in component 'shell'
- mutation: Substituted cotton with wool in component 'shell' (slot at 85%)
- mutation: Moved 5 percentage points from polyester (15% -> 10%) to wool (85% -> 90%) in component 'shell'


## men / set

hard: {'forbidden_materials': ['cotton', 'polyester']}; soft: {'preferred_dominant_material': 'nylon'}; unscorable: {}

| role(s) | candidate | viol | sorting idx | intent | plausibility |
|---|---|---|---|---|---|
| balanced+intent_focused+sorting_focused | cand_2d0a944f1c434063 | 1 | 80.0 | 100.0 | 48.13 |

SR rates % (templates / valid / front / selected): {'SR1': 33.33, 'SR2': 33.33, 'SR3': 66.67, 'SR4': 0.0, 'SR5': 0.0, 'ANY': 66.67} / {'SR1': 100.0, 'SR2': 33.33, 'SR3': 45.83, 'SR4': 0.0, 'SR5': 0.0, 'ANY': 100.0} / {'SR1': 100.0, 'SR2': 0.0, 'SR3': 50.0, 'SR4': 0.0, 'SR5': 0.0, 'ANY': 100.0} / {'SR1': 100.0, 'SR2': 0.0, 'SR3': 0.0, 'SR4': 0.0, 'SR5': 0.0, 'ANY': 100.0}

trade-off flags: {'pareto_front': {'sorting_improves_intent_decreases': 0, 'intent_improves_sorting_worsens': 1, 'plausibility_falls_substantially': 2}, 'selected': {'sorting_improves_intent_decreases': [], 'intent_improves_sorting_worsens': [], 'plausibility_falls_substantially': ['cand_2d0a944f1c434063']}, 'front_size_is_one': False, 'plausibility_drop_threshold_pts': 20.0}

**balanced+intent_focused+sorting_focused** `cand_2d0a944f1c434063` (template `g_90dc20e62daf9311`)
- SR1 is newly violated compared with the template (confirmed: undoing mutation step(s) [0] restores the template's SR1 result).
- SR3 is no longer violated compared with the template (confirmed: undoing mutation step(s) [1] restores the template's SR3 result).
- Preference 'preferred_dominant_material=nylon' satisfied: nylon is the highest-percentage material of the primary component ('nylon' at 91%).
- Sorting rule violations: template 1 -> candidate 1 (+0).
- Intent alignment index: template 0.0 -> candidate 100.0 (+100.0 points).
- Dataset-relative plausibility index: template 91.0 -> candidate 48.1 (-42.9 points).
- mutation: Substituted cotton with nylon in component 'main' (slot at 96%) (forbidden-material repair)
- mutation: Moved 5 percentage points from nylon (96% -> 91%) to elastane (4% -> 9%) in component 'main'


## baby / trousers

hard: {'forbidden_materials': []}; soft: {'stretch': 'low'}; unscorable: {}

| role(s) | candidate | viol | sorting idx | intent | plausibility |
|---|---|---|---|---|---|
| balanced+intent_focused | cand_5779825e38b12330 | 1 | 80.0 | 100.0 | 92.1 |
| sorting_focused | cand_a94afa9454222f6f | 0 | 100.0 | 0.0 | 93.08 |

SR rates % (templates / valid / front / selected): {'SR1': 0.0, 'SR2': 0.0, 'SR3': 0.0, 'SR4': 0.0, 'SR5': 0.0, 'ANY': 0.0} / {'SR1': 12.5, 'SR2': 0.0, 'SR3': 25.0, 'SR4': 0.0, 'SR5': 0.0, 'ANY': 37.5} / {'SR1': 0.0, 'SR2': 0.0, 'SR3': 50.0, 'SR4': 0.0, 'SR5': 0.0, 'ANY': 50.0} / {'SR1': 0.0, 'SR2': 0.0, 'SR3': 50.0, 'SR4': 0.0, 'SR5': 0.0, 'ANY': 50.0}

trade-off flags: {'pareto_front': {'sorting_improves_intent_decreases': 0, 'intent_improves_sorting_worsens': 1, 'plausibility_falls_substantially': 0}, 'selected': {'sorting_improves_intent_decreases': [], 'intent_improves_sorting_worsens': ['cand_5779825e38b12330'], 'plausibility_falls_substantially': []}, 'front_size_is_one': False, 'plausibility_drop_threshold_pts': 20.0}

**balanced+intent_focused** `cand_5779825e38b12330` (template `g_102c257f10841fe0`)
- SR3 is newly violated compared with the template (no single mutation step alone is confirmed to cause this change).
- Preference 'stretch=low' satisfied: proxy 'stretch=low' scored 1 from composition/text evidence (elastane=2%; bucket=low).
- Sorting rule violations: template 0 -> candidate 1 (+1).
- Intent alignment index: template 0.0 -> candidate 100.0 (+100.0 points).
- Dataset-relative plausibility index: template 93.6 -> candidate 92.1 (-1.5 points).
- Trade-off: intent alignment increased while sorting rule violations increased relative to the template.
- mutation: Moved 2 percentage points from elastane (5% -> 3%) to cotton (95% -> 97%) in component 'main'
- mutation: Moved 2 percentage points from elastane (3% -> 1%) to cotton (97% -> 99%) in component 'main'
- mutation: Moved 1 percentage points from cotton (99% -> 98%) to elastane (1% -> 2%) in component 'main'

**sorting_focused** `cand_a94afa9454222f6f` (template `g_102c257f10841fe0`)
- Preference 'stretch=low' not fully satisfied (satisfaction 0): proxy 'stretch=low' scored -1 from composition/text evidence (elastane=6%; bucket=high).
- Sorting rule violations: template 0 -> candidate 0 (+0).
- Intent alignment index: template 0.0 -> candidate 0.0 (+0.0 points).
- Dataset-relative plausibility index: template 93.6 -> candidate 93.1 (-0.5 points).
- mutation: Moved 1 percentage points from cotton (95% -> 94%) to elastane (5% -> 6%) in component 'main'

## Edge cases

- women/trousers: selected designs with sorting_improves_intent_decreases: 1
- women/dresses: intent objective dropped from Pareto (none_scorable)
- women/dresses: Pareto front contains a single candidate
- women/dresses: unscorable preferences {'thermal_warmth:neutral_value': 80}
- men/outerwear_jacket: selected designs with plausibility_falls_substantially: 1
- men/outerwear_jacket: 3 Pareto candidates fall >20.0 plausibility points below their template
- kids/sweatshirt_hoodie: selected designs with intent_improves_sorting_worsens: 1
- kids/sweatshirt_hoodie: selected designs with plausibility_falls_substantially: 1
- kids/sweatshirt_hoodie: 3 Pareto candidates fall >20.0 plausibility points below their template
- men/set: selected designs with plausibility_falls_substantially: 1
- men/set: 2 Pareto candidates fall >20.0 plausibility points below their template
- baby/trousers: selected designs with intent_improves_sorting_worsens: 1
