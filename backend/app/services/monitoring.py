"""ML monitoring: metrics aggregation, drift detection, and alerting."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from app.config import settings
from app.database import AlertDB, TransactionDB
from app.schemas import Alert, MetricsSummary
from app.services.predictor import predictor


class MonitoringService:
    """Tracks model performance and detects anomalies."""

    def __init__(self) -> None:
        self._recent_latencies: list[float] = []
        self._max_latency_buffer = 1000

    def record_latency(self, latency_ms: float) -> None:
        self._recent_latencies.append(latency_ms)
        if len(self._recent_latencies) > self._max_latency_buffer:
            self._recent_latencies = self._recent_latencies[-self._max_latency_buffer:]

    def _compute_drift(self, scores: list[float]) -> tuple[float, bool]:
        """Compare current score distribution to training reference."""
        if not scores or not predictor.metadata:
            return 0.0, False

        ref = predictor.metadata.get("reference_stats", {})
        ref_mean = ref.get("mean_score", 0.1)
        ref_std = max(ref.get("std_score", 0.1), 0.01)

        current_mean = float(np.mean(scores))
        drift_score = abs(current_mean - ref_mean) / ref_std
        drift_detected = drift_score > settings.drift_threshold
        return round(drift_score, 4), drift_detected

    def get_metrics(self, db: Session, window_minutes: int = 60) -> MetricsSummary:
        """Compute monitoring metrics for the given time window."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        txns = (
            db.query(TransactionDB)
            .filter(TransactionDB.scored_at >= cutoff)
            .order_by(TransactionDB.scored_at.desc())
            .all()
        )

        total = len(txns)
        if total == 0:
            return MetricsSummary(
                total_scored=0,
                fraud_rate=0.0,
                avg_latency_ms=0.0,
                p95_latency_ms=0.0,
                throughput_per_minute=0.0,
                model_version=predictor.version,
                drift_score=0.0,
                drift_detected=False,
                score_distribution={},
                risk_distribution={},
                window_minutes=window_minutes,
            )

        fraud_count = sum(1 for t in txns if t.is_fraud)
        latencies = [t.latency_ms for t in txns]
        scores = [t.fraud_score for t in txns]

        score_bins = {"0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0}
        for s in scores:
            if s < 0.2:
                score_bins["0-0.2"] += 1
            elif s < 0.4:
                score_bins["0.2-0.4"] += 1
            elif s < 0.6:
                score_bins["0.4-0.6"] += 1
            elif s < 0.8:
                score_bins["0.6-0.8"] += 1
            else:
                score_bins["0.8-1.0"] += 1

        risk_dist: dict[str, int] = defaultdict(int)
        for t in txns:
            risk_dist[t.risk_level] += 1

        drift_score, drift_detected = self._compute_drift(scores)

        return MetricsSummary(
            total_scored=total,
            fraud_rate=round(fraud_count / total, 4),
            avg_latency_ms=round(float(np.mean(latencies)), 2),
            p95_latency_ms=round(float(np.percentile(latencies, 95)), 2),
            throughput_per_minute=round(total / window_minutes, 2),
            model_version=predictor.version,
            drift_score=drift_score,
            drift_detected=drift_detected,
            score_distribution=dict(score_bins),
            risk_distribution=dict(risk_dist),
            window_minutes=window_minutes,
        )

    def check_and_create_alerts(self, db: Session, metrics: MetricsSummary) -> list[Alert]:
        """Evaluate thresholds and persist new alerts."""
        new_alerts: list[Alert] = []
        checks = []

        if metrics.drift_detected:
            checks.append({
                "type": "drift",
                "severity": "warning",
                "message": f"Prediction drift detected (score={metrics.drift_score:.2f})",
                "value": metrics.drift_score,
                "threshold": settings.drift_threshold,
            })

        if metrics.p95_latency_ms > settings.latency_alert_ms:
            checks.append({
                "type": "latency",
                "severity": "critical" if metrics.p95_latency_ms > settings.latency_alert_ms * 2 else "warning",
                "message": f"P95 latency elevated ({metrics.p95_latency_ms:.0f}ms)",
                "value": metrics.p95_latency_ms,
                "threshold": settings.latency_alert_ms,
            })

        if metrics.fraud_rate > 0.25 and metrics.total_scored >= 20:
            checks.append({
                "type": "fraud_spike",
                "severity": "critical",
                "message": f"Fraud rate spike ({metrics.fraud_rate:.1%})",
                "value": metrics.fraud_rate,
                "threshold": 0.25,
            })

        # Existing alert types remain active until resolved.
        existing_types = {a.alert_type for a in db.query(AlertDB).filter(AlertDB.resolved == False)}
        for check in checks:
            if check["type"] in existing_types:
                continue
            alert_id = f"alert_{uuid.uuid4().hex[:8]}"
            alert_db = AlertDB(
                alert_id=alert_id,
                alert_type=check["type"],
                severity=check["severity"],
                message=check["message"],
                value=check["value"],
                threshold=check["threshold"],
            )
            db.add(alert_db)
            new_alerts.append(Alert(
                id=alert_id,
                alert_type=check["type"],
                severity=check["severity"],
                message=check["message"],
                value=check["value"],
                threshold=check["threshold"],
                created_at=alert_db.created_at,
            ))

        if new_alerts:
            db.commit()

        return new_alerts

    def get_alerts(self, db: Session, include_resolved: bool = False) -> list[Alert]:
        query = db.query(AlertDB).order_by(AlertDB.created_at.desc())
        if not include_resolved:
            query = query.filter(AlertDB.resolved == False)  # noqa: E712
        return [
            Alert(
                id=a.alert_id,
                alert_type=a.alert_type,
                severity=a.severity,
                message=a.message,
                value=a.value,
                threshold=a.threshold,
                created_at=a.created_at,
                resolved=a.resolved,
                acknowledged_at=a.acknowledged_at,
                resolved_at=a.resolved_at,
            )
            for a in query.limit(50).all()
        ]

    def get_alert(self, db: Session, alert_id: str) -> AlertDB | None:
        """Retrieve a specific alert by its id."""
        return db.query(AlertDB).filter(AlertDB.alert_id == alert_id).first()


monitoring = MonitoringService()
