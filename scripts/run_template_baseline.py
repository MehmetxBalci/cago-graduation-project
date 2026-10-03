"""CLI: python scripts/run_template_baseline.py --processed-dir data/processed [--seed 42] [--n-templates 10]
[--per-template 5] [--request-json requests.json] [--write-candidates out.jsonl]"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cago.generation.audit import audit_request, render_markdown  # noqa: E402
from cago.generation.baseline import GenerationConfig, candidates_hash, generate_baseline  # noqa: E402
from cago.generation.support_tables import build_support_tables  # noqa: E402
from cago.requirements.validation import RequirementContext, validate_request  # noqa: E402

DEFAULT_REQUESTS = [
    {"target_segment": "women", "detail_category": "trousers", "forbidden_materials": ["polyester"],
     "preferred_dominant_material": "linen", "stretch": "low", "breathability": "high", "fit": "relaxed", "length_cut": "long"},
    {"target_segment": "men", "detail_category": "tshirt_polo", "moisture_wicking": True, "stretch": "low"},
    {"target_segment": "women", "detail_category": "dresses"},
    {"target_segment": "men", "detail_category": "outerwear_jacket", "water_repellent": True,
     "forbidden_materials": ["down", "feather"]},
    {"target_segment": "kids", "detail_category": "sweatshirt_hoodie", "forbidden_materials": ["acrylic"],
     "thermal_warmth": "heavy"},
    {"target_segment": "men", "detail_category": "set", "forbidden_materials": ["cotton", "polyester"]},   # forces repairs
    {"target_segment": "baby", "detail_category": "trousers"},      # tiny pool: edge case
]


def main() -> None:
    ap = argparse.ArgumentParser(description="CAGO template baseline generator v1")
    ap.add_argument("--processed-dir", default=Path("data/processed"), type=Path)
    ap.add_argument("--seed", default=42, type=int)
    ap.add_argument("--n-templates", default=10, type=int)
    ap.add_argument("--per-template", default=5, type=int)
    ap.add_argument("--request-json", default=None, type=Path, help="JSON list of raw requests")
    ap.add_argument("--write-candidates", default=None, type=Path, help="optional JSONL dump (off by default)")
    a = ap.parse_args()
    d = a.processed_dir

    rep = pd.read_parquet(d / "garment_representation.parquet")
    ctx = RequirementContext.from_processed(d)
    support = build_support_tables(rep)
    cfg = GenerationConfig(n_templates=a.n_templates, mutations_per_template=a.per_template, seed=a.seed)
    raw = json.loads(a.request_json.read_text(encoding="utf-8")) if a.request_json else DEFAULT_REQUESTS

    audits, edge, dump = [], [], []
    for r in raw:
        v = validate_request(r, ctx)
        if not v.ok:
            edge.append(f"request {r} rejected by validation: {[e.code for e in v.errors]}")
            continue
        res = generate_baseline(v.request, rep, support, ctx, cfg)
        again = generate_baseline(v.request, rep, support, ctx, cfg)
        au = audit_request(res, rerun_hash=candidates_hash(again["candidates"]))
        audits.append(au)
        q = f"{r['target_segment']}/{r['detail_category']}"
        if au["template_pool"]["pool_smaller_than_requested"]:
            edge.append(f"{q}: only {au['template_pool']['selected']} templates available (requested {cfg.n_templates})")
        if au["generation"]["failed_templates_unrepairable"]:
            edge.append(f"{q}: {len(au['generation']['failed_templates_unrepairable'])} templates had no admissible "
                        "replacement for a forbidden material")
        if au["generation"]["candidates_generated"] < au["generation"]["candidates_requested"]:
            edge.append(f"{q}: {au['generation']['candidates_generated']}/{au['generation']['candidates_requested']} candidates "
                        f"generated; rejections {au['generation']['rejected']}")
        dump += res["candidates"]
    t_total = sum(x["template_pool"]["train_garments_in_cell"] for x in audits)
    audit = {"config": {**json.loads(json.dumps(cfg.__dict__, default=lambda o: o.__dict__))},
             "support_tables": support.summary(),
             "leakage": {"templates_not_from_train": sum(not x["hard_constraints"]["all_templates_from_train"] for x in audits),
                         "support_splits_used": list(support.splits_used)},
             "train_garments_in_requested_cells": t_total, "requests": audits, "edge_cases": edge}
    (d / "template_baseline_audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    (d / "template_baseline_audit.md").write_text(render_markdown(audit), encoding="utf-8")
    if a.write_candidates:
        a.write_candidates.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in dump), encoding="utf-8")
    print({"requests": len(audits), "candidates": sum(x["generation"]["candidates_generated"] for x in audits),
           "edge_cases": len(edge)})


if __name__ == "__main__":
    main()
