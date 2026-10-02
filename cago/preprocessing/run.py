"""Orchestration: build tables, split, write parquet + audit."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from cago.config.settings import SPLIT_RATIOS, SPLIT_SEED
from cago.preprocessing.audit import build_audit, write_reports
from cago.preprocessing.pipeline import build_tables
from cago.preprocessing.split import assign_splits


def run(input_path: Path, support_dir: Path, output_dir: Path, seed: int = SPLIT_SEED,
        ratios: tuple[float, float, float] = SPLIT_RATIOS) -> dict[str, Any]:
    """Run the full preprocessing pipeline and write all outputs. Returns tables + audit."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    t = build_tables(Path(input_path), Path(support_dir))
    split_map = assign_splits(t["garments"], ratios, seed)
    audit, unmapped = build_audit(t, split_map, Path(support_dir), Path(input_path),
                                  {"seed": seed, "ratios": list(ratios), "method": "sha256-ordered parent groups, cut by cumulative garment-row share"})
    for name in ("garments", "components", "component_materials"):
        t[name].to_parquet(output_dir / f"{name}.parquet", index=False)
    split_map.to_parquet(output_dir / "split_mapping.parquet", index=False)
    write_reports(audit, unmapped, output_dir)
    return {**t, "split_mapping": split_map, "audit": audit, "unmapped": unmapped}
