# CAGO Demo App V1.1

A local Streamlit application on top of the frozen CAGO research pipeline. A user chooses garment requirements; the app runs the frozen
Sorting-Aware Generator B3, evaluates every candidate with the frozen Intent Alignment, SR1–SR5 Sorting Compatibility and
Dataset-relative Plausibility metrics, computes the Pareto front and shows the Balanced, Sorting-focused and Intent-focused recommendations
with evidence-based explanations.

CAGO is a graduation-project prototype. Sorting results refer only to the SR1–SR5 screening rules; zero detected violations does not
guarantee recyclability or manufacturability.

V1.1.0 adds a bilingual interface (English default, Turkish). See *Language* below and [LOCALIZATION.md](LOCALIZATION.md).

## Installation and start

Python 3.12 or 3.13 (tested: 3.12.3 and 3.13 on Linux). Dependencies: `pandas>=2.2,<3`, `pyarrow>=15`, `streamlit>=1.48`, `pytest>=8`
(tested with pandas 2.3.3, pyarrow 25.0.1, Streamlit 1.65.0, Altair 6.3.0 which Streamlit installs). pandas 3 is excluded because all
CAGO results were produced with pandas 2.

Windows PowerShell, in the project folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app/streamlit_app.py
```

macOS / Linux:

```bash
python3.12 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app/streamlit_app.py
```

Open <http://localhost:8501>. Another port: `python -m streamlit run app/streamlit_app.py --server.port 8502`.
Loading the TRAIN data takes about 1.5 s once per server process (cached with `st.cache_resource`); one request with the default budget
takes about 0.5–1 s on a 2-core laptop-class CPU.

## Required data files

The app reads exactly three files from `data/processed/` (or from the folder named in the `CAGO_PROCESSED_DIR` environment variable):

| File | Required content | Produced by |
|---|---|---|
| `garment_representation.parquet` | columns `garment_id, parent_product_id, split, target_segment, detail_category, normalized_colour, fit_label, fit_label_source, length_label, length_label_source, text_evidence_tags, is_fully_usable, has_unmapped_material, has_other_token, components`; at least one row with `split == "train"` | `scripts/run_representation.py` |
| `ml_material_vocabulary.json` | keys `tokens`, `special_tokens`, `canonical_to_token` (optional: `material_aliases`, `component_classes`, `component_names`) | `scripts/run_representation.py` |
| `category_capabilities.json` | key `categories` (per category: `controls`, `control_decisions`) | copied by `scripts/run_representation.py` |

Only rows with `split == "train"` are read (Parquet row filter at load time; there is no fallback that reads the whole file), so VAL and
TEST garments are never loaded during normal operation.

What the app does when data is not usable:

| Situation | Screen |
|---|---|
| file missing (or a folder with that name) | "Required processed data files are missing in …" plus the list of missing files and why each is needed |
| file not readable (corrupted Parquet / JSON, wrong encoding) | "A processed data file … cannot be used: `<file>`" plus the problem |
| Parquet without a required column, JSON without a required key, no TRAIN rows | same screen, naming the missing columns / keys |

The app never repairs, regenerates or downloads data. To rebuild the processed files from the raw dataset
(Li & Walther 2026, Zenodo, CC BY 4.0; <https://doi.org/10.5281/zenodo.20006389>):

```bash
python scripts/run_preprocessing.py --input <raw>/6_JSONL_component_normalized_public.jsonl --support-dir <raw folder>
python scripts/run_representation.py --support-dir <raw folder>
```

Rebuilt files must reproduce the hashes recorded in `configs/final_test_evaluation_manifest.json`; check with
`python -m pytest tests/test_final_test_evaluation.py -q`.

## Language (EN / TR)

* The **EN / TR** switcher sits in the upper-right corner. English is the default; Turkish translates the whole interface: title,
  disclaimer, form labels and options (segments, categories, materials, colours, fit, length, functional preferences), help texts,
  progress and status messages, validation errors and warnings, recommendation cards, explanations, SR1–SR5 texts, change
  descriptions, the Pareto chart and the technical details.
* Switching keeps every selection and the recommendations already generated; they are re-rendered in the new language. The generator
  is not called again (the status line, including the generation time, and the result digest stay identical), and results are not
  marked stale.
* Localization is presentation-only. The form always sends internal identifiers (`linen`, `relaxed`, `black`, …) to the frozen
  engine, so the same request and seed give identical candidates, scores, SR1–SR5 flags, Pareto front and roles in both languages.
* In Turkish, the *Technical evidence* line under each preference shows the frozen engine's original English explanation (by design);
  colour names that have no reliable Turkish equivalent (pattern / character names) are shown as in the dataset.

## Using the app

1. Sidebar: **Segment** and **Garment category** (categories without TRAIN garments in that segment are marked "(no TRAIN templates)").
2. Materials: preferred dominant material and forbidden materials (hard constraint). Look: colour (TRAIN colours of the cell), fit, length.
   Functional preferences: stretch, thermal warmth, breathability, durability, moisture wicking, water repellency. Fields that the
   category does not support are greyed out with the reason, listed under *Unavailable for this category*, and reset to
   *No preference* when the category changes.
   Selections take effect immediately (V1.1 no longer wraps the inputs in a form, so every selection is kept when the language is
   switched); recommendations are only generated when the button is pressed.
3. **Generate recommendations**. A progress bar shows validation → B3 generation → evaluation/selection; the status line reports time,
   generated / requested candidates, hard-valid candidates, Pareto-front size and TRAIN templates used. If settings change afterwards,
   a warning says the results are stale.
4. Up to three cards (Balanced, Sorting-focused, Intent-focused). One candidate winning several roles is shown once
   (e.g. *Balanced + Intent-focused*). Each card: category, colour, fit, length, component compositions, Intent alignment,
   Dataset-relative plausibility, SR1–SR5 violations, and three sections:
   * *Why this recommendation* — why the role was chosen, comparison with the other recommendations, and every preference with status
     (satisfied / partially / not satisfied / not scored), a plain-language explanation and the original technical evidence.
   * *SR1–SR5 sorting-screening results* — per rule: violation detected / no violation detected, with the reason.
   * *Changes from the TRAIN template* — numbered changes (Change 1, 2, …), rule changes confirmed by undoing one change, and the
     template → candidate trade-offs.
5. *Pareto candidate overview*: every hard-valid candidate (x = intent alignment 0–100, y = dataset-relative plausibility; numbers above
   Pareto-front dots = SR1–SR5 violations; circled = recommendations). If no candidate has a scorable preference the x axis shows
   violations (0–5). Candidate table and technical details (normalised request, run statistics) are in expanders.

Messages you can see: invalid input (e.g. unknown material), preference not available for the category, preferred material also
forbidden, possible preference conflicts, no TRAIN templates, no candidate generated (all templates blocked by forbidden materials), no
zero-violation candidate (with the SR4 colour explanation when relevant), and why there is no Intent-focused recommendation
(no soft preference, preference unavailable, or given but not scorable).

Screenshots (`docs/demo_screenshots/`, produced by `python -m app.browser_smoke`): `01_start.png`, `02_results.png`,
`02b_explanations.png`, `03_no_templates.png`, `04_single_candidate.png`, `05_conflicts.png`.
Language switch (`python -m app.browser_smoke_i18n`; the files in `docs/demo_screenshots/v1_1_i18n_fixture/` were produced with
`--fixture-data`, i.e. the SYNTHETIC test fixture, because the real processed data was not available in the V1.1 build environment):
`i18n_01_en_results.png`, `i18n_02_tr_results.png` (same recommendation in Turkish), `i18n_03_en_after_switch.png`.

## Architecture

```
app/
  streamlit_app.py    UI only (inputs, EN/TR switcher, cards, chart); calls the service
  service.py          generate_recommendations(user_request, seed=0, ..., lang="en"): the single entry point;
                      render_result / localize_result: wording of a stored result in a language (no re-run)
  i18n/               en.py / tr.py catalogs (stable keys), translator.py (lookup, interpolation, display <-> internal mapping)
  adapters.py         TRAIN-only data loader with file checks, RequirementContext from TRAIN rows, form -> request mapping,
                      field availability
  presenters.py       display-only material merging, SR1–SR5 wording, plain-language preference / change / rule wording
  state.py            session-state helpers (result storage, stale-result detection)
  integrity.py        hash snapshot of frozen research code / results (frozen_research_hashes.json)
  demo_scenarios.py   reproducible V1 demo scenarios -> docs/v1_demo_evidence.json
  browser_smoke.py    optional Playwright browser smoke test (writes docs/demo_screenshots)
  browser_smoke_i18n.py  optional Playwright EN -> TR -> EN test (selections, no regeneration, console errors, screenshots)
  tests/              application-layer tests (+ headless Streamlit AppTest)
```

`generate_recommendations` = `validate_request` (frozen) → `generate_sorting_aware` (frozen B3; selects eligible TRAIN templates) →
`evaluate_and_select` (frozen hard gate, Intent, SR1–SR5, Plausibility, Pareto, selections, explanations) → UI dictionary.
Invalid input never raises: the result carries `status` (`ok`, `invalid_request`, `no_templates`, `no_candidates`,
`no_valid_candidates`) and user-readable messages. Programmatic use:

```python
from app.adapters import load_app_data
from app.service import generate_recommendations
data = load_app_data()
r = generate_recommendations({"target_segment": "women", "detail_category": "trousers", "breathability": "high"}, data=data)
print(r["status"], [x["role_titles"] for x in r["recommendations"]])
from app.service import localize_result
print([x["role_titles"] for x in localize_result(r, "tr")["recommendations"]])   # same result, Turkish wording
```

## Demo configuration vs frozen final TEST configuration

* Generator B3 runs with exactly the frozen configuration of the final TEST evaluation (proposal + repair, STRICT_SORTING, Intent and
  Plausibility floors 0.15, max 3 repair steps, attempt limit 25, ...). A test asserts that the app's configuration equals the manifest
  and that only `n_templates`, `candidates_per_template` and `seed` can differ.
* Candidate budget (templates × candidates per template, each 1–20) and seed are application runtime parameters (Advanced section).
  The default 10 × 8, seed 0 equals the final evaluation budget. The same request, budget and seed always give the same result.
* App results do not reproduce the final TEST benchmark: requests come from the user, not from held-out garments.

## Display-only wording and normalisation

* B3 can place the same material in two slots of one component (e.g. `cotton 95` + `cotton 5`); the Oracle aggregates such slots. Cards
  merge identical materials within a component (`cotton 100%`) and say so. The merged view is never passed back (tested).
* Preference explanations, change descriptions and rule-change statements are rewritten from the frozen evaluation's structured values
  (e.g. `breathable_fibre_share=1.00` → "share of breathable fibres (linen, cotton, lyocell, viscose) in the main fabric: 100%").
  Scores, statuses and the request passed to the research functions are unchanged (tested); the original technical explanation is shown
  under each preference as *Technical evidence*.
* Generator steps are 0-based internally; the UI numbers changes from 1 and uses the same numbers in rule-change statements.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `streamlit` not recognised (Windows) | use `python -m streamlit run app/streamlit_app.py` inside the activated venv |
| `Activate.ps1 cannot be loaded` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then activate again |
| `ModuleNotFoundError: app` / `cago` | start from the project root (the folder containing `app/` and `cago/`) |
| "Required processed data files are missing" | copy the three files into `data/processed/` or set `CAGO_PROCESSED_DIR` |
| "… cannot be used" | the named file is corrupted or incomplete; copy it again or rebuild (see above) |
| port 8501 in use | add `--server.port 8502` |

Known limitations: [V1_KNOWN_LIMITATIONS.md](V1_KNOWN_LIMITATIONS.md). Demo scenarios: [V1_DEMO_SCENARIOS.md](V1_DEMO_SCENARIOS.md).
