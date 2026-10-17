"""Train priority regression and intervention recommendation models."""

from __future__ import annotations

import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, r2_score, confusion_matrix
from sklearn.model_selection import GroupShuffleSplit

from features import ARTIFACTS, PRIORITY_FEATURES, fairness_report, load_joined, numeric_frame, policy_priority, tier


def _split(df: pd.DataFrame):
    wards = df.ward.fillna("unknown")
    splitter = GroupShuffleSplit(n_splits=1, test_size=.22, random_state=2026)
    train, test = next(splitter.split(df, groups=wards))
    return train, test


def train() -> dict:
    ARTIFACTS.mkdir(exist_ok=True)
    df = load_joined()
    target = policy_priority(df)
    train_idx, test_idx = _split(df)
    X = numeric_frame(df, PRIORITY_FEATURES)
    model = GradientBoostingRegressor(n_estimators=120, max_depth=2, learning_rate=.05, random_state=2026, loss="huber")
    model.fit(X.iloc[train_idx], target.iloc[train_idx])
    pred = np.clip(model.predict(X.iloc[test_idx]), 0, 100)
    metrics = {"model": "gradient_boosting_priority", "synthetic": True, "split": "held-out wards", "r2": round(r2_score(target.iloc[test_idx], pred), 3), "mae": round(mean_absolute_error(target.iloc[test_idx], pred), 2), "rank_correlation": round(float(pd.Series(target.iloc[test_idx].to_numpy()).corr(pd.Series(pred), method="spearman")), 3), "fairness_check_mae_by_city_income": fairness_report(df, target.iloc[test_idx].to_numpy(), pred, test_idx)}
    joblib.dump({"model": model, "features": PRIORITY_FEATURES}, ARTIFACTS / "priority_model.joblib")
    all_scores = np.clip(model.predict(X), 0, 100)
    df[["pocket_id"]].assign(priority_score=np.round(all_scores, 2), tier=[tier(x) for x in all_scores]).to_csv(ARTIFACTS / "priority_scores.csv", index=False)
    # Intervention target is a policy label derived from constraints, useful for a demo.
    labels = np.select([(df.land_ownership.isin(["forest", "CRZ"]) | (df.flood_risk_score > 82)), (df.pct_kutcha_houses > .46) & (df.tenure_security_score > 50), (df.tenure_security_score < 34)], ["relocation", "in_situ_SRA", "rental_housing"], default="upgrading")
    clf = GradientBoostingClassifier(n_estimators=90, max_depth=2, random_state=2026)
    clf.fit(X.iloc[train_idx], labels[train_idx])
    int_pred = clf.predict(X.iloc[test_idx])
    metrics.update({"intervention_macro_f1": round(f1_score(labels[test_idx], int_pred, average="macro"), 3), "intervention_accuracy": round(accuracy_score(labels[test_idx], int_pred), 3), "intervention_labels": sorted(set(labels))})
    joblib.dump({"model": clf, "features": PRIORITY_FEATURES}, ARTIFACTS / "intervention_model.joblib")
    try:
        import matplotlib.pyplot as plt
        plt.figure(figsize=(8, 4)); plt.barh(PRIORITY_FEATURES, model.feature_importances_, color="#0f9d9a"); plt.title("Priority model feature importance (synthetic)"); plt.tight_layout(); plt.savefig(Path(__file__).resolve().parents[2] / "presentation/assets/priority_feature_importance.png", dpi=130); plt.close()
        cm = confusion_matrix(labels[test_idx], int_pred, labels=sorted(set(labels)))
        plt.figure(figsize=(5, 4)); plt.imshow(cm, cmap="Blues"); plt.xticks(range(len(set(labels))), sorted(set(labels)), rotation=35, ha="right"); plt.yticks(range(len(set(labels))), sorted(set(labels))); plt.title("Intervention recommendation confusion matrix"); plt.tight_layout(); plt.savefig(Path(__file__).resolve().parents[2] / "presentation/assets/intervention_confusion_matrix.png", dpi=130); plt.close()
    except Exception:
        pass
    (ARTIFACTS / "priority_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
