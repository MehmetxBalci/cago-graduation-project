"""Component selection and material aggregation shared by the rules."""
from __future__ import annotations

from dataclasses import dataclass, field

from cago.oracle.config import COATING_NAME, SURFACE_CLASS, canon_material


@dataclass
class Component:
    """Minimal component view: ordered (material_raw, pct) pairs; pct may be None/NaN if unusable."""
    component_id: str | None
    name: str
    cls: str
    materials: list[tuple[object, object]] = field(default_factory=list)


def _norm(x) -> str:
    return str(x or "").strip().lower()


def make_component(component_id, name, cls, materials) -> Component:
    return Component(component_id, _norm(name), _norm(cls), list(materials))


def aggregate(materials) -> dict[str, float]:
    """Canonicalize materials and sum duplicate names (insertion-ordered). Unparseable pct/blank names skipped.

    Zero/negative percentages are NOT removed here (see `positive_only`).
    """
    out: dict[str, float] = {}
    for raw, pct in materials:
        mat = canon_material(raw)
        if mat is None:
            continue
        try:
            val = float(pct)
        except (TypeError, ValueError):
            continue
        if val != val:  # NaN
            continue
        out[mat] = out.get(mat, 0.0) + val
    return out


def positive_only(agg: dict[str, float]) -> dict[str, float]:
    """Drop aggregated entries with pct <= 0 (applied for SR1-SR3 only)."""
    return {m: p for m, p in agg.items() if p > 0}


def select_readable(comps: list[Component]) -> tuple[Component | None, str | None]:
    """First surface_component, else first component (SR1-SR3)."""
    for c in comps:
        if c.cls == SURFACE_CLASS:
            return c, "surface_component"
    if comps:
        return comps[0], "first_component_fallback"
    return None, None


def select_surface_reference(comps: list[Component]) -> tuple[Component | None, dict[str, float], str | None]:
    """SR5 reference: surface 'coating' -> first surface_component -> first component.

    As in the published implementation, a candidate only qualifies if it has >=1 usable material;
    the final first-component fallback is taken regardless. Pct <= 0 entries are kept in the reference set.
    """
    for c in comps:
        if c.cls == SURFACE_CLASS and c.name == COATING_NAME:
            agg = aggregate(c.materials)
            if agg:
                return c, agg, "surface_coating"
    for c in comps:
        if c.cls == SURFACE_CLASS:
            agg = aggregate(c.materials)
            if agg:
                return c, agg, "surface_component"
    if comps:
        return comps[0], aggregate(comps[0].materials), "first_component_fallback"
    return None, {}, None
