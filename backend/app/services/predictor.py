"""ML model loading and fraud scoring service."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from app.config import settings
from app.schemas import RiskLevel, TransactionInput
from ml.data_generator import FEATURE_COLUMNS


class FraudPredictor:
    """Loads and serves the fraud detection model."""

    def __init__(self) -> None:
        self.model = None
        self.metadata: dict[str, Any] = {}
        self._loaded = False

    def load(self) -> bool:
        """Load model and metadata from disk."""
        model_path = Path(settings.model_path)
        metadata_path = Path(settings.metadata_path)

        if not model_path.exists():
            from ml.train import train_model

            train_model()

        self.model = joblib.load(model_path)

        if metadata_path.exists():
            with open(metadata_path) as f:
                self.metadata = json.load(f)

        self._loaded = True
        return True

    @property
    def is_loaded(self) -> bool:
        return self._loaded and self.model is not None

    @property
    def version(self) -> str:
        return self.metadata.get("version", "unknown")

    def _to_dataframe(self, txn: TransactionInput) -> pd.DataFrame:
        data = txn.model_dump()
        return pd.DataFrame([{col: data[col] for col in FEATURE_COLUMNS}])

    def score(self, txn: TransactionInput) -> tuple[float, float]:
        """Return (fraud_probability, latency_ms)."""
        if not self.is_loaded:
            raise RuntimeError("Model not loaded")

        start = time.perf_counter()
        df = self._to_dataframe(txn)
        proba = float(self.model.predict_proba(df)[0, 1])
        latency_ms = (time.perf_counter() - start) * 1000
        return proba, latency_ms

    @staticmethod
    def classify_risk(fraud_score: float) -> RiskLevel:
        if fraud_score >= settings.risk_threshold_critical:
            return RiskLevel.CRITICAL
        if fraud_score >= settings.risk_threshold_high:
            return RiskLevel.HIGH
        if fraud_score >= settings.risk_threshold_low:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW


predictor = FraudPredictor()