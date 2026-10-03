"""Soft-preference conflict detection. Conflicts warn; they never reject a request."""
from __future__ import annotations

from typing import Any

# fit -> stretch -> compatibility in [-1, 1]. <0 triggers a 'preference_conflict' warning.
FIT_STRETCH_COMPAT: dict[str, dict[str, float]] = {
    "slim":      {"high": 1.0, "low": 1.0, "none": -0.3},   # V1 slim also covers former skinny
    "regular":   {"high": 0.0, "low": 0.0, "none": 0.0},
    "relaxed":   {"none": 1.0, "low": 0.5, "high": -0.5},
    "oversized": {"none": 1.0, "low": 0.5, "high": -0.5},
}


def fit_stretch_compat(fit: str | None, stretch: str | None) -> float:
    """Compatibility of a stretch level with a fit; 0.0 (neutral) if either is unspecified."""
    if fit is None or stretch is None:
        return 0.0
    return FIT_STRETCH_COMPAT[fit][stretch]


def _w(fields: tuple[str, ...], severity: str, message: str) -> dict[str, Any]:
    return {"code": "preference_conflict", "fields": list(fields), "severity": severity, "message": message}


def detect_conflicts(prefs: dict[str, Any], forbidden: list[str]) -> list[dict[str, Any]]:
    """Warnings for mutually awkward soft preferences / preferences vs hard constraints."""
    out: list[dict[str, Any]] = []
    fit, stretch = prefs.get("fit"), prefs.get("stretch")
    score = fit_stretch_compat(fit, stretch)
    if score < 0:
        out.append(_w(("fit", "stretch"), "strong" if score <= -1.0 else "mild",
                      f"fit={fit} is usually not paired with stretch={stretch}"))
    if prefs.get("breathability") == "high" and prefs.get("water_repellent"):
        out.append(_w(("breathability", "water_repellent"), "mild",
                      "water-repellent evidence (coating/membrane) works against the breathability proxy"))
    if prefs.get("thermal_warmth") == "heavy" and prefs.get("breathability") == "high":
        out.append(_w(("thermal_warmth", "breathability"), "mild",
                      "heavy warmth proxies (filling/padding) work against the breathability proxy"))
    if stretch in ("low", "high") and "elastane" in forbidden:
        out.append(_w(("stretch", "forbidden_materials"), "strong",
                      "stretch proxy is elastane-based but elastane is forbidden"))
    if prefs.get("moisture_wicking") and {"polyester", "nylon"} <= set(forbidden):
        out.append(_w(("moisture_wicking", "forbidden_materials"), "strong",
                      "moisture-wicking proxy rewards polyester/nylon, both forbidden"))
    if prefs.get("preferred_dominant_material") == "elastane" and stretch == "none":
        out.append(_w(("preferred_dominant_material", "stretch"), "strong",
                      "elastane-dominant composition contradicts stretch=none"))
    return out
