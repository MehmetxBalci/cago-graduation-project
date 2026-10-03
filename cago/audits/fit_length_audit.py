"""Aggregate fit/length evidence into the audit (TRAIN defines statistics/decisions; VAL/TEST reported separately)."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from cago.audits.fit_length_patterns import (FIT_LABELS, LENGTH_LABELS, MERGE_TARGETS, MIN_CATEGORY_TRAIN_GARMENTS,
                                             MIN_TRAIN_GARMENTS, MIN_TRAIN_PARENTS, MIN_VAL_TEST_GARMENTS,
                                             RAW_MERGE_CANDIDATES, RAW_PHRASES)

SPLITS = ("train", "val", "test")
DIMS = {"fit": FIT_LABELS, "length": LENGTH_LABELS}
CONTROL = {"fit": "fit", "length": "length_cut"}


def _pct(a: int, b: int) -> float | None:
    return round(100 * a / b, 3) if b else None


def _split_counts(ev: pd.DataFrame, mask: pd.Series) -> dict[str, dict[str, Any]]:
    out = {}
    for sp in SPLITS:
        d = ev[ev["split"] == sp]
        m = mask[d.index]
        out[sp] = {"garments": int(m.sum()), "parents": int(d.loc[m, "parent_product_id"].nunique()),
                   "share_of_split_pct": _pct(int(m.sum()), len(d))}
    return out


def leakage_check(ev: pd.DataFrame) -> dict[str, Any]:
    per = ev.dropna(subset=["parent_product_id"]).groupby("parent_product_id")["split"].nunique()
    inc = {}
    tr = ev[ev["split"] == "train"]
    for dim in DIMS:
        lab = tr.dropna(subset=[f"{dim}_label"]).groupby("parent_product_id")[f"{dim}_label"].nunique()
        inc[dim] = int((lab > 1).sum())
    return {"parents_in_multiple_splits": int((per > 1).sum()), "parent_leakage": bool((per > 1).any()),
            "train_parents_with_inconsistent_labels_across_variants": inc}


def recommend(label: str, dim: str, stats: dict[str, Any]) -> dict[str, Any]:
    """KEEP / MERGE / REMOVE_FROM_V1 from TRAIN support (+ val/test availability). Thresholds in patterns module."""
    def ok(s):  # s: per-split dict
        return (s["train"]["garments"] >= MIN_TRAIN_GARMENTS and s["train"]["parents"] >= MIN_TRAIN_PARENTS
                and s["val"]["garments"] >= MIN_VAL_TEST_GARMENTS and s["test"]["garments"] >= MIN_VAL_TEST_GARMENTS)
    own = stats[label]["per_split"]
    if ok(own):
        return {"label": label, "recommendation": "KEEP", "reason": "meets train/val/test support thresholds"}
    tgt = MERGE_TARGETS.get(label) if dim == "fit" else None
    if tgt and ok(stats[tgt]["per_split"]):
        return {"label": label, "recommendation": "MERGE", "merge_into": tgt,
                "reason": f"below thresholds (train {own['train']['garments']} garments / {own['train']['parents']} parents); "
                          f"hypothesis: merge into '{tgt}' (human decision)"}
    return {"label": label, "recommendation": "REMOVE_FROM_V1",
            "reason": f"insufficient support (train {own['train']['garments']} garments / {own['train']['parents']} parents)"}


def build_fit_length_audit(ev: pd.DataFrame, caps: dict[str, Any] | None = None) -> dict[str, Any]:
    ev = ev.reset_index(drop=True)
    tr = ev[ev["split"] == "train"]
    audit: dict[str, Any] = {
        "garments": len(ev), "split_garments": {sp: int((ev["split"] == sp).sum()) for sp in SPLITS},
        "split_parents": {sp: int(ev.loc[ev["split"] == sp, "parent_product_id"].nunique()) for sp in SPLITS},
        "statistics_basis": "TRAIN (patterns, support decisions); VAL/TEST reported separately",
        "thresholds": {"min_train_garments": MIN_TRAIN_GARMENTS, "min_train_parents": MIN_TRAIN_PARENTS,
                       "min_val_test_garments_each": MIN_VAL_TEST_GARMENTS,
                       "min_category_train_garments": MIN_CATEGORY_TRAIN_GARMENTS},
        "leakage": leakage_check(ev), "dimensions": {}, "raw_phrases": {}, "recommendations": {},
    }
    for dim, labels in DIMS.items():
        d: dict[str, Any] = {}
        d["any_strong_evidence"] = _split_counts(ev, ev[f"{dim}_any_strong_evidence"])
        d["labeled"] = _split_counts(ev, ev[f"{dim}_label"].notna())
        d["any_weak_term_only"] = _split_counts(ev, ~ev[f"{dim}_any_strong_evidence"] & (ev[f"{dim}_weak_terms"].str.len() > 0))
        d["status_counts"] = {sp: {k: int(v) for k, v in ev.loc[ev["split"] == sp, f"{dim}_status"].value_counts().items()}
                              for sp in SPLITS}
        d["cross_source_conflicts"] = _split_counts(ev, ev[f"{dim}_cross_source_conflict"])
        conf = ev[ev[f"{dim}_status"].isin(["structured_conflict", "phrase_conflict"])]
        d["conflict_label_combinations_train"] = dict(Counter(
            "+".join(sorted(set(a) | set(b))) + ("+unmapped:" + "|".join(c) if c else "")
            for a, b, c in zip(conf.loc[conf["split"] == "train", f"{dim}_structured_labels"],
                               conf.loc[conf["split"] == "train", f"{dim}_explicit_labels"],
                               conf.loc[conf["split"] == "train", f"{dim}_structured_unmapped"])).most_common(15))
        d["unmapped_structured_values_train"] = dict(Counter(
            v for vs in tr[f"{dim}_structured_unmapped"] for v in vs).most_common(25))
        d["top_raw_matches_train"] = dict(Counter(m for ms in tr[f"{dim}_raw_matches"] for m in ms).most_common(25))
        stats = {}
        for lab in labels:
            m = ev[f"{dim}_label"] == lab
            per_split = _split_counts(ev, m)
            src = {s: {sp: int(((ev["split"] == sp) & m & (ev[f"{dim}_label_source"] == s)).sum()) for sp in SPLITS}
                   for s in ("structured", "phrase")}
            labeled = {sp: int(((ev["split"] == sp) & ev[f"{dim}_label"].notna()).sum()) for sp in SPLITS}
            weak_only = int(((ev["split"] == "train") & ~m & ev[f"{dim}_weak_terms"].map(lambda t: lab in t)).sum())
            stats[lab] = {"per_split": per_split, "by_source": src,
                          "share_of_labeled_pct": {sp: _pct(per_split[sp]["garments"], labeled[sp]) for sp in SPLITS},
                          "weak_term_only_train_garments": weak_only}
        d["labels"] = stats
        # per detail category
        cats = {}
        for cat, g in ev.groupby("detail_category"):
            cats[cat] = {sp: {"garments": int((g["split"] == sp).sum()),
                              "any_strong_evidence": int(((g["split"] == sp) & g[f"{dim}_any_strong_evidence"]).sum()),
                              "labeled": int(((g["split"] == sp) & g[f"{dim}_label"].notna()).sum()),
                              "labels": {lab: int(((g["split"] == sp) & (g[f"{dim}_label"] == lab)).sum()) for lab in labels}}
                         for sp in SPLITS}
        d["by_detail_category"] = cats
        d["usable_categories_per_label"] = {lab: sorted(c for c, v in cats.items()
                                                        if v["train"]["labels"][lab] >= MIN_CATEGORY_TRAIN_GARMENTS)
                                            for lab in labels}
        if caps:
            enabled = [c for c, v in caps["categories"].items() if v["controls"].get(CONTROL[dim])]
            sub = tr[tr["detail_category"].isin(enabled)]
            d["control_enabled_categories"] = enabled
            d["train_coverage_in_control_enabled_categories"] = {
                "garments": len(sub), "labeled": int(sub[f"{dim}_label"].notna().sum()),
                "labeled_pct": _pct(int(sub[f"{dim}_label"].notna().sum()), len(sub))}
            d["enabled_but_no_supported_label"] = [c for c in enabled
                                                   if not any(c in d["usable_categories_per_label"][lab] for lab in labels)]
        # examples (train, distinct parents, deterministic)
        ex = {}
        for lab in labels:
            sel = tr[tr[f"{dim}_label"] == lab].sort_values("garment_id").drop_duplicates("parent_product_id").head(3)
            ex[lab] = [{"garment_id": r.garment_id, "detail_category": r.detail_category, "product_name": r.product_name,
                        "source": getattr(r, f"{dim}_label_source"), "matches": list(getattr(r, f"{dim}_raw_matches"))[:4]}
                       for r in sel.itertuples()]
        d["examples_train"] = ex
        audit["dimensions"][dim] = d
        audit["recommendations"][dim] = [recommend(lab, dim, stats) for lab in labels]
        if dim == "fit":   # raw merge candidates (e.g. loose) measured on TRAIN
            audit["recommendations"]["fit_raw_merge_candidates_train"] = {
                lab: {v: int(sum(v in vs for vs in tr["fit_structured_unmapped"])) for v in vals}
                for lab, vals in RAW_MERGE_CANDIDATES.items()}
    # raw phrase audit
    hits = ev[["garment_id", "parent_product_id", "split", "raw_phrase_hits"]].explode("raw_phrase_hits").dropna(subset=["raw_phrase_hits"])
    hits[["phrase", "source"]] = hits["raw_phrase_hits"].str.rsplit("@", n=1, expand=True)
    for p in RAW_PHRASES:
        h = hits[hits["phrase"] == p]
        audit["raw_phrases"][p] = {
            sp: {"garments_any_source": int(h.loc[h["split"] == sp, "garment_id"].nunique()),
                 "parents": int(h.loc[h["split"] == sp, "parent_product_id"].nunique()),
                 "by_source": {s: int(h.loc[(h["split"] == sp) & (h["source"] == s), "garment_id"].nunique())
                               for s in ("name", "description", "function")}} for sp in SPLITS}
    return audit


def render_markdown(a: dict[str, Any]) -> str:
    def T(rows, hdr):
        return "\n".join(["| " + " | ".join(hdr) + " |", "|" + "|".join("---" for _ in hdr) + "|",
                          *["| " + " | ".join(str(x) for x in r) + " |" for r in rows]])
    L = ["# CAGO fit / length text-evidence audit", "",
         f"Basis: {a['statistics_basis']}. Garments: {a['garments']} (train/val/test = "
         f"{a['split_garments']['train']}/{a['split_garments']['val']}/{a['split_garments']['test']}). "
         f"Parent leakage: **{a['leakage']['parent_leakage']}** ({a['leakage']['parents_in_multiple_splits']} parents in >1 split).", "",
         "Thresholds: " + json.dumps(a["thresholds"]), ""]
    for dim, d in a["dimensions"].items():
        L += [f"## {dim.upper()}", "", "### Coverage (garments / % of split)", "",
              T([[k, *[f"{d[k][sp]['garments']} ({d[k][sp]['share_of_split_pct']}%)" for sp in SPLITS]]
                 for k in ("any_strong_evidence", "labeled", "cross_source_conflicts", "any_weak_term_only")],
                ["metric", "train", "val", "test"]), "",
              "### Label counts (garments / parents)", "",
              T([[lab, *[f"{s['per_split'][sp]['garments']} / {s['per_split'][sp]['parents']}" for sp in SPLITS],
                  s["by_source"]["structured"]["train"], s["by_source"]["phrase"]["train"], s["weak_term_only_train_garments"]]
                 for lab, s in d["labels"].items()],
                ["label", "train", "val", "test", "train structured", "train phrase-only", "train weak-term-only"]), "",
              "### Status counts", "", "```json\n" + json.dumps(d["status_counts"]) + "\n```", "",
              "### Conflict combinations (train)", "", "```json\n" + json.dumps(d["conflict_label_combinations_train"]) + "\n```", "",
              "### Unmapped structured values (train, top 25)", "", "```json\n" + json.dumps(d["unmapped_structured_values_train"]) + "\n```", "",
              "### Top matched evidence (train)", "", "```json\n" + json.dumps(d["top_raw_matches_train"]) + "\n```", ""]
        if "train_coverage_in_control_enabled_categories" in d:
            L += ["Coverage in categories where the UI control is enabled (train): "
                  + json.dumps(d["train_coverage_in_control_enabled_categories"])
                  + "; enabled categories with no supported label: " + json.dumps(d["enabled_but_no_supported_label"]), ""]
        L += ["### By detail category (train labeled / train garments; labels train)", "",
              T([[c, v["train"]["labeled"], v["train"]["garments"], v["val"]["labeled"], v["test"]["labeled"],
                  " ".join(f"{k}:{n}" for k, n in v["train"]["labels"].items() if n)]
                 for c, v in d["by_detail_category"].items()],
                ["category", "train labeled", "train garments", "val labeled", "test labeled", "train labels"]), "",
              "### Categories with >= %d train garments per label" % a["thresholds"]["min_category_train_garments"], "",
              "```json\n" + json.dumps(d["usable_categories_per_label"]) + "\n```", "", "### Examples (train)", ""]
        for lab, exs in d["examples_train"].items():
            for e in exs:
                L.append(f"- **{lab}** [{e['detail_category']}] {e['product_name']!r} ({e['source']}) {e['matches']}")
        L.append("")
    L += ["## Raw phrase audit (garments any source / parents, per split)", "",
          T([[p, *[f"{v[sp]['garments_any_source']} / {v[sp]['parents']}" for sp in SPLITS],
              json.dumps(v["train"]["by_source"])] for p, v in a["raw_phrases"].items()],
            ["phrase", "train", "val", "test", "train by source"]), "",
          "## Train-only label consistency", "", "```json\n" + json.dumps(a["leakage"]["train_parents_with_inconsistent_labels_across_variants"]) + "\n```", "",
          "## Recommendations", ""]
    for dim in DIMS:
        for r in a["recommendations"][dim]:
            L.append(f"- {dim}/{r['label']}: **{r['recommendation']}**" + (f" -> {r['merge_into']}" if r.get("merge_into") else "")
                     + f" ({r['reason']})")
    L += ["", "Raw merge candidates (train): " + json.dumps(a["recommendations"]["fit_raw_merge_candidates_train"]), ""]
    return "\n".join(L)


def write_outputs(ev: pd.DataFrame, audit: dict[str, Any], patterns: dict[str, Any], out: Path) -> None:
    out = Path(out)
    ev.to_parquet(out / "fit_length_evidence.parquet", index=False)
    (out / "fit_length_audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "fit_length_audit.md").write_text(render_markdown(audit), encoding="utf-8")
    (out / "fit_length_patterns.json").write_text(json.dumps(patterns, indent=2, ensure_ascii=False), encoding="utf-8")
