"""Synthetic credit card transaction data generation."""

from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import pandas as pd

MERCHANT_CATEGORIES = [
    "grocery",
    "restaurant",
    "retail",
    "gas",
    "travel",
    "entertainment",
    "healthcare",
    "online",
    "atm",
    "transfer",
]

FEATURE_COLUMNS = [
    "amount",
    "merchant_category",
    "transaction_hour",
    "distance_from_home_km",
    "prev_transaction_count_24h",
    "avg_transaction_amount_7d",
    "is_foreign",
    "device_trust_score",
]


def _generate_fraud_label(row: pd.Series, rng: np.random.Generator) -> int:
    """Rule-based fraud label with noise for realistic training data."""
    score = 0.0

    if row["amount"] > row["avg_transaction_amount_7d"] * 3:
        score += 0.35
    if row["distance_from_home_km"] > 100:
        score += 0.25
    if row["prev_transaction_count_24h"] > 8:
        score += 0.2
    if row["is_foreign"]:
        score += 0.15
    if row["device_trust_score"] < 0.4:
        score += 0.25
    if row["transaction_hour"] in (0, 1, 2, 3, 4):
        score += 0.1
    if row["merchant_category"] in ("atm", "transfer", "online"):
        score += 0.1

    noise = rng.uniform(-0.15, 0.15)
    return int(score + noise > 0.45)


def generate_transactions(n_samples: int = 5000, fraud_rate: float = 0.08, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic transaction dataset."""
    rng = np.random.default_rng(seed)
    random.seed(seed)

    records = []
    for i in range(n_samples):
        is_fraud_seed = rng.random() < fraud_rate
        avg_amount = float(rng.uniform(20, 200))

        if is_fraud_seed:
            amount = float(rng.uniform(avg_amount * 2, avg_amount * 8))
            distance = float(rng.uniform(50, 500))
            prev_count = int(rng.integers(5, 20))
            device_trust = float(rng.uniform(0.1, 0.5))
            is_foreign = bool(rng.random() > 0.3)
            hour = int(rng.choice([0, 1, 2, 3, 4, 22, 23, rng.integers(8, 20)]))
            category = rng.choice(["atm", "transfer", "online", "retail", "travel"])
        else:
            amount = float(rng.lognormal(np.log(avg_amount), 0.4))
            distance = float(rng.exponential(15))
            prev_count = int(rng.poisson(2))
            device_trust = float(rng.uniform(0.6, 1.0))
            is_foreign = bool(rng.random() < 0.05)
            hour = int(rng.integers(6, 23))
            category = rng.choice(MERCHANT_CATEGORIES)

        row = {
            "transaction_id": f"txn_{i:06d}",
            "amount": round(amount, 2),
            "merchant_category": category,
            "transaction_hour": hour,
            "distance_from_home_km": round(distance, 2),
            "prev_transaction_count_24h": prev_count,
            "avg_transaction_amount_7d": round(avg_amount, 2),
            "is_foreign": is_foreign,
            "device_trust_score": round(device_trust, 3),
        }
        row["is_fraud"] = _generate_fraud_label(pd.Series(row), rng)
        records.append(row)

    return pd.DataFrame(records)


def save_training_data(output_path: Path | None = None, n_samples: int = 5000) -> Path:
    """Generate and save training CSV."""
    if output_path is None:
        output_path = Path(__file__).resolve().parent.parent / "data" / "training.csv"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = generate_transactions(n_samples=n_samples)
    df.to_csv(output_path, index=False)
    return output_path
