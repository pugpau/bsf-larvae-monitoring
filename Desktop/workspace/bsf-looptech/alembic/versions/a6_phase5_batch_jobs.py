"""Phase 5 Migration: batch_job_runs

Revision ID: a6_phase5_batch
Revises: a5_phase4_rag
Create Date: 2026-02-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a6_phase5_batch"
down_revision = "a5_phase4_rag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "batch_job_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("result_summary", postgresql.JSON, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
    )
    op.create_index("ix_batch_job_runs_job_name", "batch_job_runs", ["job_name"])
    op.create_index(
        "ix_batch_job_runs_name_started",
        "batch_job_runs",
        ["job_name", "started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_batch_job_runs_name_started", table_name="batch_job_runs")
    op.drop_index("ix_batch_job_runs_job_name", table_name="batch_job_runs")
    op.drop_table("batch_job_runs")
