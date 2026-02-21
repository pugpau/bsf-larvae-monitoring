"""Phase 3 Migration: ml_models + ml_predictions

Revision ID: a4_phase3_ml
Revises: a3_phase1_rc
Create Date: 2026-02-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a4_phase3_ml"
down_revision = "a3_phase1_rc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ml_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, index=True),
        sa.Column("model_type", sa.String(30), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("training_records", sa.Integer, nullable=False),
        sa.Column("feature_columns", postgresql.JSON, nullable=True),
        sa.Column("target_columns", postgresql.JSON, nullable=True),
        sa.Column("metrics", postgresql.JSON, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_ml_models_type_active", "ml_models", ["model_type", "is_active"])

    op.create_table(
        "ml_predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("waste_record_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("waste_records.id"), nullable=True),
        sa.Column("model_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("ml_models.id"), nullable=True),
        sa.Column("input_features", postgresql.JSON, nullable=False),
        sa.Column("prediction", postgresql.JSON, nullable=False),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("actual_formulation", postgresql.JSON, nullable=True),
        sa.Column("actual_passed", sa.Boolean, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_ml_predictions_waste_record", "ml_predictions", ["waste_record_id"])
    op.create_index("ix_ml_predictions_created", "ml_predictions", ["created_at"])


def downgrade() -> None:
    op.drop_table("ml_predictions")
    op.drop_table("ml_models")
