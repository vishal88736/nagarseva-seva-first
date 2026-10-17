"""Train multilingual-friendly character n-gram grievance classifier."""

from __future__ import annotations

import json
from pathlib import Path
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split

from features import ARTIFACTS, read_table


def train() -> dict:
    df = read_table("grievances.csv")
    train_df, test_df = train_test_split(df, test_size=.2, random_state=2026, stratify=df.category)
    pipe = Pipeline([("tfidf", TfidfVectorizer(analyzer="char", ngram_range=(2, 5), min_df=1, sublinear_tf=True)), ("classifier", LogisticRegression(max_iter=300, class_weight="balanced"))])
    pipe.fit(train_df.text, train_df.category)
    pred = pipe.predict(test_df.text)
    report = classification_report(test_df.category, pred, output_dict=True, zero_division=0)
    metrics = {"model": "char_tfidf_logistic_regression", "synthetic": True, "macro_f1": round(f1_score(test_df.category, pred, average="macro"), 3), "per_class_f1": {k: round(v.get("f1-score", 0), 3) for k, v in report.items() if isinstance(v, dict)}}
    joblib.dump(pipe, ARTIFACTS / "grievance_model.joblib")
    (ARTIFACTS / "grievance_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
