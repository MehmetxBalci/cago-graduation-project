"""Reproduction audit for the baseline Oracle: computed counts vs published counts (never forced)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from cago.oracle.config import PUBLISHED_COUNTS, PUBLISHED_N

RULE_COLS = {"SR1": "sr1_violation", "SR2": "sr2_violation", "SR3": "sr3_violation",
             "SR4": "sr4_violation", "SR5": "sr5_violation", "ANY": "any_violation"}


def build_oracle_audit(res: pd.DataFrame) -> dict[str, Any]:
    n = len(res)
    rows = {}
    for k, col in RULE_COLS.items():
        cnt = int(res[col].sum())
        pub = PUBLISHED_COUNTS[k]
        rows[k] = {"computed": cnt, "computed_share_pct": round(100 * cnt / n, 2) if n else None,
                   "published": pub, "published_share_pct": round(100 * pub / PUBLISHED_N, 2),
                   "diff": cnt - pub, "match": cnt == pub}
    return {
        "n_garments": n, "published_n": PUBLISHED_N, "n_matches_published": n == PUBLISHED_N,
        "all_counts_match": n == PUBLISHED_N and all(r["match"] for r in rows.values()),
        "counts": rows,
        "violation_count_distribution": {str(k): int(v) for k, v in res["violation_count"].value_counts().sort_index().items()},
        "sr1_reason_counts": {str(k): int(v) for k, v in res["sr1_reason"].value_counts().items()},
        "readable_component_source": {str(k): int(v) for k, v in
                                      res["readable_component_source"].fillna("<none>").value_counts().items()},
        "sr5_surface_source": {str(k): int(v) for k, v in res["sr5_surface_source"].fillna("<none>").value_counts().items()},
        "note": "violation_count = number of triggered baseline rule indicators; not a circularity or recyclability score.",
    }


def render_oracle_markdown(a: dict[str, Any]) -> str:
    L = ["# CAGO Oracle v1 reproduction audit (baseline SR1-SR5)", "",
         f"Garments evaluated: {a['n_garments']} (published: {a['published_n']})", "",
         "| rule | computed | % | published | % | diff | match |", "|---|---|---|---|---|---|---|"]
    for k, r in a["counts"].items():
        L.append(f"| {k} | {r['computed']} | {r['computed_share_pct']} | {r['published']} | "
                 f"{r['published_share_pct']} | {r['diff']} | {'yes' if r['match'] else '**NO**'} |")
    L += ["", f"All counts match published: **{a['all_counts_match']}**", "", "## violation_count distribution", "",
          "| violations | garments |", "|---|---|"] + [f"| {k} | {v} |" for k, v in a["violation_count_distribution"].items()]
    for title, key in (("SR1 reasons", "sr1_reason_counts"), ("Readable component source", "readable_component_source"),
                       ("SR5 surface reference source", "sr5_surface_source")):
        L += ["", f"## {title}", "", "| value | n |", "|---|---|"] + [f"| {k} | {v} |" for k, v in a[key].items()]
    L += ["", a["note"], ""]
    return "\n".join(L)


def write_oracle_reports(res: pd.DataFrame, out_dir: Path) -> dict[str, Any]:
    out_dir = Path(out_dir)
    audit = build_oracle_audit(res)
    (out_dir / "oracle_audit_report.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    (out_dir / "oracle_audit_report.md").write_text(render_oracle_markdown(audit), encoding="utf-8")
    return audit
