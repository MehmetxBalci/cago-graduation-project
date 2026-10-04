"""CLI: python scripts/run_baseline_benchmark.py --processed-dir data/processed [--seed 0] [--per-template 10]"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cago.benchmark.audit import render_benchmark_md  # noqa: E402
from cago.benchmark.benchmark_requests import build_benchmark_requests  # noqa: E402
from cago.benchmark.perturbations import load_eval_garments  # noqa: E402
from cago.benchmark.runner import run_benchmark  # noqa: E402
from cago.generation.baseline import GenerationConfig  # noqa: E402
from cago.generation.support_tables import build_support_tables  # noqa: E402
from cago.requirements.validation import RequirementContext  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="CAGO baseline benchmark over many request cells")
    ap.add_argument("--processed-dir", default=Path("data/processed"), type=Path)
    ap.add_argument("--seed", default=0, type=int)
    ap.add_argument("--n-templates", default=10, type=int)
    ap.add_argument("--per-template", default=10, type=int)
    ap.add_argument("--max-requests", default=300, type=int)
    ap.add_argument("--n-bootstrap", default=1000, type=int)
    ap.add_argument("--rerun-check", default=20, type=int)
    a = ap.parse_args()
    d = a.processed_dir
    rep = pd.read_parquet(d / "garment_representation.parquet")
    ctx = RequirementContext.from_processed(d)
    support = build_support_tables(rep)                                    # TRAIN only
    tests = load_eval_garments(rep, "test", seed=a.seed, one_per_parent=False)
    reqs = build_benchmark_requests(tests, support, a.seed, max_requests=a.max_requests)
    gcfg = GenerationConfig(n_templates=a.n_templates, mutations_per_template=a.per_template, seed=a.seed)
    out = run_benchmark(reqs, rep, ctx, support, gcfg, n_boot=a.n_bootstrap, seed=a.seed, rerun_check=a.rerun_check)
    out["seed"], out["n_bootstrap"] = a.seed, a.n_bootstrap
    out["config"] = {"n_templates": a.n_templates, "candidates_per_template": a.per_template, "max_requests": a.max_requests}
    out["notes"] = [
        "Requests are derived from held-out TEST garments (dominant material, elastane bucket, colour, V1 fit/length labels); "
        "all templates, support tables and generation are TRAIN-only.",
        "Stage rows are pooled over requests; request-level and cluster-bootstrap statistics are reported to avoid treating candidates as independent.",
        "Descriptive evaluation: no causal superiority claim; selected designs are Pareto-restricted subsets of the generated candidates."]
    (d / "baseline_benchmark.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (d / "baseline_benchmark.md").write_text(render_benchmark_md(out), encoding="utf-8")
    print({"requests": out["coverage"]["n_requests"], "cells": out["coverage"]["cells"], "totals": out["totals"], "determinism": out["determinism"]})


if __name__ == "__main__":
    main()
