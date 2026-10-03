"""CLI: python scripts/run_representation.py --processed-dir data/processed [--support-dir DIR] [--min-count N]"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cago.config.materials import FAMILY_BY_CANONICAL  # noqa: E402
from cago.preprocessing.materials import MaterialMapper  # noqa: E402
from cago.representation.audit import build_representation_audit, render_representation_markdown  # noqa: E402
from cago.representation.builder import build_representation, is_usable  # noqa: E402
from cago.representation.vocabulary import DEFAULT_MIN_COUNT, fit_vocabulary, mapping_table  # noqa: E402
from cago.requirements.capabilities import (CAPABILITIES_PATH, fit_length_support, generate_capabilities,  # noqa: E402
                                            load_capabilities, revise_capabilities, save_capabilities)


def main() -> None:
    ap = argparse.ArgumentParser(description="CAGO garment representation v1")
    ap.add_argument("--processed-dir", default=Path("data/processed"), type=Path)
    ap.add_argument("--support-dir", default=None, type=Path, help="adds source material aliases to the vocabulary file")
    ap.add_argument("--min-count", default=DEFAULT_MIN_COUNT, type=int)
    ap.add_argument("--capabilities", default=CAPABILITIES_PATH, type=Path)
    ap.add_argument("--no-capability-revision", action="store_true",
                    help="keep category_capabilities.json as is (default: disable fit/length controls lacking TRAIN support)")
    a = ap.parse_args()
    d = a.processed_dir

    g = pd.read_parquet(d / "garments.parquet")
    c = pd.read_parquet(d / "components.parquet")
    m = pd.read_parquet(d / "component_materials.parquet")
    sm = pd.read_parquet(d / "split_mapping.parquet")

    if not a.capabilities.exists():   # first run only: draft from dataset categories, then hand-editable
        cats = g.drop_duplicates("detail_category").set_index("detail_category")["parent_category"].to_dict()
        save_capabilities(generate_capabilities(cats, "derived from garments.parquet detail_category"), a.capabilities)
    caps = load_capabilities(a.capabilities)

    usable = c[[is_usable(s, p) for s, p in zip(c["validation_status"], c["pct_sum_calculated"])]]
    mat_rows = m[m["component_id"].isin(set(usable["component_id"]))][["garment_id", "material_canonical"]]
    aliases = MaterialMapper.from_support_dir(a.support_dir).label_to_canonical if a.support_dir else None
    vocab = fit_vocabulary(mat_rows, sm, a.min_count, FAMILY_BY_CANONICAL.keys(), aliases, usable)
    (d / "ml_material_vocabulary.json").write_text(json.dumps(vocab, indent=2, ensure_ascii=False), encoding="utf-8")
    mapping_table(vocab).to_csv(d / "material_to_ml_token.csv", index=False, encoding="utf-8")

    rep = build_representation(g, c, m, sm, vocab)
    rep.to_parquet(d / "garment_representation.parquet", index=False)
    if not a.no_capability_revision:
        caps, _ = revise_capabilities(caps, fit_length_support(rep))   # TRAIN-only support
        save_capabilities(caps, a.capabilities)
    shutil.copyfile(a.capabilities, d / "category_capabilities.json")
    audit = build_representation_audit(rep, vocab, caps, len(c), len(g))
    (d / "representation_audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    (d / "representation_audit.md").write_text(render_representation_markdown(audit), encoding="utf-8")
    print({"garments": audit["garments"], "active": audit["components"]["active"], "anomalous": audit["components"]["anomalous"],
           "vocab_size": vocab["vocabulary_size"], "leakage": audit["split"]["parent_leakage_count"]})


if __name__ == "__main__":
    main()
