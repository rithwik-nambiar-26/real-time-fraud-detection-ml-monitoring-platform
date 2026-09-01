"""Configuration for the fraud detection platform."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = BASE_DIR / "ml" / "artifacts"
DATA_DIR = BASE_DIR / "data"


class Settings(BaseSettings):
    app_name: str = "Fraud Detection Platform"
    api_prefix: str = "/api/v1"
    database_url: str = os.environ.get("DATABASE_URL", f"sqlite:///{DATA_DIR / 'fraud.db'}")
    model_path: str = str(ARTIFACTS_DIR / "model.joblib")
    metadata_path: str = str(ARTIFACTS_DIR / "metadata.json")

    fraud_threshold: float = 0.65
    drift_threshold: float = 0.15
    latency_alert_ms: float = 500.0
    max_transactions_stored: int = 10_000

    class Config:
        env_file = ".env"


settings = Settings()
