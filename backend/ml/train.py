"""Fraud detection model training pipeline."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml.data_generator import FEATURE_COLUMNS, save_training_data

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "training.csv"

NUMERIC_FEATURES = [
    "amount",
    "transaction_hour",
    "distance_from_home_km",
    "prev_transaction_count_24h",
    "avg_transaction_amount_7d",
    "device_trust_score",
]
CATEGORICAL_FEATURES = ["merchant_category"]
BOOLEAN_FEATURES = ["is_foreign"]


def build_pipeline() -> Pipeline:
    """Build sklearn preprocessing + classifier pipeline."""
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
            ("bool", "passthrough", BOOLEAN_FEATURES),
        ]
    )

    classifier = RandomForestClassifier(
        n_estimators=100,
        max_depth=12,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    return Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", classifier),
    ])


def train_model(data_path: Path | None = None) -> dict:
    """Train model and save artifacts."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    if data_path is None or not data_path.exists():
        data_path = save_training_data(DATA_PATH)

    df = pd.read_csv(data_path)
    X = df[FEATURE_COLUMNS]
    y = df["is_fraud"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_proba)
    report = classification_report(y_test, y_pred, output_dict=True)

    version = datetime.now(timezone.utc).strftime("v%Y.%m.%d.%H%M")
    model_path = ARTIFACTS_DIR / "model.joblib"
    joblib.dump(pipeline, model_path)

    # Reference distribution for drift detection
    ref_scores = pipeline.predict_proba(X_train)[:, 1]
    reference_stats = {
        "mean_score": float(np.mean(ref_scores)),
        "std_score": float(np.std(ref_scores)),
        "score_histogram": np.histogram(ref_scores, bins=10, range=(0, 1))[0].tolist(),
    }

    metadata = {
        "version": version,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "fraud_rate": float(y.mean()),
        "roc_auc": round(auc, 4),
        "classification_report": report,
        "feature_columns": FEATURE_COLUMNS,
        "reference_stats": reference_stats,
    }

    metadata_path = ARTIFACTS_DIR / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Model trained: {model_path}")
    print(f"ROC-AUC: {auc:.4f}")
    print(f"Version: {version}")

    return metadata


if __name__ == "__main__":
    train_model()
