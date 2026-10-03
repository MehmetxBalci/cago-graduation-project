"""Representation audit (all figures computed from data)."""
from __future__ import annotations

import json
from collections import Counter
from typing import Any

import pandas as pd

from cago.config.settings import PCT_TOLERANCE_HIGH, PCT_TOLERANCE_LOW
from cago.config.fit_length_v1 import CONTROL_LABEL_COLUMN, CONTROL_LABELS, FIT_LABELS_V1, LENGTH_LABELS_V1
from cago.representation.builder import fit_length_hash, representation_hash
from cago.representation.vocabulary import FIT_SPLIT, OTHER, token_reason
from cago.requirements.capabilities import REVIEW_CATEGORIES, coverage_report
from cago.requirements.properties import GarmentProfile, build_profile, stretch_bucket


def _vc(s: pd.Series) -> dict[str, int]:
    return {str(k): int(v) for k, v in s.fillna("<NULL>").value_counts().items()}


SPLITS = ("train", "val", "test")


def _pct(a: int, b: int) -> float | None:
    return round(100 * a / b, 3) if b else None


def fit_length_section(rep: pd.DataFrame, caps: dict[str, Any]) -> dict[str, Any]:
    """Fit/Length V1 audit: coverage, distributions, merges, unsupported/conflicts, enabled-control coverage."""
    out: dict[str, Any] = {"vocabulary": {"fit": list(FIT_LABELS_V1), "length": list(LENGTH_LABELS_V1)},
                           "capability_basis": caps.get("fit_length_v1", {}).get("basis"),
                           "labels_sha256": fit_length_hash(rep)}
    n = {sp: int((rep["split"] == sp).sum()) for sp in SPLITS}
    for dim, ctrl, labels, merges, unsup in (("fit", "fit", FIT_LABELS_V1, ("skinny->slim", "loose->relaxed"), None),
                                              ("length", "length_cut", LENGTH_LABELS_V1, (), "cropped")):
        lab = rep[f"{dim}_label"]
        d: dict[str, Any] = {}
        d["labeled"] = {sp: {"garments": int(((rep["split"] == sp) & lab.notna()).sum()),
                             "share_of_split_pct": _pct(int(((rep["split"] == sp) & lab.notna()).sum()), n[sp]),
                             "parents": int(rep.loc[(rep["split"] == sp) & lab.notna(), "parent_product_id"].nunique())}
                        for sp in SPLITS}
        lab_n = {sp: d["labeled"][sp]["garments"] for sp in SPLITS}
        d["label_distribution"] = {sp: {l: {"garments": int(((rep["split"] == sp) & (lab == l)).sum()),
                                            "share_of_labeled_pct": _pct(int(((rep["split"] == sp) & (lab == l)).sum()), lab_n[sp])}
                                        for l in labels} for sp in SPLITS}
        d["label_source"] = {sp: _vc(rep.loc[rep["split"] == sp, f"{dim}_label_source"]) for sp in SPLITS}
        d["evidence_confidence"] = {sp: _vc(rep.loc[rep["split"] == sp, f"{dim}_evidence_confidence"]) for sp in SPLITS}
        d["status_counts"] = {sp: _vc(rep.loc[rep["split"] == sp, f"{dim}_status"]) for sp in SPLITS}
        d["conflict_garments"] = {sp: int(rep.loc[rep["split"] == sp, f"{dim}_conflict"].sum()) for sp in SPLITS}
        d["cross_source_conflict_garments"] = {sp: int(rep.loc[rep["split"] == sp, f"{dim}_cross_source_conflict"].sum())
                                               for sp in SPLITS}
        d["unlabeled_with_strong_evidence_unsupported_or_conflict"] = {
            sp: int(((rep["split"] == sp) & lab.isna() & rep[f"{dim}_status"].ne("none")).sum()) for sp in SPLITS}
        mf = rep[f"{dim}_merged_from"]
        d["merged"] = {m: {sp: {"labeled_with_merge_source": int(((rep["split"] == sp) & mf.map(lambda x: m in list(x))).sum()),
                                "labeled_only_via_merge": int(((rep["split"] == sp) & mf.map(lambda x: m in list(x))
                                                               & rep[f"{dim}_label_via_merge_only"]).sum())}
                           for sp in SPLITS} for m in merges}
        if unsup:
            ue = rep[f"{dim}_unsupported_evidence"]
            d["excluded_v1_evidence"] = {unsup: {sp: int(((rep["split"] == sp) & ue.map(lambda x: unsup in list(x))).sum())
                                                 for sp in SPLITS}}
        enabled = [c for c, v in caps["categories"].items() if v["controls"].get(ctrl)]
        cov = {}
        for c in enabled:
            sub = rep[rep["detail_category"] == c]
            cov[c] = {sp: {"garments": int((sub["split"] == sp).sum()),
                           "labeled": int(((sub["split"] == sp) & sub[f"{dim}_label"].notna()).sum()),
                           "labeled_pct": _pct(int(((sub["split"] == sp) & sub[f"{dim}_label"].notna()).sum()),
                                               int((sub["split"] == sp).sum())),
                           "labels": {l: int(((sub["split"] == sp) & (sub[f"{dim}_label"] == l)).sum()) for l in labels}}
                      for sp in SPLITS}
        d["enabled_control_categories"] = enabled
        d["enabled_control_coverage"] = cov
        d["disabled_control_decisions"] = {c: v.get("control_decisions", {}).get(ctrl) for c, v in caps["categories"].items()
                                           if not v["controls"].get(ctrl)}
        out[dim] = d
    out["capability_changes"] = caps.get("fit_length_v1", {}).get("changes", [])
    out["supported_but_disabled_by_design"] = caps.get("fit_length_v1", {}).get("supported_but_disabled_by_design", [])
    return out


def build_representation_audit(rep: pd.DataFrame, vocab: dict[str, Any], caps: dict[str, Any],
                               n_source_components: int, n_source_garments: int) -> dict[str, Any]:
    comps = [(sp, c) for sp, cl in zip(rep["split"], rep["components"]) for c in cl]
    anom = [a for al in rep["anomalous_components"] for a in al]
    devs = [abs(c["pct_sum"] - 100.0) for _, c in comps]
    n_other = Counter()
    n_mat = Counter()
    reasons: dict[str, Counter] = {}
    for sp, c in comps:
        for canon, tok in zip(c["materials"], c["ml_tokens"]):
            n_mat[sp] += 1
            if tok == OTHER:
                n_other[sp] += 1
                reasons.setdefault(sp, Counter())[token_reason(canon, vocab)] += 1

    # independent recount of train-only vocabulary counts from the representation itself
    recount = Counter(m for sp, c in comps if sp == FIT_SPLIT for m in c["materials"] if m is not None)
    table = {r["material_canonical"]: r["train_occurrences"] for r in vocab["count_table"]}
    vocab_consistent = all(recount.get(k, 0) == v for k, v in table.items()) and set(recount) <= set(table)

    leak = rep.dropna(subset=["parent_product_id"]).groupby("parent_product_id")["split"].nunique()
    buckets = Counter()
    coat = 0
    for cl in rep["components"]:
        if not cl:
            continue
        p: GarmentProfile = build_profile(
            [{"component_class": c["component_class"], "component_name_normalized": c["component_name_normalized"],
              "materials": [{"material": m, "pct": x} for m, x in zip(c["materials"], c["percentages"])]} for c in cl])
        buckets[stretch_bucket(p.elastane_pct)] += 1
        coat += p.coating_present
    tags = Counter(t for ts in rep["text_evidence_tags"] for t in ts)

    audit: dict[str, Any] = {
        "garments": len(rep), "source_garments": n_source_garments,
        "garment_count_matches_source": len(rep) == n_source_garments,
        "garment_id_unique": bool(rep["garment_id"].is_unique),
        "components": {
            "source_components": n_source_components, "active": len(comps), "anomalous": len(anom),
            "active_plus_anomalous_equals_source": len(comps) + len(anom) == n_source_components,
            "anomalous_by_status": dict(Counter(a["validation_status"] for a in anom)),
            "tolerance": [PCT_TOLERANCE_LOW, PCT_TOLERANCE_HIGH],
            "max_abs_pct_sum_deviation_active": max(devs) if devs else None,
            "active_not_exactly_100": int(sum(d > 1e-6 for d in devs)),
            "active_per_garment": {str(k): int(v) for k, v in rep["n_active_components"].value_counts().sort_index().items()},
            "class_active": dict(Counter(c["component_class"] for _, c in comps)),
        },
        "garments_without_active_component": int((rep["n_active_components"] == 0).sum()),
        "garments_with_anomalous_component": int((rep["n_anomalous_components"] > 0).sum()),
        "fully_usable_garments": int(rep["is_fully_usable"].sum()),
        "garments_with_unmapped_material": int(rep["has_unmapped_material"].sum()),
        "garments_with_other_token": int(rep["has_other_token"].sum()),
        "split": {"garments": _vc(rep["split"]),
                  "parents": {k: int(v) for k, v in rep.groupby("split")["parent_product_id"].nunique().items()},
                  "parent_leakage_count": int((leak > 1).sum())},
        "distributions": {"target_segment": _vc(rep["target_segment"]), "detail_category": _vc(rep["detail_category"])},
        "vocabulary": {k: vocab[k] for k in ("fit_split", "min_count", "vocabulary_size", "n_train_garments",
                                              "n_train_material_occurrences", "train_unmapped_occurrences",
                                              "threshold_sweep", "tokens")},
        "vocabulary_counts_consistent_with_train_only_recount": bool(vocab_consistent),
        "other_token_rate_by_split": {sp: {"material_occurrences": int(n_mat[sp]), "other": int(n_other[sp]),
                                           "rate_pct": round(100 * n_other[sp] / n_mat[sp], 4) if n_mat[sp] else None,
                                           "reasons": dict(reasons.get(sp, {}))} for sp in sorted(n_mat)},
        "vocab_count_table": vocab["count_table"],
        "text_evidence_tag_counts": dict(sorted(tags.items())),
        "proxy_sanity": {"stretch_bucket_counts_default_limits": dict(buckets), "garments_with_coating_component": int(coat)},
        "capabilities": {**coverage_report(caps, rep["detail_category"].unique()),
                         "needs_review": [k for k, v in caps["categories"].items() if v.get("needs_review")],
                         "disabled_controls_per_category": {k: sorted(f for f, on in v["controls"].items() if not on)
                                                            for k, v in caps["categories"].items()}},
        "representation_sha256": representation_hash(rep),
    }
    audit["fit_length_v1"] = fit_length_section(rep, caps)
    return audit


def _t(rows: list[list[Any]], headers: list[str]) -> str:
    return "\n".join(["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|",
                      *["| " + " | ".join(str(x) for x in r) + " |" for r in rows]])


def _fit_length_md(f: dict[str, Any]) -> list[str]:
    L = ["## Fit / Length V1", "", f"Vocabulary: {json.dumps(f['vocabulary'])}; capability basis: {f['capability_basis']}", ""]
    for dim in ("fit", "length"):
        d = f[dim]
        L += [f"### {dim}", "",
              _t([[sp, d["labeled"][sp]["garments"], d["labeled"][sp]["share_of_split_pct"], d["labeled"][sp]["parents"],
                   d["conflict_garments"][sp], d["cross_source_conflict_garments"][sp],
                   d["unlabeled_with_strong_evidence_unsupported_or_conflict"][sp]] for sp in d["labeled"]],
                 ["split", "labeled", "% of split", "labeled parents", "conflict", "cross-source conflict",
                  "unlabeled w/ evidence (conflict/unmapped/unsupported)"]), "",
              _t([[l, *[f"{d['label_distribution'][sp][l]['garments']} ({d['label_distribution'][sp][l]['share_of_labeled_pct']}%)"
                        for sp in d["labeled"]]] for l in d["label_distribution"]["train"]], ["label", "train", "val", "test"]), "",
              "status counts: " + json.dumps(d["status_counts"]), "",
              "confidence: " + json.dumps(d["evidence_confidence"]), "",
              "merged: " + json.dumps(d["merged"]), ""]
        if "excluded_v1_evidence" in d:
            L += ["excluded from V1: " + json.dumps(d["excluded_v1_evidence"]), ""]
        L += ["enabled-control coverage (labeled / garments, train | val | test):", "",
              _t([[c, *[f"{v[sp]['labeled']}/{v[sp]['garments']} ({v[sp]['labeled_pct']}%)" for sp in ("train", "val", "test")]]
                  for c, v in d["enabled_control_coverage"].items()], ["category", "train", "val", "test"]), "",
              "disabled controls: " + json.dumps(d["disabled_control_decisions"]), ""]
    L += ["capability changes: " + json.dumps([(c["category"], c["control"]) for c in f["capability_changes"]]), "",
          "supported but disabled by design (review): " + json.dumps([(c["category"], c["control"]) for c in f["supported_but_disabled_by_design"]]), ""]
    return L


def render_representation_markdown(a: dict[str, Any]) -> str:
    c, v, s = a["components"], a["vocabulary"], a["split"]
    L = ["# CAGO garment representation audit", "",
         _t([["garments", a["garments"]], ["garment count == source", a["garment_count_matches_source"]],
             ["source components", c["source_components"]], ["active components", c["active"]],
             ["anomalous components (preserved separately)", c["anomalous"]],
             ["active + anomalous == source", c["active_plus_anomalous_equals_source"]],
             ["garments without active component", a["garments_without_active_component"]],
             ["garments with anomalous component", a["garments_with_anomalous_component"]],
             ["fully usable garments", a["fully_usable_garments"]],
             ["garments with unmapped material", a["garments_with_unmapped_material"]],
             ["garments with OTHER token", a["garments_with_other_token"]],
             ["max |pct_sum - 100| (active)", c["max_abs_pct_sum_deviation_active"]],
             ["active components not exactly 100", c["active_not_exactly_100"]],
             ["parent leakage", s["parent_leakage_count"]], ["representation sha256", a["representation_sha256"]]],
            ["metric", "value"]), "",
         "## Anomalous by status", "", _t([[k, n] for k, n in c["anomalous_by_status"].items()], ["status", "n"]), "",
         "## Split", "", _t([[k, n, s["parents"].get(k)] for k, n in s["garments"].items()], ["split", "garments", "parents"]), "",
         f"## ML material vocabulary (fit on `{v['fit_split']}` only)", "",
         f"Size: **{v['vocabulary_size']}** (min_count={v['min_count']}; incl. special tokens). "
         f"Train garments: {v['n_train_garments']}; train material occurrences: {v['n_train_material_occurrences']}; "
         f"train unmapped occurrences: {v['train_unmapped_occurrences']}.", "",
         "Threshold sweep (materials kept at each min train count):", "",
         _t([[k, n] for k, n in v["threshold_sweep"].items()], ["min_count", "materials kept"]), "",
         f"Counts consistent with independent train-only recount: {a['vocabulary_counts_consistent_with_train_only_recount']}", "",
         _t([[r["material_canonical"], r["train_occurrences"], r["train_garments"], r["ml_token"], r["token_reason"]]
             for r in a["vocab_count_table"]], ["material", "train occ.", "train garments", "token", "reason"]), "",
         "## OTHER-token rate by split (reporting only; never used for fitting)", "",
         _t([[k, x["material_occurrences"], x["other"], x["rate_pct"], x["reasons"]]
             for k, x in a["other_token_rate_by_split"].items()], ["split", "occurrences", "OTHER", "%", "reasons"]), "",
         "## Distributions", "", "**target_segment**", _t(list(a["distributions"]["target_segment"].items()), ["target_segment", "n"]), "",
         "**detail_category**", _t(list(a["distributions"]["detail_category"].items()), ["category", "n"]), "",
         "## Text evidence tags", "", _t(list(a["text_evidence_tag_counts"].items()), ["tag", "garments"]), "",
         "## Proxy sanity", "", f"```json\n{__import__('json').dumps(a['proxy_sanity'])}\n```", "",
         *_fit_length_md(a["fit_length_v1"]),
         "## Capabilities", "", f"```json\n{__import__('json').dumps({k: a['capabilities'][k] for k in ('dataset_categories', 'capability_categories', 'missing_in_capabilities', 'extra_in_capabilities', 'needs_review')})}\n```", ""]
    return "\n".join(L)
