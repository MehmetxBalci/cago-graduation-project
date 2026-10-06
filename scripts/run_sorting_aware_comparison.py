"""CLI: python scripts/run_sorting_aware_comparison.py --processed-dir data/processed  (VAL-only development comparison)"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cago.benchmark.sorting_aware_comparison import default_variants, run_comparison  # noqa: E402
from cago.benchmark.sorting_aware_requests import assert_dev_only, build_val_requests, dev_view  # noqa: E402
from cago.generation.support_tables import build_support_tables  # noqa: E402
from cago.requirements.validation import RequirementContext  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Sorting-aware generator VAL development comparison")
    ap.add_argument("--processed-dir", default=Path("data/processed"), type=Path)
    ap.add_argument("--seed", default=0, type=int)
    ap.add_argument("--n-templates", default=10, type=int)
    ap.add_argument("--per-template", default=8, type=int)
    ap.add_argument("--max-requests", default=300, type=int)
    ap.add_argument("--n-bootstrap", default=500, type=int)
    ap.add_argument("--no-policy-variant", action="store_true")
    a = ap.parse_args()
    d = a.processed_dir
    rep = dev_view(pd.read_parquet(d / "garment_representation.parquet"))      # TEST rows dropped here
    assert_dev_only(rep)
    ctx = RequirementContext.from_processed(d)
    support = build_support_tables(rep)                                         # TRAIN only
    reqs = build_val_requests(rep, support, a.seed, max_requests=a.max_requests)
    variants = default_variants(a.n_templates, a.per_template, a.seed, policy_variants=not a.no_policy_variant)
    out = run_comparison(reqs, rep, ctx, support, variants, n_boot=a.n_bootstrap, seed=a.seed)
    out.update({"seed": a.seed, "n_bootstrap": a.n_bootstrap, "development_splits": ["train", "val"], "test_rows_in_working_set": 0,
                "config": {"n_templates": a.n_templates, "candidates_per_template": a.per_template}})
    from cago.benchmark.sorting_aware_report import render_comparison_md
    (d / "sorting_aware_val_comparison.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (d / "sorting_aware_val_comparison.md").write_text(render_comparison_md(out), encoding="utf-8")
    print({"requests": out["coverage"]["n_requests"], "cells": out["coverage"]["cells"], "fairness": out["fairness"]["identical_template_pool_and_selection_across_variants"],
           "determinism": out["determinism"]})


if __name__ == "__main__":
    main()
