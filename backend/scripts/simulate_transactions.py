"""Simulate real-time transaction stream for demo/testing."""

from __future__ import annotations

import argparse
import random
import time
import uuid

import httpx

from ml.data_generator import MERCHANT_CATEGORIES, generate_transactions

API_URL = "http://localhost:8000/api/v1/score"


def simulate(count: int = 50, delay: float = 0.5, fraud_bias: float = 0.15) -> None:
    """Send synthetic transactions to the scoring API."""
    df = generate_transactions(n_samples=count * 2, seed=random.randint(0, 99999))

    sent = 0
    with httpx.Client(timeout=10.0) as client:
        for _, row in df.iterrows():
            if sent >= count:
                break

            payload = {
                "transaction_id": f"sim_{uuid.uuid4().hex[:8]}",
                "amount": float(row["amount"]),
                "merchant_category": str(row["merchant_category"]),
                "transaction_hour": int(row["transaction_hour"]),
                "distance_from_home_km": float(row["distance_from_home_km"]),
                "prev_transaction_count_24h": int(row["prev_transaction_count_24h"]),
                "avg_transaction_amount_7d": float(row["avg_transaction_amount_7d"]),
                "is_foreign": bool(row["is_foreign"]),
                "device_trust_score": float(row["device_trust_score"]),
            }

            try:
                resp = client.post(API_URL, json=payload)
                resp.raise_for_status()
                result = resp.json()
                flag = "FRAUD" if result["is_fraud"] else "OK"
                print(
                    f"[{flag}] {payload['transaction_id']} "
                    f"score={result['fraud_score']:.3f} "
                    f"risk={result['risk_level']} "
                    f"${payload['amount']:.2f} {payload['merchant_category']}"
                )
                sent += 1
            except httpx.HTTPError as e:
                print(f"Error: {e}")
                break

            time.sleep(delay)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate transaction stream")
    parser.add_argument("-n", "--count", type=int, default=30, help="Number of transactions")
    parser.add_argument("-d", "--delay", type=float, default=0.8, help="Delay between txns (seconds)")
    args = parser.parse_args()
    simulate(count=args.count, delay=args.delay)
