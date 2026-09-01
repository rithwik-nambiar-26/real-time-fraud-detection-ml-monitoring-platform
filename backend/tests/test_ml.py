"""Tests for ML training pipeline."""

import json
from pathlib import Path

import joblib
import pytest

from ml.data_generator import FEATURE_COLUMNS, generate_transactions
from ml.train import ARTIFACTS_DIR, train_model


def test_generate_transactions():
    df = generate_transactions(n_samples=100, seed=42)
    assert len(df) == 100
    assert "is_fraud" in df.columns
    for col in FEATURE_COLUMNS:
        assert col in df.columns
    assert df["is_fraud"].sum() > 0


def test_train_model():
    metadata = train_model()
    assert "version" in metadata
    assert "roc_auc" in metadata
    assert metadata["roc_auc"] > 0.7

    model_path = ARTIFACTS_DIR / "model.joblib"
    assert model_path.exists()
    model = joblib.load(model_path)
    assert hasattr(model, "predict_proba")

    metadata_path = ARTIFACTS_DIR / "metadata.json"
    assert metadata_path.exists()
    with open(metadata_path) as f:
        saved = json.load(f)
    assert saved["version"] == metadata["version"]
