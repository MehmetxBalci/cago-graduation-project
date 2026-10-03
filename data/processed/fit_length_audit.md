# CAGO fit / length text-evidence audit

Basis: TRAIN (patterns, support decisions); VAL/TEST reported separately. Garments: 47522 (train/val/test = 33265/7128/7129). Parent leakage: **False** (0 parents in >1 split).

Thresholds: {"min_train_garments": 500, "min_train_parents": 200, "min_val_test_garments_each": 50, "min_category_train_garments": 100}

## FIT

### Coverage (garments / % of split)

| metric | train | val | test |
|---|---|---|---|
| any_strong_evidence | 26191 (78.734%) | 5511 (77.315%) | 5497 (77.108%) |
| labeled | 21261 (63.914%) | 4533 (63.594%) | 4494 (63.038%) |
| cross_source_conflicts | 339 (1.019%) | 74 (1.038%) | 77 (1.08%) |
| any_weak_term_only | 2531 (7.609%) | 567 (7.955%) | 617 (8.655%) |

### Label counts (garments / parents)

| label | train | val | test | train structured | train phrase-only | train weak-term-only |
|---|---|---|---|---|---|---|
| skinny | 175 / 144 | 43 / 33 | 35 / 33 | 172 | 3 | 3 |
| slim | 5353 / 4286 | 1090 / 865 | 1084 / 880 | 5286 | 67 | 215 |
| regular | 12161 / 9588 | 2620 / 2024 | 2581 / 2055 | 12115 | 46 | 5152 |
| relaxed | 1862 / 1263 | 404 / 284 | 395 / 274 | 1858 | 4 | 752 |
| oversized | 1710 / 1271 | 376 / 283 | 399 / 294 | 1693 | 17 | 914 |

### Status counts

```json
{"train": {"labeled_structured": 21124, "none": 7074, "structured_unmapped": 4929, "labeled_phrase": 137, "structured_conflict": 1}, "val": {"labeled_structured": 4494, "none": 1617, "structured_unmapped": 977, "labeled_phrase": 39, "structured_conflict": 1}, "test": {"labeled_structured": 4453, "none": 1632, "structured_unmapped": 1000, "labeled_phrase": 41, "structured_conflict": 3}}
```

### Conflict combinations (train)

```json
{"skinny+unmapped:loose fit": 1}
```

### Unmapped structured values (train, top 25)

```json
{"loose fit": 4346, "very fitted": 231, "fitted": 150, "loose": 136, "muscle fit": 36, "fit-and-flare": 11, "very relaxed": 11, "compression fit": 5, "tight": 4}
```

### Top matched evidence (train)

```json
{"structured:fit:regular fit": 11216, "structured:fit:slim fit": 5190, "structured:fit:loose fit": 4346, "phrase:description:regular": 2269, "structured:fit:oversized": 1693, "phrase:description:slim": 1259, "structured:fit:relaxed fit": 1205, "phrase:description:relaxed": 1055, "name_term:name:oversized": 995, "phrase:name:regular": 941, "structured:fit:regular": 899, "structured:fit:relaxed": 656, "phrase:name:slim": 539, "phrase:name:relaxed": 368, "structured:fit:very fitted": 231, "phrase:description:oversized": 210, "structured:fit:skinny fit": 158, "phrase:name:oversized": 152, "structured:fit:fitted": 150, "structured:fit:loose": 136, "structured:fit:slim": 96, "phrase:description:skinny": 73, "structured:fit:muscle fit": 36, "phrase:name:skinny": 20, "structured:fit:skinny": 14}
```

Coverage in categories where the UI control is enabled (train): {"garments": 29315, "labeled": 20982, "labeled_pct": 71.574}; enabled categories with no supported label: ["set"]

### By detail category (train labeled / train garments; labels train)

| category | train labeled | train garments | val labeled | test labeled | train labels |
|---|---|---|---|---|---|
| bras_lingerie | 22 | 531 | 9 | 5 | slim:20 relaxed:2 |
| dresses | 2759 | 3384 | 583 | 633 | slim:1052 regular:1585 relaxed:37 oversized:85 |
| jeans | 1216 | 1723 | 232 | 222 | skinny:99 slim:390 regular:567 relaxed:128 oversized:32 |
| joggers | 602 | 749 | 121 | 112 | slim:41 regular:448 relaxed:112 oversized:1 |
| jumpsuits_overalls | 158 | 269 | 30 | 18 | slim:31 regular:120 relaxed:6 oversized:1 |
| leggings | 169 | 645 | 38 | 37 | skinny:29 slim:104 regular:36 |
| outerwear_coat | 342 | 446 | 73 | 78 | slim:7 regular:186 relaxed:76 oversized:73 |
| outerwear_gilet | 377 | 398 | 91 | 47 | slim:169 regular:196 relaxed:9 oversized:3 |
| outerwear_jacket | 1669 | 2005 | 379 | 395 | skinny:1 slim:221 regular:1068 relaxed:136 oversized:243 |
| set | 129 | 922 | 19 | 24 | slim:19 regular:84 relaxed:25 oversized:1 |
| shirt_blouse | 2389 | 2922 | 499 | 501 | slim:466 regular:1333 relaxed:267 oversized:323 |
| shorts | 805 | 1292 | 170 | 185 | skinny:14 slim:126 regular:533 relaxed:130 oversized:2 |
| skirts | 962 | 1231 | 206 | 227 | skinny:3 slim:239 regular:715 relaxed:5 |
| sleepwear_homewear | 171 | 761 | 43 | 52 | slim:2 regular:158 relaxed:11 |
| socks_hosiery | 197 | 1170 | 27 | 34 | skinny:2 slim:12 regular:139 relaxed:44 |
| sweater_cardigan | 2421 | 3104 | 467 | 494 | slim:445 regular:1527 relaxed:101 oversized:348 |
| sweatshirt_hoodie | 965 | 1383 | 223 | 236 | slim:9 regular:601 relaxed:94 oversized:261 |
| swimwear | 10 | 916 | 3 | 2 | slim:1 regular:9 |
| tank_camisole_vest | 547 | 692 | 152 | 128 | slim:322 regular:220 relaxed:4 oversized:1 |
| top_generic | 563 | 617 | 125 | 118 | slim:341 regular:208 relaxed:1 oversized:13 |
| trousers | 1970 | 2916 | 415 | 392 | skinny:25 slim:526 regular:960 relaxed:448 oversized:11 |
| tshirt_polo | 2768 | 3856 | 617 | 546 | slim:781 regular:1452 relaxed:223 oversized:312 |
| underwear_bottoms | 50 | 1333 | 11 | 8 | skinny:2 slim:29 regular:16 relaxed:3 |

### Categories with >= 100 train garments per label

```json
{"skinny": [], "slim": ["dresses", "jeans", "leggings", "outerwear_gilet", "outerwear_jacket", "shirt_blouse", "shorts", "skirts", "sweater_cardigan", "tank_camisole_vest", "top_generic", "trousers", "tshirt_polo"], "regular": ["dresses", "jeans", "joggers", "jumpsuits_overalls", "outerwear_coat", "outerwear_gilet", "outerwear_jacket", "shirt_blouse", "shorts", "skirts", "sleepwear_homewear", "socks_hosiery", "sweater_cardigan", "sweatshirt_hoodie", "tank_camisole_vest", "top_generic", "trousers", "tshirt_polo"], "relaxed": ["jeans", "joggers", "outerwear_jacket", "shirt_blouse", "shorts", "sweater_cardigan", "trousers", "tshirt_polo"], "oversized": ["outerwear_jacket", "shirt_blouse", "sweater_cardigan", "sweatshirt_hoodie", "tshirt_polo"]}
```

### Examples (train)

- **skinny** [skirts] 'Rib-knit skirt' (structured) ['structured:fit:skinny fit']
- **skinny** [leggings] 'Flared Leggings' (structured) ['structured:fit:skinny fit']
- **skinny** [leggings] 'Leather leggings' (structured) ['structured:fit:skinny fit']
- **slim** [dresses] 'Square-neck twill dress' (structured) ['structured:fit:slim fit']
- **slim** [shirt_blouse] 'CHECKED COTTON-JACQUARD SHIRT' (structured) ['structured:fit:slim fit', 'phrase:description:slim']
- **slim** [trousers] 'Knitted crease-front trousers' (structured) ['structured:fit:slim fit']
- **regular** [shorts] 'Poplin shorts' (structured) ['structured:fit:regular fit']
- **regular** [tank_camisole_vest] 'Satin bandeau top' (structured) ['structured:fit:regular fit']
- **regular** [shorts] 'Lace-trimmed satin shorts' (structured) ['structured:fit:regular fit']
- **relaxed** [joggers] 'Track pants with DryMove™' (structured) ['structured:fit:relaxed fit', 'phrase:description:relaxed']
- **relaxed** [shirt_blouse] 'Relaxed Overshirt' (structured) ['structured:fit:relaxed fit', 'phrase:description:relaxed']
- **relaxed** [jeans] 'Relaxed Fit Jeans' (structured) ['structured:fit:relaxed fit', 'phrase:name:relaxed', 'phrase:description:relaxed']
- **oversized** [outerwear_jacket] 'Reversible bomber jacket' (structured) ['structured:fit:oversized', 'phrase:description:oversized']
- **oversized** [shirt_blouse] 'Off-the-shoulder poplin blouse' (structured) ['structured:fit:oversized']
- **oversized** [jeans] 'Baggy darted jeans' (structured) ['structured:fit:oversized']

## LENGTH

### Coverage (garments / % of split)

| metric | train | val | test |
|---|---|---|---|
| any_strong_evidence | 25796 (77.547%) | 5455 (76.529%) | 5586 (78.356%) |
| labeled | 17150 (51.556%) | 3584 (50.281%) | 3677 (51.578%) |
| cross_source_conflicts | 323 (0.971%) | 64 (0.898%) | 48 (0.673%) |
| any_weak_term_only | 881 (2.648%) | 221 (3.1%) | 178 (2.497%) |

### Label counts (garments / parents)

| label | train | val | test | train structured | train phrase-only | train weak-term-only |
|---|---|---|---|---|---|---|
| cropped | 268 / 213 | 61 / 49 | 92 / 55 | 233 | 35 | 189 |
| standard | 10367 / 8760 | 2209 / 1861 | 2182 / 1846 | 10357 | 10 | 0 |
| long | 6515 / 5431 | 1314 / 1099 | 1403 / 1169 | 6515 | 0 | 7341 |

### Status counts

```json
{"train": {"labeled_structured": 17105, "structured_unmapped": 7582, "none": 7469, "structured_conflict": 1064, "labeled_phrase": 45}, "val": {"labeled_structured": 3582, "none": 1673, "structured_unmapped": 1659, "structured_conflict": 212, "labeled_phrase": 2}, "test": {"labeled_structured": 3643, "structured_unmapped": 1657, "none": 1543, "structured_conflict": 252, "labeled_phrase": 34}}
```

### Conflict combinations (train)

```json
{"long+standard": 580, "standard+unmapped:short": 338, "standard+unmapped:knee length": 95, "long+unmapped:short": 39, "standard+unmapped:ankle length": 3, "long+unmapped:knee length": 3, "cropped+unmapped:ankle length": 2, "long+unmapped:maxi": 1, "long+unmapped:midi": 1, "cropped+unmapped:short": 1, "standard+unmapped:three-quarter length": 1}
```

### Unmapped structured values (train, top 25)

```json
{"short": 4648, "knee length": 1419, "midi": 926, "mini": 388, "ankle length": 320, "maxi": 206, "extra-long legs": 96, "extra long legs": 42, "three-quarter length": 40}
```

### Top matched evidence (train)

```json
{"structured:length:regular length": 11374, "structured:length:long": 7139, "structured:length:short": 4648, "structured:length:knee length": 1419, "structured:length:midi": 926, "structured:length:mini": 388, "phrase:description:standard": 330, "structured:length:ankle length": 320, "structured:length:cropped": 236, "structured:length:maxi": 206, "name_term:name:cropped": 167, "structured:length:extra-long legs": 96, "structured:length:extra long legs": 42, "phrase:description:cropped": 40, "structured:length:three-quarter length": 40, "phrase:name:standard": 8, "phrase:name:cropped": 1}
```

Coverage in categories where the UI control is enabled (train): {"garments": 27995, "labeled": 16513, "labeled_pct": 58.986}; enabled categories with no supported label: ["outerwear_coat", "shorts"]

### By detail category (train labeled / train garments; labels train)

| category | train labeled | train garments | val labeled | test labeled | train labels |
|---|---|---|---|---|---|
| bras_lingerie | 34 | 531 | 4 | 23 | cropped:19 standard:15 |
| dresses | 378 | 3384 | 86 | 69 | standard:13 long:365 |
| jeans | 1359 | 1723 | 225 | 258 | cropped:9 standard:23 long:1327 |
| joggers | 711 | 749 | 144 | 132 | long:711 |
| jumpsuits_overalls | 126 | 269 | 37 | 22 | long:126 |
| leggings | 533 | 645 | 120 | 144 | cropped:1 standard:3 long:529 |
| outerwear_coat | 139 | 446 | 40 | 30 | standard:72 long:67 |
| outerwear_gilet | 295 | 398 | 62 | 39 | cropped:17 standard:225 long:53 |
| outerwear_jacket | 1547 | 2005 | 335 | 372 | cropped:22 standard:1435 long:90 |
| set | 152 | 922 | 36 | 39 | standard:42 long:110 |
| shirt_blouse | 2261 | 2922 | 464 | 475 | cropped:31 standard:2014 long:216 |
| shorts | 3 | 1292 | 1 | 0 | long:3 |
| skirts | 123 | 1231 | 28 | 23 | long:123 |
| sleepwear_homewear | 219 | 761 | 38 | 70 | standard:17 long:202 |
| socks_hosiery | 66 | 1170 | 11 | 17 | standard:4 long:62 |
| sweater_cardigan | 2130 | 3104 | 415 | 434 | cropped:16 standard:1939 long:175 |
| sweatshirt_hoodie | 1168 | 1383 | 248 | 263 | cropped:9 standard:1116 long:43 |
| swimwear | 52 | 916 | 15 | 9 | cropped:3 standard:43 long:6 |
| tank_camisole_vest | 464 | 692 | 124 | 105 | cropped:45 standard:406 long:13 |
| top_generic | 427 | 617 | 106 | 100 | cropped:42 standard:364 long:21 |
| trousers | 2194 | 2916 | 449 | 473 | cropped:16 standard:14 long:2164 |
| tshirt_polo | 2731 | 3856 | 585 | 568 | cropped:38 standard:2608 long:85 |
| underwear_bottoms | 38 | 1333 | 11 | 12 | standard:14 long:24 |

### Categories with >= 100 train garments per label

```json
{"cropped": [], "standard": ["outerwear_gilet", "outerwear_jacket", "shirt_blouse", "sweater_cardigan", "sweatshirt_hoodie", "tank_camisole_vest", "top_generic", "tshirt_polo"], "long": ["dresses", "jeans", "joggers", "jumpsuits_overalls", "leggings", "set", "shirt_blouse", "skirts", "sleepwear_homewear", "sweater_cardigan", "trousers"]}
```

### Examples (train)

- **cropped** [tshirt_polo] 'Oversized Fit Tee' (structured) ['structured:length:cropped']
- **cropped** [jeans] 'BLOOM Barrel Jeans' (structured) ['structured:length:cropped']
- **cropped** [sweatshirt_hoodie] 'Printed cropped hoodie' (structured) ['structured:length:cropped', 'name_term:name:cropped']
- **standard** [outerwear_jacket] 'Utility twill jacket' (structured) ['structured:length:regular length']
- **standard** [tshirt_polo] 'Print Tee' (structured) ['structured:length:regular length']
- **standard** [tank_camisole_vest] 'Satin bandeau top' (structured) ['structured:length:regular length']
- **long** [set] 'Ribbed cotton set' (structured) ['structured:length:long']
- **long** [trousers] 'Knitted crease-front trousers' (structured) ['structured:length:long']
- **long** [joggers] 'Track pants with DryMove™' (structured) ['structured:length:long']

## Raw phrase audit (garments any source / parents, per split)

| phrase | train | val | test | train by source |
|---|---|---|---|---|
| slim fit | 5394 / 4344 | 1111 / 883 | 1098 / 893 | {"name": 539, "description": 1259, "function": 5190} |
| skinny fit | 165 / 142 | 37 / 32 | 35 / 33 | {"name": 20, "description": 73, "function": 159} |
| regular fit | 11470 / 9486 | 2437 / 1999 | 2495 / 2042 | {"name": 941, "description": 2269, "function": 11216} |
| relaxed fit | 1425 / 1263 | 312 / 276 | 302 / 268 | {"name": 368, "description": 1055, "function": 1205} |
| loose fit | 4472 / 3683 | 920 / 761 | 918 / 766 | {"name": 805, "description": 3360, "function": 4346} |
| oversized | 2624 / 2046 | 584 / 461 | 586 / 452 | {"name": 995, "description": 2174, "function": 1693} |
| wide leg | 1346 / 1062 | 261 / 197 | 282 / 228 | {"name": 279, "description": 371, "function": 1241} |
| straight leg | 1331 / 1104 | 252 / 213 | 278 / 235 | {"name": 129, "description": 282, "function": 1258} |
| tapered | 983 / 624 | 179 / 119 | 188 / 124 | {"name": 137, "description": 769, "function": 697} |
| cropped | 460 / 371 | 113 / 89 | 135 / 84 | {"name": 167, "description": 361, "function": 236} |
| ankle length | 675 / 535 | 160 / 127 | 132 / 99 | {"name": 25, "description": 567, "function": 320} |
| full length | 71 / 69 | 11 / 11 | 7 / 7 | {"name": 0, "description": 71, "function": 0} |
| longline | 7 / 7 | 0 / 0 | 2 / 2 | {"name": 4, "description": 6, "function": 0} |
| maxi | 259 / 205 | 52 / 41 | 57 / 46 | {"name": 164, "description": 139, "function": 206} |
| midi | 964 / 794 | 209 / 167 | 242 / 192 | {"name": 186, "description": 113, "function": 926} |
| mini | 653 / 469 | 121 / 84 | 143 / 114 | {"name": 445, "description": 463, "function": 394} |

## Train-only label consistency

```json
{"fit": 0, "length": 0}
```

## Recommendations

- fit/skinny: **MERGE** -> slim (below thresholds (train 175 garments / 144 parents); hypothesis: merge into 'slim' (human decision))
- fit/slim: **KEEP** (meets train/val/test support thresholds)
- fit/regular: **KEEP** (meets train/val/test support thresholds)
- fit/relaxed: **KEEP** (meets train/val/test support thresholds)
- fit/oversized: **KEEP** (meets train/val/test support thresholds)
- length/cropped: **REMOVE_FROM_V1** (insufficient support (train 268 garments / 213 parents))
- length/standard: **KEEP** (meets train/val/test support thresholds)
- length/long: **KEEP** (meets train/val/test support thresholds)

Raw merge candidates (train): {"relaxed": {"loose": 136, "loose fit": 4346}}
