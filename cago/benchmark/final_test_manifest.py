"""Frozen evaluation manifest for the final TEST evaluation (A vs B3): configuration, seeds, source-file hashes, data ids.

The manifest is written BEFORE any TEST result exists and verified before the TEST run starts and by the test-suite.
Anything that differs from the manifest at run time aborts the evaluation (no silent drift).
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from cago.evaluation.config import EvaluationConfig
from cago.generation.baseline import GenerationConfig
from cago.generation_sorting.config import MODE_CONFIGS, SortingAwareGenerationConfig
from cago.preprocessing.ids import stable_hash

MANIFEST_VERSION = 1
SCAN_DIRS = ("cago", "scripts", "tests")
NEW_CODE_PREFIXES = ("cago/benchmark/final_test_", "scripts/run_final_test_evaluation.py", "tests/test_final_test_", "tests/final_fixtures.py")
DATA_ARTIFACTS = ("garment_representation.parquet", "split_mapping.parquet", "garments.parquet", "components.parquet", "component_materials.parquet",
                  "ml_material_vocabulary.json", "material_to_ml_token.csv", "category_capabilities.json")
PRIOR_RESULTS = ("baseline_benchmark.json", "baseline_benchmark.md", "evaluation_validation_audit.json", "evaluation_validation_audit.md",
                 "candidate_evaluation_audit.json", "template_baseline_audit.json", "sorting_aware_val_comparison.json", "sorting_aware_val_comparison.md",
                 "sorting_aware_generator_audit.json", "oracle_audit_report.json", "data_audit_report.json", "representation_audit.json")
PRIMARY_OUTCOMES = (
    "P1: stage B (hard-valid pool) mean violation_count per request, B3 - A",
    "P2: stage E (Sorting-focused selection) violation_count, B3 - A",
    "P3: stage B zero-violation share per request, B3 - A",
    "P4: stage D (Balanced selection) Intent Alignment, B3 - A",
    "P5: stage D (Balanced selection) Dataset-relative Plausibility, B3 - A")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_new_code(rel: str) -> bool:
    return rel.startswith(NEW_CODE_PREFIXES)


def list_sources(root: Path) -> list[str]:
    out = []
    for d in SCAN_DIRS:
        for p in sorted((Path(root) / d).rglob("*.py")):
            if "__pycache__" not in p.parts:
                out.append(p.relative_to(root).as_posix())
    return out


def frozen_configs(n_templates: int, per_template: int, seed: int) -> dict[str, Any]:
    a = GenerationConfig(n_templates=n_templates, mutations_per_template=per_template, seed=seed)
    b = SortingAwareGenerationConfig(n_templates=n_templates, candidates_per_template=per_template, seed=seed, **MODE_CONFIGS["B3"])
    return {"generator_A_baseline": asdict(a), "generator_B3_sorting_aware": asdict(b), "candidate_evaluation": asdict(EvaluationConfig())}


def split_digest(split_map: pd.DataFrame) -> str:
    return stable_hash(sorted(zip(split_map["garment_id"], split_map["split"])), length=32)


def build_manifest(root: Path, data_dir: Path, n_templates: int = 10, per_template: int = 8, seed: int = 0, k_per_type: int = 3,
                   n_bootstrap: int = 2000) -> dict[str, Any]:
    root, data_dir = Path(root), Path(data_dir)
    sm = pd.read_parquet(data_dir / "split_mapping.parquet")
    rep = pd.read_parquet(data_dir / "garment_representation.parquet", columns=["garment_id", "parent_product_id", "split"])
    srcs = list_sources(root)
    return {
        "manifest_version": MANIFEST_VERSION, "purpose": "Final held-out TEST evaluation: frozen Generator A vs frozen Generator B3",
        "frozen_before_test_run": True,
        "no_tuning_statement": "No hyperparameter, threshold, mutation probability, repair rule or analysis choice was selected using TEST results. "
                               "Configurations are the V1 defaults / VAL development choices recorded here.",
        "configs": frozen_configs(n_templates, per_template, seed),
        "comparison_conditions": {"variants": {"baseline": "A_baseline", "variant": "B3_proposal_plus_repair"}, "policy_B3": "STRICT_SORTING",
                                  "n_templates": n_templates, "candidates_per_template": per_template, "requested_candidates_per_request": n_templates * per_template,
                                  "seed": seed, "seed_policy": "same integer seed for A and B3; each candidate RNG = sha256(seed, request_key, template_id, serial, attempt) for both generators",
                                  "template_selection": "cago.generation.template_selector.select_templates (TRAIN only, exact segment+category match, one template per parent product and composition, ranked by forbidden-repair count then diagnostic preference match then seeded hash) - identical call in both generators",
                                  "generator_input_rows": "TRAIN rows only (VAL and TEST rows are removed before generation)",
                                  "evaluation": "cago.evaluation.candidate.evaluate_request_candidates + pareto_sort + select_designs (identical for both generators)"},
        "request_construction": {"evaluation_split": "test", "k_per_type": k_per_type, "types": ["no_pref", "derived_full", "derived_forbid"],
                                 "garment_order": "sha256(seed, garment_id), one garment per parent product", "seed": seed,
                                 "test_derived_information": "cells and observable properties of held-out garments define requests only; never templates or support"},
        "analysis_plan": {"primary_outcomes": list(PRIMARY_OUTCOMES), "stages": ["A_templates", "B_hard_valid_candidates", "C_pareto_front", "D_balanced", "E_sorting_focused", "F_intent_focused"],
                          "bootstrap": {"n_resamples": n_bootstrap, "seed": seed, "level": 0.95, "method": "percentile"},
                          "uncertainty": ["request-level", "parent-product-clustered (primary)", "cell-clustered (sensitivity: requests of one cell share the TRAIN template pool)"],
                          "multiplicity": "none: 95% CIs are unadjusted; only P1-P5 are pre-specified primary outcomes, everything else is exploratory"},
        "splits": {"digest": split_digest(sm), "garments": {s: int((rep["split"] == s).sum()) for s in ("train", "val", "test")},
                   "parents": {s: int(rep.loc[rep["split"] == s, "parent_product_id"].nunique()) for s in ("train", "val", "test")}},
        "frozen_files": {r: file_sha256(root / r) for r in srcs if not is_new_code(r)},
        "new_evaluation_code": {r: file_sha256(root / r) for r in srcs if is_new_code(r)},
        "data_artifacts": {n: file_sha256(data_dir / n) for n in DATA_ARTIFACTS if (data_dir / n).exists()},
        "prior_results": {n: file_sha256(data_dir / n) for n in PRIOR_RESULTS if (data_dir / n).exists()},
        "environment_informational": {"python": sys.version.split()[0], "platform": platform.platform(), "pandas": pd.__version__,
                                      "cpu_count": os.cpu_count()}}


def manifest_digest(manifest: dict[str, Any]) -> str:
    core = {k: v for k, v in manifest.items() if k not in ("environment_informational",)}
    return hashlib.sha256(json.dumps(core, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def verify_manifest(manifest: dict[str, Any], root: Path, data_dir: Path) -> dict[str, Any]:
    """Compare the current project with the manifest. `ok` requires zero mismatches in frozen sources, data, prior results and configs."""
    root, data_dir = Path(root), Path(data_dir)
    mism = {"frozen_files": [], "data_artifacts": [], "prior_results": [], "configs": [], "new_code_changed_since_freeze": [], "split_digest": []}
    for rel, h in manifest["frozen_files"].items():
        p = root / rel
        if not p.exists() or file_sha256(p) != h:
            mism["frozen_files"].append(rel)
    current = {r for r in list_sources(root) if not is_new_code(r)}
    mism["frozen_files"] += sorted(f"UNLISTED:{r}" for r in current - set(manifest["frozen_files"]))
    for rel, h in manifest["new_evaluation_code"].items():
        p = root / rel
        if not p.exists() or file_sha256(p) != h:
            mism["new_code_changed_since_freeze"].append(rel)
    for sect in ("data_artifacts", "prior_results"):
        for n, h in manifest[sect].items():
            p = data_dir / n
            if not p.exists() or file_sha256(p) != h:
                mism[sect].append(n)
    c = manifest["comparison_conditions"]
    now = json.loads(json.dumps(frozen_configs(c["n_templates"], c["candidates_per_template"], c["seed"]), default=str))
    if json.loads(json.dumps(manifest["configs"], default=str)) != now:
        mism["configs"].append("generator/evaluation configuration differs from code defaults")
    sm = pd.read_parquet(data_dir / "split_mapping.parquet")
    if split_digest(sm) != manifest["splits"]["digest"]:
        mism["split_digest"].append("split mapping changed")
    return {"ok": not any(v for k, v in mism.items() if k != "new_code_changed_since_freeze"), "mismatches": mism,
            "manifest_digest": manifest_digest(manifest)}
