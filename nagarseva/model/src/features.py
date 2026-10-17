"""Shared feature engineering and deterministic policy scoring helpers."""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "synthetic"
ARTIFACTS = ROOT / "artifacts"

PRIORITY_FEATURES = [
    "pct_below_poverty", "density_per_ha", "pct_kutcha_houses", "flood_risk_score",
    "fire_risk_score", "structural_risk_score", "distance_to_hospital_km",
    "tenure_security_score", "water_hours_per_day", "toilets_per_100_people",
    "outage_hours_per_week", "waste_collection_frequency",
]


def read_table(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / name)


def load_joined() -> pd.DataFrame:
    pockets = read_table("slum_pockets.csv")
    services = read_table("service_access.csv")
    return pockets.merge(services, on="pocket_id", how="left")


def numeric_frame(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    result = df.reindex(columns=columns).copy()
    return result.apply(pd.to_numeric, errors="coerce").fillna(result.median(numeric_only=True)).fillna(0)


def minmax(series: pd.Series, low: float | None = None, high: float | None = None) -> pd.Series:
    s = series.astype(float).fillna(series.median())
    if low is None:
        low = float(s.quantile(.05))
    if high is None:
        high = float(s.quantile(.95))
    return ((s - low) / max(high - low, 1e-6)).clip(0, 1)


def policy_priority(df: pd.DataFrame) -> pd.Series:
    """Transparent target used to train the priority model."""
    need = (
        .20 * minmax(df.pct_below_poverty) + .15 * minmax(df.density_per_ha)
        + .14 * minmax(df.pct_kutcha_houses) + .12 * minmax(df.flood_risk_score)
        + .12 * minmax(df.fire_risk_score) + .12 * minmax(df.structural_risk_score)
        + .08 * minmax(df.outage_hours_per_week) + .07 * (1 - minmax(df.water_hours_per_day, 0, 12))
    )
    return (need * 100).clip(0, 100)


def tier(score: float) -> str:
    if pd.isna(score):
        return "Unassessed"
    if score >= 75:
        return "Critical"
    if score >= 55:
        return "High"
    if score >= 35:
        return "Medium"
    return "Low"


def service_index(row: pd.Series) -> dict[str, float]:
    def value(key: str, default: float = 0) -> float:
        raw = row.get(key, default)
        try:
            numeric = float(raw)
            return default if np.isnan(numeric) else numeric
        except (TypeError, ValueError):
            return default

    return {
        "water": float(np.clip(value("water_hours_per_day") / 12 * 100, 0, 100)),
        "sanitation": float(np.clip(value("toilets_per_100_people") / 30 * 100, 0, 100)),
        "power": float(np.clip(100 - value("outage_hours_per_week", 24) / 24 * 100, 0, 100)),
        "waste": float(np.clip(value("waste_collection_frequency") / 7 * 100, 0, 100)),
        "health": float(np.clip((value("clinic_within_1km") + value("anganwadi_within_500m")) / 2 * 100, 0, 100)),
    }


def fairness_report(df: pd.DataFrame, actual: pd.Series | np.ndarray, predicted: pd.Series | np.ndarray, indexes: np.ndarray | list[int]) -> dict[str, dict[str, float]]:
    """Small group audit used in metrics files for city and income bands."""
    view = df.iloc[indexes].copy().reset_index(drop=True)
    view["actual"] = np.asarray(actual)
    view["predicted"] = np.asarray(predicted)
    view["absolute_error"] = (view.actual - view.predicted).abs()
    income = view.get("avg_household_income_inr", pd.Series(np.nan, index=view.index))
    view["income_band"] = pd.qcut(income.rank(method="first"), q=3, labels=["low", "middle", "high"], duplicates="drop") if income.notna().any() else "unknown"
    result: dict[str, dict[str, float]] = {}
    for group_column in ["city", "income_band"]:
        if group_column not in view:
            continue
        result[group_column] = {str(group): round(float(group_frame.absolute_error.mean()), 3) for group, group_frame in view.groupby(group_column, observed=False)}
    return result
