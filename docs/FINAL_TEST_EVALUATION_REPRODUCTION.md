# CAGO final TEST evaluation - reproduction guide

Compares frozen Generator A (Oracle-unaware template + probabilistic mutation) with frozen Generator B3 (sorting-aware proposal + repair,
STRICT_SORTING) on held-out TEST requests. No Git is used or required.

## Requirements
Python 3.11+ (final run: Python 3.13), `pandas>=2.2,<3` (final run: 2.3.3), `pyarrow`, `pytest`. pandas 3 changes default string dtypes and was
not used for any CAGO result. The processed data in `data/processed/` must be present (`garment_representation.parquet`,
`split_mapping.parquet`, `garments.parquet`, `ml_material_vocabulary.json`, `category_capabilities.json`, ...). If a file is missing the
script stops with an error instead of producing results.

## Steps
1. `python scripts/run_final_test_evaluation.py --freeze`
   Writes `configs/final_test_evaluation_manifest.json`: generator/evaluation configurations, seeds, budgets, template-selection method,
   analysis plan (primary outcomes P1-P5), split digest, sha256 of every frozen source file, data artifact and earlier result.
   Reads no TEST result and refuses to overwrite an existing manifest (`--force-refreeze --reason "..."` records a re-freeze history).
2. `python -m pytest -q` - full suite, including manifest / source-integrity tests.
3. `python scripts/run_final_test_evaluation.py --run --workers 2 --cache-dir <dir>`
   Verifies the manifest (aborts on any mismatch), checks parent/garment leakage between TRAIN/VAL/TEST, builds the TEST requests,
   runs A and B3 under identical conditions with TRAIN-only rows and support tables, writes
   `data/processed/final_test_evaluation_report.json` and `.md`. `--workers` and `--cache-dir` never change results: per-request work is a
   pure function of the request (tested); the cache only lets an interrupted run resume. About 10-20 CPU-minutes.
4. `python scripts/run_final_test_evaluation.py --reproduce-request '<request_id>'` re-runs one request and prints its selected designs.
5. `python scripts/run_final_test_evaluation.py --dry-run-val --max-requests 12 --output-dir <dir>` checks the pipeline on VAL requests
   (never writes into `data/processed`).

## What TEST data is used for
TEST cells and TEST garments' observable properties (dominant material, elastane bucket, colour, V1 fit/length labels) define requests only.
TEST compositions are never templates and never enter TRAIN support tables; generators receive TRAIN rows only.

## Interpretation rules
Zero violations = zero SR1-SR5 screening violations, not recyclability. Intent Alignment is a preference-alignment index and
Dataset-relative Plausibility measures similarity to the TRAIN distribution; neither is a physical-performance or manufacturability measure.
P1-P5 are the pre-specified primary outcomes; everything else is exploratory. CIs are unadjusted percentile bootstrap intervals
(parent-clustered primary; cell-clustered and request-level as sensitivity).
