"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TransactionInput(BaseModel):
    transaction_id: str = Field(..., examples=["txn_001"])
    amount: float = Field(..., gt=0, examples=[125.50])
    merchant_category: str = Field(..., examples=["grocery"])
    transaction_hour: int = Field(..., ge=0, le=23, examples=[14])
    distance_from_home_km: float = Field(..., ge=0, examples=[5.2])
    prev_transaction_count_24h: int = Field(..., ge=0, examples=[3])
    avg_transaction_amount_7d: float = Field(..., ge=0, examples=[85.0])
    is_foreign: bool = Field(default=False, examples=[False])
    device_trust_score: float = Field(default=0.8, ge=0, le=1, examples=[0.85])


class ScoreResponse(BaseModel):
    transaction_id: str
    fraud_score: float
    risk_level: RiskLevel
    is_fraud: bool
    latency_ms: float
    model_version: str
    scored_at: datetime


class TransactionRecord(ScoreResponse):
    amount: float
    merchant_category: str
    features: dict


class MetricsSummary(BaseModel):
    total_scored: int
    fraud_rate: float
    avg_latency_ms: float
    p95_latency_ms: float
    throughput_per_minute: float
    model_version: str
    drift_score: float
    drift_detected: bool
    score_distribution: dict[str, int]
    risk_distribution: dict[str, int]
    window_minutes: int = 60


class Alert(BaseModel):
    id: str
    alert_type: str
    severity: str
    message: str
    value: float
    threshold: float
    created_at: datetime
    resolved: bool = False
    # New fields for alert lifecycle
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: Optional[str] = None
    database_connected: bool
