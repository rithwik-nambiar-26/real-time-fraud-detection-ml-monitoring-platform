"""Transaction scoring and persistence service."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.database import TransactionDB
from app.schemas import ScoreResponse, TransactionInput, TransactionRecord
from app.services.monitoring import monitoring
from app.services.predictor import predictor


class TransactionService:
    """Orchestrates scoring, storage, and monitoring hooks."""

    def score_transaction(self, db: Session, txn: TransactionInput) -> ScoreResponse:
        fraud_score, latency_ms = predictor.score(txn)
        monitoring.record_latency(latency_ms)

        risk_level = predictor.classify_risk(fraud_score)
        is_fraud = fraud_score >= settings.fraud_threshold
        scored_at = datetime.now(timezone.utc)

        record = TransactionDB(
            transaction_id=txn.transaction_id,
            amount=txn.amount,
            merchant_category=txn.merchant_category,
            fraud_score=round(fraud_score, 4),
            risk_level=risk_level.value,
            is_fraud=is_fraud,
            latency_ms=round(latency_ms, 2),
            model_version=predictor.version,
            features_json=json.dumps(txn.model_dump()),
            scored_at=scored_at,
        )
        db.add(record)
        db.commit()

        metrics = monitoring.get_metrics(db)
        monitoring.check_and_create_alerts(db, metrics)

        return ScoreResponse(
            transaction_id=txn.transaction_id,
            fraud_score=round(fraud_score, 4),
            risk_level=risk_level,
            is_fraud=is_fraud,
            latency_ms=round(latency_ms, 2),
            model_version=predictor.version,
            scored_at=scored_at,
        )

    def get_recent(self, db: Session, limit: int = 50, fraud_only: bool = False) -> list[TransactionRecord]:
        query = db.query(TransactionDB).order_by(TransactionDB.scored_at.desc())
        if fraud_only:
            query = query.filter(TransactionDB.is_fraud == True)  # noqa: E712
        rows = query.limit(limit).all()

        return [
            TransactionRecord(
                transaction_id=r.transaction_id,
                amount=r.amount,
                merchant_category=r.merchant_category,
                fraud_score=r.fraud_score,
                risk_level=r.risk_level,
                is_fraud=r.is_fraud,
                latency_ms=r.latency_ms,
                model_version=r.model_version,
                scored_at=r.scored_at,
                features=json.loads(r.features_json),
            )
            for r in rows
        ]


transaction_service = TransactionService()
