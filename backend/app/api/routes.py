"""REST API routes for fraud scoring and monitoring."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import Alert, MetricsSummary, ScoreResponse, TransactionInput, TransactionRecord
from app.services.monitoring import monitoring
from app.services.transactions import transaction_service

router = APIRouter()


@router.post("/score", response_model=ScoreResponse)
def score_transaction(
    txn: TransactionInput,
    db: Annotated[Session, Depends(get_db)],
) -> ScoreResponse:
    """Score a single transaction for fraud risk."""
    return transaction_service.score_transaction(db, txn)


@router.post("/score/batch", response_model=list[ScoreResponse])
def score_batch(
    transactions: list[TransactionInput],
    db: Annotated[Session, Depends(get_db)],
) -> list[ScoreResponse]:
    """Score multiple transactions."""
    return [transaction_service.score_transaction(db, txn) for txn in transactions]


@router.get("/transactions", response_model=list[TransactionRecord])
def list_transactions(
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=500),
    fraud_only: bool = Query(default=False),
) -> list[TransactionRecord]:
    """List recent scored transactions."""
    return transaction_service.get_recent(db, limit=limit, fraud_only=fraud_only)


@router.get("/metrics", response_model=MetricsSummary)
def get_metrics(
    db: Annotated[Session, Depends(get_db)],
    window_minutes: int = Query(default=60, ge=5, le=1440),
) -> MetricsSummary:
    """Get ML monitoring metrics."""
    return monitoring.get_metrics(db, window_minutes=window_minutes)


@router.get("/alerts", response_model=list[Alert])
def get_alerts(
    db: Annotated[Session, Depends(get_db)],
    include_resolved: bool = Query(default=False),
) -> list[Alert]:
    """Get monitoring alerts."""
    return monitoring.get_alerts(db, include_resolved=include_resolved)


@router.put("/alerts/{alert_id}/acknowledge", response_model=Alert)
def acknowledge_alert(
    alert_id: str,
    db: Annotated[Session, Depends(get_db)],
):
    """Mark an alert as acknowledged."""
    alert_db = monitoring.get_alert(db, alert_id)
    if not alert_db:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert_db.resolved:
        raise HTTPException(status_code=400, detail="Alert already resolved")
    if alert_db.acknowledged_at:
        raise HTTPException(status_code=400, detail="Alert already acknowledged")
    alert_db.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    return Alert(
        id=alert_db.alert_id,
        alert_type=alert_db.alert_type,
        severity=alert_db.severity,
        message=alert_db.message,
        value=alert_db.value,
        threshold=alert_db.threshold,
        created_at=alert_db.created_at,
        resolved=alert_db.resolved,
        acknowledged_at=alert_db.acknowledged_at,
        resolved_at=alert_db.resolved_at,
    )


@router.put("/alerts/{alert_id}/resolve", response_model=Alert)
def resolve_alert(
    alert_id: str,
    db: Annotated[Session, Depends(get_db)],
):
    """Mark an alert as resolved."""
    alert_db = monitoring.get_alert(db, alert_id)
    if not alert_db:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert_db.resolved:
        raise HTTPException(status_code=400, detail="Alert already resolved")
    alert_db.resolved = True
    alert_db.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return Alert(
        id=alert_db.alert_id,
        alert_type=alert_db.alert_type,
        severity=alert_db.severity,
        message=alert_db.message,
        value=alert_db.value,
        threshold=alert_db.threshold,
        created_at=alert_db.created_at,
        resolved=alert_db.resolved,
        acknowledged_at=alert_db.acknowledged_at,
        resolved_at=alert_db.resolved_at,
    )
