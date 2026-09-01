"""Backend test suite."""

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use in-memory DB for tests before app imports bind to file DB
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_transaction():
    return {
        "transaction_id": f"test_{uuid.uuid4().hex[:8]}",
        "amount": 150.0,
        "merchant_category": "grocery",
        "transaction_hour": 14,
        "distance_from_home_km": 5.0,
        "prev_transaction_count_24h": 2,
        "avg_transaction_amount_7d": 80.0,
        "is_foreign": False,
        "device_trust_score": 0.9,
    }


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("healthy", "degraded")
    assert data["model_loaded"] is True


def test_score_transaction(client, sample_transaction):
    resp = client.post("/api/v1/score", json=sample_transaction)
    assert resp.status_code == 200
    data = resp.json()
    assert "fraud_score" in data
    assert 0 <= data["fraud_score"] <= 1
    assert data["transaction_id"] == sample_transaction["transaction_id"]
    assert "risk_level" in data
    assert "latency_ms" in data


def test_score_high_risk_transaction(client):
    txn = {
        "transaction_id": f"fraud_{uuid.uuid4().hex[:8]}",
        "amount": 5000.0,
        "merchant_category": "atm",
        "transaction_hour": 2,
        "distance_from_home_km": 300.0,
        "prev_transaction_count_24h": 15,
        "avg_transaction_amount_7d": 50.0,
        "is_foreign": True,
        "device_trust_score": 0.2,
    }
    resp = client.post("/api/v1/score", json=txn)
    assert resp.status_code == 200
    data = resp.json()
    assert data["fraud_score"] > 0.3


def test_list_transactions(client, sample_transaction):
    client.post("/api/v1/score", json=sample_transaction)
    resp = client.get("/api/v1/transactions?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_metrics(client, sample_transaction):
    client.post("/api/v1/score", json=sample_transaction)
    resp = client.get("/api/v1/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_scored" in data
    assert "fraud_rate" in data
    assert "model_version" in data


def test_alerts(client):
    resp = client.get("/api/v1/alerts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_batch_score(client, sample_transaction):
    txns = [
        {**sample_transaction, "transaction_id": f"batch_{uuid.uuid4().hex[:8]}"}
        for _ in range(3)
    ]
    resp = client.post("/api/v1/score/batch", json=txns)
    assert resp.status_code == 200
    assert len(resp.json()) == 3
