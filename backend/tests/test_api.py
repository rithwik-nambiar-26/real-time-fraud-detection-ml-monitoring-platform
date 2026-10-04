"""Backend test suite."""
import os
import uuid

# Set the test database URL BEFORE importing app modules
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    # Create test engine with StaticPool to share in-memory database
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Replace the engine in the app.database module
    import app.database
    # Dispose the old engine to close any connections
    app.database.engine.dispose()
    # Replace the engine
    app.database.engine = test_engine
    # Recreate SessionLocal with the new engine
    app.database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # Create all tables
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = app.database.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db
    yield
    fastapi_app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="module")
def client():
    with TestClient(fastapi_app) as c:
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
    txn1 = {**sample_transaction, "transaction_id": f"batch_{uuid.uuid4().hex[:8]}"}
    txn2 = {**sample_transaction, "transaction_id": f"batch_{uuid.uuid4().hex[:8]}"}
    txn3 = {**sample_transaction, "transaction_id": f"batch_{uuid.uuid4().hex[:8]}"}
    txns = [txn1, txn2, txn3]
    resp = client.post("/api/v1/score/batch", json=txns)
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def _create_alert(alert_id: str) -> None:
    """Insert an alert row directly via the test session."""
    import app.database
    from app.database import AlertDB

    db = app.database.SessionLocal()
    try:
        db.add(AlertDB(
            alert_id=alert_id,
            alert_type="drift",
            severity="warning",
            message="Test alert",
            value=1.0,
            threshold=0.15,
            resolved=False,
        ))
        db.commit()
    finally:
        db.close()


def test_acknowledge_alert(client):
    alert_id = f"alert_{uuid.uuid4().hex[:8]}"
    _create_alert(alert_id)

    resp = client.put(f"/api/v1/alerts/{alert_id}/acknowledge")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == alert_id
    assert data["acknowledged_at"] is not None
    assert data["resolved"] is False

    # Acknowledging twice is rejected
    resp = client.put(f"/api/v1/alerts/{alert_id}/acknowledge")
    assert resp.status_code == 400


def test_resolve_alert(client):
    alert_id = f"alert_{uuid.uuid4().hex[:8]}"
    _create_alert(alert_id)

    resp = client.put(f"/api/v1/alerts/{alert_id}/resolve")
    assert resp.status_code == 200
    data = resp.json()
    assert data["resolved"] is True
    assert data["resolved_at"] is not None

    # Resolving twice is rejected
    resp = client.put(f"/api/v1/alerts/{alert_id}/resolve")
    assert resp.status_code == 400

    # Acknowledging a resolved alert is rejected
    resp = client.put(f"/api/v1/alerts/{alert_id}/acknowledge")
    assert resp.status_code == 400


def test_drift_computation_matches_baseline(client):
    """Drift is a z-score of the window's mean score vs the training baseline.

    With the default drift_threshold=0.15, even one transaction scoring
    more than ~0.15 standard deviations from the reference mean is flagged.
    This test locks in that intended behavior.
    """
    from app.services.monitoring import monitoring
    from app.services.predictor import predictor

    ref = predictor.metadata["reference_stats"]
    mean, std = ref["mean_score"], ref["std_score"]

    # No scores → no drift
    assert monitoring._compute_drift([]) == (0.0, False)

    # Score equal to the reference mean → zero drift
    score, detected = monitoring._compute_drift([mean])
    assert score == 0.0
    assert detected is False

    # One score one std above the mean → drift 1.0 > 0.15 → detected
    score, detected = monitoring._compute_drift([mean + std])
    assert score == 1.0
    assert detected is True


def test_acknowledge_resolve_unknown_alert(client):
    resp = client.put("/api/v1/alerts/nonexistent_alert/acknowledge")
    assert resp.status_code == 404
    resp = client.put("/api/v1/alerts/nonexistent_alert/resolve")
    assert resp.status_code == 404