# CAGO V1 — release checklist

Executed on 2026-10-09, Linux x86_64 (2 CPU cores), Python 3.12.3 (fresh venv from `requirements.txt`) and Python 3.13.
Packages: pandas 2.3.3, pyarrow 25.0.1, Streamlit 1.65.0, Altair 6.3.0, pytest 9.1.1; Playwright + Chromium for the browser test.

## Frozen research state

| Check | Command | Result |
|---|---|---|
| Frozen research files unchanged (127 hashed files: `cago/`, `scripts/`, `tests/`, results, configs) | `python -c "from app.integrity import verify; print(verify())"` | `changed: [], missing: [], added_in_frozen_dirs: []` |
| Final TEST manifest verifies | `verify_manifest` (also in `tests/test_final_test_evaluation.py`) | `ok: True`, 0 mismatches in frozen files, data artifacts, prior results, configs, split digest; manifest digest `37645a68f848099bbc3176d836155b91cd05d20a17ec4c15f6eba6ccaf629551` |
| Final TEST report unchanged | sha256 (below) | byte-identical to the previous release package |
| No new `.py` files in `cago/`, `scripts/`, `tests/` | integrity `added_in_frozen_dirs` | none (all new code is in `app/`) |
| No research configuration or data file changed | diff against previous release | only `app/`, `docs/`, `README.md` differ |

sha256: `final_test_evaluation_report.json` = `030a39bca1d8a076db4dbb7930f45b0cb27b1c5f541ebfaa4b936ab5b8641442`,
`final_test_evaluation_report.md` = `1ad3869ade1b6150644e3d9ff91aae10c8557e57a40d7fbb2c5e375940a3c3d1`,
`configs/final_test_evaluation_manifest.json` = `1c9dbb7a0fc2a18574df244f94c7a732e80245d9ac3954c70be8ceb79f50117c`.

## Tests

| Suite | Python 3.12.3 | Python 3.13 |
|---|---|---|
| Whole project with raw data (`CAGO_INPUT`, `CAGO_SUPPORT_DIR` set) | 324 passed, 0 failed, 0 skipped | 324 passed, 0 failed, 0 skipped |
| Whole project without raw data | — | 314 passed, 10 skipped (`tests/test_integrity.py`, raw data not set) |
| App layer `python -m pytest app/tests -q` (incl. 5 Streamlit AppTest tests) | 52 passed | 52 passed |
| Real browser `python -m app.browser_smoke` (Chromium) | — | 7/7 checks passed, 0 browser console errors |
| Demo scenarios `python -m app.demo_scenarios` | — | 8 scenarios, statuses as documented; two runs identical |
| Fresh copy from the release ZIP (new 3.12 venv): whole project / app tests / scenarios / Streamlit `/_stcore/health` | 324 passed / 52 passed / identical evidence to 3.13 / `ok` | |

The 2 pytest warnings are `DeprecationWarning`s from `os.fork()` in the frozen final-TEST parallel test.

## Application checks (Phase 1 audit)

| Item | Status |
|---|---|
| Validation errors / unsupported preferences shown as messages, no exception | tested (`test_validation_errors_are_returned_not_raised`, S4, S7) |
| Empty / insufficient TRAIN pool | tested (S3, `test_empty_template_state`, small-pool message) |
| Missing data | tested (`test_missing_data_screen`, `test_missing_data_is_detected`) |
| Corrupted / incomplete data | **fixed**, tested (`test_corrupted_file_raises_data_load_error`, `test_corrupted_data_screen`, S8) |
| TRAIN-only loading, no all-split fallback | **fixed**, tested (`test_missing_columns_never_fall_back_to_reading_all_splits`, `test_every_row_read_uses_the_train_filter`) |
| Duplicate roles shown once | tested (`test_identical_candidate_selected_for_multiple_roles`, S1, S2) |
| Display-only merging never fed back | tested (`test_merged_view_is_never_fed_back_into_evaluation`, `test_research_inputs_unchanged_by_wording_layer`) |
| Human-readable explanations, technical evidence kept | **improved**, tested (`test_preference_lines_are_readable_and_keep_technical_evidence`, …) |
| "No Intent-focused" message accurate | **fixed**, tested (3 tests) |
| Disabled fields keep no stale value | verified, regression test added |
| Pareto chart with identical intent values | **fixed** (fixed 0–100 axis), checked in browser (S5) |
| Template-distance caption | **fixed** wording (absolute change summed over slots) |
| Determinism (same request/budget/seed → same digest) | tested (`test_deterministic_seed_behaviour`, scenario re-run) |
| Caching (`st.cache_resource`, TRAIN load ≈ 1.5 s once) | checked |
| No recyclability / sustainability percentage claims | tested (`BANNED_CLAIMS` checks on all generated text) |

## Release package

| Item | Status |
|---|---|
| ZIP without `.git`, `.github`, `.gitattributes`, `__pycache__`, `.pytest_cache`, venvs | checked by listing |
| Raw dataset not included; processed data included with CC BY 4.0 attribution (README) | yes |
| Fresh unzip → Python 3.12 venv → `pip install -r requirements.txt` → tests, demo scenarios, Streamlit health | passed (324 / 52 tests, 8 scenarios, health `ok`) |

## Not verified
* Windows / macOS execution (commands documented only). Expected Windows difference: the fork-based research test, see
  `V1_KNOWN_LIMITATIONS.md`.
* Screen readers / accessibility, multi-user or remote deployment.
