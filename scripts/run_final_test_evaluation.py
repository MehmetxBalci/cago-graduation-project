"""Final held-out TEST evaluation: frozen Generator A vs frozen Generator B3.

  python scripts/run_final_test_evaluation.py --freeze                # write the frozen manifest (no TEST results are read)
  python scripts/run_final_test_evaluation.py --run                   # verify manifest, run the TEST evaluation, write reports
  python scripts/run_final_test_evaluation.py --dry-run-val           # pipeline check on VAL requests (never writes into data/processed)
  python scripts/run_final_test_evaluation.py --reproduce-request ID  # re-run one request and print its selected designs

Nothing here selects parameters: all values come from the frozen manifest (TEST run) or the V1 defaults (VAL dry run).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cago.benchmark.final_test_manifest import build_manifest, manifest_digest, verify_manifest  # noqa: E402
from cago.benchmark.final_test_report import assemble_report, render_markdown, validate_report_schema  # noqa: E402
from cago.benchmark.final_test_requests import (assert_split_integrity, build_final_test_requests, coverage_report, eligibility_audit,  # noqa: E402
                                                generation_view)
from cago.benchmark.final_test_runner import reproduce_request, run_requests  # noqa: E402
from cago.benchmark.sorting_aware_comparison import default_variants  # noqa: E402
from cago.evaluation.config import EvaluationConfig  # noqa: E402
from cago.generation.support_tables import build_support_tables  # noqa: E402
from cago.requirements.validation import RequirementContext  # noqa: E402

MANIFEST = ROOT / "configs" / "final_test_evaluation_manifest.json"
A, B3 = "A_baseline", "B3_proposal_plus_repair"


def pick_examples(raw) -> list[tuple[str, str]]:
    ra, rb = raw["recs"][A], raw["recs"][B3]
    pairs = []
    for i in ra:
        a, b = ra[i]["stages"]["B_hard_valid_candidates"], rb[i]["stages"]["B_hard_valid_candidates"]
        if a and b:
            pairs.append((b["vc_mean"] - a["vc_mean"], i))
    pairs.sort()
    ex = []
    if pairs:
        ex.append(("largest_B3_improvement_pool_violation", pairs[0][1]))
        if pairs[-1][0] > 1e-9:
            ex.append(("largest_A_advantage_pool_violation", pairs[-1][1]))
    small = sorted(i for i in ra if ra[i]["pool"] < 5 and ra[i]["hard_valid"] and rb[i]["hard_valid"])
    if small:
        ex.append(("small_template_pool", small[0]))
    return ex


def main() -> None:
    ap = argparse.ArgumentParser(description="CAGO final TEST evaluation (A vs B3)")
    ap.add_argument("--processed-dir", default=ROOT / "data" / "processed", type=Path)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--freeze", action="store_true")
    g.add_argument("--run", action="store_true")
    g.add_argument("--dry-run-val", action="store_true")
    g.add_argument("--reproduce-request", default=None)
    ap.add_argument("--force-refreeze", action="store_true", help="overwrite an existing manifest (only legitimate before any TEST result exists)")
    ap.add_argument("--reason", default=None, help="required with --force-refreeze")
    ap.add_argument("--cache-dir", default=None, type=Path, help="per-request result cache: an interrupted run resumes with identical results")
    ap.add_argument("--workers", default=1, type=int, help="process-pool size (results are independent of this value)")
    ap.add_argument("--max-requests", default=None, type=int, help="dry-run only")
    ap.add_argument("--output-dir", default=None, type=Path, help="dry-run only")
    ap.add_argument("--split", default="test", choices=("test", "val"), help="used by --reproduce-request")
    a = ap.parse_args()
    d = a.processed_dir

    if a.freeze:
        if MANIFEST.exists() and not a.force_refreeze:
            sys.exit(f"manifest already exists: {MANIFEST} (frozen); refusing to overwrite")
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        m = build_manifest(ROOT, d)
        if MANIFEST.exists():
            if not a.reason:
                sys.exit("--force-refreeze requires --reason")
            old = json.loads(MANIFEST.read_text(encoding="utf-8"))
            m["refreeze_history"] = old.get("refreeze_history", []) + [{"previous_digest": manifest_digest(old), "reason": a.reason,
                                                                       "test_results_existed": (d / "final_test_evaluation_report.json").exists()}]
        MANIFEST.write_text(json.dumps(m, indent=1, ensure_ascii=False), encoding="utf-8")
        print({"manifest": str(MANIFEST), "digest": manifest_digest(m), "frozen_files": len(m["frozen_files"]), "new_code_files": len(m["new_evaluation_code"])})
        return

    eval_split = "val" if a.dry_run_val else (a.split if a.reproduce_request else "test")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else None
    if a.run:
        if manifest is None:
            sys.exit("no frozen manifest: run --freeze first")
        ver = verify_manifest(manifest, ROOT, d)
        if not ver["ok"]:
            sys.exit("frozen manifest verification FAILED (no TEST evaluation is run): " + json.dumps(ver["mismatches"], indent=1))
    else:
        ver = verify_manifest(manifest, ROOT, d) if manifest else {"ok": None, "mismatches": {}, "manifest_digest": None}
    cond = (manifest or {}).get("comparison_conditions", {"n_templates": 10, "candidates_per_template": 8, "seed": 0})
    rc = (manifest or {}).get("request_construction", {"k_per_type": 3})
    bs = (manifest or {}).get("analysis_plan", {"bootstrap": {"n_resamples": 2000, "seed": 0}})["bootstrap"]
    n_t, per_t, seed, k = cond["n_templates"], cond["candidates_per_template"], cond["seed"], rc["k_per_type"]

    rep = pd.read_parquet(d / "garment_representation.parquet")
    sm = pd.read_parquet(d / "split_mapping.parquet")
    integrity = assert_split_integrity(rep, sm)                      # raises on any parent/garment leakage
    rep_gen = generation_view(rep)                                   # TRAIN rows only: generators never see VAL or TEST
    support = build_support_tables(rep_gen)
    assert support.splits_used == ("train",) and support.n_train_garments == len(rep_gen)
    ctx = RequirementContext.from_processed(d)
    ecfg = EvaluationConfig()
    allv = default_variants(n_t, per_t, seed, policy_variants=False)
    variants = {A: allv[A], B3: allv[B3]}
    requests = build_final_test_requests(rep, support, eval_split, seed, k)

    if a.reproduce_request:
        rq = next((r for r in requests if r["request_id"] == a.reproduce_request), None)
        if rq is None:
            sys.exit(f"unknown request id; {len(requests)} requests exist for split {eval_split}")
        print(json.dumps(reproduce_request(rq, rep_gen, ctx, support, variants, ecfg), indent=1, default=str))
        return

    if a.max_requests:
        requests = requests[::max(1, len(requests) // a.max_requests)][:a.max_requests]
    tag = "val" if a.dry_run_val else (manifest_digest(manifest)[:12] if manifest else "none")
    raw = run_requests(requests, rep_gen, ctx, support, variants, ecfg, rerun_check=10, cache_dir=a.cache_dir, cache_tag=tag,
                       workers=a.workers, example_variant=B3, progress=lambda i, n: print(f"  {i}/{n} requests", flush=True))
    print(f"requests loaded from cache: {raw['requests_loaded_from_cache']}", flush=True)
    cov = coverage_report(requests, eligibility_audit(rep, eval_split))
    mi = {"digest": manifest_digest(manifest) if manifest else None, "path": "configs/final_test_evaluation_manifest.json" if manifest else None,
          "verification_ok": ver["ok"], "new_code_changed_since_freeze": ver["mismatches"].get("new_code_changed_since_freeze", []),
          "evaluation_split": eval_split, "dry_run": bool(a.dry_run_val), "refreeze_history": (manifest or {}).get("refreeze_history", []),
          "execution": {"workers": a.workers, "requests_loaded_from_cache": raw["requests_loaded_from_cache"],
                        "note": "per-request computation is a pure function of the request; worker count and caching do not change results"}}
    integ = {"split_integrity": integrity, "generator_input_splits": sorted(rep_gen["split"].unique()), "support_splits_used": list(support.splits_used),
             "support_train_garments": support.n_train_garments, "evaluation_split": eval_split,
             "templates_all_from_train": all(t in set(rep_gen["garment_id"]) for r in raw["recs"].values() for x in r.values() for t in x["template_ids"])}
    by_id = {r["request_id"]: r for r in requests}
    examples = {"reproduction_command": "python scripts/run_final_test_evaluation.py --reproduce-request '<request_id>'",
                "selected_requests": {lab: reproduce_request(by_id[i], rep_gen, ctx, support, variants, ecfg) for lab, i in pick_examples(raw)}}
    report = assemble_report(raw, cov, integ, mi, bs["n_resamples"], bs["seed"], ecfg, A, B3, examples)
    problems = validate_report_schema(report)
    if problems:
        sys.exit("report schema problems: " + "; ".join(problems))
    out = (a.output_dir or Path("dryrun_output")) if a.dry_run_val else d
    out.mkdir(parents=True, exist_ok=True)
    stem = "final_test_evaluation_report"
    (out / f"{stem}.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (out / f"{stem}.md").write_text(render_markdown(report), encoding="utf-8")
    p = {o["metric"] + "@" + o["stage"][:1]: (o["summary"].get("mean_diff"), o["summary"]["n_paired"]) for o in report["primary_outcomes"]}
    print({"split": eval_split, "requests": len(requests), "run": report["conditions"]["requests_run"], "determinism": raw["determinism"]["all_identical"],
           "primary_mean_diffs": p, "out": str(out)})


if __name__ == "__main__":
    main()
