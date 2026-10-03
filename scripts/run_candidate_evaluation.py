"""CLI: python scripts/run_candidate_evaluation.py --processed-dir data/processed [--seed 42] [--request-json file]"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cago.evaluation.audit import audit_request, render_md  # noqa: E402
from cago.evaluation.config import EvaluationConfig  # noqa: E402
from cago.evaluation.pipeline import evaluate_and_select  # noqa: E402
from cago.generation.baseline import GenerationConfig  # noqa: E402
from cago.generation.support_tables import build_support_tables  # noqa: E402
from cago.requirements.validation import RequirementContext, validate_request  # noqa: E402

DEFAULT_REQUESTS = [
    {"target_segment": "women", "detail_category": "trousers", "forbidden_materials": ["polyester"],
     "preferred_dominant_material": "linen", "stretch": "low", "breathability": "high", "fit": "relaxed", "length_cut": "long"},
    {"target_segment": "men", "detail_category": "tshirt_polo", "moisture_wicking": True, "stretch": "low", "colour": "black"},
    {"target_segment": "women", "detail_category": "dresses"},                                  # no preferences: intent null
    {"target_segment": "women", "detail_category": "dresses", "thermal_warmth": "standard", "fit": "slim", "length_cut": "long"},
    {"target_segment": "men", "detail_category": "outerwear_jacket", "water_repellent": True, "durability_wear": "reinforced",
     "forbidden_materials": ["down", "feather"]},
    {"target_segment": "kids", "detail_category": "sweatshirt_hoodie", "forbidden_materials": ["acrylic"],
     "thermal_warmth": "heavy", "fit": "oversized"},
    {"target_segment": "men", "detail_category": "set", "forbidden_materials": ["cotton", "polyester"],
     "preferred_dominant_material": "nylon"},
    {"target_segment": "baby", "detail_category": "trousers", "stretch": "low"},
]


def main() -> None:
    ap = argparse.ArgumentParser(description="CAGO candidate evaluation + Pareto selection v1")
    ap.add_argument("--processed-dir", default=Path("data/processed"), type=Path)
    ap.add_argument("--seed", default=42, type=int)
    ap.add_argument("--n-templates", default=10, type=int)
    ap.add_argument("--per-template", default=8, type=int)
    ap.add_argument("--request-json", default=None, type=Path)
    a = ap.parse_args()
    d = a.processed_dir
    rep = pd.read_parquet(d / "garment_representation.parquet")
    ctx = RequirementContext.from_processed(d)
    support = build_support_tables(rep)
    gcfg = GenerationConfig(n_templates=a.n_templates, mutations_per_template=a.per_template, seed=a.seed)
    cfg = EvaluationConfig()
    raw = json.loads(a.request_json.read_text(encoding="utf-8")) if a.request_json else DEFAULT_REQUESTS
    audits, edge = [], []
    for r in raw:
        v = validate_request(r, ctx)
        q = f"{r.get('target_segment')}/{r.get('detail_category')}"
        if not v.ok:
            edge.append(f"{q}: request rejected by validation {[e.code for e in v.errors]}")
            continue
        res1 = evaluate_and_select(v.request, rep, support, ctx, gcfg, cfg)
        res2 = evaluate_and_select(v.request, rep, support, ctx, gcfg, cfg)
        au = audit_request(res1, res2["digest"], cfg.plausibility_drop_substantial)
        audits.append(au)
        for w in v.request["warnings"]:
            if w["code"] == "control_not_available":
                edge.append(f"{q}: preference ignored by capabilities: {w['fields']}")
        if au["hard_valid"] == 0:
            edge.append(f"{q}: no hard-valid candidates ({au['generated']} generated)")
        if au["pareto"]["front_size"] == 1:
            edge.append(f"{q}: Pareto front contains a single candidate")
        if au["unscorable_preferences"]:
            edge.append(f"{q}: unscorable preferences {au['unscorable_preferences']}")
        if au["pareto"].get("intent_dimension") != "active" and au["hard_valid"]:
            edge.append(f"{q}: intent objective dropped from Pareto ({au['pareto']['intent_dimension']})")
        fs = au["tradeoff_flags"]["selected"]
        for k, ids in fs.items():
            if ids:
                edge.append(f"{q}: selected designs with {k}: {len(ids)}")
        if au["tradeoff_flags"]["pareto_front"]["plausibility_falls_substantially"]:
            edge.append(f"{q}: {au['tradeoff_flags']['pareto_front']['plausibility_falls_substantially']} Pareto candidates fall "
                        f">{au['tradeoff_flags']['plausibility_drop_threshold_pts']} plausibility points below their template")
    audit = {"seed": a.seed, "generation_config": {"n_templates": a.n_templates, "per_template": a.per_template},
             "support_splits_used": list(support.splits_used), "requests": audits, "edge_cases": edge}
    (d / "candidate_evaluation_audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    (d / "candidate_evaluation_audit.md").write_text(render_md(audit), encoding="utf-8")
    print({"requests": len(audits), "hard_valid": sum(x["hard_valid"] for x in audits),
           "front_sizes": [x["pareto"]["front_size"] for x in audits], "deterministic": all(x["deterministic_rerun_digest_equal"] for x in audits)})


if __name__ == "__main__":
    main()
