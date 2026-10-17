"""Train CPU-friendly cost and delay estimators."""

from __future__ import annotations

import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupShuffleSplit

from features import ARTIFACTS, read_table

FEATURES = ["units", "carpet_area_sqft", "land_value_per_sqm", "FSI", "cross_subsidy_ratio"]


def train() -> dict:
    df = read_table("redevelopment_projects.csv")
    X = df[FEATURES].apply(pd.to_numeric, errors="coerce").fillna(df[FEATURES].median())
    splitter = GroupShuffleSplit(n_splits=1, test_size=.22, random_state=2026)
    train_idx, test_idx = next(splitter.split(X, groups=df.ward.fillna("unknown")))
    eval_cost = RandomForestRegressor(n_estimators=100, random_state=2026, min_samples_leaf=3)
    eval_delay = RandomForestRegressor(n_estimators=100, random_state=2026, min_samples_leaf=3)
    eval_cost.fit(X.iloc[train_idx], df.construction_cost_per_sqft.iloc[train_idx]); eval_delay.fit(X.iloc[train_idx], df.delay_months.iloc[train_idx])
    cost_test = eval_cost.predict(X.iloc[test_idx]); delay_test = eval_delay.predict(X.iloc[test_idx])
    metrics = {"model": "random_forest_cost_delay", "synthetic": True, "split": "held-out wards", "cost_mae": round(mean_absolute_error(df.construction_cost_per_sqft.iloc[test_idx], cost_test), 1), "cost_r2": round(r2_score(df.construction_cost_per_sqft.iloc[test_idx], cost_test), 3), "delay_mae_months": round(mean_absolute_error(df.delay_months.iloc[test_idx], delay_test), 1), "delay_r2": round(r2_score(df.delay_months.iloc[test_idx], delay_test), 3), "interval": "empirical +/- 1.28 residual standard deviations"}
    model_cost = RandomForestRegressor(n_estimators=100, random_state=2026, min_samples_leaf=3)
    model_delay = RandomForestRegressor(n_estimators=100, random_state=2026, min_samples_leaf=3)
    model_cost.fit(X, df.construction_cost_per_sqft); model_delay.fit(X, df.delay_months)
    cost_pred = model_cost.predict(X); delay_pred = model_delay.predict(X)
    joblib.dump({"cost": model_cost, "delay": model_delay, "features": FEATURES, "cost_residual_std": float(np.std(df.construction_cost_per_sqft - cost_pred)), "delay_residual_std": float(np.std(df.delay_months - delay_pred))}, ARTIFACTS / "cost_model.joblib")
    (ARTIFACTS / "cost_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
