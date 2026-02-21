"""Formulation records — linking delivery/waste to recipe workflow

Revision ID: a9_formulation_records
Revises: a8_recipe_versions
Create Date: 2026-02-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "a9_formulation_records"
down_revision = "a8_recipe_versions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "formulation_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("waste_record_id", UUID(as_uuid=True), sa.ForeignKey("waste_records.id"), nullable=False),
        sa.Column("recipe_id", UUID(as_uuid=True), sa.ForeignKey("recipes.id"), nullable=True),
        sa.Column("recipe_version", sa.Integer(), nullable=True),
        sa.Column("prediction_id", UUID(as_uuid=True), sa.ForeignKey("ml_predictions.id"), nullable=True),
        sa.Column("source_type", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(20), nullable=False, server_default="proposed"),
        sa.Column("planned_formulation", sa.JSON(), nullable=True),
        sa.Column("actual_formulation", sa.JSON(), nullable=True),
        sa.Column("elution_result", sa.JSON(), nullable=True),
        sa.Column("elution_passed", sa.Boolean(), nullable=True),
        sa.Column("estimated_cost", sa.Float(), nullable=True),
        sa.Column("actual_cost", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("reasoning", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_formulation_records_waste_record", "formulation_records", ["waste_record_id"])
    op.create_index("ix_formulation_records_status", "formulation_records", ["status"])
    op.create_index("ix_formulation_records_created", "formulation_records", ["created_at"])


def downgrade() -> None:
    op.drop_table("formulation_records")
