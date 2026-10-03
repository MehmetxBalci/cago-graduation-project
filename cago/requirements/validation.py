"""Request validation (hard errors, soft warnings) and hard-constraint checks for generated candidates."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from cago.config.settings import CANDIDATE_PCT_SUM_ABS_TOL
from cago.preprocessing.colours import normalize_colour
from cago.preprocessing.materials import material_key
from cago.requirements.capabilities import controls_for, load_capabilities
from cago.requirements.conflicts import detect_conflicts
from cago.requirements.schema import (ALL_FIELDS, CAPABILITY_FIELDS, ENUMS, REMOVED_V1_VALUES, REQUIRED_FIELDS,
                                      SOFT_FIELDS, TRUE_ONLY_FIELDS, Issue, RequirementResult)


@dataclass
class RequirementContext:
    """Everything validation needs; built from processed data + vocabulary + capabilities."""
    target_segments: frozenset[str]                # dataset gender_section values (women/men/kids/baby)
    categories: frozenset[str]
    materials: frozenset[str]                       # valid canonical material names
    capabilities: dict[str, Any]
    aliases: dict[str, str] = field(default_factory=dict)
    component_classes: frozenset[str] = frozenset()
    component_names: frozenset[str] = frozenset()
    ml_tokens: frozenset[str] = frozenset({"OTHER", "PAD"})   # training-only tokens: never physical materials

    @classmethod
    def from_processed(cls, processed_dir: Path, capabilities_path: Path | None = None) -> "RequirementContext":
        d = Path(processed_dir)
        g = pd.read_parquet(d / "garments.parquet", columns=["gender_section", "detail_category"])
        vocab = json.loads((d / "ml_material_vocabulary.json").read_text(encoding="utf-8"))
        caps = load_capabilities(capabilities_path) if capabilities_path else load_capabilities(d / "category_capabilities.json")
        return cls(frozenset(g["gender_section"].dropna().unique()),  # provenance column -> target_segment values
                   frozenset(g["detail_category"].dropna().unique()),
                   frozenset(vocab["canonical_to_token"]), caps, vocab.get("material_aliases", {}),
                   frozenset(vocab.get("component_classes", [])), frozenset(vocab.get("component_names", [])),
                   frozenset(vocab["special_tokens"]))


def resolve_material(name: Any, ctx: RequirementContext) -> str | None:
    """Canonical material for a user string (canonical name or known source alias), else None."""
    key = material_key(name)
    if key is None:
        return None
    if key in ctx.materials:
        return key
    return ctx.aliases.get(key) if ctx.aliases.get(key) in ctx.materials else None


def _err(errors: list[Issue], code: str, fld: str, msg: str) -> None:
    errors.append(Issue(code, fld, msg))


def validate_request(raw: Any, ctx: RequirementContext) -> RequirementResult:
    """Validate and normalize a user request. Errors: missing/invalid required fields, unknown fields/values,
    unknown materials. Warnings (never failures): preference conflicts, disabled controls, ignored preferences."""
    errors: list[Issue] = []
    if not isinstance(raw, dict):
        return RequirementResult(False, None, [Issue("invalid_request", None, "request must be an object")])
    for k in raw:
        if k not in ALL_FIELDS:
            _err(errors, "unknown_field", str(k), f"unknown field '{k}'")

    norm: dict[str, Any] = {}
    for f_, allowed, code in (("target_segment", ctx.target_segments, "invalid_target_segment"), ("detail_category", ctx.categories, "invalid_detail_category")):
        v = raw.get(f_)
        if v is None or (isinstance(v, str) and not v.strip()):
            _err(errors, "missing_required_field", f_, f"'{f_}' is required")
        elif not isinstance(v, str) or v.strip().casefold() not in allowed:
            _err(errors, code, f_, f"{v!r} is not one of {sorted(allowed)}")
        else:
            norm[f_] = v.strip().casefold()

    soft: dict[str, Any] = {k: None for k in SOFT_FIELDS}
    for f_, allowed in ENUMS.items():
        v = raw.get(f_)
        if v is None:
            continue
        removed = REMOVED_V1_VALUES.get(f_, {})
        if isinstance(v, str) and v.strip().casefold() in removed:
            hint = removed[v.strip().casefold()]
            _err(errors, "removed_in_v1", f_, f"{v!r} was removed in V1" + (f"; use {hint!r}" if hint else "")
                 + f" (allowed: {list(allowed)})")
        elif not isinstance(v, str) or v.strip().casefold() not in allowed:
            _err(errors, "invalid_value", f_, f"{v!r} is not one of {list(allowed)} (use null for no preference)")
        else:
            soft[f_] = v.strip().casefold()
    for f_ in TRUE_ONLY_FIELDS:
        v = raw.get(f_)
        if v is None:
            continue
        if v is not True:
            _err(errors, "invalid_value", f_, f"{v!r} is not allowed: use true or null")
        else:
            soft[f_] = True

    colour = raw.get("colour")
    if colour is not None:
        c = normalize_colour(colour)
        if c is None:
            _err(errors, "invalid_value", "colour", "colour must be a non-empty string or null")
        else:
            soft["colour"] = c

    forbidden: list[str] = []
    fm = raw.get("forbidden_materials")
    if fm is not None:
        if not isinstance(fm, list):
            _err(errors, "invalid_value", "forbidden_materials", "must be a list of material names or null")
        else:
            for item in fm:
                canon = resolve_material(item, ctx)
                if canon is None:
                    _err(errors, "unknown_material", "forbidden_materials", f"unknown material {item!r}")
                elif canon not in forbidden:
                    forbidden.append(canon)
    pdm = raw.get("preferred_dominant_material")
    if pdm is not None:
        canon = resolve_material(pdm, ctx)
        if canon is None:
            _err(errors, "unknown_material", "preferred_dominant_material", f"unknown material {pdm!r}")
        else:
            soft["preferred_dominant_material"] = canon

    if errors:
        return RequirementResult(False, None, errors)

    warnings: list[dict[str, Any]] = []
    ignored: dict[str, Any] = {}
    controls = controls_for(ctx.capabilities, norm["detail_category"])
    for f_ in CAPABILITY_FIELDS:
        if soft[f_] is not None and not controls.get(f_, False):
            ignored[f_] = soft[f_]
            soft[f_] = None
            warnings.append({"code": "control_not_available", "fields": [f_], "severity": "info",
                             "message": f"'{f_}' is not available for {norm['detail_category']}; preference ignored"})
    if soft["preferred_dominant_material"] in forbidden:
        warnings.append({"code": "preference_conflict", "fields": ["preferred_dominant_material", "forbidden_materials"],
                         "severity": "hard_override",
                         "message": "preferred dominant material is forbidden; the hard constraint wins and the preference is ignored"})
        ignored["preferred_dominant_material"] = soft["preferred_dominant_material"]
        soft["preferred_dominant_material"] = None
    warnings += detect_conflicts(soft, forbidden)

    request = {"target_segment": norm["target_segment"], "detail_category": norm["detail_category"],
               "hard_constraints": {"forbidden_materials": sorted(forbidden)},
               "soft_preferences": soft, "warnings": warnings, "ignored_preferences": ignored}
    return RequirementResult(True, request, [], warnings)


def validate_candidate(components: list[dict[str, Any]], forbidden: list[str], ctx: RequirementContext) -> list[Issue]:
    """Hard-constraint check for a generated garment (list of components with materials=[{material,pct}]).

    Checks: vocabulary (material/class/name when known), pct >= 0, per-component sum == 100 within
    CANDIDATE_PCT_SUM_ABS_TOL (stricter than the 99-101 source-data tolerance), forbidden materials never present.
    PAD/OTHER are training-only tokens and are rejected as physical materials. Returns [] when valid.
    """
    issues: list[Issue] = []
    forb = set(forbidden)
    for i, c in enumerate(components):
        tag = f"component[{i}]"
        if ctx.component_classes and c.get("component_class") not in ctx.component_classes:
            issues.append(Issue("unknown_component_class", tag, f"{c.get('component_class')!r}"))
        name = c.get("component_name_normalized", c.get("component_name"))
        if ctx.component_names and name not in ctx.component_names:
            issues.append(Issue("unknown_component_name", tag, f"{name!r}"))
        pcts: list[float] = []
        for m in c.get("materials", []):
            mat, pct = m.get("material"), m.get("pct")
            if isinstance(mat, str) and mat.strip().casefold() in {t.casefold() for t in ctx.ml_tokens}:
                issues.append(Issue("non_physical_token", tag, f"{mat!r} is a training-only token, not a material"))
            elif mat not in ctx.materials:
                issues.append(Issue("unknown_material", tag, f"{mat!r}"))
            if mat in forb:
                issues.append(Issue("forbidden_material_present", tag, f"{mat}"))
            if not isinstance(pct, (int, float)) or isinstance(pct, bool) or pct != pct:
                issues.append(Issue("invalid_percentage", tag, f"{mat}: {pct!r}"))
                continue
            if pct < 0:
                issues.append(Issue("negative_percentage", tag, f"{mat}: {pct}"))
            pcts.append(float(pct))
        total = math.fsum(pcts)
        if abs(total - 100.0) > CANDIDATE_PCT_SUM_ABS_TOL:
            issues.append(Issue("percentage_sum_out_of_tolerance", tag, f"sum={total!r} (must equal 100)"))
    return issues
