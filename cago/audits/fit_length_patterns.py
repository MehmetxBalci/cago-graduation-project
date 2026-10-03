"""Explicit, conservative fit/length text-evidence patterns (Fit/Length Text Evidence Audit v1).

Patterns were chosen after inspecting TRAIN rows only. Nothing here infers `regular` or `standard` from the
absence of other terms: a label needs positive text evidence.

Evidence tiers (highest first):
  structured  : value of a `fit` / `sock fit` / `length` key in raw_function_text ("Key: value | Key: value").
                `sleeve_length` is never used. Exact, normalized value match only.
  phrase      : explicit "<label> fit" (fit) or "regular length"/"cropped length|cut" (length) in product_name,
                raw_description_text or the non-fit/length parts of raw_function_text.
  name_term   : bare `oversized` / `cropped` (not before 'sleeve(s)') in product_name only.
  weak_term   : bare terms anywhere (slim, skinny, relaxed, regular, loose, oversized, cropped, long). Reported,
                NEVER used to assign a label ('slim straight jeans', 'long sleeve', 'cropped sleeves' ...).
"""
from __future__ import annotations

import re

FIT_LABELS = ("skinny", "slim", "regular", "relaxed", "oversized")
LENGTH_LABELS = ("cropped", "standard", "long")

FIT_KEYS = frozenset({"fit", "sock fit"})
LENGTH_KEYS = frozenset({"length"})            # 'sleeve_length' deliberately excluded

FIT_STRUCTURED_VALUES = {
    "skinny": "skinny", "skinny fit": "skinny", "super skinny fit": "skinny",
    "slim": "slim", "slim fit": "slim",
    "regular": "regular", "regular fit": "regular",
    "relaxed": "relaxed", "relaxed fit": "relaxed",
    "oversized": "oversized",
}
LENGTH_STRUCTURED_VALUES = {"cropped": "cropped", "long": "long", "regular length": "standard"}

FIT_PHRASES = {
    "skinny": r"\b(?:super |extra )?skinny[- ]fit\b", "slim": r"\bslim[- ]fit\b", "regular": r"\bregular[- ]fit\b",
    "relaxed": r"\brelaxed[- ]fit\b", "oversized": r"\boversized[- ]fit\b",
}
LENGTH_PHRASES = {"standard": r"\bregular length\b", "cropped": r"\bcropped (?:length|cut)\b"}
FIT_NAME_TERMS = {"oversized": r"\boversized\b"}
LENGTH_NAME_TERMS = {"cropped": r"\bcropped\b(?!\s+sleeves?\b)"}
FIT_WEAK_TERMS = {t: rf"\b{t}\b" for t in ("skinny", "slim", "regular", "relaxed", "loose", "oversized")}
LENGTH_WEAK_TERMS = {"cropped": r"\bcropped\b", "long": r"\blong\b"}

# Raw phrase audit (counted in raw text, independent of label logic).
RAW_PHRASES = ("slim fit", "skinny fit", "regular fit", "relaxed fit", "loose fit", "oversized", "wide leg",
               "straight leg", "tapered", "cropped", "ankle length", "full length", "longline", "maxi", "midi", "mini")
RAW_PHRASE_REGEX = {p: rf"\b{re.escape(p).replace(chr(92) + ' ', '[ -]')}\b" for p in RAW_PHRASES}

# ML-usefulness thresholds (TRAIN-based; val/test only checked for evaluation availability).
MIN_TRAIN_GARMENTS = 500
MIN_TRAIN_PARENTS = 200
MIN_VAL_TEST_GARMENTS = 50
MIN_CATEGORY_TRAIN_GARMENTS = 100
# Human-reviewable merge hypotheses (never applied to labels automatically).
MERGE_TARGETS = {"skinny": "slim"}
RAW_MERGE_CANDIDATES = {"relaxed": ["loose", "loose fit"]}   # structured values that would extend a label

COMPILED = {
    "fit_phrase": {k: re.compile(v) for k, v in FIT_PHRASES.items()},
    "length_phrase": {k: re.compile(v) for k, v in LENGTH_PHRASES.items()},
    "fit_name": {k: re.compile(v) for k, v in FIT_NAME_TERMS.items()},
    "length_name": {k: re.compile(v) for k, v in LENGTH_NAME_TERMS.items()},
    "fit_weak": {k: re.compile(v) for k, v in FIT_WEAK_TERMS.items()},
    "length_weak": {k: re.compile(v) for k, v in LENGTH_WEAK_TERMS.items()},
    "raw": {k: re.compile(v) for k, v in RAW_PHRASE_REGEX.items()},
}


def patterns_document() -> dict:
    """JSON-serialisable description of every rule (written to fit_length_patterns.json)."""
    return {
        "version": 1, "defined_on_split": "train",
        "principles": ["exact/phrase evidence only", "no label from absence of evidence (regular/standard included)",
                       "structured values are authoritative; unmapped structured values block text-based labelling",
                       "mixed mapped+unmapped or multiple labels within a tier -> conflict, label left null",
                       "weak bare terms are reported but never label a garment"],
        "tiers": ["structured", "phrase", "name_term", "weak_term"],
        "fit": {"labels": list(FIT_LABELS), "structured_keys": sorted(FIT_KEYS),
                "structured_value_map": FIT_STRUCTURED_VALUES, "phrase_regex": FIT_PHRASES,
                "name_term_regex": FIT_NAME_TERMS, "weak_term_regex": FIT_WEAK_TERMS},
        "length": {"labels": list(LENGTH_LABELS), "structured_keys": sorted(LENGTH_KEYS),
                   "ignored_structured_keys": ["sleeve_length"], "structured_value_map": LENGTH_STRUCTURED_VALUES,
                   "phrase_regex": LENGTH_PHRASES, "name_term_regex": LENGTH_NAME_TERMS,
                   "weak_term_regex": LENGTH_WEAK_TERMS,
                   "notes": ["'long' is only taken from the structured `length` value (never free text: 'long sleeve')",
                             "'standard' only from explicit 'Regular length' text"]},
        "raw_phrase_regex": RAW_PHRASE_REGEX,
        "usefulness_thresholds": {"min_train_garments": MIN_TRAIN_GARMENTS, "min_train_parents": MIN_TRAIN_PARENTS,
                                  "min_val_test_garments_each": MIN_VAL_TEST_GARMENTS,
                                  "min_category_train_garments": MIN_CATEGORY_TRAIN_GARMENTS},
        "merge_hypotheses": {"label_to_target": MERGE_TARGETS, "raw_values_that_would_extend_label": RAW_MERGE_CANDIDATES},
    }
