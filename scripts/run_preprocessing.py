"""CLI: python scripts/run_preprocessing.py --input X.jsonl --support-dir DIR --output-dir data/processed"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cago.config.settings import SPLIT_RATIOS, SPLIT_SEED  # noqa: E402
from cago.preprocessing.run import run  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="CAGO data preprocessor v1")
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--support-dir", required=True, type=Path)
    ap.add_argument("--output-dir", default=Path("data/processed"), type=Path)
    ap.add_argument("--seed", default=SPLIT_SEED, type=int)
    ap.add_argument("--ratios", default=SPLIT_RATIOS, type=float, nargs=3, metavar=("TRAIN", "VAL", "TEST"))
    a = ap.parse_args()
    r = run(a.input, a.support_dir, a.output_dir, a.seed, tuple(a.ratios))
    c = r["audit"]["counts"]
    print(f"garments={c['garments']} components={c['components']} materials={c['material_occurrences']} "
          f"malformed={c['malformed_json_lines']} -> {a.output_dir}")


if __name__ == "__main__":
    main()
