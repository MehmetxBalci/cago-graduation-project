"""CLI: python scripts/run_sorting_aware_generator.py --processed-dir data/processed  (VAL development requests only)"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cago.benchmark.sorting_aware_requests import assert_dev_only, build_val_requests, dev_view  # noqa: E402
from cago.generation.baseline import GenerationConfig  # noqa: E402
from cago.generation.support_tables import build_support_tables  # noqa: E402
from cago.generation_sorting.audit import aggregate_traces, render_generator_md  # noqa: E402
from cago.generation_sorting.config import MODE_CONFIGS, NONDOMINATED_LOCAL, STRICT_SORTING, SortingAwareGenerationConfig  # noqa: E402
from cago.generation_sorting.generator import generate_sorting_aware  # noqa: E402
from cago.requirements.validation import RequirementContext, validate_request  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Sorting-aware generator audit")
    ap.add_argument("--processed-dir", default=Path("data/processed"), type=Path)
    ap.add_argument("--seed", default=0, type=int)
    ap.add_argument("--stride", default=5, type=int, help="audit every k-th VAL request")
    a = ap.parse_args()
    d = a.processed_dir
    rep = dev_view(pd.read_parquet(d / "garment_representation.parquet"))
    assert_dev_only(rep)
    ctx = RequirementContext.from_processed(d)
    support = build_support_tables(rep)
    reqs = build_val_requests(rep, support, a.seed)[::a.stride]
    policies: dict = {}
    deterministic, budget_ok = True, True
    for policy in (STRICT_SORTING, NONDOMINATED_LOCAL):
        cfg = SortingAwareGenerationConfig(seed=a.seed, policy=policy, **MODE_CONFIGS["B3"])
        results = []
        for rq in reqs:
            v = validate_request(rq["raw"], ctx)
            if not v.ok:
                continue
            r1 = generate_sorting_aware(v.request, rep, support, ctx, cfg)
            r2 = generate_sorting_aware(v.request, rep, support, ctx, cfg)
            deterministic &= [c["candidate_id"] for c in r1["candidates"]] == [c["candidate_id"] for c in r2["candidates"]] and \
                [c["components"] for c in r1["candidates"]] == [c["components"] for c in r2["candidates"]]
            budget_ok &= r1["attempts"] <= cfg.n_templates * cfg.candidates_per_template * cfg.max_proposal_attempts
            budget_ok &= all(len(c["repair_trace"]) <= cfg.max_repair_steps * cfg.max_repair_proposals_per_step for c in r1["candidates"])
            results.append(r1)
        tot = Counter()
        for r in results:
            tot.update(r["search"])
        ex = [{"candidate_id": c["candidate_id"], "trace": [{k: v for k, v in s.items() if k != "entries"} for s in c["repair_trace"]]}
              for r in results for c in r["candidates"] if c["repair_trace"]][:5]
        policies[f"B3 / {policy}"] = {"traces": aggregate_traces(results, support, cfg), "search_totals": dict(sorted(tot.items())), "examples": ex}
    audit = {"development_splits": ["train", "val"], "test_rows_in_working_set": 0, "support_splits_used": list(support.splits_used),
             "n_requests": len(reqs), "config": {k: v for k, v in asdict(SortingAwareGenerationConfig(seed=a.seed, **MODE_CONFIGS["B3"])).items() if k != "mutation_settings"},
             "determinism_identical": deterministic, "budget_check": budget_ok,
             "sr4_note": "SR4 (colour == 'black') is immutable in Generator B V1 because colour is not mutated; it is counted as 'sr4_immutable_violation', never as an unresolved repairable rule.",
             "policies": policies}
    (d / "sorting_aware_generator_audit.json").write_text(json.dumps(audit, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (d / "sorting_aware_generator_audit.md").write_text(render_generator_md(audit), encoding="utf-8")
    print({"requests": len(reqs), "deterministic": deterministic, "budget_ok": budget_ok,
           "policies": {k: (v["traces"]["candidates"], v["traces"]["candidates_with_accepted_repair"]) for k, v in policies.items()}})


if __name__ == "__main__":
    main()
