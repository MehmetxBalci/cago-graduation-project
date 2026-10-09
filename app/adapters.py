"""Data loading and request adapters for the CAGO demo app.

The app reads TRAIN rows only: the representation parquet is loaded with a split == "train" row filter, so VAL / TEST garment
compositions are never loaded into memory during normal operation. The RequirementContext is assembled from the same TRAIN rows,
the TRAIN-fitted material vocabulary and the frozen category capabilities (the frozen `RequirementContext.from_processed` reads
labels of all splits, so it is intentionally not used here).
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from cago.generation.support_tables import SupportTables, build_support_tables
from cago.requirements.capabilities import load_capabilities
from cago.requirements.schema import ENUMS
from cago.requirements.validation import RequirementContext

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROCESSED_DIR = ROOT / "data" / "processed"
REQUIRED_FILES = {
    "garment_representation.parquet": "TRAIN garment templates (component compositions, labels, split column); built by scripts/run_representation.py",
    "ml_material_vocabulary.json": "TRAIN-fitted material vocabulary (valid material names / aliases); built by scripts/run_representation.py",
    "category_capabilities.json": "which preferences each garment category supports; copied by scripts/run_representation.py",
}
REPRESENTATION_COLUMNS = ["garment_id", "parent_product_id", "split", "target_segment", "detail_category", "normalized_colour", "fit_label",
                          "fit_label_source", "length_label", "length_label_source", "text_evidence_tags", "is_fully_usable",
                          "has_unmapped_material", "has_other_token", "components"]

# UI field -> request-schema field
UI_TO_REQUEST = {"segment": "target_segment", "category": "detail_category", "preferred_material": "preferred_dominant_material",
                 "forbidden_materials": "forbidden_materials", "colour": "colour", "fit": "fit", "length": "length_cut", "stretch": "stretch",
                 "thermal_warmth": "thermal_warmth", "breathability": "breathability", "durability": "durability_wear",
                 "moisture_wicking": "moisture_wicking", "water_repellent": "water_repellent"}
REQUEST_TO_UI = {v: k for k, v in UI_TO_REQUEST.items()}
UI_LABELS = {"segment": "Segment", "category": "Garment category", "preferred_material": "Preferred dominant material",
             "forbidden_materials": "Forbidden materials", "colour": "Colour", "fit": "Fit", "length": "Length", "stretch": "Stretch",
             "thermal_warmth": "Thermal warmth", "breathability": "Breathability", "durability": "Durability",
             "moisture_wicking": "Moisture wicking", "water_repellent": "Water repellency"}
CAPABILITY_UI_FIELDS = ("stretch", "thermal_warmth", "breathability", "durability", "moisture_wicking", "water_repellent", "fit", "length")
BOOLEAN_UI_FIELDS = ("moisture_wicking", "water_repellent")
ENUM_UI_FIELDS = {"fit": "fit", "length": "length_cut", "stretch": "stretch", "thermal_warmth": "thermal_warmth",
                  "breathability": "breathability", "durability": "durability_wear"}
NO_PREFERENCE = None


class MissingDataError(RuntimeError):
    """Required processed files are missing; `missing` lists them with a description."""

    def __init__(self, processed_dir: Path, missing: dict[str, str]):
        self.processed_dir, self.missing = Path(processed_dir), missing
        super().__init__(f"missing processed files in {processed_dir}: {sorted(missing)}")


def missing_files(processed_dir: Path) -> dict[str, str]:
    d = Path(processed_dir)
    return {n: why for n, why in REQUIRED_FILES.items() if not (d / n).exists()}


@dataclass
class AppData:
    """Everything the app needs, built once (TRAIN-derived)."""
    processed_dir: Path
    rep_train: pd.DataFrame
    support: SupportTables
    ctx: RequirementContext
    vocab_tokens: tuple[str, ...]
    capabilities: dict[str, Any]
    cells: dict[str, dict[str, int]]                          # segment -> category -> TRAIN garment count
    colours: dict[tuple[str, str], list[tuple[str, int]]]     # (segment, category) -> TRAIN colours with counts
    loaded_splits: tuple[str, ...] = ("train",)
    notes: list[str] = field(default_factory=list)

    def categories_for(self, segment: str) -> list[str]:
        return sorted(self.cells.get(segment, {}))

    def segments(self) -> list[str]:
        order = {"women": 0, "men": 1, "kids": 2, "baby": 3}
        return sorted(self.cells, key=lambda s: (order.get(s, 9), s))

    def materials_for(self, category: str) -> list[str]:
        """Physical in-vocabulary materials observed in TRAIN for the category, most frequent first."""
        cnt = self.support.materials_by_category.get(category, Counter())
        valid = set(self.vocab_tokens)
        return [m for m in sorted(cnt, key=lambda k: (-cnt[k], k)) if m in valid]


def read_train_representation(processed_dir: Path) -> pd.DataFrame:
    """TRAIN rows only, filtered while reading (VAL/TEST rows are never materialised)."""
    path = Path(processed_dir) / "garment_representation.parquet"
    try:
        rep = pd.read_parquet(path, columns=REPRESENTATION_COLUMNS, filters=[("split", "==", "train")])
    except (ValueError, KeyError):                    # older pyarrow / missing optional columns: fall back, then filter
        rep = pd.read_parquet(path)
        rep = rep[rep["split"] == "train"]
    rep = rep.reset_index(drop=True)
    if set(rep["split"].unique()) - {"train"}:
        raise ValueError("application data must contain TRAIN rows only")
    return rep


def build_context(rep_train: pd.DataFrame, vocab: dict[str, Any], caps: dict[str, Any]) -> RequirementContext:
    return RequirementContext(
        target_segments=frozenset(rep_train["target_segment"].dropna().unique()),
        categories=frozenset(rep_train["detail_category"].dropna().unique()),
        materials=frozenset(vocab["canonical_to_token"]), capabilities=caps, aliases=vocab.get("material_aliases", {}),
        component_classes=frozenset(vocab.get("component_classes", [])), component_names=frozenset(vocab.get("component_names", [])),
        ml_tokens=frozenset(vocab["special_tokens"]))


def build_app_data(rep_train: pd.DataFrame, vocab: dict[str, Any], caps: dict[str, Any], processed_dir: Path = Path(".")) -> AppData:
    if set(rep_train["split"].unique()) - {"train"}:
        raise ValueError("application data must contain TRAIN rows only")
    support = build_support_tables(rep_train)
    cells: dict[str, dict[str, int]] = {}
    for (s, c), n in rep_train.groupby(["target_segment", "detail_category"]).size().items():
        cells.setdefault(s, {})[c] = int(n)
    colours: dict[tuple[str, str], list[tuple[str, int]]] = {}
    for (s, c), g in rep_train.groupby(["target_segment", "detail_category"]):
        vc = g["normalized_colour"].dropna().value_counts()
        colours[(s, c)] = [(str(k), int(v)) for k, v in sorted(vc.items(), key=lambda kv: (-kv[1], kv[0]))]
    tokens = tuple(t for t in vocab["tokens"] if t not in vocab["special_tokens"])
    return AppData(Path(processed_dir), rep_train, support, build_context(rep_train, vocab, caps), tokens, caps, cells, colours)


def load_app_data(processed_dir: Path = DEFAULT_PROCESSED_DIR) -> AppData:
    """Load processed files (raises MissingDataError listing what is missing)."""
    d = Path(processed_dir)
    miss = missing_files(d)
    if miss:
        raise MissingDataError(d, miss)
    vocab = json.loads((d / "ml_material_vocabulary.json").read_text(encoding="utf-8"))
    caps = load_capabilities(d / "category_capabilities.json")
    return build_app_data(read_train_representation(d), vocab, caps, d)


# ---------------------------------------------------------------- form <-> request
def field_availability(category: str | None, caps: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Per UI field: enabled flag + human-readable reason when disabled (from the frozen capability table)."""
    out: dict[str, dict[str, Any]] = {}
    entry = (caps.get("categories") or {}).get(category or "", {})
    controls, decisions = entry.get("controls", {}), entry.get("control_decisions", {})
    for f in CAPABILITY_UI_FIELDS:
        rf = UI_TO_REQUEST[f]
        on = bool(controls.get(rf, False))
        reason = None
        if not on:
            d = decisions.get(rf)
            reason = ("not enough labelled TRAIN garments for this category" if d == "disabled_insufficient_train_support"
                      else "not applicable to this garment category in CAGO V1")
        out[f] = {"enabled": on, "reason": reason}
    return out


def enum_options(ui_field: str) -> tuple[str, ...]:
    return tuple(ENUMS[ENUM_UI_FIELDS[ui_field]])


def form_to_raw_request(form: dict[str, Any]) -> dict[str, Any]:
    """Map UI form values to the frozen request schema. `None` / empty selections mean 'no preference' and are omitted.
    Boolean properties map True -> True and False/None -> omitted (the schema accepts only true or null)."""
    raw: dict[str, Any] = {}
    for ui, rf in UI_TO_REQUEST.items():
        v = form.get(ui)
        if v is None or (isinstance(v, str) and not v.strip()):
            continue
        if ui == "forbidden_materials":
            if v:
                raw[rf] = list(v)
            continue
        if ui in BOOLEAN_UI_FIELDS:
            if v is True:
                raw[rf] = True
            continue
        raw[rf] = v
    return raw
