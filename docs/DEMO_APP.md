# CAGO Demo App V1

A local Streamlit application on top of the frozen CAGO research pipeline. A user chooses garment requirements; the app runs the frozen
Sorting-Aware Generator B3, evaluates every candidate with the frozen Intent Alignment, SR1–SR5 Sorting Compatibility and
Dataset-relative Plausibility metrics, computes the Pareto front and shows the Balanced, Sorting-focused and Intent-focused recommendations
with evidence-based explanations.

CAGO is a graduation-project prototype. Sorting results refer only to the SR1–SR5 screening rules; zero detected violations does not
guarantee recyclability or manufacturability.

## Required data files

The app reads three files from `data/processed/` (or from the folder in the `CAGO_PROCESSED_DIR` environment variable):

| File | Content | Produced by |
|---|---|---|
| `garment_representation.parquet` | garment templates (component compositions, fit/length labels, `split` column) | `scripts/run_representation.py` |
| `ml_material_vocabulary.json` | TRAIN-fitted material vocabulary and aliases | `scripts/run_representation.py` |
| `category_capabilities.json` | which preferences each garment category supports | `scripts/run_representation.py` |

Only rows with `split == "train"` are read (row filter at load time); VAL and TEST garments are never loaded during normal operation.
If a file is missing, the app shows which one and why it is needed instead of crashing. To rebuild the files from the raw dataset
archive: `scripts/run_preprocessing.py` → `scripts/run_representation.py` (see the earlier reproduction notes).

## Installation

```bash
python -m venv .venv && source .venv/bin/activate      # optional
pip install -r requirements.txt                        # pandas>=2.2,<3, pyarrow, pytest, streamlit>=1.48
```

Tested with Python 3.13, pandas 2.3.3, pyarrow 26, Streamlit 1.65. pandas 3 is excluded because all CAGO results were produced with pandas 2.

## Run

From the project root:

```bash
streamlit run app/streamlit_app.py
```

Then open http://localhost:8501. Tests: `python -m pytest -q` (whole project) or `python -m pytest app/tests -q` (app only).

## Example flow

1. Sidebar: Segment `women`, Garment category `trousers`.
2. Preferred dominant material `linen`, Fit `relaxed`, Breathability `high` (fields that the category does not support are greyed out and
   listed under *Unavailable for this category*).
3. Press **Generate recommendations**. A progress bar shows the stages (validation → B3 generation → evaluation/selection); the status line
   reports generation time, generated / requested candidates, hard-valid candidates, Pareto-front size and eligible TRAIN templates.
4. Up to three cards appear (Balanced, Sorting-focused, Intent-focused). If one candidate wins several roles it is shown once, titled e.g.
   *Balanced + Intent-focused*. Each card shows category, colour, fit, length, component compositions, Intent Alignment, Dataset-relative
   Plausibility, the SR1–SR5 violation count and expandable sections: *Why this recommendation*, *SR1–SR5 sorting-screening results*,
   *Changes from the TRAIN template*.
5. *Pareto candidate overview*: every hard-valid candidate as a dot (x = Intent Alignment, y = Dataset-relative Plausibility; numbers above
   Pareto-front dots = SR1–SR5 violations; the recommendations are circled and labelled). Without scorable preferences the x axis shows
   violations instead.

Screenshots: `docs/demo_screenshots/` (start screen, results, opened explanations, a cell without TRAIN templates).

## Architecture

```
app/
  streamlit_app.py   UI only (form, cards, chart); calls the service
  service.py         generate_recommendations(user_request, seed=0, ...): the single entry point
  adapters.py        TRAIN-only data loader, RequirementContext from TRAIN rows, form -> request mapping, field availability
  presenters.py      display-only material merging, SR1–SR5 wording, score labels, banned-claim check
  state.py           session-state helpers (result storage, stale-result detection)
  integrity.py       hash snapshot of frozen research code / results (frozen_research_hashes.json)
  tests/             application-layer tests (+ headless Streamlit AppTest smoke tests)
```

`generate_recommendations` = `validate_request` (frozen) → `generate_sorting_aware` (frozen B3; selects eligible TRAIN templates) →
`evaluate_and_select` (frozen hard gate, Intent, SR1–SR5, Plausibility, Pareto, selections, explanations) → UI-friendly dictionary.
Invalid input never raises: the result carries a `status` (`ok`, `invalid_request`, `no_templates`, `no_candidates`, `no_valid_candidates`)
and user-readable messages. Loaded data and TRAIN support tables are cached with `st.cache_resource`.

## Demo configuration vs frozen final TEST configuration

* Generator B3 runs with exactly the frozen configuration of the final TEST evaluation (proposal + repair, STRICT_SORTING, Intent and
  Plausibility floors 0.15, max 3 repair steps, attempt limit 25, ...). A test asserts that the app's default configuration equals the
  manifest `configs/final_test_evaluation_manifest.json` and that only `n_templates`, `candidates_per_template` and `seed` can differ.
* Candidate budget (templates × candidates per template) and seed are **application runtime parameters** (Advanced section). The default
  10 × 8, seed 0 equals the final evaluation budget because it is fast enough (typically < 1 s per request on a laptop CPU).
* App results do not reproduce the final TEST benchmark: requests come from the user, not from held-out garments.

## Display-only normalisation

B3 can place the same material in two slots of one component (e.g. `cotton 95` + `cotton 5`); the Oracle aggregates such slots. The cards
merge identical materials within a component (`cotton 100%`) and note it. The merged view is never passed back to generation or evaluation
(tested).

## Known limitations

* Colour, fit and length are inherited from the TRAIN template; CAGO V1 never recolours or re-cuts a garment. A black template therefore
  always keeps the SR4 colour-screening flag, and colour / fit / length preferences can only be met by choosing matching templates.
* Functional preferences (stretch, warmth, breathability, durability, moisture wicking, water repellency) are composition / text proxies,
  not measured performance.
* Dataset-relative Plausibility measures support and similarity relative to the TRAIN data; it is not a manufacturability estimate.
* Cells with few or no TRAIN templates (e.g. `baby / skirts`, `men / leggings`) give few or no candidates; the app says so instead of
  inventing fallbacks.
* B3 is more expensive than Baseline A; the budget slider trades diversity for speed.
* Explanation sentences reuse the frozen evaluation's evidence; some proxy explanations keep technical wording (e.g. `breathable_fibre_share`).
* Single-user local prototype; no persistence, accounts or export.
