"""WebSocket handler for live transaction streaming."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database import SessionLocal, TransactionDB
from app.schemas import TransactionInput
from app.services.transactions import transaction_service

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
    await manager.connect(ws)
    last_id = 0

    try:
        db: Session = SessionLocal()
        latest = db.query(TransactionDB).order_by(TransactionDB.id.desc()).first()
        if latest:
            last_id = latest.id
        db.close()

        while True:
            db = SessionLocal()
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

            db.close()
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(ws)


async def notify_new_transaction(result: dict) -> None:
    """Broadcast a newly scored transaction."""
    await manager.broadcast({"type": "transaction", "data": result})
