# CAGO garment representation audit

| metric | value |
|---|---|
| garments | 47522 |
| garment count == source | True |
| source components | 67492 |
| active components | 67486 |
| anomalous components (preserved separately) | 6 |
| active + anomalous == source | True |
| garments without active component | 0 |
| garments with anomalous component | 6 |
| fully usable garments | 47516 |
| garments with unmapped material | 61 |
| garments with OTHER token | 314 |
| max |pct_sum - 100| (active) | 1.0 |
| active components not exactly 100 | 1 |
| parent leakage | 0 |
| representation sha256 | 238226c16350bbf66aeb9fa08648f7dce8b244fbb166071edc89fce89b45d5ef |

## Anomalous by status

| status | n |
|---|---|
| zero_sum_component | 6 |

## Split

| split | garments | parents |
|---|---|---|
| train | 33265 | 25126 |
| test | 7129 | 5386 |
| val | 7128 | 5348 |

## ML material vocabulary (fit on `train` only)

Size: **24** (min_count=30; incl. special tokens). Train garments: 33265; train material occurrences: 82876; train unmapped occurrences: 82.

Threshold sweep (materials kept at each min train count):

| min_count | materials kept |
|---|---|
| 1 | 40 |
| 5 | 34 |
| 10 | 28 |
| 20 | 24 |
| 30 | 22 |
| 50 | 20 |
| 100 | 15 |
| 200 | 12 |
| 500 | 9 |

Counts consistent with independent train-only recount: True

| material | train occ. | train garments | token | reason |
|---|---|---|---|---|
| polyester | 23716 | 17907 | polyester | in_vocab |
| cotton | 23530 | 19303 | cotton | in_vocab |
| elastane | 15362 | 13188 | elastane | in_vocab |
| nylon | 6675 | 5938 | nylon | in_vocab |
| viscose | 5555 | 5374 | viscose | in_vocab |
| wool | 2235 | 2214 | wool | in_vocab |
| acrylic | 1771 | 1753 | acrylic | in_vocab |
| linen | 1330 | 1320 | linen | in_vocab |
| lyocell | 661 | 650 | lyocell | in_vocab |
| elastomultiester | 361 | 311 | elastomultiester | in_vocab |
| modal | 280 | 280 | modal | in_vocab |
| cashmere | 208 | 208 | cashmere | in_vocab |
| metallised_fibre | 181 | 176 | metallised_fibre | in_vocab |
| polyurethane | 174 | 167 | polyurethane | in_vocab |
| mohair | 134 | 134 | mohair | in_vocab |
| alpaca | 93 | 93 | alpaca | in_vocab |
| cupro | 84 | 76 | cupro | in_vocab |
| silk | 68 | 68 | silk | in_vocab |
| leather | 58 | 58 | leather | in_vocab |
| acetate | 51 | 48 | acetate | in_vocab |
| unspecified_material | 48 | 47 | OTHER | unspecified_source_label |
| down | 30 | 30 | down | in_vocab |
| feather | 30 | 30 | feather | in_vocab |
| rubber | 22 | 22 | OTHER | rare_in_train |
| tpu | 22 | 22 | OTHER | rare_in_train |
| elastodiene | 19 | 19 | OTHER | rare_in_train |
| modacrylic | 19 | 19 | OTHER | rare_in_train |
| pbt | 14 | 14 | OTHER | rare_in_train |
| suede | 13 | 13 | OTHER | rare_in_train |
| paper | 9 | 9 | OTHER | rare_in_train |
| pctg | 7 | 7 | OTHER | rare_in_train |
| ramie | 7 | 7 | OTHER | rare_in_train |
| polyethylene | 6 | 6 | OTHER | rare_in_train |
| polypropylene | 6 | 5 | OTHER | rare_in_train |
| polystyrene | 5 | 5 | OTHER | rare_in_train |
| brass | 3 | 2 | OTHER | rare_in_train |
| eva | 2 | 2 | OTHER | rare_in_train |
| resin | 2 | 2 | OTHER | rare_in_train |
| abs | 1 | 1 | OTHER | rare_in_train |
| cellulose | 1 | 1 | OTHER | rare_in_train |
| wax | 1 | 1 | OTHER | rare_in_train |
| copper | 0 | 0 | OTHER | unseen_in_train |
| glass | 0 | 0 | OTHER | unseen_in_train |
| hemp | 0 | 0 | OTHER | unseen_in_train |
| iron | 0 | 0 | OTHER | unseen_in_train |
| jute | 0 | 0 | OTHER | unseen_in_train |
| latex | 0 | 0 | OTHER | unseen_in_train |
| mabs | 0 | 0 | OTHER | unseen_in_train |
| metal | 0 | 0 | OTHER | unseen_in_train |
| pearl | 0 | 0 | OTHER | unseen_in_train |
| pmma | 0 | 0 | OTHER | unseen_in_train |
| polycarbonate | 0 | 0 | OTHER | unseen_in_train |
| pom | 0 | 0 | OTHER | unseen_in_train |
| ptfe | 0 | 0 | OTHER | unseen_in_train |
| silicone | 0 | 0 | OTHER | unseen_in_train |
| steel | 0 | 0 | OTHER | unseen_in_train |
| textile | 0 | 0 | OTHER | unseen_in_train |
| tpe | 0 | 0 | OTHER | unseen_in_train |
| triacetate | 0 | 0 | OTHER | unseen_in_train |
| zinc | 0 | 0 | OTHER | unseen_in_train |

## OTHER-token rate by split (reporting only; never used for fitting)

| split | occurrences | OTHER | % | reasons |
|---|---|---|---|---|
| test | 18019 | 53 | 0.2941 | {'unspecified_source_label': 9, 'unmapped_source_material': 21, 'rare_in_train': 21, 'unseen_in_train': 2} |
| train | 82876 | 289 | 0.3487 | {'unspecified_source_label': 48, 'unmapped_source_material': 82, 'rare_in_train': 159} |
| val | 17932 | 40 | 0.2231 | {'unspecified_source_label': 16, 'rare_in_train': 19, 'unmapped_source_material': 5} |

## Distributions

**target_segment**
| target_segment | n |
|---|---|
| women | 25554 |
| kids | 14655 |
| men | 7051 |
| baby | 262 |

**detail_category**
| category | n |
|---|---|
| tshirt_polo | 5461 |
| dresses | 4854 |
| sweater_cardigan | 4378 |
| shirt_blouse | 4125 |
| trousers | 4116 |
| outerwear_jacket | 2978 |
| jeans | 2351 |
| sweatshirt_hoodie | 2008 |
| underwear_bottoms | 1926 |
| shorts | 1805 |
| skirts | 1765 |
| socks_hosiery | 1678 |
| set | 1345 |
| swimwear | 1292 |
| sleepwear_homewear | 1098 |
| joggers | 1054 |
| tank_camisole_vest | 1011 |
| leggings | 985 |
| top_generic | 890 |
| bras_lingerie | 835 |
| outerwear_coat | 638 |
| outerwear_gilet | 562 |
| jumpsuits_overalls | 367 |

## Text evidence tags

| tag | garments |
|---|---|
| brushed | 3053 |
| double_layer | 556 |
| durable | 327 |
| fleece | 496 |
| heavyweight | 486 |
| lamination | 12 |
| moisture_wicking | 967 |
| padded | 1764 |
| quick_dry | 1812 |
| reinforced | 391 |
| ripstop | 46 |
| thermal | 381 |
| water_resistant | 697 |

## Proxy sanity

```json
{"stretch_bucket_counts_default_limits": {"low": 4205, "none": 30016, "high": 13301}, "garments_with_coating_component": 234}
```

## Fit / Length V1

Vocabulary: {"fit": ["slim", "regular", "relaxed", "oversized"], "length": ["standard", "long"]}; capability basis: TRAIN split only (val/test never used)

### fit

| split | labeled | % of split | labeled parents | conflict | cross-source conflict | unlabeled w/ evidence (conflict/unmapped/unsupported) |
|---|---|---|---|---|---|---|
| train | 25744 | 77.391 | 20164 | 1 | 471 | 449 |
| val | 5443 | 76.361 | 4226 | 1 | 101 | 68 |
| test | 5395 | 75.677 | 4283 | 3 | 106 | 102 |

| label | train | val | test |
|---|---|---|---|
| slim | 5528 (21.473%) | 1133 (20.816%) | 1119 (20.741%) |
| regular | 12161 (47.238%) | 2620 (48.135%) | 2581 (47.841%) |
| relaxed | 6345 (24.647%) | 1314 (24.141%) | 1296 (24.022%) |
| oversized | 1710 (6.642%) | 376 (6.908%) | 399 (7.396%) |

status counts: {"train": {"labeled_structured": 25605, "none": 7072, "structured_unmapped": 448, "labeled_phrase": 139, "structured_conflict": 1}, "val": {"labeled_structured": 5404, "none": 1617, "structured_unmapped": 67, "labeled_phrase": 39, "structured_conflict": 1}, "test": {"labeled_structured": 5354, "none": 1632, "structured_unmapped": 99, "labeled_phrase": 41, "structured_conflict": 3}}

confidence: {"train": {"high": 25605, "<NULL>": 7521, "medium": 139}, "val": {"high": 5404, "<NULL>": 1685, "medium": 39}, "test": {"high": 5354, "<NULL>": 1734, "medium": 41}}

merged: {"skinny->slim": {"train": {"labeled_with_merge_source": 175, "labeled_only_via_merge": 175}, "val": {"labeled_with_merge_source": 43, "labeled_only_via_merge": 43}, "test": {"labeled_with_merge_source": 35, "labeled_only_via_merge": 35}}, "loose->relaxed": {"train": {"labeled_with_merge_source": 4483, "labeled_only_via_merge": 4483}, "val": {"labeled_with_merge_source": 910, "labeled_only_via_merge": 910}, "test": {"labeled_with_merge_source": 901, "labeled_only_via_merge": 901}}}

enabled-control coverage (labeled / garments, train | val | test):

| category | train | val | test |
|---|---|---|---|
| dresses | 3176/3384 (93.853%) | 679/726 (93.526%) | 714/744 (95.968%) |
| jeans | 1699/1723 (98.607%) | 305/305 (100.0%) | 318/323 (98.452%) |
| joggers | 729/749 (97.33%) | 144/157 (91.72%) | 136/148 (91.892%) |
| jumpsuits_overalls | 179/269 (66.543%) | 34/53 (64.151%) | 19/45 (42.222%) |
| leggings | 169/645 (26.202%) | 38/167 (22.754%) | 37/173 (21.387%) |
| outerwear_coat | 411/446 (92.152%) | 89/94 (94.681%) | 86/98 (87.755%) |
| outerwear_gilet | 390/398 (97.99%) | 95/105 (90.476%) | 51/59 (86.441%) |
| outerwear_jacket | 1937/2005 (96.608%) | 461/478 (96.444%) | 463/495 (93.535%) |
| shirt_blouse | 2800/2922 (95.825%) | 579/608 (95.23%) | 588/595 (98.824%) |
| shorts | 1124/1292 (86.997%) | 218/251 (86.853%) | 237/262 (90.458%) |
| skirts | 1116/1231 (90.658%) | 243/263 (92.395%) | 253/271 (93.358%) |
| sleepwear_homewear | 196/761 (25.756%) | 48/158 (30.38%) | 59/179 (32.961%) |
| sweater_cardigan | 2904/3104 (93.557%) | 547/603 (90.713%) | 590/671 (87.928%) |
| sweatshirt_hoodie | 1334/1383 (96.457%) | 295/308 (95.779%) | 309/317 (97.476%) |
| tank_camisole_vest | 581/692 (83.96%) | 157/176 (89.205%) | 132/143 (92.308%) |
| top_generic | 599/617 (97.083%) | 134/137 (97.81%) | 130/136 (95.588%) |
| trousers | 2786/2916 (95.542%) | 588/606 (97.03%) | 562/594 (94.613%) |
| tshirt_polo | 3196/3856 (82.884%) | 717/816 (87.868%) | 636/789 (80.608%) |

disabled controls: {"bras_lingerie": "disabled_by_design", "set": "disabled_insufficient_train_support", "socks_hosiery": "disabled_by_design", "swimwear": "disabled_by_design", "underwear_bottoms": "disabled_by_design"}

### length

| split | labeled | % of split | labeled parents | conflict | cross-source conflict | unlabeled w/ evidence (conflict/unmapped/unsupported) |
|---|---|---|---|---|---|---|
| train | 16882 | 50.75 | 14191 | 1061 | 323 | 8914 |
| val | 3523 | 49.425 | 2960 | 210 | 64 | 1932 |
| test | 3585 | 50.288 | 3015 | 249 | 48 | 2001 |

| label | train | val | test |
|---|---|---|---|
| standard | 10367 (61.409%) | 2209 (62.702%) | 2182 (60.865%) |
| long | 6515 (38.591%) | 1314 (37.298%) | 1403 (39.135%) |

status counts: {"train": {"labeled_structured": 16872, "structured_unmapped": 7585, "none": 7469, "structured_conflict": 1061, "structured_unsupported_v1": 233, "phrase_unsupported_v1": 35, "labeled_phrase": 10}, "val": {"labeled_structured": 3523, "none": 1673, "structured_unmapped": 1661, "structured_conflict": 210, "structured_unsupported_v1": 59, "phrase_unsupported_v1": 2}, "test": {"labeled_structured": 3585, "structured_unmapped": 1660, "none": 1543, "structured_conflict": 249, "structured_unsupported_v1": 58, "phrase_unsupported_v1": 34}}

confidence: {"train": {"high": 16872, "<NULL>": 16383, "medium": 10}, "val": {"<NULL>": 3605, "high": 3523}, "test": {"high": 3585, "<NULL>": 3544}}

merged: {}

excluded from V1: {"cropped": {"train": 316, "val": 83, "test": 105}}

enabled-control coverage (labeled / garments, train | val | test):

| category | train | val | test |
|---|---|---|---|
| dresses | 378/3384 (11.17%) | 86/726 (11.846%) | 69/744 (9.274%) |
| jeans | 1350/1723 (78.352%) | 225/305 (73.77%) | 257/323 (79.567%) |
| joggers | 711/749 (94.927%) | 144/157 (91.72%) | 132/148 (89.189%) |
| jumpsuits_overalls | 126/269 (46.84%) | 37/53 (69.811%) | 22/45 (48.889%) |
| leggings | 532/645 (82.481%) | 120/167 (71.856%) | 144/173 (83.237%) |
| outerwear_jacket | 1525/2005 (76.06%) | 326/478 (68.201%) | 359/495 (72.525%) |
| shirt_blouse | 2230/2922 (76.318%) | 459/608 (75.493%) | 464/595 (77.983%) |
| skirts | 123/1231 (9.992%) | 28/263 (10.646%) | 23/271 (8.487%) |
| sleepwear_homewear | 219/761 (28.778%) | 38/158 (24.051%) | 70/179 (39.106%) |
| sweater_cardigan | 2114/3104 (68.106%) | 414/603 (68.657%) | 431/671 (64.232%) |
| sweatshirt_hoodie | 1159/1383 (83.803%) | 244/308 (79.221%) | 259/317 (81.703%) |
| tank_camisole_vest | 419/692 (60.549%) | 118/176 (67.045%) | 100/143 (69.93%) |
| top_generic | 385/617 (62.399%) | 96/137 (70.073%) | 93/136 (68.382%) |
| trousers | 2178/2916 (74.691%) | 447/606 (73.762%) | 470/594 (79.125%) |
| tshirt_polo | 2693/3856 (69.839%) | 573/816 (70.221%) | 552/789 (69.962%) |

disabled controls: {"bras_lingerie": "disabled_by_design", "outerwear_coat": "disabled_insufficient_train_support", "outerwear_gilet": "disabled_by_design", "set": "disabled_by_design", "shorts": "disabled_insufficient_train_support", "socks_hosiery": "disabled_by_design", "swimwear": "disabled_by_design", "underwear_bottoms": "disabled_by_design"}

capability changes: [["outerwear_coat", "length_cut"], ["set", "fit"], ["shorts", "length_cut"]]

supported but disabled by design (review): [["outerwear_gilet", "length_cut"], ["set", "length_cut"]]

## Capabilities

```json
{"dataset_categories": 23, "capability_categories": 23, "missing_in_capabilities": [], "extra_in_capabilities": [], "needs_review": ["jumpsuits_overalls", "set", "sleepwear_homewear", "swimwear", "top_generic"]}
```
