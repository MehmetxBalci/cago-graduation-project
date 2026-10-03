"""Fit/Length V1 labelling for the garment representation.

Conservative evidence rules (unchanged from the audit): structured `fit:` / `length:` values are authoritative;
explicit phrases are used only when no structured value exists; conflicting or unmapped structured evidence is
never overwritten by weaker evidence; no label is ever inferred from missing evidence.

V1 changes: skinny -> slim, loose/loose fit -> relaxed (tracked in `*_merged_from`); `cropped` is excluded
(recorded as unsupported evidence, never a label).
"""
from __future__ import annotations

import re
from typing import Any

from cago.audits.fit_length_evidence import _norm, _s, parse_function_text, resolve
from cago.audits.fit_length_patterns import FIT_KEYS, LENGTH_KEYS
from cago.config.fit_length_v1 import FIT_LABELS_V1, LENGTH_EXCLUDED, LENGTH_LABELS_V1

# raw structured value -> (V1 label, merged family or None)
FIT_STRUCTURED_V1 = {
    "skinny": ("slim", "skinny"), "skinny fit": ("slim", "skinny"), "super skinny fit": ("slim", "skinny"),
    "slim": ("slim", None), "slim fit": ("slim", None),
    "regular": ("regular", None), "regular fit": ("regular", None),
    "relaxed": ("relaxed", None), "relaxed fit": ("relaxed", None),
    "loose": ("relaxed", "loose"), "loose fit": ("relaxed", "loose"),
    "oversized": ("oversized", None),
}
LENGTH_STRUCTURED_V1 = {"long": ("long", None), "regular length": ("standard", None)}

_R = re.compile
FIT_PHRASES_V1 = [("slim", None, _R(r"\bslim[- ]fit\b")), ("slim", "skinny", _R(r"\b(?:super |extra )?skinny[- ]fit\b")),
                  ("regular", None, _R(r"\bregular[- ]fit\b")), ("relaxed", None, _R(r"\brelaxed[- ]fit\b")),
                  ("relaxed", "loose", _R(r"\bloose[- ]fit\b")), ("oversized", None, _R(r"\boversized[- ]fit\b"))]
FIT_NAME_V1 = [("oversized", None, _R(r"\boversized\b"))]
LENGTH_PHRASES_V1 = [("standard", None, _R(r"\bregular length\b")), ("cropped", None, _R(r"\bcropped (?:length|cut)\b"))]
LENGTH_NAME_V1 = [("cropped", None, _R(r"\bcropped\b(?!\s+sleeves?\b)"))]

_V1 = {"fit": set(FIT_LABELS_V1), "length": set(LENGTH_LABELS_V1)}


def _dimension(dim: str, values: list[str], vmap: dict[str, tuple[str, str | None]], excluded: set[str],
               phrases: list, name_terms: list, segs: dict[str, str], name: str) -> dict[str, Any]:
    mapped: set[str] = set()
    s_native: set[str] = set()
    s_merged: dict[str, set[str]] = {}
    unmapped: list[str] = []
    unsupported: list[str] = []
    raw = []
    for v in values:
        for piece in v.split(","):
            n = _norm(piece)
            if not n:
                continue
            raw.append(f"structured:{dim}:{n}")
            if n in vmap:
                lab, fam = vmap[n]
                mapped.add(lab)
                (s_merged.setdefault(lab, set()).add(fam) if fam else s_native.add(lab))
            else:
                unmapped.append(n)
                if n in excluded:
                    unsupported.append(n)
    explicit: set[str] = set()
    e_native: set[str] = set()
    e_merged: dict[str, set[str]] = {}
    for lab, fam, rx in phrases:
        for src, txt in segs.items():
            m = rx.search(txt)
            if m:
                explicit.add(lab)
                raw.append(f"phrase:{src}:{m.group(0)}")
                (e_merged.setdefault(lab, set()).add(fam) if fam else e_native.add(lab))
                if lab in excluded:
                    unsupported.append(m.group(0))
    for lab, fam, rx in name_terms:
        m = rx.search(name)
        if m:
            explicit.add(lab)
            raw.append(f"name_term:name:{m.group(0)}")
            (e_merged.setdefault(lab, set()).add(fam) if fam else e_native.add(lab))
            if lab in excluded:
                unsupported.append(m.group(0))

    label, status, cross = resolve(mapped, unmapped, bool(values), explicit)
    if status == "structured_unmapped" and unmapped and all(u in excluded for u in unmapped):
        status = "structured_unsupported_v1"
    if label is not None and label not in _V1[dim]:        # e.g. phrase-only 'cropped'
        label, status = None, "phrase_unsupported_v1"
    source = status.split("_", 1)[1] if status.startswith("labeled_") else None
    merged_from: list[str] = []
    via_merge_only = False
    if label is not None:
        merged, native = (s_merged, s_native) if source == "structured" else (e_merged, e_native)
        merged_from = sorted(f"{fam}->{label}" for fam in merged.get(label, ()))
        via_merge_only = bool(merged_from) and label not in native
    conflict_labels: list[str] = []
    if status == "structured_conflict":
        conflict_labels = sorted(mapped | set(unmapped))
    elif status == "phrase_conflict":
        conflict_labels = sorted(explicit)
    return {
        f"{dim}_label": label, f"{dim}_label_source": source, f"{dim}_status": status,
        f"{dim}_evidence_confidence": {"structured": "high", "phrase": "medium"}.get(source) if label else None,
        f"{dim}_conflict": status in ("structured_conflict", "phrase_conflict"),
        f"{dim}_conflict_labels": conflict_labels, f"{dim}_cross_source_conflict": bool(cross),
        f"{dim}_merged_from": merged_from, f"{dim}_label_via_merge_only": via_merge_only,
        f"{dim}_unsupported_evidence": sorted(set(unsupported)), f"{dim}_raw_evidence": raw,
    }


def evaluate_fit_length_v1(product_name: Any, description: Any, function_text: Any) -> dict[str, Any]:
    """Fit/length V1 labels + provenance for one garment (pure)."""
    name, desc, func = _s(product_name), _s(description), _s(function_text)
    kvs, other_func = parse_function_text(func)
    segs = {"name": name, "description": desc, "function": other_func}
    fit_vals = [v for k, v in kvs if k in FIT_KEYS]
    len_vals = [v for k, v in kvs if k in LENGTH_KEYS]
    out = _dimension("fit", fit_vals, FIT_STRUCTURED_V1, set(), FIT_PHRASES_V1, FIT_NAME_V1, segs, name)
    out.update(_dimension("length", len_vals, LENGTH_STRUCTURED_V1, set(LENGTH_EXCLUDED), LENGTH_PHRASES_V1,
                          LENGTH_NAME_V1, segs, name))
    return out
