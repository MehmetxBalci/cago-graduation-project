"""CLI: python scripts/run_fit_length_audit.py --processed-dir data/processed"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cago.audits.fit_length_audit import build_fit_length_audit, write_outputs  # noqa: E402
from cago.audits.fit_length_evidence import build_evidence  # noqa: E402
from cago.audits.fit_length_patterns import patterns_document  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Fit/length text evidence audit (read-only on existing outputs)")
    ap.add_argument("--processed-dir", default=Path("data/processed"), type=Path)
    d = ap.parse_args().processed_dir
    g = pd.read_parquet(d / "garments.parquet", columns=["garment_id", "parent_product_id", "detail_category",
                                                         "product_name", "raw_description_text", "raw_function_text"])
    sm = pd.read_parquet(d / "split_mapping.parquet")
    caps_path = d / "category_capabilities.json"
    caps = json.loads(caps_path.read_text(encoding="utf-8")) if caps_path.exists() else None
    ev = build_evidence(g, sm)
    audit = build_fit_length_audit(ev, caps)
    patterns = patterns_document()
    patterns["train_observed_unmapped_structured_values"] = {dim: audit["dimensions"][dim]["unmapped_structured_values_train"]
                                                             for dim in ("fit", "length")}
    write_outputs(ev, audit, patterns, d)
    print({dim: {r["label"]: r["recommendation"] for r in audit["recommendations"][dim]} for dim in ("fit", "length")},
          "leakage =", audit["leakage"]["parent_leakage"])


if __name__ == "__main__":
    main()
