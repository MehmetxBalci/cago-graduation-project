"""Oracle engine: evaluate garments from the processed parquet tables."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from cago.oracle import rules
from cago.oracle.selection import (Component, aggregate, make_component, positive_only, select_readable,
                                   select_surface_reference)


def _j(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=False)


def evaluate_garment(garment_id: str, colour_raw: Any, comps: list[Component],
                     source_row_number: int | None = None) -> dict[str, Any]:
    """Evaluate SR1-SR5 for one garment and return a flat result row."""
    readable_comp, readable_src = select_readable(comps)
    readable = positive_only(aggregate(readable_comp.materials)) if readable_comp else {}
    ordered = rules.sorted_materials(readable)

    v1, r1 = rules.sr1(readable)
    v2, n_fibres = rules.sr2(readable)
    v3, t3 = rules.sr3(readable)
    v4, colour_norm = rules.sr4(colour_raw)
    surf_comp, surf_set, surf_src = select_surface_reference(comps)
    v5, hid_comp, t5 = rules.sr5(comps, surf_set)

    flags = [v1, v2, v3, v4, v5]
    expl = []
    if v1:
        expl.append(f"SR1:{r1}")
    if v2:
        expl.append(f"SR2:{n_fibres}_fibres")
    if v3:
        expl.append("SR3:minor<5%:" + ",".join(f"{t['material']}={t['pct']:g}" for t in t3))
    if v4:
        expl.append("SR4:black")
    if v5:
        expl.append(f"SR5:{hid_comp.name}>5%_absent_from_{surf_comp.name if surf_comp else 'none'}:"
                    + ",".join(f"{t['material']}={t['pct']:g}" for t in t5))
    return {
        "garment_id": garment_id, "source_row_number": source_row_number,
        "readable_component_id": readable_comp.component_id if readable_comp else None,
        "readable_component_name": readable_comp.name if readable_comp else None,
        "readable_component_source": readable_src,
        "readable_materials": _j([{"material": m, "pct": p} for m, p in ordered]),
        "n_distinct_fibres": len(readable),
        "sr1_violation": v1, "sr1_reason": r1,
        "sr2_violation": v2, "sr2_fibre_count": n_fibres,
        "sr3_violation": v3, "sr3_trigger_materials": _j(t3),
        "sr4_violation": v4, "sr4_normalized_colour": colour_norm,
        "sr5_violation": v5,
        "sr5_surface_component": surf_comp.name if surf_comp else None,
        "sr5_surface_component_id": surf_comp.component_id if surf_comp else None,
        "sr5_surface_source": surf_src,
        "sr5_surface_materials": _j(sorted(surf_set)),
        "sr5_hidden_component": hid_comp.name if hid_comp else None,
        "sr5_hidden_component_id": hid_comp.component_id if hid_comp else None,
        "sr5_trigger_materials": _j(t5),
        "violation_count": int(sum(flags)), "any_violation": any(flags),
        "explanation": "; ".join(expl) if expl else "no_baseline_violation",
    }


def load_components(garments: pd.DataFrame, components: pd.DataFrame,
                    component_materials: pd.DataFrame) -> dict[str, list[Component]]:
    """garment_id -> ordered components with ordered materials (from the processed tables)."""
    cm = component_materials.sort_values(["component_id", "material_index"], kind="stable")
    mats: dict[str, list] = {}
    for cid, raw, pct in zip(cm["component_id"], cm["material_raw"], cm["pct"]):
        mats.setdefault(cid, []).append((raw, pct))
    cs = components.sort_values(["garment_id", "component_index"], kind="stable")
    by_g: dict[str, list[Component]] = {}
    for cid, gid, name, cls in zip(cs["component_id"], cs["garment_id"], cs["component_name_normalized"],
                                   cs["component_class"]):
        by_g.setdefault(gid, []).append(make_component(cid, name, cls, mats.get(cid, [])))
    return by_g


def run_oracle(processed_dir: Path) -> pd.DataFrame:
    """Evaluate every garment in `processed_dir` (garments/components/component_materials parquet)."""
    processed_dir = Path(processed_dir)
    g = pd.read_parquet(processed_dir / "garments.parquet",
                        columns=["garment_id", "source_row_number", "variant_colour_raw"])
    c = pd.read_parquet(processed_dir / "components.parquet")
    m = pd.read_parquet(processed_dir / "component_materials.parquet")
    by_g = load_components(g, c, m)
    rows = [evaluate_garment(gid, col, by_g.get(gid, []), int(rn))
            for gid, rn, col in zip(g["garment_id"], g["source_row_number"], g["variant_colour_raw"])]
    return pd.DataFrame(rows)
