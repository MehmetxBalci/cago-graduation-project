# CAGO V1 — known limitations

## Scope of the claims
* SR1–SR5 are screening rules reproduced from Li & Walther (2026). "No violations detected" means none of these five rules flagged the
  composition; it does not mean the garment is recyclable, sortable in a specific facility, or manufacturable.
* Dataset-relative Plausibility measures support and similarity relative to TRAIN garments, not production feasibility.
* Functional preferences (stretch, thermal warmth, breathability, durability, moisture wicking, water repellency) are composition / text
  proxies, not measured performance. Water repellency needs strong evidence (coating, membrane, lamination, water-resistant text); a
  synthetic outer fabric alone is never treated as proof.
* Intent alignment only counts explicitly requested, scorable preferences. A neutral value (`standard`) or a template without a fit /
  length label is "not scored", not a miss. If nothing is scorable, intent is n/a and there is no Intent-focused recommendation.

## Generation
* Colour, fit and length are inherited from the TRAIN template; V1 never recolours or re-cuts. A black template therefore always keeps
  the SR4 flag, and colour / fit / length preferences can only be met by choosing matching templates.
* Only TRAIN templates of the same segment and category are used. Cells with no or few templates (e.g. `baby / skirts`)
  give no or few candidates; the app explains this and does not fall back to other cells.
* Forbidden materials are hard constraints; templates whose forbidden material has no TRAIN-supported replacement are dropped, which can
  leave no candidate.
* B3 can create intermediate steps that are undone later (e.g. viscose → wool → viscose in S6) and duplicate material slots in one
  component; the cards merge duplicates for display only.
* App results are demonstrations for user-chosen requests; they do not reproduce or extend the final TEST benchmark.

## Application
* Single-user local prototype: no accounts, persistence, export or deployment configuration.
* The Pareto chart is a 2-D view (intent × plausibility) of a 3-objective front; violation counts are printed above front points.
* Invalid values can only arrive through the Python service API; the form offers valid values only.
* Category availability of preferences comes from the frozen capability table; preferences disabled there cannot be requested.
* Explanations are rewritten into plain language from structured evidence; unusual evidence tokens that have no mapping are shown
  unchanged. The original technical explanation is always shown beside it.

## Category availability (V1.2)
* A category is offered for a segment when at least one TRAIN garment of that exact cell passes the frozen template-eligibility check.
  One eligible template is enough to be listed; such cells give few and less diverse candidates (the small-pool message explains this),
  and forbidden materials can still leave no candidate (`no_candidates`).
* The list follows the processed TRAIN data shipped with the release. Rebuilt data with different TRAIN rows changes the lists.
* A segment without any available category is handled (message, generation disabled), but the counts of the real data could not be
  re-checked in the V1.2 build environment because `garment_representation.parquet` was absent there; run
  `python -m app.browser_smoke_categories` with the real data to record them.

## Localization (V1.1)
* Two languages: English (default) and Turkish. The wording is presentation-only; research outputs are identical in both (tested).
* The *Technical evidence* line under each preference is the frozen engine's own English explanation and is shown verbatim in
  Turkish too. Evidence tokens without a mapping and unknown warning codes (none occur with the frozen engine) would also appear in
  their original form.
* Dataset colours are free retail names; parts without a reliable Turkish translation (pattern, licence or character names such as
  `spider-man`, `mole`) are shown as in the data. Some materials keep their identifier (`elastomultiester`, `lyocell`, polymer
  abbreviations).
* Built-in Streamlit texts that the app cannot set (e.g. "No results" inside an empty dropdown search, the "Deploy" / main menu, the
  "Running..." indicator) stay in English.
* The real-browser language check of the V1.1 build was run on the SYNTHETIC test fixture because the processed TRAIN data
  (`garment_representation.parquet`) was not available in that environment; re-run `python -m app.browser_smoke_i18n` and
  `python -m app.demo_scenarios --lang tr` with the real data before presenting.

## Platform and environment
* Verified on Linux with Python 3.12.3 and 3.13 (pandas 2.3.3, pyarrow 25.0.1, Streamlit 1.65.0). Windows and macOS commands are
  documented but were **not executed** in this release check.
* Windows: the frozen final-TEST runner uses a fork-based process pool for `--workers > 1`; fork does not exist on Windows. Use
  `--workers 1` there. For the same reason the research test
  `tests/test_final_test_evaluation.py::test_parallel_and_cached_execution_reproduce_sequential_results` is expected to fail on Windows;
  run the suite with
  `python -m pytest -q --deselect tests/test_final_test_evaluation.py::test_parallel_and_cached_execution_reproduce_sequential_results`.
  The demo app does not use multiprocessing. (Frozen research code is intentionally not changed in V1.)
* pandas 3 is not supported (`pandas<3`), because all results were produced with pandas 2.
* The browser smoke test needs Playwright + Chromium, which are not in `requirements.txt`.

## Data
* The app requires the processed files listed in `docs/DEMO_APP.md`; it does not rebuild, repair or download data.
* Rebuilding the research tests from the raw dataset needs the raw Zenodo files (`CAGO_INPUT`, `CAGO_SUPPORT_DIR`), which are not part of
  this package.
