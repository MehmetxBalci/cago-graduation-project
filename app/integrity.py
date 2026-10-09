"""Integrity snapshot of the frozen research code and results, taken before the demo app was added.

`python -m app.integrity --snapshot` (one-off) writes app/frozen_research_hashes.json; the app test-suite verifies it.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = Path(__file__).with_name("frozen_research_hashes.json")
CODE_DIRS = ("cago", "scripts", "tests")
RESULT_FILES = ("configs/final_test_evaluation_manifest.json", "data/processed/final_test_evaluation_report.json",
                "data/processed/final_test_evaluation_report.md", "data/processed/baseline_benchmark.json", "data/processed/evaluation_validation_audit.json",
                "data/processed/sorting_aware_val_comparison.json", "data/processed/oracle_audit_report.json", "data/processed/garment_representation.parquet",
                "data/processed/split_mapping.parquet", "data/processed/ml_material_vocabulary.json", "data/processed/category_capabilities.json",
                "requirements.txt")


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def current_hashes(root: Path = ROOT) -> dict[str, str]:
    out = {}
    for d in CODE_DIRS:
        for p in sorted((root / d).rglob("*.py")):
            if "__pycache__" not in p.parts:
                out[p.relative_to(root).as_posix()] = sha256(p)
    for r in RESULT_FILES:
        if (root / r).exists():
            out[r] = sha256(root / r)
    return out


def verify(root: Path = ROOT) -> dict[str, list[str]]:
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))["files"]
    now = current_hashes(root)
    allowed_changes = set(json.loads(SNAPSHOT.read_text(encoding="utf-8")).get("documented_changes", {}))
    return {"changed": sorted(k for k in snap if k in now and now[k] != snap[k] and k not in allowed_changes),
            "missing": sorted(k for k in snap if k not in now),
            "added_in_frozen_dirs": sorted(k for k in now if k not in snap and k.endswith(".py"))}


if __name__ == "__main__" and "--snapshot" in sys.argv:
    SNAPSHOT.write_text(json.dumps({"purpose": "frozen research code/results before Demo App V1", "files": current_hashes(),
                                    "documented_changes": {}}, indent=1), encoding="utf-8")
    print(f"wrote {SNAPSHOT} ({len(current_hashes())} files)")
