# CAGO — Constraint-Aware Garment Optimization (V1.1)

Graduation-project prototype. CAGO adapts real garment templates from the TRAIN split of a public garment-composition dataset to a
user's requirements and screens every candidate with the SR1–SR5 textile-sorting rules (a reproduction of Li & Walther 2026).
It contains the frozen research pipeline (preprocessing, Oracle, requirement engine, Generator A / B3, evaluation, Pareto, benchmark,
final TEST evaluation) and a local Streamlit demo app.

> CAGO is a prototype. Sorting results refer only to the SR1–SR5 screening rules; zero detected violations does **not** guarantee
> recyclability or manufacturability. Plausibility is dataset-relative (support and similarity relative to the TRAIN data).

## Quick start (demo app)

Requirements: Python 3.12 or 3.13 (tested: 3.12.3 and 3.13), `pandas>=2.2,<3`, `pyarrow>=15`, `streamlit>=1.48`, `pytest>=8`.

**Windows (PowerShell)**, from the project folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app/streamlit_app.py
```

**macOS / Linux**:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app/streamlit_app.py
```

The browser opens at <http://localhost:8501>. Stop the app with `Ctrl+C` in the terminal.

## Language / Dil (English · Türkçe)

The interface is available in **English** (default) and **Turkish**. Use the **EN / TR** switcher in the upper-right corner of the
page. Switching keeps all selections and the recommendations already on screen; it only changes the wording and never runs the
generator again. Localization is presentation-only: the request sent to the frozen research engine, the candidates, all scores, the
SR1–SR5 flags, the Pareto front and the selected roles are identical in both languages, and the frozen evaluation results are not
affected. Architecture, glossary and translation policy: [docs/LOCALIZATION.md](docs/LOCALIZATION.md).

Arayüz **İngilizce** (varsayılan) ve **Türkçe** kullanılabilir. Sayfanın sağ üst köşesindeki **EN / TR** seçicisiyle dil değiştirilir;
seçimleriniz ve ekrandaki öneriler korunur, öneriler yeniden üretilmez. Yerelleştirme yalnızca sunum katmanını etkiler; araştırma
motoru ve dondurulmuş değerlendirme sonuçları değişmez.

## Required data files

The app needs three processed files in `data/processed/` (relative to the project root):

| Path | Purpose |
|---|---|
| `data/processed/garment_representation.parquet` | garment templates; only rows with `split == "train"` are read |
| `data/processed/ml_material_vocabulary.json` | TRAIN-fitted material vocabulary and aliases |
| `data/processed/category_capabilities.json` | which preferences each garment category supports |

They are included in this release (derived from the CC BY 4.0 dataset below). To use another folder, set `CAGO_PROCESSED_DIR`
(PowerShell: `$env:CAGO_PROCESSED_DIR = "D:\cago\processed"`; bash: `export CAGO_PROCESSED_DIR=/path/to/processed`).
If a file is missing, the app lists the missing files; if a file is corrupted or incomplete, it names the file and the problem. It never
repairs, regenerates or downloads data. See [docs/DEMO_APP.md](docs/DEMO_APP.md#required-data-files) for rebuilding from the raw dataset.

The research tests that rebuild data from the raw dataset additionally need the raw files (not included):
`CAGO_INPUT=<raw>/6_JSONL_component_normalized_public.jsonl` and `CAGO_SUPPORT_DIR=<raw folder>`; without them those tests
(`tests/test_integrity.py`) are skipped. All other tests use the processed files or synthetic fixtures.

## Tests

```bash
python -m pytest -q                 # whole project (research + app), about 1.5–2 min
python -m pytest app/tests -q       # application layer only, including headless Streamlit AppTest and the EN/TR tests
CAGO_I18N_STRICT=1 python -m pytest app/tests -q   # same, a missing translation key raises instead of falling back
python -m app.demo_scenarios        # V1 demo scenarios on real data -> docs/v1_demo_evidence.json (--lang tr: Turkish wording)
python -m app.browser_smoke         # optional real-browser test (needs: pip install playwright; python -m playwright install chromium)
python -m app.browser_smoke_i18n    # optional real-browser EN -> TR -> EN test (selections kept, no regeneration, screenshots)
```

## Project layout

```
app/        Streamlit demo app, service layer, adapters, presenters, i18n/ (English + Turkish catalogs, translator), app tests,
            demo-scenario and browser-smoke runners
cago/       frozen research package (preprocessing, oracle, requirements, representation, generation, generation_sorting,
            evaluation, optimization, benchmark)
scripts/    frozen research entry points (run_preprocessing.py, run_representation.py, run_final_test_evaluation.py, ...)
tests/      frozen research tests
configs/    final_test_evaluation_manifest.json (frozen TEST configuration and hashes)
data/processed/  processed data, audits and reports (incl. final_test_evaluation_report.*)
docs/       DEMO_APP.md, LOCALIZATION.md, V1_1_RELEASE_NOTES.md, V1_DEMO_SCENARIOS.md, V1_RELEASE_CHECKLIST.md, V1_KNOWN_LIMITATIONS.md,
            FINAL_TEST_EVALUATION_REPRODUCTION.md
```

## Documentation

* [docs/DEMO_APP.md](docs/DEMO_APP.md) — app usage, architecture, data, troubleshooting
* [docs/LOCALIZATION.md](docs/LOCALIZATION.md) — English / Turkish interface: switching, architecture, glossary
* [docs/V1_1_RELEASE_NOTES.md](docs/V1_1_RELEASE_NOTES.md) — V1.1.0 changes, verification results and readiness
* [docs/V1_DEMO_SCENARIOS.md](docs/V1_DEMO_SCENARIOS.md) — reproducible demo scenarios with recorded output
* [docs/V1_RELEASE_CHECKLIST.md](docs/V1_RELEASE_CHECKLIST.md) — release verification and results
* [docs/V1_KNOWN_LIMITATIONS.md](docs/V1_KNOWN_LIMITATIONS.md)
* [docs/FINAL_TEST_EVALUATION_REPRODUCTION.md](docs/FINAL_TEST_EVALUATION_REPRODUCTION.md) — frozen final TEST evaluation

## Data source and licence

Li, K., & Walther, G. (2026). *A harmonized fast-fashion garment-variant dataset for textile circularity and sustainability assessment.*
Zenodo. <https://doi.org/10.5281/zenodo.20006389> — licensed CC BY 4.0 (<https://creativecommons.org/licenses/by/4.0/>).
The files in `data/processed/` are derived from that dataset by the CAGO preprocessing (parsing, normalisation, parent-grouped
TRAIN/VAL/TEST split, representation); no records were added or invented.
