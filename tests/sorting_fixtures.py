"""Synthetic fixtures for the sorting-aware generator tests (new helper; no TEST data is ever used for development logic)."""
from __future__ import annotations

import pandas as pd

from cago.generation.mutations import MutationContext, clone_components
from cago.generation.support_tables import build_support_tables
from cago.generation.template_selector import Template, template_components
from cago.generation_sorting.config import SortingAwareGenerationConfig
from cago.evaluation.config import EvaluationConfig
from tests.synthetic_data import CTX, CTX_FULL, garment, request

LIN = [("cotton", 100)]


def _g(gid, split, shell, lining, **kw):
    return garment(gid, f"p_{gid}", split, shell, lining, **kw)


def make_sorting_rep() -> pd.DataFrame:
    rows, n = [], 0
    def add(count, shell, lining, **kw):
        nonlocal n
        for _ in range(count):
            n += 1
            rows.append(_g(f"T{n}", "train", shell, lining, **kw))
    for lining in (LIN, [("polyester", 100)], [("viscose", 100)], [("nylon", 100)], [("linen", 100)]):
        add(2, [("cotton", 100)], lining)
        add(1, [("polyester", 100)], lining)
    add(3, [("linen", 100)], LIN)
    add(2, [("nylon", 100)], [("nylon", 100)])
    add(6, [("cotton", 60), ("polyester", 40)], LIN)
    add(3, [("cotton", 98), ("elastane", 2)], LIN)
    add(3, [("polyester", 70), ("nylon", 30)], [("nylon", 100)])
    add(3, [("wool", 50), ("cotton", 50)], LIN)
    add(3, [("cotton", 60), ("polyester", 30), ("elastane", 10)], LIN)
    add(2, [("cotton", 95), ("polyester", 5)], LIN)
    add(2, [("cotton", 96), ("polyester", 4)], LIN)
    add(2, [("linen", 60), ("polyester", 40)], LIN, colour="black")
    # men/shorts (small pool)
    for i in range(3):
        n += 1
        rows.append(_g(f"S{n}", "train", [("cotton", 100)], LIN, seg="men", cat="shorts"))
    # VAL development garments (including a VAL-only combination: linen + wool)
    rows += [_g("V1", "val", [("cotton", 70), ("polyester", 30)], LIN, colour="red", fit="slim", length="long"),
             _g("V2", "val", [("linen", 50), ("wool", 50)], LIN, colour="blue"),
             _g("V3", "val", [("polyester", 100)], [("polyester", 100)], colour="black"),
             _g("V4", "val", [("cotton", 100)], LIN, seg="men", cat="shorts", colour="white")]
    # TEST rows (must never influence development)
    rows += [_g("X1", "test", [("wool", 100)], [("wool", 100)], colour="red"),
             _g("X2", "test", [("nylon", 60), ("wool", 40)], [("nylon", 100)], seg="men", cat="shorts")]
    rep = pd.DataFrame(rows)
    for c in ("fit", "length"):
        rep[f"{c}_label_source"] = rep[f"{c}_label"].map(lambda v: None if v is None else "structured")
    return rep


def tmpl(shell, lining, colour="red", gid="TT", fit=None, length=None, tags=()) -> Template:
    row = garment(gid, f"p_{gid}", "train", shell, lining, colour=colour, fit=fit, length=length)
    return Template(gid, f"p_{gid}", "women", "trousers", "train", colour, fit, length, tuple(tags), template_components(row["components"]))


def mctx(t: Template, support, forbidden=(), soft=None) -> MutationContext:
    return MutationContext(t.detail_category, support, frozenset(forbidden), (soft or {}).get("preferred_dominant_material"), soft or {},
                           t.colour, frozenset(t.text_tags))


REP = make_sorting_rep()
DEV = REP[REP["split"] != "test"].reset_index(drop=True)
SUP = build_support_tables(DEV)
CFG = SortingAwareGenerationConfig(n_templates=5, candidates_per_template=6, seed=3)
ECFG = EvaluationConfig()
