"""Fixtures for the final-evaluation tests (new helper). TEST rows only define requests, never templates."""
from __future__ import annotations

import pandas as pd

from cago.benchmark.final_test_requests import generation_view
from cago.benchmark.sorting_aware_comparison import default_variants
from cago.generation.support_tables import build_support_tables
from tests.sorting_fixtures import REP as _BASE
from tests.synthetic_data import CTX_FULL, garment


def make_final_rep() -> pd.DataFrame:
    rows = _BASE.to_dict("records")
    n = 0
    for shell, lining, kw in (([("cotton", 60), ("polyester", 40)], [("cotton", 100)], {}), ([("linen", 100)], [("cotton", 100)], {"colour": "black"}),
                              ([("cotton", 96), ("polyester", 4)], [("cotton", 100)], {}), ([("polyester", 70), ("nylon", 30)], [("nylon", 100)], {}),
                              ([("cotton", 100)], [("polyester", 100)], {}), ([("wool", 50), ("cotton", 50)], [("cotton", 100)], {"fit": "slim"})):
        n += 1
        rows.append(garment(f"E{n}", f"pe{n}", "test", shell, lining, **kw))
    for shell, lining in (([("cotton", 100)], [("cotton", 100)]), ([("polyester", 100)], [("polyester", 100)])):
        n += 1
        rows.append(garment(f"F{n}", f"pf{n}", "test", shell, lining, seg="men", cat="shorts"))
    rows.append(garment("E_bad", "pe_bad", "test", [("cotton", 70), ("zinc", 30)], [("cotton", 100)]))      # non-vocabulary: not eligible for derived requests
    rep = pd.DataFrame(rows)
    for c in ("fit", "length"):
        rep[f"{c}_label_source"] = rep[f"{c}_label"].map(lambda v: None if v is None else "structured")
    return rep


REP = make_final_rep()
REP_GEN = generation_view(REP)
SUP = build_support_tables(REP_GEN)
VARIANTS = {k: v for k, v in default_variants(4, 4, 0, policy_variants=False).items() if k in ("A_baseline", "B3_proposal_plus_repair")}
CTX = CTX_FULL
