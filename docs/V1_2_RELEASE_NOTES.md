# CAGO V1.2.0 — segment-aware category filtering: release notes and verification

Application-layer update of V1.1.0. After choosing a target segment, the **Garment category** list contains only categories with at
least one eligible TRAIN template in that segment, in English and Turkish. No research code, generator behaviour, material percentage,
score, sorting rule, configuration, manifest or report changed; internal segment / category identifiers are unchanged.

Verification run: 2026-10-12, Linux x86_64, Python 3.13.16 and Python 3.12.3 (fresh venv from the release ZIP and `requirements.txt`);
pandas 2.3.3, pyarrow 25.0.1, Streamlit 1.65.0, pytest 9.1.1; Playwright 1.63 + Chromium 141.

## Category-availability method

For every TRAIN cell (target_segment, detail_category):

```
eligible_templates(seg, cat) = number of rows r of the TRAIN-filtered representation with
    r.target_segment == seg and r.detail_category == cat and
    cago.generation.template_selector.ineligibility_reason(r, template_components(r.components)) is None
```

* `ineligibility_reason` and `template_components` are the frozen functions the generator's `select_templates` applies; they are
  imported, not copied or changed. A row is eligible when it is fully usable, has no unmapped and no OTHER material, and every
  component sums to 100 %. `select_templates` reports exactly this number as `eligible_templates`; forbidden materials and soft
  preferences only rank templates and therefore do not affect it.
* Implemented in `app/adapters.py` (`eligible_template_counts`, stored as `AppData.eligible`; helpers `available_categories(segment)`,
  `eligible_templates(segment, category)`, `is_available(...)`). Computed once when the data is loaded (about 0.5 s for 33,265 TRAIN
  garments, measured on replicated fixture rows; cached with `st.cache_resource`).
* A category is selectable for a segment iff `eligible_templates > 0`. Neither the global vocabulary, `category_capabilities.json`, nor
  TRAIN garments that cannot serve as templates make a category available. Nothing is hard-coded per segment.

### TRAIN-only evidence

* The representation parquet is read with the row filter `split == "train"` (unchanged V1 loader; no read-all fallback).
* `eligible_template_counts` raises `ValueError` if any non-TRAIN row reaches it (`test_availability_is_train_only`).
* Fixture cells that exist only in VAL / TEST (`men / dresses`, the whole `baby` segment) never become available, and rewriting every
  VAL / TEST garment into a new cell leaves availability unchanged (`test_val_and_test_rows_never_change_availability`).
* For every TRAIN cell, the app count equals `eligible_templates` from the frozen `select_templates`
  (`test_counts_equal_the_frozen_template_selector_pool`) and from the service result
  (`test_availability_matches_the_service_template_pool`). The same check runs on the real data when it is present
  (`test_real_data_categories_match_frozen_selector`, skipped here).

## UI behaviour (English and Turkish)

* The category dropdown is built from `available_categories(segment)`; no "(no TRAIN templates)" entries (the V1.1 catalog keys were
  removed). Labels are translated (e.g. `shorts` → *Şort*, `trousers` → *Pantolon*); options remain internal identifiers.
* Before the dropdown is drawn, the stored selection is validated with `app.state.resolve_category`: still available → kept; not
  available (previous segment, old session, injected display label or unknown id) → replaced by `trousers` if available, else by the
  first available category. An invalid combination therefore never stays in session state and is never submitted; a defensive check
  before calling the service shows `form.invalid_combination` instead of generating.
* A segment without available categories shows `form.no_categories` (sidebar and main area) and the **Generate** button is disabled.
  Other inputs are kept and restored when a segment with categories is chosen again.
* Fit, length, preferred / forbidden material, colour and functional options refresh for the new (segment, category) cell; disabled
  fields are reset as before.
* Results generated before an input change stay visible with the outdated-results warning plus a line naming their request
  ("The results below belong to the previous request: Segment: women · Garment category: trousers …" /
  "Aşağıdaki sonuçlar önceki isteğe aittir: Hedef grup: Kadın · Giysi kategorisi: Pantolon …"). A language-only change keeps the
  selection and the results and never regenerates.
* Service: `generate_recommendations` is unchanged. An unavailable pair returns the existing `no_templates` status (0 eligible
  templates, no template used — tested by spying on the frozen `generate_for_template`); unknown segments / categories return
  `invalid_request`. Result formats are unchanged; the English output still equals the V1.0.0 golden file (34 cases) and the V1.1
  EN/TR equivalence record is byte-identical.

## Files

Added: `app/tests/category_fixtures.py`, `app/tests/test_category_availability.py` (36 tests + 1 real-data test),
`app/browser_smoke_categories.py`, `docs/V1_2_RELEASE_NOTES.md`, `docs/demo_screenshots/v1_2_categories_fixture/` (4 PNG).

Modified: `app/adapters.py` (eligible counts), `app/streamlit_app.py` (category selector, empty state, stale-result line, guard),
`app/state.py` (`resolve_category`), `app/presenters.py` (`request_summary`), `app/i18n/en.py`, `app/i18n/tr.py` (new keys, two removed),
`app/browser_smoke.py` (S3 checks that baby / skirts is not offered), `app/browser_smoke_i18n.py` (fixture = category fixture),
`README.md`, `docs/DEMO_APP.md`, `docs/LOCALIZATION.md`, `docs/V1_DEMO_SCENARIOS.md`, `docs/V1_KNOWN_LIMITATIONS.md`.

Tests adapted to the intended behaviour change (a category without eligible templates can no longer be picked in the UI):
* `app/tests/test_app_release_v1.py::test_disabled_field_does_not_keep_a_stale_value` — reaches `shorts` via segment `men` instead of
  picking `shorts` for `women` (same assertion: the disabled Fit field is reset).
* `app/tests/test_i18n.py::test_turkish_empty_state_and_disabled_fields` — checks that `men` lists only *Şort*; the empty-pool message is
  checked through the service.
* `app/tests/test_app_ui.py::test_unsupported_fields_disabled_and_empty_cell_explained` (real data, skipped here) — checks that
  `skirts` is not offered for `baby` and that the service still returns `no_templates`.

Unchanged: `cago/`, `scripts/`, `tests/`, `configs/`, `data/processed/`, `requirements.txt`, `app/service.py`.

## Tests

| Run | Result |
|---|---|
| Whole project, Python 3.13.16, `CAGO_I18N_STRICT=1 python -m pytest -q` | **426 passed, 4 failed, 24 skipped** |
| Whole project, Python 3.12.3, fresh venv from the release ZIP (`CAGO_I18N_STRICT=1`) | **426 passed, 4 failed, 24 skipped** (identical) |
| V1.1.0 in the same environment | 390 passed, 4 failed, 23 skipped |

The 4 failures are the same environmental ones as in V1.1: the git-ignored `garment_representation.parquet` and
`split_mapping.parquet` are not present in this checkout (they are part of the V1.0.0 release package; the raw Zenodo data could not be
downloaded here). They are `test_frozen_research_files_remain_unchanged` (reports the two files as *missing*, `changed: []`),
`test_final_test_manifest_still_verifies` (needs `split_mapping.parquet`) and two `tests/test_requirements.py` real-context tests.

Windows: `tests/test_final_test_evaluation.py::test_parallel_and_cached_execution_reproduce_sequential_results` uses a fork-based process
pool and is expected to fail on Windows; deselect it there (see README / V1_KNOWN_LIMITATIONS). Frozen research code is not changed.

## Browser verification

`python -m app.browser_smoke_categories --fixture-data` (SYNTHETIC category fixture; the real processed data was not available):
**16 / 16 checks passed, 0 console errors** — for every segment in EN and TR the dropdown shows exactly the available categories
(women: shorts, trousers / Şort, Pantolon; men: shorts / Şort), no "(no TRAIN templates)" entry; `kids` (TRAIN garments, none
eligible) shows the empty-state message with generation disabled; `trousers` is replaced by `shorts` for women → men while `shorts`
stays selected; a result generated for women / trousers is labelled as the previous request after switching to men, in EN and TR;
the language switch keeps the selection and does not regenerate. `python -m app.browser_smoke_i18n --fixture-data`: 14 / 14 passed,
0 console errors. Both scripts were run on the working copy and again on the unpacked release ZIP with identical results.
Screenshots: `docs/demo_screenshots/v1_2_categories_fixture/`.

**Real-data browser verification is incomplete**: no category lists or counts of the real dataset are claimed. With the processed
data present, run `python -m app.browser_smoke_categories` — it computes the expected lists from the data, checks every segment
(including men) in both languages, prints the per-segment eligible-template counts and saves screenshots.

## Integrity

| Check | Result |
|---|---|
| `app.integrity.verify()` (127 hashed frozen files) | `changed: []`, `added_in_frozen_dirs: []`; `missing`: the two absent parquet files |
| Final TEST manifest: sha256 of all 115 frozen + evaluation source files | 0 mismatches |
| Manifest prior results (12) and present data artifacts (3) | 0 mismatches |
| `final_test_evaluation_report.json` / `.md`, `final_test_evaluation_manifest.json`, `v1_demo_evidence.json` | unchanged (`030a39bc…`, `1ad3869a…`, `1c9dbb7a…`, `2619d910…`) |

## Readiness

Recommended for release as **V1.2.0** after one run with the complete V1.0.0 `data/processed/` folder:
`python -m pytest -q` (expect 0 failures), `python -m app.browser_smoke_categories` (records the real per-segment lists and screenshots),
`python -m app.browser_smoke` and `python -m app.demo_scenarios` (evidence must stay byte-identical).

## Correction: real-data test `test_app_ui.py::test_unsupported_fields_disabled_and_empty_cell_explained`

Reported on Windows with the real processed data: the test compared Streamlit AppTest `.options` (display labels, e.g.
`jumpsuits overalls`) with `data.available_categories("baby")` (canonical identifiers, e.g. `jumpsuits_overalls`). Production code was
correct; only this test was changed:

* The expected options are now produced with the rendered widget's own formatter (`Selectbox.format_func`, the callable Streamlit
  registered for the category dropdown) applied to `available_categories("baby")` — no hand-made mapping.
* Runs in English and Turkish in one session (labels from the i18n catalog); checks that `skirts` has 0 eligible TRAIN templates for
  `baby`, is not in the list and its label is not offered; the selected value and `st.session_state["w_category"]` are canonical
  identifiers whose label is displayed (in Turkish no raw identifier is shown); socks_hosiery still disables Fit / Length; a direct
  service request for baby / skirts returns `no_templates` with the empty-pool message in both languages.
* Verification without the real data (not available in this environment): in a scratch copy whose `data/processed/` held a SYNTHETIC
  parquet shaped like the real cells (baby: `dresses`, `jumpsuits_overalls`; `skirts` only in other segments or in VAL/TEST) plus the
  real vocabulary and capability files, the V1.2.0 test reproduced the reported failure
  (`'jumpsuits overalls' != 'jumpsuits_overalls'`) and the corrected test passed (`test_app_ui.py`: 3 passed). Please confirm with
  the real data: `python -m pytest -q app/tests/test_app_ui.py` and the full suite.
