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

## Capabilities

```json
{"dataset_categories": 23, "capability_categories": 23, "missing_in_capabilities": [], "extra_in_capabilities": [], "needs_review": ["jumpsuits_overalls", "set", "sleepwear_homewear", "swimwear", "top_generic"]}
```
