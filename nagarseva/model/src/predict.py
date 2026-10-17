"""Small programmatic prediction facade used by notebooks and integrations."""

from __future__ import annotations

from functools import lru_cache
from typing import Any
import joblib
import numpy as np
import pandas as pd

try:
    from .explain import priority_reasons
    from .features import ARTIFACTS, PRIORITY_FEATURES, numeric_frame, service_index, tier
except ImportError:  # Running this file directly from model/src.
    from explain import priority_reasons
    from features import ARTIFACTS, PRIORITY_FEATURES, numeric_frame, service_index, tier


@lru_cache(maxsize=None)
def _artifact(name: str) -> Any:
    return joblib.load(ARTIFACTS / name)


def predict_priority(features: dict[str, Any]) -> dict[str, Any]:
    model_bundle = _artifact("priority_model.joblib")
    row = pd.DataFrame([features])
    score = float(np.clip(model_bundle["model"].predict(numeric_frame(row, model_bundle["features"]))[0], 0, 100))
    return {"priority_score": round(score, 1), "tier": tier(score), "reasons": priority_reasons(features), "synthetic": True}


def recommend_intervention(features: dict[str, Any]) -> dict[str, Any]:
    bundle = _artifact("intervention_model.joblib")
    row = pd.DataFrame([features])
    probabilities = bundle["model"].predict_proba(numeric_frame(row, bundle["features"]))[0]
    classes = bundle["model"].classes_
    top = sorted(({"type": str(label), "probability": round(float(prob), 3)} for label, prob in zip(classes, probabilities)), key=lambda item: item["probability"], reverse=True)[:2]
    return {"top_options": top, "reasons": ["Model output is a planning aid; validate risk, tenure and resident preference."]}


def predict_service_failure(features: dict[str, Any]) -> dict[str, Any]:
    bundle = _artifact("service_gap_model.joblib")
    row = pd.DataFrame([features])
    probability = float(bundle["model"].predict_proba(numeric_frame(row, bundle["features"]))[0, 1])
    return {"failure_probability_90d": round(probability, 3), "assurance_index": round(100 - probability * 100, 1), "service_assurance": service_index(pd.Series(features)), "synthetic": True}


def estimate_cost(features: dict[str, Any]) -> dict[str, Any]:
    bundle = _artifact("cost_model.joblib")
    row = pd.DataFrame([features])[bundle["features"]]
    value = float(bundle["cost"].predict(row)[0]); delay = float(bundle["delay"].predict(row)[0])
    return {"construction_cost_per_sqft": round(value), "cost_interval": [round(value - bundle["cost_residual_std"] * 1.28), round(value + bundle["cost_residual_std"] * 1.28)], "expected_delay_months": round(delay, 1), "synthetic": True}


def classify_grievance(text: str) -> dict[str, Any]:
    model = _artifact("grievance_model.joblib")
    return {"category": str(model.predict([text])[0]), "confidence": round(float(max(model.predict_proba([text])[0])), 3), "synthetic": True}
