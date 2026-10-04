"""Tests for database engine configuration and session lifecycle."""
import os

# Set the test database URL BEFORE importing app modules
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.database
from app.database import Base, _create_engine_from_url, check_db_connection
from app.config import settings


def test_sqlite_engine_uses_check_same_thread_false():
    engine = _create_engine_from_url("sqlite:///:memory:")
    assert engine.dialect.name == "sqlite"
    engine.dispose()


def test_postgres_engine_uses_pooling_config():
    # Create with a postgres URL but do NOT connect; only inspect configuration.
    engine = _create_engine_from_url(
        "postgresql+psycopg2://user:pass@localhost:5432/dbname"
    )
    assert engine.dialect.name == "postgresql"
    assert engine.pool.size() == settings.db_pool_size
    assert engine.pool._max_overflow == settings.db_max_overflow
    assert engine.pool._pre_ping is True
    engine.dispose()


def test_check_db_connection_success():
    # check_db_connection uses the module-level engine, which tests replace
    # with an in-memory SQLite engine via the fixture below.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    original = app.database.engine
    app.database.engine = engine
    try:
        assert check_db_connection() is True
    finally:
        app.database.engine = original
        engine.dispose()


def test_check_db_connection_failure_returns_false():
    # An invalid driver/URL engine that fails on connect.
    engine = create_engine("sqlite:////nonexistent_dir_xyz/db.sqlite")
    original = app.database.engine
    app.database.engine = engine
    try:
        assert check_db_connection() is False
    finally:
        app.database.engine = original
        engine.dispose()


def test_init_db_creates_tables():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    original_engine = app.database.engine
    original_session = app.database.SessionLocal
    app.database.engine = engine
    app.database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    try:
        app.database.init_db(max_retries=1)
        with engine.connect() as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                )
            }
        assert "transactions" in tables
        assert "alerts" in tables
    finally:
        app.database.engine = original_engine
        app.database.SessionLocal = original_session
        engine.dispose()


def test_session_closes_correctly():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = TestSession()
    session.execute(text("SELECT 1"))
    session.close()
    # A closed session can be reused by SQLAlchemy (it re-acquires a
    # connection); verify it no longer holds an active transaction/connection.
    assert not session.in_transaction()
    engine.dispose()
