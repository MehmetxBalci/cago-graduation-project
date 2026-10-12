# CAGO V1.1.0 — bilingual interface (English / Turkish): release notes and verification

V1.1.0 is a user-interface localization update of the frozen V1.0.0 prototype. **No algorithmic change**: preprocessing, Oracle,
Generator A / B3, Intent Alignment, Plausibility, Pareto, selection and evaluation code, the final TEST configuration, reports and all
frozen research files are unchanged (hash-verified below). No TEST data was used for any decision. Architecture and glossary:
[LOCALIZATION.md](LOCALIZATION.md).

Verification run: 2026-10-12, Linux x86_64, Python 3.13.16 (development) and Python 3.12.3 (fresh venv from the release ZIP and
`requirements.txt`); pandas 2.3.3, pyarrow 25.0.1, Streamlit 1.65.0, Altair 6.3.0, pytest 9.1.1; Playwright 1.63 + Chromium 141.

## What changed

* **EN / TR switcher** in the upper-right corner (`st.segmented_control`, state in `st.session_state["cago_lang"]`), English default.
* **Localization layer** `app/i18n/` (`en.py`, `tr.py`, `translator.py`): stable keys, strict interpolation, reversible
  display ↔ internal mappings for segment, category, material, colour, fit, length and functional-preference values.
* **Service** renders all wording from structured, language-independent data (`render_result`); a stored result can be re-rendered in
  another language without regeneration (`localize_result`). `generate_recommendations(..., lang="en")` keeps the V1 signature.
* **UI**: every input has a stable key and uses internal identifiers as options; the language switch re-asserts the internal values so
  selections survive the label change. The inputs are no longer wrapped in `st.form` (selections are committed immediately so they can
  always be preserved); generation still runs only on **Generate recommendations**.
* Metric tooltips (Intent Alignment, Dataset-relative Plausibility, SR violations) added in both languages; the result digest is shown in
  *Technical details* (used to prove that a language switch does not regenerate).
* English wording is unchanged from V1.0.0 (golden test on 34 request cases).

### Files

Added
* `app/i18n/__init__.py`, `app/i18n/en.py`, `app/i18n/tr.py`, `app/i18n/translator.py`
* `app/browser_smoke_i18n.py` — real-browser EN → TR → EN check
* `app/tests/test_i18n.py` — 92 localization tests
* `app/tests/golden_cases.py`, `app/tests/golden_en_v1.json` — English output of the V1.0.0 code (written before the refactor)
* `docs/LOCALIZATION.md`, `docs/V1_1_RELEASE_NOTES.md`, `docs/v1_1_i18n_equivalence_evidence.json`
* `docs/demo_screenshots/v1_1_i18n_fixture/i18n_01_en_results.png`, `i18n_02_tr_results.png`, `i18n_03_en_after_switch.png`

Modified
* `app/streamlit_app.py`, `app/service.py`, `app/presenters.py`, `app/adapters.py` (structured `DataLoadError.code/params`,
  availability reason codes; English strings unchanged), `app/state.py` (language key, generation counter), `app/demo_scenarios.py`
  (`--lang`)
* `README.md`, `docs/DEMO_APP.md`, `docs/V1_DEMO_SCENARIOS.md`, `docs/V1_KNOWN_LIMITATIONS.md`

Unchanged: everything in `cago/`, `scripts/`, `tests/`, `configs/`, `data/processed/`, `requirements.txt`, the existing V1 app tests
(`app/tests/test_app_service.py`, `test_app_release_v1.py`, `test_app_ui.py`) and `docs/v1_demo_evidence.json`.

## EN / TR equivalence

`python -m app.tests.golden_cases --equivalence` → [v1_1_i18n_equivalence_evidence.json](v1_1_i18n_equivalence_evidence.json):
34 request cases (successful generation, conflicts, unavailable preferences, single-candidate / duplicate roles, empty template pool,
no candidate, 13 invalid requests) on the synthetic test fixture, same request / budget / seed in both languages:
**34 / 34 identical** in status, digest, candidate IDs, material compositions, Intent and Plausibility scores, SR1–SR5 flags, Pareto
front, ranks, selected roles (incl. de-duplication), message codes and statistics. Tests:
`test_identical_research_outputs_in_both_languages` (34 cases; also re-rendering EN→TR and TR→EN equals direct generation),
`test_research_engine_receives_identical_requests` (spies on B3 and evaluation: identical internal requests, no Turkish label passed),
`test_localize_result_never_regenerates_or_mutates`, `test_duplicate_role_deduplication_is_language_independent`,
`test_english_output_identical_to_v1_golden`.

## Automated tests

| Run | Result |
|---|---|
| Whole project, Python 3.13.16, `CAGO_I18N_STRICT=1 python -m pytest -q` | **390 passed, 4 failed, 23 skipped** |
| Whole project, Python 3.12.3, fresh venv from the release ZIP | **390 passed, 4 failed, 23 skipped** (identical) |
| App layer `python -m pytest app/tests -q` (incl. Streamlit AppTest, 92 i18n tests) | 139 passed, 2 failed, 4 skipped |
| Before V1.1 changes (same environment, V1.0.0 code) | 298 passed, 4 failed, 22 skipped |

The **4 failures are environmental and identical before and after the change**: this checkout does not contain the git-ignored
`data/processed/garment_representation.parquet` and `split_mapping.parquet` (the raw Zenodo dataset could not be downloaded either:
network policy). They are `test_frozen_research_files_remain_unchanged` (reports the two files as *missing*, `changed: []`),
`test_final_test_manifest_still_verifies` (reads `split_mapping.parquet`) and two `tests/test_requirements.py` real-context tests.
The skipped tests need the same processed data or the raw dataset (`CAGO_INPUT`, `CAGO_SUPPORT_DIR`). With the complete V1.0.0
`data/processed/` folder these tests run as in the V1.0.0 release (324 / 324).

i18n test coverage (`app/tests/test_i18n.py`): identical key sets, no empty / untranslated Turkish strings, identical placeholders, every
key used in the code exists, dynamic key families complete, strict lookup and recorded fallback, number formatting, Turkish labels for
every material / category / segment / enum value / component / text tag of the read-only source vocabulary files, deliberate
identifier retention only, unique reversible mappings in both languages (incl. Pamuk → cotton, Keten → linen, Siyah → black,
Rahat kesim → relaxed), colour policy, Turkish explanations, warnings, SR wording and disclaimer, empty-template / no-candidate /
invalid-request messages in both languages, AppTest: English default, switcher, selections preserved EN → TR → EN, **no regeneration**
(generator call count and generation counter stay at 1), results not stale, Turkish form generates the same recommendation, Turkish
empty state, missing-data and corrupted-data screens; recorded demo evidence unchanged; frozen-code and manifest hashes.

## Browser verification (real Chromium)

`python -m app.browser_smoke_i18n --fixture-data` — run twice (working copy and the unpacked release ZIP), **14 / 14 checks passed both
times, 0 browser console errors**. Data: the **SYNTHETIC** test fixture (the real processed TRAIN data was not available in this
environment). Request: Segment women, category trousers, Preferred dominant material linen, Fit relaxed, Breathability high, seed 0,
budget 10 × 8.

| Check | Result |
|---|---|
| 1 English is the default; EN / TR switcher visible | PASS |
| 2 switching to TR translates the form (Giysiniz, Önerileri üret, …) | PASS |
| 3 Turkish results (Dengeli, Ayıklama Odaklı, Tercihlere Uyum, Prototip uyarısı); Turkish form usable (stale warning in Turkish) | PASS |
| 4 switching back restores the English UI | PASS |
| 5 selections preserved: Keten / Rahat kesim / Yüksek in TR, linen / relaxed / high in EN | PASS |
| 6 no regeneration: digest `98c2e1a5ecafdf5e036eb139` in EN, TR and EN again; identical status line incl. generation time | PASS |
| 7 no browser console errors | PASS (0) |

Status line EN: "generated in 2.0 s · 40 of 80 requested candidates · 40 hard-valid · 8 on the Pareto front · 10 of 44 eligible TRAIN
templates used · seed 0"; TR: "2,0 sn içinde üretildi · istenen 80 adaydan 40 tanesi üretildi · 40 aday zorunlu kısıtları sağlıyor ·
8 aday Pareto cephesinde · 44 uygun TRAIN şablonundan 10 tanesi kullanıldı · tohum 0".
Screenshots of the same recommendation: `docs/demo_screenshots/v1_1_i18n_fixture/i18n_01_en_results.png`, `i18n_02_tr_results.png`,
`i18n_03_en_after_switch.png`.

Not run in this environment (real data missing): `python -m app.browser_smoke` (V1 scenarios S1–S5) and
`python -m app.demo_scenarios [--lang tr]`. The real-data test `test_demo_scenarios_reproduce_recorded_evidence_in_both_languages` is
included and skips without data.

## Frozen-source integrity

| Check | Result |
|---|---|
| `app.integrity.verify()` (127 hashed frozen files) | `changed: []`, `added_in_frozen_dirs: []`; `missing`: only the two absent parquet files |
| Final TEST manifest: sha256 of all 115 frozen + evaluation source files | 0 mismatches |
| Manifest prior results (12) and present data artifacts (vocabulary, material map, capabilities) | 0 mismatches |
| `final_test_evaluation_report.json` | `030a39bca1d8a076db4dbb7930f45b0cb27b1c5f541ebfaa4b936ab5b8641442` (unchanged) |
| `final_test_evaluation_report.md` | `1ad3869ade1b6150644e3d9ff91aae10c8557e57a40d7fbb2c5e375940a3c3d1` (unchanged) |
| `configs/final_test_evaluation_manifest.json` | `1c9dbb7a0fc2a18574df244f94c7a732e80245d9ac3954c70be8ceb79f50117c` (unchanged) |
| `docs/v1_demo_evidence.json` | `2619d910085925534113522e2603ac55a7115fbfc0cf63958180c98b76275cf3` (unchanged) |

## Known limitations of V1.1

See [V1_KNOWN_LIMITATIONS.md](V1_KNOWN_LIMITATIONS.md#localization-v11). In short: technical evidence lines stay in the engine's
original English; colour parts without a reliable translation are shown as in the data; a few built-in Streamlit texts stay English;
real-data browser and scenario runs still need to be repeated where `data/processed/` is complete; Windows/macOS not executed.

## Release readiness

Recommended for release as **V1.1.0** after one step on a machine with the complete V1.0.0 `data/processed/` folder:

```bash
python -m pytest -q                      # expect 0 failures (324 V1 tests + the new app tests)
python -m app.demo_scenarios             # docs/v1_demo_evidence.json must stay byte-identical
python -m app.demo_scenarios --lang tr   # Turkish wording of the same scenarios
python -m app.browser_smoke_i18n         # real-data EN -> TR -> EN check; replaces the fixture screenshots if desired
```

Everything that can be verified without the real data passed: EN/TR equivalence, English unchanged from V1.0.0, complete Turkish
catalog, state preservation, no regeneration, no console errors, frozen sources and results untouched.
