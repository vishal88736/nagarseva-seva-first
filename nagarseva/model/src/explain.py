"""Human-readable feature explanations with optional SHAP integration."""

from __future__ import annotations

from typing import Any
import math

REASONS = {
    "pct_below_poverty": ("high poverty exposure", "increase priority"),
    "density_per_ha": ("high population density", "increase priority"),
    "pct_kutcha_houses": ("many structurally vulnerable homes", "increase priority"),
    "flood_risk_score": ("flood exposure", "increase priority"),
    "fire_risk_score": ("fire exposure", "increase priority"),
    "structural_risk_score": ("structural risk", "increase priority"),
    "distance_to_hospital_km": ("limited access to a hospital", "increase priority"),
    "water_hours_per_day": ("low daily water supply", "increase priority"),
    "outage_hours_per_week": ("frequent power outages", "increase priority"),
    "tenure_security_score": ("tenure uncertainty", "increase priority"),
}


def priority_reasons(row: dict[str, Any], limit: int = 4) -> list[dict[str, Any]]:
    values = []
    for feature, (label, direction) in REASONS.items():
        value = row.get(feature)
        if value is None:
            continue
        numeric = float(value)
        if not math.isfinite(numeric):
            continue
        # Feature signal strength, explicitly not a model attribution or a share of the prediction.
        contribution = numeric / 100
        if feature.startswith("pct_"):
            contribution = numeric
        if feature == "density_per_ha":
            contribution = numeric / 2000
        if feature == "outage_hours_per_week":
            contribution = numeric / 24
        if feature == "water_hours_per_day":
            contribution = 1 - numeric / 12
        if feature == "tenure_security_score":
            contribution = 1 - numeric / 100
        if feature == "distance_to_hospital_km":
            contribution = min(numeric / 10, 1)
        values.append({"feature": feature, "label": label, "value": round(numeric, 2), "contribution": round(min(1, max(0, contribution)) * 100, 1), "direction": direction})
    return sorted(values, key=lambda item: item["contribution"], reverse=True)[:limit]


def shap_values_if_available(model: Any, X: Any) -> Any:
    try:
        import shap  # type: ignore
        return shap.Explainer(model)(X)
    except Exception:
        return None
