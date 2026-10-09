"""Synthetic fixtures for the app tests (reuses the research test fixtures; no real data needed)."""
from __future__ import annotations

from app.adapters import build_app_data
from tests.sorting_fixtures import REP
from tests.synthetic_data import CAPS_ALL, VOCAB

VOCAB_DOC = {"tokens": ["PAD", "OTHER", *sorted(VOCAB)], "special_tokens": ["PAD", "OTHER"],
             "canonical_to_token": {m: m for m in sorted(VOCAB | {"silk", "zinc"})}, "material_aliases": {"polyamide": "nylon"},
             "component_classes": ["surface_component", "lining_component"], "component_names": ["shell", "lining"]}
CAPS = {"categories": {c: {**v, "control_decisions": {}} for c, v in CAPS_ALL["categories"].items()}}
REP_ALL = REP                                                     # TRAIN + VAL + TEST rows
REP_TRAIN = REP[REP["split"] == "train"].reset_index(drop=True)
DATA = build_app_data(REP_TRAIN, VOCAB_DOC, CAPS)
