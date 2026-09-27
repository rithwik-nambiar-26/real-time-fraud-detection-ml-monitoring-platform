"""WebSocket handler for live transaction streaming."""

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database import SessionLocal, TransactionDB
from app.schemas import TransactionInput
from app.services.transactions import transaction_service
from app.logging import get_request_id

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: dict) -> None:
        dead: list[WebSocket] = []
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


@router.websocket("/ws/transactions")
async def transaction_stream(ws: WebSocket) -> None:
    """Stream new scored transactions to connected clients."""
    connection_id = str(uuid.uuid4())
    logger.info(
        "WebSocket connection opened",
        extra={"connection_id": connection_id},
    )
    await manager.connect(ws)
    last_id = 0

    try:
        db: Session = SessionLocal()
        try:
            latest = db.query(TransactionDB).order_by(TransactionDB.id.desc()).first()
            if latest:
                last_id = latest.id
        finally:
            db.close()

        while True:
            db = SessionLocal()
            try:
                new_txns = (
                    db.query(TransactionDB)
                    .filter(TransactionDB.id > last_id)
                    .order_by(TransactionDB.id.asc())
                    .all()
                )

                for txn in new_txns:
                    await ws.send_json({
                        "type": "transaction",
                        "data": {
                            "transaction_id": txn.transaction_id,
                            "amount": txn.amount,
                            "merchant_category": txn.merchant_category,
                            "fraud_score": txn.fraud_score,
                            "risk_level": txn.risk_level,
                            "is_fraud": txn.is_fraud,
                            "latency_ms": txn.latency_ms,
                            "scored_at": txn.scored_at.isoformat(),
                        },
                    })
                    last_id = txn.id
            finally:
                db.close()
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        logger.info(
            "WebSocket connection closed by client",
            extra={"connection_id": connection_id},
        )
        manager.disconnect(ws)
    except Exception as exc:
        logger.error(
            f"Unexpected error in WebSocket connection: {exc}",
            extra={"connection_id": connection_id},
            exc_info=True,
        )
        try:
            await ws.close(code=1011)  # Internal error
        except Exception:
            pass
        manager.disconnect(ws)


async def notify_new_transaction(result: dict) -> None:
    """Broadcast a newly scored transaction."""
    await manager.broadcast({"type": "transaction", "data": result})