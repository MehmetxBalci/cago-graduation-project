"""Audit statistics (all computed from data) and report writers."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from cago.config.materials import MANUAL_OVERRIDES
from cago.config.settings import (PCT_TOLERANCE_HIGH, PCT_TOLERANCE_LOW, REFERENCE_AUDIT,
                                  SUPPORT_COMPONENT_TABLE)


def _vc(s: pd.Series, top: int | None = None) -> dict[str, int]:
    vc = s.fillna("<NULL>").astype(str).value_counts()
    return {str(k): int(v) for k, v in (vc.head(top) if top else vc).items()}


def _null_counts(df: pd.DataFrame) -> dict[str, dict[str, int]]:
    out = {}
    for col in df.columns:
        if col in ("missing_fields", "missing_required_fields"):  # null == nothing missing
            continue
        s = df[col]
        n_null = int(s.isna().sum()) if s.dtype != object else int(s.map(lambda v: v is None or (isinstance(v, float) and np.isnan(v))).sum())
        n_empty = int(s.map(lambda v: isinstance(v, str) and not v.strip()).sum()) if s.dtype == object or str(s.dtype) in ("str", "string") else 0
        if n_null or n_empty:
            out[col] = {"null": n_null, "empty_string": n_empty}
    return out


def _component_support_check(components: pd.DataFrame, support_dir: Path) -> dict[str, Any]:
    path = Path(support_dir) / SUPPORT_COMPONENT_TABLE
    if not path.exists():
        return {"available": False}
    with path.open(encoding="utf-8-sig", newline="") as fh:
        known = {(r["component_name_norm"], r["component_class"]) for r in csv.DictReader(fh)}
    pairs = components.groupby(["component_name_normalized", "component_class"], dropna=False).size()
    missing = {f"{a} | {b}": int(n) for (a, b), n in pairs.items() if (a, b) not in known}
    return {"available": True, "distinct_pairs_in_data": int(len(pairs)),
            "pairs_not_in_support_table": missing}


def _unmapped_table(cm: pd.DataFrame) -> pd.DataFrame:
    um = cm[cm["material_mapping_status"].isin(["unmapped", "missing_material"])]
    if um.empty:
        return pd.DataFrame(columns=["material_raw", "material_mapping_status", "n_occurrences",
                                     "n_components", "n_garments"])
    g = um.groupby(["material_raw", "material_mapping_status"], dropna=False).agg(
        n_occurrences=("component_id", "size"), n_components=("component_id", "nunique"),
        n_garments=("garment_id", "nunique")).reset_index()
    return g.sort_values(["n_occurrences", "material_raw"], ascending=[False, True]).reset_index(drop=True)


def build_audit(tables: dict[str, Any], split_map: pd.DataFrame, support_dir: Path,
                input_path: Path, split_cfg: dict[str, Any]) -> tuple[dict[str, Any], pd.DataFrame]:
    g, c, m = tables["garments"], tables["components"], tables["component_materials"]
    n_g = len(g)
    black = int(g["is_exact_black"].sum())
    unmapped = _unmapped_table(m)

    mat_rows = (m.groupby(["material_raw", "material_canonical", "material_family", "material_mapping_status"],
                          dropna=False).size().reset_index(name="n").sort_values("n", ascending=False))
    parents = g["parent_product_id"].dropna()
    pid_stats = g.groupby("parent_product_id").agg(n_variants=("garment_id", "size"),
                                                  n_urls=("url", "nunique"),
                                                  n_brand_region=("brand", lambda s: 0))
    multi_ctx = g.groupby("parent_product_id").apply(
        lambda d: d[["brand", "region"]].drop_duplicates().shape[0] > 1, include_groups=False)

    st = c["validation_status"].value_counts()
    flag_vs_calc = pd.crosstab(c["pct_sum_flag_source"].fillna("<NULL>"), c["pct_valid"])
    sm = split_map.merge(g[["garment_id"]], on="garment_id")
    split_rows = sm["split"].value_counts()
    split_parents = sm.dropna(subset=["parent_product_id"]).groupby("split")["parent_product_id"].nunique()

    mapped_status = _vc(m["material_mapping_status"])
    comp_stat = {
        "pct_sum_calculated_min": float(c["pct_sum_calculated"].min()),
        "pct_sum_calculated_max": float(c["pct_sum_calculated"].max()),
    }
    ref = {}
    computed = {"garments": n_g, "unique_parent_products": int(parents.nunique()),
                "exact_black_variants": black, "components": len(c), "material_occurrences": len(m)}
    for k, (val, tol) in REFERENCE_AUDIT.items():
        ref[k] = {"computed": computed[k], "previous_audit": val, "abs_tolerance": tol,
                  "diff": computed[k] - val, "within_tolerance": abs(computed[k] - val) <= tol}

    audit: dict[str, Any] = {
        "input_file": str(input_path),
        "counts": {
            "garments": n_g, "valid_json_records": tables["n_valid_json"],
            "malformed_json_lines": len(tables["malformed"]), "blank_lines": tables["blank_lines"],
            "unique_parent_products": int(parents.nunique()), "components": len(c),
            "material_occurrences": len(m), **tables["duplicate_stats"],
        },
        "malformed_json_examples": [{"row": r, "error": e} for r, e in tables["malformed"][:20]],
        "reference_comparison": ref,
        "parent_product_id": {
            "ids_with_multiple_variants": int((pid_stats["n_variants"] > 1).sum()),
            "max_variants_per_parent": int(pid_stats["n_variants"].max()),
            "ids_spanning_multiple_urls": int((pid_stats["n_urls"] > 1).sum()),
            "ids_spanning_multiple_brand_region": int(multi_ctx.sum()),
        },
        "missing_values": {"garments": _null_counts(g.drop(columns=["all_colour_labels"])),
                           "components": _null_counts(c), "component_materials": _null_counts(m)},
        "garments_with_missing_required_fields": int(g["missing_required_fields"].notna().sum()),
        "distributions": {
            "brand": _vc(g["brand"]), "region": _vc(g["region"]), "gender_section": _vc(g["gender_section"]),
            "parent_category": _vc(g["parent_category"]), "detail_category": _vc(g["detail_category"]),
            "composition_assignment_type": _vc(g["composition_assignment_type"]),
            "components_per_garment": {str(k): int(v) for k, v in
                                       g["component_count"].value_counts().sort_index().items()},
            "component_class": _vc(c["component_class"]),
            "component_name_normalized_top30": _vc(c["component_name_normalized"], 30),
            "component_normalization_source": _vc(c["component_normalization_source"]),
            "materials_per_component": {str(k): int(v) for k, v in
                                        c["material_count"].value_counts().sort_index().items()},
        },
        "component_support_table_check": _component_support_check(c, support_dir),
        "materials": {
            "unique_material_raw": int(m["material_raw"].nunique()),
            "unique_material_canonical": int(m["material_canonical"].nunique()),
            "mapping_status_counts": mapped_status,
            "family_counts": _vc(m["material_family"]),
            "manual_overrides_configured": MANUAL_OVERRIDES,
            "manual_overrides_used": _vc(m.loc[m["material_mapping_status"] == "mapped_manual_override",
                                              "material_raw"]),
            "all_materials": [{"material_raw": r.material_raw, "material_canonical": r.material_canonical,
                               "material_family": r.material_family, "status": r.material_mapping_status,
                               "count": int(r.n)} for r in mat_rows.itertuples()],
            "unmapped": [{"material_raw": r.material_raw, "status": r.material_mapping_status,
                          "n_occurrences": int(r.n_occurrences), "n_garments": int(r.n_garments)}
                         for r in unmapped.itertuples()],
        },
        "percentage_validation": {
            "tolerance": [PCT_TOLERANCE_LOW, PCT_TOLERANCE_HIGH],
            "validation_status_counts": {k: int(v) for k, v in st.items()},
            "components_pct_valid": int(c["pct_valid"].sum()),
            "components_pct_invalid": int((~c["pct_valid"]).sum()),
            "zero_sum_components": int((c["validation_status"] == "zero_sum_component").sum()),
            "source_flag_vs_calculated_pct_valid": {str(k): {str(kk): int(vv) for kk, vv in row.items()}
                                                    for k, row in flag_vs_calc.iterrows()},
            "pct_sum_source_vs_calculated_mismatch_gt_0.01": int(
                ((c["pct_sum_source"] - c["pct_sum_calculated"]).abs() > 0.01).sum()),
            "garments_with_any_invalid_component": int((~g["all_components_pct_valid"]).sum()),
            "material_pct_status_counts": _vc(m["pct_status"]),
            **comp_stat,
            "out_of_tolerance_examples": c.loc[c["validation_status"] != "valid",
                                               ["component_id", "garment_id", "component_name_raw",
                                                "pct_sum_calculated", "validation_status"]].head(20)
                                          .to_dict("records"),
        },
        "recycled_content": {
            "material_rows_with_recycled_pct": int(m["recycled_pct"].notna().sum()),
            "material_rows_recycled_pct_null": int(m["recycled_pct"].isna().sum()),
            "garments_with_recycled_info": int(g["has_recycled_content_information"].sum()),
            "garments_with_recycled_info_pct": round(100 * g["has_recycled_content_information"].mean(), 3),
            "recycled_pct_zero_rows": int((m["recycled_pct"] == 0).sum()),
            "recycled_pct_greater_than_pct_rows": int((m["recycled_pct"] > m["pct"]).sum()),
            "recycled_pct_status_counts": _vc(m["recycled_pct_status"]),
        },
        "colours": {
            "raw_cardinality": int(g["variant_colour_raw"].nunique()),
            "normalized_cardinality": int(g["variant_colour_normalized"].nunique()),
            "exact_black_count": black,
            "exact_black_percentage": round(100 * black / n_g, 4) if n_g else None,
            "exact_black_raw_spellings": _vc(g.loc[g["is_exact_black"], "variant_colour_raw"]),
            "top_normalized_colours": _vc(g["variant_colour_normalized"], 20),
        },
        "split": {**split_cfg,
                  "rows": {k: int(v) for k, v in split_rows.items()},
                  "row_share": {k: round(float(v) / len(sm), 4) for k, v in split_rows.items()},
                  "parents": {k: int(v) for k, v in split_parents.items()},
                  "parent_leakage_count": int(split_map.dropna(subset=["parent_product_id"])
                                              .groupby("parent_product_id")["split"].nunique().gt(1).sum())},
    }
    return audit, unmapped


def _tbl(rows: list[list[Any]], headers: list[str]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]
    return "\n".join(out)


def _dist(d: dict[str, int], total: int | None = None, head: str = "value") -> str:
    return _tbl([[k, v] + ([f"{100 * v / total:.2f}%"] if total else []) for k, v in d.items()],
                [head, "n"] + (["%"] if total else []))


def render_markdown(a: dict[str, Any]) -> str:
    n, cnt = a["counts"]["garments"], a["counts"]
    L = ["# CAGO data audit report", "", f"Input: `{a['input_file']}`", "", "## Counts", "",
         _tbl([[k, v] for k, v in cnt.items()], ["metric", "value"]), ""]
    if a["malformed_json_examples"]:
        L += ["Malformed lines (first 20):", _tbl([[e["row"], e["error"]] for e in a["malformed_json_examples"]],
                                                   ["row", "error"]), ""]
    L += ["## Comparison with previous audit (sanity check only; processing was not altered)", "",
          _tbl([[k, v["computed"], v["previous_audit"], v["diff"], v["abs_tolerance"],
                 "yes" if v["within_tolerance"] else "**NO**"] for k, v in a["reference_comparison"].items()],
               ["metric", "computed", "previous", "diff", "abs tol", "within tol"]), ""]
    p = a["parent_product_id"]
    L += ["## parent_product_id", "", _tbl([[k, v] for k, v in p.items()], ["metric", "value"]), "",
          "## Missing values", "", f"Garments with >=1 missing required field: {a['garments_with_missing_required_fields']}", ""]
    for t, d in a["missing_values"].items():
        L += [f"**{t}**", _tbl([[k, v["null"], v["empty_string"]] for k, v in d.items()],
                               ["column", "null", "empty string"]) if d else "_none_", ""]
    D = a["distributions"]
    L += ["## Distributions", ""]
    for key in ("brand", "region", "gender_section", "parent_category", "composition_assignment_type"):
        L += [f"**{key}**", _dist(D[key], n, key), ""]
    L += ["**detail_category**", _dist(D["detail_category"], n, "detail_category"), "",
          "**components per garment**", _dist(D["components_per_garment"], None, "components"), "",
          "**component_class**", _dist(D["component_class"], cnt["components"], "class"), "",
          "**component_name_normalized (top 30)**", _dist(D["component_name_normalized_top30"], None, "name"), "",
          "**materials per component**", _dist(D["materials_per_component"], None, "materials"), "",
          "**component support-table check**", "```json",
          json.dumps(a["component_support_table_check"], indent=2, ensure_ascii=False), "```", ""]
    M = a["materials"]
    L += ["## Materials", "", f"Unique raw: {M['unique_material_raw']}; unique canonical: {M['unique_material_canonical']}", "",
          "**mapping status**", _dist(M["mapping_status_counts"], cnt["material_occurrences"], "status"), "",
          "**family**", _dist(M["family_counts"], cnt["material_occurrences"], "family"), "",
          "**all observed materials**",
          _tbl([[x["material_raw"], x["material_canonical"], x["material_family"], x["status"], x["count"]]
                for x in M["all_materials"]], ["raw", "canonical", "family", "status", "n"]), "",
          "**unmapped**", _tbl([[x["material_raw"], x["status"], x["n_occurrences"], x["n_garments"]]
                                for x in M["unmapped"]], ["raw", "status", "occurrences", "garments"])
          if M["unmapped"] else "_none_", ""]
    V = a["percentage_validation"]
    L += ["## Percentage validation", "", f"Tolerance: {V['tolerance'][0]} <= sum <= {V['tolerance'][1]}", "",
          _dist(V["validation_status_counts"], cnt["components"], "status"), "",
          _tbl([[k, v] for k, v in V.items() if isinstance(v, (int, float))], ["metric", "value"]), "",
          "**source pct_sum_flag vs calculated pct_valid**", "```json",
          json.dumps(V["source_flag_vs_calculated_pct_valid"], indent=2), "```", ""]
    if V["out_of_tolerance_examples"]:
        L += ["Non-valid examples (first 20):",
              _tbl([[e["component_id"], e["component_name_raw"], e["pct_sum_calculated"], e["validation_status"]]
                    for e in V["out_of_tolerance_examples"]], ["component_id", "name", "sum", "status"]), ""]
    R, C, S = a["recycled_content"], a["colours"], a["split"]
    L += ["## Recycled content", "", _tbl([[k, v] for k, v in R.items() if not isinstance(v, dict)],
                                         ["metric", "value"]), "",
          "## Colours", "", _tbl([[k, v] for k, v in C.items() if not isinstance(v, dict)], ["metric", "value"]), "",
          "**exact-black raw spellings**", _dist(C["exact_black_raw_spellings"], None, "raw"), "",
          "## Split (by parent_product_id)", "",
          _tbl([[k, v] for k, v in S.items() if not isinstance(v, dict)], ["setting", "value"]), "",
          _tbl([[sp, S["rows"].get(sp), S["row_share"].get(sp), S["parents"].get(sp)] for sp in S["rows"]],
               ["split", "garments", "row share", "parents"]), ""]
    return "\n".join(L)


def write_reports(audit: dict[str, Any], unmapped: pd.DataFrame, out_dir: Path) -> None:
    out_dir = Path(out_dir)
    (out_dir / "data_audit_report.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False, default=lambda o: None if o is None else str(o)),
        encoding="utf-8")
    (out_dir / "data_audit_report.md").write_text(render_markdown(audit), encoding="utf-8")
    unmapped.to_csv(out_dir / "unmapped_materials.csv", index=False, encoding="utf-8")
