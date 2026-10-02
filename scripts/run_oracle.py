"""CLI: python scripts/run_oracle.py --processed-dir data/processed [--output-dir data/processed]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cago.oracle.audit import write_oracle_reports  # noqa: E402
from cago.oracle.engine import run_oracle  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="CAGO Oracle v1 (baseline SR1-SR5)")
    ap.add_argument("--processed-dir", default=Path("data/processed"), type=Path)
    ap.add_argument("--output-dir", default=None, type=Path)
    a = ap.parse_args()
    out = a.output_dir or a.processed_dir
    out.mkdir(parents=True, exist_ok=True)
    res = run_oracle(a.processed_dir)
    res.to_parquet(out / "oracle_results.parquet", index=False)
    audit = write_oracle_reports(res, out)
    print({k: v["computed"] for k, v in audit["counts"].items()}, "all_match =", audit["all_counts_match"])


if __name__ == "__main__":
    main()
