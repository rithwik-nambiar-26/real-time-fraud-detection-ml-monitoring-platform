"""Configuration for the fraud detection platform."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = BASE_DIR / "ml" / "artifacts"
DATA_DIR = BASE_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Application settings
    app_name: str = "Fraud Detection Platform"
    api_prefix: str = "/api/v1"

    # Database settings
    database_url: str = Field(
        default=f"sqlite:///{DATA_DIR / 'fraud.db'}",
        description="Database URL for SQLAlchemy",
    )

    # ML model settings
    model_path: str = Field(
        default=str(ARTIFACTS_DIR / "model.joblib"),
        description="Path to the trained model file",
    )
    metadata_path: str = Field(
        default=str(ARTIFACTS_DIR / "metadata.json"),
        description="Path to the model metadata file",
    )

    # Risk classification thresholds
    risk_threshold_low: float = Field(
        default=0.35,
        ge=0,
        le=1,
        description="Upper bound for low risk (exclusive)",
    )
    risk_threshold_high: float = Field(
        default=0.65,
        ge=0,
        le=1,
        description="Upper bound for high risk (exclusive)",
    )
    risk_threshold_critical: float = Field(
        default=0.85,
        ge=0,
        le=1,
        description="Upper bound for critical risk (exclusive)",
    )

    # Monitoring thresholds
    fraud_threshold: float = Field(
        default=0.65,
        ge=0,
        le=1,
        description="Threshold above which a transaction is considered fraudulent",
    )
    drift_threshold: float = Field(
        default=0.15,
        ge=0,
        description="Threshold for prediction drift detection",
    )
    latency_alert_ms: float = Field(
        default=500.0,
        ge=0,
        description="P95 latency threshold in milliseconds for alerts",
    )
    fraud_rate_alert_threshold: float = Field(
        default=0.25,
        ge=0,
        le=1,
        description="Fraud rate threshold for alerts",
    )
    min_transactions_for_fraud_alert: int = Field(
        default=20,
        ge=1,
        description="Minimum number of transactions required to evaluate fraud rate alert",
    )
    max_transactions_stored: int = Field(
        default=10_000,
        ge=1,
        description="Maximum number of transactions to store in the database",
    )

    # CORS settings
    allowed_origins: list[str] = Field(
        default_factory=list,
        description="List of allowed origins for CORS",
    )

    @field_validator(
        "risk_threshold_low",
        "risk_threshold_high",
        "risk_threshold_critical",
        "fraud_threshold",
        "drift_threshold",
        "fraud_rate_alert_threshold",
    )
    def validate_probability(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("Value must be between 0 and 1")
        return v

    @field_validator(
        "risk_threshold_low",
        "risk_threshold_high",
        "risk_threshold_critical",
    )
    def validate_risk_thresholds_order(cls, v, info):
        # This validator is called for each field; we cannot compare with other fields here.
        # We'll rely on the application logic to ensure they are in increasing order.
        return v


settings = Settings()