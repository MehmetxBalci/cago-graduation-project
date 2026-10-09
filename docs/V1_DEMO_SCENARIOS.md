# CAGO V1 — demo scenarios

All scenarios use the real processed data (TRAIN rows only), the default app budget (10 templates × 8 candidates) and seed 0.
Reproduce the recorded output with

```bash
python -m app.demo_scenarios        # writes docs/v1_demo_evidence.json (full recorded output) and prints a summary
python -m app.browser_smoke         # drives S1, S2, S3, S5 in a real browser (Chromium), writes docs/demo_screenshots/
```

Two consecutive runs of `app.demo_scenarios` produced byte-identical evidence (apart from the Python version field). The digest is the
frozen evaluation digest of the result. Observed values below were recorded on 2026-10-09 (Python 3.13, Linux).
Only S8 uses synthetic input, and it is labelled as such.

---

## S1 — Successful generation

**UI input:** Segment `men`, Garment category `tshirt polo`, Preferred dominant material `cotton`, Breathability `high`, rest *No preference*.

**Expected:** one or more cards, sorting summary in the screening wording, preferences explained, Pareto chart.

**Observed** (status `ok`, digest `92f3b44a71388f353fdbf864`): 944 TRAIN garments / 944 eligible templates, 10 used; 67 of 80 candidates
generated, 67 hard-valid, Pareto front 2. One card **Balanced + Sorting-focused + Intent-focused** (`candB_3d6a0861f9e384d5`, template
`g_cf650174e85ab44e`): colour purple, fit regular, main `cotton 100%`; intent 100, plausibility 99.5, 0 / 5 violations.
* Card text: "No violations detected under the CAGO SR1–SR5 sorting-screening rules."
* Preferences: dominant material satisfied ("The largest material in the main fabric is cotton at 100%."), breathability satisfied
  ("Composition-based estimate: fully meets 'high' breathability — share of breathable fibres (linen, cotton, lyocell, viscose) in the main
  fabric: 100%. This is a proxy from the material list, not a measured property.").
* Info: "One candidate fulfils several recommendation roles; it is shown once with all its roles."
* Browser: PASS (single card with all three roles + zero-violation wording), screenshot `04_single_candidate.png`.

## S2 — Intent-focused and Sorting-focused choose different candidates

**UI input:** Segment `women`, Garment category `trousers`, Preferred dominant material `linen`, Fit `relaxed`, Breathability `high`.

**Expected:** two cards; the intent-optimal design keeps a sorting flag, the sorting-optimal design gives up the linen preference.

**Observed** (status `ok`, digest `a507fe44a42f2861ad2f583d`): 1,876 TRAIN garments / 1,868 eligible, 76 of 80 generated, 76 hard-valid,
Pareto front 2.

| Card | Candidate | Composition | Intent | Plausibility | Violations |
|---|---|---|---|---|---|
| Balanced + Intent-focused | `candB_5b76def70df4603a` | body: linen 57%, cotton 43% · pocket lining: polyester 80%, cotton 20% | 100 | 91.55 | 1 (SR1) |
| Sorting-focused | `candB_1ff31da66c8ede20` | body: cotton 100% · pocket lining: polyester 80%, cotton 20% | 60 | 79.89 | 0 |

Both come from template `g_b0805103496ec5d1` (grey, relaxed).
* Sorting-focused changes: "Change 1: replaced linen with cotton in the body component (that material made up 53% of it)." and
  "SR1 (supported fibre composition) is no longer flagged, while the template was flagged; confirmed: undoing change 1 on its own brings the
  flag back." Preference "Preferred dominant material = linen: not satisfied. The largest material in the main fabric (body) is cotton at
  100%, not linen."
* Comparison line: "Compared with the Balanced / Intent-focused recommendation, this candidate has fewer sorting-rule violations (0 vs 1),
  lower intent alignment (60 vs 100), lower dataset-relative plausibility (80 vs 92)."
* Browser: PASS (two cards, readable preference and change wording), screenshots `02_results.png`, `02b_explanations.png`.

## S3 — Empty TRAIN template pool

**UI input:** Segment `baby`, Garment category `skirts` (marked "(no TRAIN templates)" in the list).

**Expected:** sidebar warning before submitting; after submitting an error, no cards, no fabricated fallback.

**Observed** (status `no_templates`): 0 TRAIN garments, 0 eligible templates, 0 candidates. Error: "No recommendations can be generated because
there are no TRAIN garments for this segment and category. CAGO only builds designs from TRAIN garment templates of the same segment and
category." Browser: PASS, screenshot `03_no_templates.png`.

## S4 — Invalid preferences (API / JSON request)

The form only offers valid values, so invalid values can only arrive through the service API:

```python
generate_recommendations({"target_segment": "women", "detail_category": "trousers", "fit": "skinny", "water_repellent": "yes"}, data=data)
```

**Expected:** status `invalid_request`, one message per problem, no exception, nothing generated.

**Observed** (status `invalid_request`):
* "Fit: 'skinny' was removed in V1; use 'slim' (allowed: ['slim', 'regular', 'relaxed', 'oversized'])."
* "Invalid value for Water repellency: 'yes' is not allowed: only true or 'No preference' is allowed."

## S5 — Conflicting preferences (possible in the UI)

**UI input:** `women` / `trousers`, Preferred dominant material `linen`, Forbidden materials `linen`, `elastane`, Stretch `high`.

**Expected:** warnings for both conflicts; forbidden materials win (hard constraint); the stretch preference is kept and visibly unmet.

**Observed** (status `ok`, digest `e8c91f536c1da034dd9f2549`): 57 of 80 generated, 57 hard-valid, Pareto front 1.
* Warning: "Your preferred material is also forbidden. Forbidden materials are a hard constraint, so the preference was not used."
* Warning: "Possible conflict between Stretch, Forbidden materials: stretch is estimated from elastane, but elastane is forbidden. Both
  preferences are kept; the trade-off is visible in the results."
* Info: "Only one candidate is non-dominated, so all recommendation roles point to the same design."
* Card Balanced + Sorting-focused + Intent-focused (`candB_83557607eca4f5a1`): main `cotton 100%`, intent 0, plausibility 79.46, 0 / 5.
  "Stretch = high: not satisfied. Composition-based estimate: does not meet 'high' stretch — elastane share: 0%; stretch level: no
  elastane (no stretch)." No linen or elastane in the composition.
* Browser: PASS (both warnings shown), screenshot `05_conflicts.png`.

## S6 — Black colour: SR4 prevents zero violations

**UI input:** `women` / `dresses`, Preferred dominant material `viscose`, Colour `black`.

**Observed** (status `ok`, digest `08a790b39e7bbee96e56a605`): 74 of 80 generated, Pareto front 9. One card for all roles
(`candB_197733d2edb4ca0c`): shell `viscose 87%, polyester 13%`, lining `polyester 100%`, black, slim; intent 100, plausibility 73.86,
1 / 5 ("1 of 5 sorting-screening rules flagged: SR4 (colour screening).").
* Info: "No candidate reached zero detected SR1–SR5 violations (lowest: 1). Every candidate with the lowest violation count keeps the SR4
  colour flag: the colour is inherited from TRAIN templates and is not changed by CAGO V1."
* Rule changes: SR1 and SR2 are no longer flagged ("confirmed: undoing any one of changes 1 or 3 on its own brings the flag back").

## S7 — Preference not available for the category

**UI:** choosing `socks hosiery` greys out Fit, Length and Water repellency ("Unavailable for this category: fit, length, water
repellency."); a Fit chosen earlier for trousers is reset to *No preference* (AppTest `test_disabled_field_does_not_keep_a_stale_value`).
**API input:** `{"target_segment": "women", "detail_category": "socks_hosiery", "fit": "relaxed", "stretch": "low"}`.

**Observed** (status `ok`, digest `6918e3e4365b7d3e1d76fb2a`): warning "Fit is not available for this garment category, so this preference
was not used."; Balanced + Intent-focused (`candB_768e6531ca079097`, polyester 99% / elastane 1%, intent 100, 1 / 5: SR3) and
Sorting-focused (`candB_98bdc7ac42d33df0`, polyester 93% / elastane 7%, intent 0, 0 / 5).

## S8 — SYNTHETIC: corrupted data file

`app.demo_scenarios` copies the three processed files to a temporary folder and overwrites the **copy** of
`garment_representation.parquet` with invalid bytes (real data is untouched).
**Observed:** `DataLoadError` for `garment_representation.parquet`: "not a readable Parquet file". In the app (AppTest
`test_corrupted_data_screen`) the screen reads "A processed data file in `…` cannot be used: `garment_representation.parquet`." with the
problem and recovery advice, instead of a traceback.
