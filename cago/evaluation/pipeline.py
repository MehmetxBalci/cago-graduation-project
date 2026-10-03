"""End-to-end for one request: generate (frozen baseline) -> hard gate -> evaluate -> Pareto -> select -> explain."""
from __future__ import annotations

from typing import Any

import pandas as pd

from cago.evaluation.candidate import evaluate_request_candidates
from cago.evaluation.config import EvaluationConfig
from cago.evaluation.explanations import explain_candidate
from cago.generation.baseline import GenerationConfig, generate_baseline
from cago.generation.support_tables import SupportTables
from cago.optimization.pareto import pareto_sort
from cago.optimization.selection import select_designs
from cago.preprocessing.ids import stable_hash
from cago.requirements.validation import RequirementContext


def evaluate_and_select(request: dict[str, Any], rep: pd.DataFrame, support: SupportTables, ctx: RequirementContext,
                        gen_cfg: GenerationConfig = GenerationConfig(), cfg: EvaluationConfig = EvaluationConfig(),
                        res: dict[str, Any] | None = None) -> dict[str, Any]:
    res = res or generate_baseline(request, rep, support, ctx, gen_cfg)
    ev = evaluate_request_candidates(res, support, ctx, cfg)
    valid = ev["valid"]
    summary = pareto_sort(valid, cfg.objective_decimals) if valid else {"dimensions": [], "front_size": 0, "n_candidates": 0}
    sel = select_designs(valid, summary["dimensions"], cfg) if valid else {"selections": [], "by_role": {}, "front_size": 0}
    cmap = {c["candidate_id"]: c for c in res["candidates"]}
    emap = {e["candidate_id"]: e for e in valid}
    tmap = {t.garment_id: t for t in res["templates"]}
    explanations = [explain_candidate(cmap[s["candidate_id"]], emap[s["candidate_id"]], ev["templates"][cmap[s["candidate_id"]]["template_garment_id"]],
                                      tmap[cmap[s["candidate_id"]]["template_garment_id"]], s["roles"], cfg) for s in sel["selections"]]
    digest = stable_hash([[e["candidate_id"], e["objectives"], e["pareto_rank"]] for e in valid], sel["by_role"], length=24)
    return {"request": request, "generation": res, "evaluation": ev, "pareto": summary, "selection": sel,
            "explanations": explanations, "digest": digest}
