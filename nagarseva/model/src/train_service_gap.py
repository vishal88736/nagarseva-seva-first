"""Train service-failure classifiers and create service assurance scores."""

from __future__ import annotations

import json
from pathlib import Path
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit

from features import ARTIFACTS, fairness_report, load_joined, numeric_frame

FEATURES = ["water_hours_per_day", "toilets_per_100_people", "outage_hours_per_week", "waste_collection_frequency", "drain_blockage_incidents", "flood_risk_score", "pct_below_poverty", "population"]


def train() -> dict:
    df = load_joined()
    X = numeric_frame(df, FEATURES)
    failure = ((df.water_hours_per_day.fillna(0) < 4) | (df.toilets_per_100_people.fillna(0) < 15) | (df.outage_hours_per_week.fillna(0) > 12) | (df.waste_collection_frequency.fillna(0) < 3)).astype(int)
    split = GroupShuffleSplit(n_splits=1, test_size=.22, random_state=2026)
    train, test = next(split.split(X, groups=df.ward.fillna("unknown")))
    model = RandomForestClassifier(n_estimators=100, max_depth=7, random_state=2026, class_weight="balanced")
    model.fit(X.iloc[train], failure.iloc[train])
    probability = model.predict_proba(X.iloc[test])[:, 1]
    metrics = {"model": "random_forest_service_gap", "synthetic": True, "split": "held-out wards", "f1": round(f1_score(failure.iloc[test], probability > .5), 3), "roc_auc": round(roc_auc_score(failure.iloc[test], probability), 3), "fairness_check_mae_by_city_income": fairness_report(df, failure.iloc[test].to_numpy(), probability, test)}
    joblib.dump({"model": model, "features": FEATURES}, ARTIFACTS / "service_gap_model.joblib")
    all_probability = model.predict_proba(X)[:, 1]
    (ARTIFACTS / "service_gap_scores.csv").write_text("pocket_id,failure_probability,assurance_index\n" + "\n".join(f"{pid},{prob:.4f},{100 - prob * 100:.1f}" for pid, prob in zip(df.pocket_id, all_probability)), encoding="utf-8")
    (ARTIFACTS / "service_gap_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    try:
        import matplotlib.pyplot as plt
        plt.figure(figsize=(6, 4)); plt.bar(FEATURES, model.feature_importances_, color="#f3a712"); plt.xticks(rotation=40, ha="right"); plt.title("Service-gap feature importance"); plt.tight_layout(); plt.savefig(Path(__file__).resolve().parents[2] / "presentation/assets/service_gap_importance.png", dpi=130); plt.close()
    except Exception:
        pass
    return metrics


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
