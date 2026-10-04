"""SQLAlchemy database models, engine, and session management."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)


def _create_engine_from_url(database_url: str) -> Engine:
    """Create a SQLAlchemy engine with dialect-appropriate configuration.

    - SQLite: uses check_same_thread=False (single-node app / tests).
    - PostgreSQL (and other server DBs): connection pooling with pre-ping
      and connection recycling for reliability.
    """
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite":
        return create_engine(database_url, connect_args={"check_same_thread": False})
    return create_engine(
        database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_pre_ping=True,
        pool_recycle=settings.db_pool_recycle_seconds,
    )


engine = _create_engine_from_url(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class TransactionDB(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(64), unique=True, index=True, nullable=False)
    amount = Column(Float, nullable=False)
    merchant_category = Column(String(32), nullable=False)
    fraud_score = Column(Float, nullable=False)
    risk_level = Column(String(16), nullable=False)
    is_fraud = Column(Boolean, nullable=False)
    latency_ms = Column(Float, nullable=False)
    model_version = Column(String(32), nullable=False)
    features_json = Column(Text, nullable=False)
    scored_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class AlertDB(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(64), unique=True, index=True, nullable=False)
    alert_type = Column(String(32), nullable=False)
    severity = Column(String(16), nullable=False)
    message = Column(Text, nullable=False)
    value = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolved = Column(Boolean, default=False)
    # New lifecycle timestamps
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)


def check_db_connection() -> bool:
    """Return True if the database accepts a simple query."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001 - health check must not raise
        logger.warning("Database connectivity check failed: %s", exc)
        return False


def init_db(max_retries: int = 5, retry_delay_seconds: float = 2.0) -> None:
    """Create all tables, retrying while the database is unavailable.

    Retries handle the case where PostgreSQL is still starting up when the
    application boots (e.g. first `docker compose up`). Raises the last
    error if the database never becomes reachable.
    """
    from app.config import DATA_DIR

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database initialized (attempt %d/%d)", attempt, max_retries)
            return
        except Exception as exc:  # noqa: BLE001 - retry any connection failure
            last_error = exc
            logger.warning(
                "Database initialization failed (attempt %d/%d): %s",
                attempt,
                max_retries,
                exc,
            )
            if attempt < max_retries:
                time.sleep(retry_delay_seconds)
    raise RuntimeError(
        f"Could not initialize database after {max_retries} attempts"
    ) from last_error


def get_db():
    """Dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
