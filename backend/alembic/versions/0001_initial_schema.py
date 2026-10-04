"""Initial schema: transactions and alerts tables.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-04

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("transaction_id", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("merchant_category", sa.String(length=32), nullable=False),
        sa.Column("fraud_score", sa.Float(), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("is_fraud", sa.Boolean(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("model_version", sa.String(length=32), nullable=False),
        sa.Column("features_json", sa.Text(), nullable=False),
        sa.Column("scored_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transactions_transaction_id", "transactions", ["transaction_id"], unique=True)
    op.create_index("ix_transactions_scored_at", "transactions", ["scored_at"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("alert_id", sa.String(length=64), nullable=False),
        sa.Column("alert_type", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_alert_id", "alerts", ["alert_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_alerts_alert_id", table_name="alerts")
    op.drop_table("alerts")
    op.drop_index("ix_transactions_scored_at", table_name="transactions")
    op.drop_index("ix_transactions_transaction_id", table_name="transactions")
    op.drop_table("transactions")
