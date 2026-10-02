# CAGO data audit report

Input: `/home/claude/data/raw/6_JSONL_component_normalized_public.jsonl`

## Counts

| metric | value |
|---|---|
| garments | 47522 |
| valid_json_records | 47522 |
| malformed_json_lines | 0 |
| blank_lines | 0 |
| unique_parent_products | 35860 |
| components | 67492 |
| material_occurrences | 118833 |
| duplicate_key_groups | 75 |
| rows_in_duplicate_key_groups | 150 |
| duplicate_extra_rows | 75 |

## Comparison with previous audit (sanity check only; processing was not altered)

| metric | computed | previous | diff | abs tol | within tol |
|---|---|---|---|---|---|
| garments | 47522 | 47522 | 0 | 0 | yes |
| unique_parent_products | 35860 | 35860 | 0 | 0 | yes |
| exact_black_variants | 6515 | 6515 | 0 | 0 | yes |
| components | 67492 | 67500 | -8 | 50 | yes |
| material_occurrences | 118833 | 118800 | 33 | 50 | yes |

## parent_product_id

| metric | value |
|---|---|
| ids_with_multiple_variants | 8367 |
| max_variants_per_parent | 35 |
| ids_spanning_multiple_urls | 7524 |
| ids_spanning_multiple_brand_region | 7502 |

## Missing values

Garments with >=1 missing required field: 0

**garments**
| column | null | empty string |
|---|---|---|
| raw_description_text | 93 | 0 |
| raw_function_text | 2577 | 0 |

**components**
_none_

**component_materials**
| column | null | empty string |
|---|---|---|
| material_canonical | 108 | 0 |
| recycled_pct | 116785 | 0 |

## Distributions

**brand**
| brand | n | % |
|---|---|---|
| hm | 41077 | 86.44% |
| uniqlo | 6445 | 13.56% |

**region**
| region | n | % |
|---|---|---|
| gb | 26839 | 56.48% |
| au | 17063 | 35.91% |
| uk | 3620 | 7.62% |

**gender_section**
| gender_section | n | % |
|---|---|---|
| women | 25554 | 53.77% |
| kids | 14655 | 30.84% |
| men | 7051 | 14.84% |
| baby | 262 | 0.55% |

**parent_category**
| parent_category | n | % |
|---|---|---|
| tops | 22051 | 46.40% |
| bottoms | 12076 | 25.41% |
| overall | 7664 | 16.13% |
| underwear | 5731 | 12.06% |

**composition_assignment_type**
| composition_assignment_type | n | % |
|---|---|---|
| native_variant_hm | 41077 | 86.44% |
| shared_no_variants | 5688 | 11.97% |
| mapped_by_colour_only | 280 | 0.59% |
| mapped_by_id_only | 270 | 0.57% |
| mapped_by_other_colours_default | 158 | 0.33% |
| mapped_by_id_then_colour | 49 | 0.10% |

**detail_category**
| detail_category | n | % |
|---|---|---|
| tshirt_polo | 5461 | 11.49% |
| dresses | 4854 | 10.21% |
| sweater_cardigan | 4378 | 9.21% |
| shirt_blouse | 4125 | 8.68% |
| trousers | 4116 | 8.66% |
| outerwear_jacket | 2978 | 6.27% |
| jeans | 2351 | 4.95% |
| sweatshirt_hoodie | 2008 | 4.23% |
| underwear_bottoms | 1926 | 4.05% |
| shorts | 1805 | 3.80% |
| skirts | 1765 | 3.71% |
| socks_hosiery | 1678 | 3.53% |
| set | 1345 | 2.83% |
| swimwear | 1292 | 2.72% |
| sleepwear_homewear | 1098 | 2.31% |
| joggers | 1054 | 2.22% |
| tank_camisole_vest | 1011 | 2.13% |
| leggings | 985 | 2.07% |
| top_generic | 890 | 1.87% |
| bras_lingerie | 835 | 1.76% |
| outerwear_coat | 638 | 1.34% |
| outerwear_gilet | 562 | 1.18% |
| jumpsuits_overalls | 367 | 0.77% |

**components per garment**
| components | n |
|---|---|
| 1 | 31954 |
| 2 | 12277 |
| 3 | 2530 |
| 4 | 526 |
| 5 | 156 |
| 6 | 54 |
| 7 | 14 |
| 8 | 11 |

**component_class**
| class | n | % |
|---|---|---|
| surface_component | 47847 | 70.89% |
| lining_component | 9580 | 14.19% |
| pocket_component | 4708 | 6.98% |
| trim_component | 2641 | 3.91% |
| panel_component | 1329 | 1.97% |
| filling_component | 844 | 1.25% |
| other_component | 369 | 0.55% |
| decoration_component | 174 | 0.26% |

**component_name_normalized (top 30)**
| name | n |
|---|---|
| main | 28787 |
| shell | 16367 |
| lining | 8337 |
| pocket_lining | 4385 |
| body | 2194 |
| rib | 1064 |
| padding | 643 |
| lace | 518 |
| cup_lining | 404 |
| waist | 354 |
| bottom_panel | 320 |
| hood_lining | 267 |
| coating | 240 |
| top_panel | 222 |
| back_panel | 205 |
| sleeve_lining | 202 |
| inner_layer | 190 |
| mesh | 190 |
| pocket | 189 |
| collar | 176 |
| crotch | 170 |
| filling | 152 |
| face | 139 |
| front_panel | 120 |
| body_lining | 118 |
| base_fabric | 108 |
| pocket_fabric | 106 |
| binder_part | 100 |
| cuff | 90 |
| elastic_part | 87 |

**materials per component**
| materials | n |
|---|---|
| 1 | 29833 |
| 2 | 27420 |
| 3 | 7348 |
| 4 | 2424 |
| 5 | 384 |
| 6 | 81 |
| 7 | 2 |

**component support-table check**
```json
{
  "available": true,
  "distinct_pairs_in_data": 86,
  "pairs_not_in_support_table": {}
}
```

## Materials

Unique raw: 64; unique canonical: 42

**mapping status**
| status | n | % |
|---|---|---|
| mapped_source_canonical | 118456 | 99.68% |
| mapped_manual_override | 269 | 0.23% |
| unmapped | 108 | 0.09% |

**family**
| family | n | % |
|---|---|---|
| synthetic | 69202 | 58.23% |
| natural_plant | 35586 | 29.95% |
| regenerated_cellulosic | 9430 | 7.94% |
| natural_animal | 4000 | 3.37% |
| metal | 287 | 0.24% |
| unknown | 181 | 0.15% |
| leather | 102 | 0.09% |
| other | 45 | 0.04% |

**all observed materials**
| raw | canonical | family | status | n |
|---|---|---|---|---|
| polyester | polyester | synthetic | mapped_source_canonical | 34011 |
| cotton | cotton | natural_plant | mapped_source_canonical | 33690 |
| elastane | elastane | synthetic | mapped_source_canonical | 22041 |
| nylon | nylon | synthetic | mapped_source_canonical | 9712 |
| viscose | viscose | regenerated_cellulosic | mapped_source_canonical | 7902 |
| wool | wool | natural_animal | mapped_source_canonical | 3164 |
| acrylic | acrylic | synthetic | mapped_source_canonical | 2549 |
| linen | linen | natural_plant | mapped_source_canonical | 1876 |
| lyocell | lyocell | regenerated_cellulosic | mapped_source_canonical | 945 |
| elastomultiester | elastomultiester | synthetic | mapped_source_canonical | 500 |
| modal | modal | regenerated_cellulosic | mapped_source_canonical | 293 |
| metallised_fibre | metallised_fibre | metal | mapped_source_canonical | 284 |
| cashmere | cashmere | natural_animal | mapped_source_canonical | 274 |
| polyurethane | polyurethane | synthetic | mapped_source_canonical | 259 |
| mohair | mohair | natural_animal | mapped_source_canonical | 194 |
| alpaca | alpaca | natural_animal | mapped_source_canonical | 129 |
| lyocell™ modal | modal | regenerated_cellulosic | mapped_manual_override | 119 |
| silk | silk | natural_animal | mapped_source_canonical | 94 |
| cupro | cupro | regenerated_cellulosic | mapped_source_canonical | 87 |
| acetate | acetate | regenerated_cellulosic | mapped_source_canonical | 80 |
| unspecified_material | unspecified_material | unknown | mapped_source_canonical | 73 |
| australian wool | wool | natural_animal | mapped_manual_override | 59 |
| feather | feather | natural_animal | mapped_source_canonical | 43 |
| down | down | natural_animal | mapped_source_canonical | 43 |
| reprocessed feather | nan | unknown | unmapped | 39 |
| reprocessed down | nan | unknown | unmapped | 39 |
| sheep leather | leather | leather | mapped_manual_override | 31 |
| elastodiene | elastodiene | synthetic | mapped_source_canonical | 28 |
| rubber | rubber | other | mapped_source_canonical | 27 |
| modacrylic | modacrylic | synthetic | mapped_source_canonical | 24 |
| tpu | tpu | synthetic | mapped_source_canonical | 23 |
| leather | leather | leather | mapped_source_canonical | 21 |
| lamb leather | leather | leather | mapped_manual_override | 20 |
| pbt | pbt | synthetic | mapped_source_canonical | 17 |
| paper | paper | other | mapped_source_canonical | 12 |
| ramie | ramie | natural_plant | mapped_source_canonical | 10 |
| cow leather | leather | leather | mapped_manual_override | 10 |
| pctg | pctg | synthetic | mapped_source_canonical | 9 |
| goat suede | suede | leather | mapped_manual_override | 9 |
| suede | suede | leather | mapped_source_canonical | 8 |
| yak wool | nan | unknown | unmapped | 8 |
| down - recycled down | nan | unknown | unmapped | 7 |
| european linen™ | linen | natural_plant | mapped_manual_override | 7 |
| feather - recycled feather | nan | unknown | unmapped | 7 |
| polyethylene | polyethylene | synthetic | mapped_source_canonical | 7 |
| polypropylene | polypropylene | synthetic | mapped_source_canonical | 7 |
| polyethylene terephthalate | polyester | synthetic | mapped_manual_override | 5 |
| polystyrene | polystyrene | synthetic | mapped_source_canonical | 5 |
| eva | eva | synthetic | mapped_source_canonical | 4 |
| resin | resin | other | mapped_source_canonical | 3 |
| goat leather | leather | leather | mapped_manual_override | 3 |
| brass | brass | metal | mapped_source_canonical | 3 |
| european linen ™ | linen | natural_plant | mapped_manual_override | 3 |
| lyocell™ lyocell | lyocell | regenerated_cellulosic | mapped_manual_override | 3 |
| polyester resin | nan | unknown | unmapped | 2 |
| silicone | silicone | other | mapped_source_canonical | 2 |
| polyester - metallised | nan | unknown | unmapped | 2 |
| mdf | nan | unknown | unmapped | 1 |
| cellulose | cellulose | regenerated_cellulosic | mapped_source_canonical | 1 |
| abs | abs | synthetic | mapped_source_canonical | 1 |
| polystyrene foam | nan | unknown | unmapped | 1 |
| pine | nan | unknown | unmapped | 1 |
| wax | wax | other | mapped_source_canonical | 1 |
| zinc alloy | nan | unknown | unmapped | 1 |

**unmapped**
| raw | status | occurrences | garments |
|---|---|---|---|
| reprocessed down | unmapped | 39 | 39 |
| reprocessed feather | unmapped | 39 | 39 |
| yak wool | unmapped | 8 | 8 |
| down - recycled down | unmapped | 7 | 7 |
| feather - recycled feather | unmapped | 7 | 7 |
| polyester - metallised | unmapped | 2 | 2 |
| polyester resin | unmapped | 2 | 2 |
| mdf | unmapped | 1 | 1 |
| pine | unmapped | 1 | 1 |
| polystyrene foam | unmapped | 1 | 1 |
| zinc alloy | unmapped | 1 | 1 |

## Percentage validation

Tolerance: 99.0 <= sum <= 101.0

| status | n | % |
|---|---|---|
| valid | 67486 | 99.99% |
| zero_sum_component | 6 | 0.01% |

| metric | value |
|---|---|
| components_pct_valid | 67486 |
| components_pct_invalid | 6 |
| zero_sum_components | 6 |
| pct_sum_source_vs_calculated_mismatch_gt_0.01 | 0 |
| garments_with_any_invalid_component | 6 |
| pct_sum_calculated_min | 0.0 |
| pct_sum_calculated_max | 100.0 |

**source pct_sum_flag vs calculated pct_valid**
```json
{
  "ok": {
    "False": 6,
    "True": 67486
  }
}
```

Non-valid examples (first 20):
| component_id | name | sum | status |
|---|---|---|---|
| c_adc5a6515d10178d | Coating | 0.0 | zero_sum_component |
| c_40bf91f9d97fa2d6 | Coating | 0.0 | zero_sum_component |
| c_1d213958f51cc8d9 | Coating | 0.0 | zero_sum_component |
| c_b584df2667624be2 | Coating | 0.0 | zero_sum_component |
| c_1577991e0f8545fb | Coating | 0.0 | zero_sum_component |
| c_6d79f02df0b3fc4f | Coating | 0.0 | zero_sum_component |

## Recycled content

| metric | value |
|---|---|
| material_rows_with_recycled_pct | 2048 |
| material_rows_recycled_pct_null | 116785 |
| garments_with_recycled_info | 1666 |
| garments_with_recycled_info_pct | 3.506 |
| recycled_pct_zero_rows | 0 |
| recycled_pct_greater_than_pct_rows | 1072 |

## Colours

| metric | value |
|---|---|
| raw_cardinality | 5486 |
| normalized_cardinality | 5332 |
| exact_black_count | 6515 |
| exact_black_percentage | 13.7094 |

**exact-black raw spellings**
| raw | n |
|---|---|
| Black | 5360 |
| BLACK | 1154 |
| black | 1 |

## Split (by parent_product_id)

| setting | value |
|---|---|
| seed | 42 |
| ratios | [0.7, 0.15, 0.15] |
| method | sha256-ordered parent groups, cut by cumulative garment-row share |
| parent_leakage_count | 0 |

| split | garments | row share | parents |
|---|---|---|---|
| train | 33265 | 0.7 | 25126 |
| test | 7129 | 0.15 | 5386 |
| val | 7128 | 0.15 | 5348 |
