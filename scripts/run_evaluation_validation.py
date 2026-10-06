"""CLI: python scripts/run_evaluation_validation.py --processed-dir data/processed [--n-garments 600] [--seed 1]"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cago.benchmark.audit import questionable_flags, render_validation_md  # noqa: E402
from cago.benchmark.intent_validation import run_intent_validation  # noqa: E402
from cago.benchmark.perturbations import load_eval_garments  # noqa: E402
from cago.benchmark.plausibility_validation import run_plausibility_validation  # noqa: E402
from cago.generation.support_tables import build_support_tables  # noqa: E402
from cago.requirements.validation import RequirementContext  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="CAGO evaluation validation (perturbations, intent experiments)")
    ap.add_argument("--processed-dir", default=Path("data/processed"), type=Path)
    ap.add_argument("--n-garments", default=600, type=int, help="TEST garments sampled (one per parent product)")
    ap.add_argument("--seed", default=1, type=int)
    ap.add_argument("--n-bootstrap", default=1000, type=int)
    a = ap.parse_args()
    d = a.processed_dir
    rep = pd.read_parquet(d / "garment_representation.parquet")
    ctx = RequirementContext.from_processed(d)
    support = build_support_tables(rep)                                    # TRAIN only
    vocab_doc = json.loads((d / "ml_material_vocabulary.json").read_text(encoding="utf-8"))
    vocab = [t for t in vocab_doc["tokens"] if t not in ("PAD", "OTHER")]
    garments = load_eval_garments(rep, "test", n=a.n_garments, seed=a.seed)
    test_ids = {g.garment_id for g in garments}
    train_ids = set(rep.loc[rep["split"] == "train", "garment_id"])
    pl, _ = run_plausibility_validation(garments, support, vocab, ctx, a.seed, a.n_bootstrap)
    it = run_intent_validation(garments, vocab)
    audit = {"seed": a.seed, "n_bootstrap": a.n_bootstrap, "vocabulary_fit_split": vocab_doc["fit_split"],
             "leakage_checks": {"support_splits_used": list(support.splits_used), "support_n_train_garments": support.n_train_garments,
                                "eval_garments_in_train": len(test_ids & train_ids), "eval_split": "test"},
             "plausibility": pl, "intent": it, "questionable_behaviour": questionable_flags(pl, it)}
    (d / "evaluation_validation_audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    (d / "evaluation_validation_audit.md").write_text(render_validation_md(audit), encoding="utf-8")
    print({"test_garments": len(garments), "plausibility_rows": pl["n_rows"], "intent_cases": it["n_cases"], "intent_overall": it["overall"]})


if __name__ == "__main__":
    main()
