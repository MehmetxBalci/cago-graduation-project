"""Per-garment fit/length evidence extraction (pure functions + table builder)."""
from __future__ import annotations

import re
from typing import Any

import pandas as pd

from cago.audits.fit_length_patterns import (COMPILED, FIT_KEYS, FIT_STRUCTURED_VALUES, LENGTH_KEYS,
                                             LENGTH_STRUCTURED_VALUES)

_WS = re.compile(r"\s+")


def _s(x: Any) -> str:
    return x.casefold() if isinstance(x, str) else ""


def _norm(v: str) -> str:
    return _WS.sub(" ", v.replace("\u30fb", " ").strip().casefold()).strip(" .")


def parse_function_text(text: str) -> tuple[list[tuple[str, str]], str]:
    """Split 'Key: value | Key: value' text. Returns ([(key_norm, value)] for fit/length keys, other free text).

    Values of `sleeve_length` and every non-fit/length key go to the free text (sleeve_length is dropped entirely).
    """
    structured, other = [], []
    for part in text.split(" | "):
        key, sep, val = part.partition(":")
        k = _norm(key) if sep else ""
        if sep and k in FIT_KEYS | LENGTH_KEYS:
            structured.append((k, val.strip()))
        elif sep and k == "sleeve_length":
            continue
        else:
            other.append(val.strip() if sep else part.strip())
    return structured, " | ".join(other)


def _structured(values: list[str], mapping: dict[str, str]) -> tuple[set[str], list[str]]:
    mapped, unmapped = set(), []
    for v in values:
        for piece in v.split(","):
            n = _norm(piece)
            if not n:
                continue
            if n in mapping:
                mapped.add(mapping[n])
            else:
                unmapped.append(n)
    return mapped, unmapped


def resolve(structured: set[str], unmapped: list[str], structured_present: bool,
            explicit: set[str]) -> tuple[str | None, str, bool]:
    """Return (label, status, cross_source_conflict). Structured evidence is authoritative."""
    if structured_present:
        if len(structured) == 1 and not unmapped:
            return next(iter(structured)), "labeled_structured", bool(explicit - structured)
        if len(structured) > 1 or (structured and unmapped):
            return None, "structured_conflict", False
        return None, "structured_unmapped", False
    if explicit:
        if len(explicit) == 1:
            return next(iter(explicit)), "labeled_phrase", False
        return None, "phrase_conflict", False
    return None, "none", False


def evaluate_text(product_name: Any, description: Any, function_text: Any) -> dict[str, Any]:
    """Evidence for one garment. Pure; no dataset state."""
    name, desc, func = _s(product_name), _s(description), _s(function_text)
    kvs, other_func = parse_function_text(func)
    segs = {"name": name, "description": desc, "function": other_func}
    out: dict[str, Any] = {}
    for dim, keys, vmap in (("fit", FIT_KEYS, FIT_STRUCTURED_VALUES), ("length", LENGTH_KEYS, LENGTH_STRUCTURED_VALUES)):
        values = [v for k, v in kvs if k in keys]
        mapped, unmapped = _structured(values, vmap)
        explicit: set[str] = set()
        matches = [f"structured:{dim}:{_norm(p)}" for v in values for p in v.split(",") if _norm(p)]
        for label, rx in COMPILED[f"{dim}_phrase"].items():
            for src, txt in segs.items():
                if rx.search(txt):
                    explicit.add(label); matches.append(f"phrase:{src}:{label}")
        for label, rx in COMPILED[f"{dim}_name"].items():
            if rx.search(name):
                explicit.add(label); matches.append(f"name_term:name:{label}")
        weak = sorted({t for t, rx in COMPILED[f"{dim}_weak"].items() if any(rx.search(x) for x in segs.values())})
        label, status, cross = resolve(mapped, unmapped, bool(values), explicit)
        out.update({
            f"{dim}_label": label, f"{dim}_status": status,
            f"{dim}_label_source": status.split("_", 1)[1] if status.startswith("labeled_") else None,
            f"{dim}_structured_labels": sorted(mapped), f"{dim}_structured_unmapped": sorted(set(unmapped)),
            f"{dim}_explicit_labels": sorted(explicit), f"{dim}_cross_source_conflict": bool(cross),
            f"{dim}_weak_terms": weak, f"{dim}_any_strong_evidence": bool(values or explicit),
            f"{dim}_raw_matches": matches,
        })
    out["raw_phrase_hits"] = [f"{p}@{src}" for p, rx in COMPILED["raw"].items()
                              for src, txt in (("name", name), ("description", desc), ("function", func)) if rx.search(txt)]
    return out


def build_evidence(garments: pd.DataFrame, split_map: pd.DataFrame) -> pd.DataFrame:
    """One evidence row per garment (existing split mapping; no re-splitting)."""
    split_of = dict(zip(split_map["garment_id"], split_map["split"]))
    rows = []
    for r in garments.itertuples(index=False):
        ev = evaluate_text(r.product_name, r.raw_description_text, r.raw_function_text)
        rows.append({"garment_id": r.garment_id, "parent_product_id": r.parent_product_id,
                     "split": split_of.get(r.garment_id), "detail_category": r.detail_category,
                     "product_name": r.product_name, **ev})
    return pd.DataFrame(rows)
