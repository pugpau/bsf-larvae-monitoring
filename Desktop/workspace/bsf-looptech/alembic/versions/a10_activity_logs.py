"""Activity logs — persistent audit trail for workflow events

Revision ID: a10_activity_logs
Revises: a9_formulation_records
Create Date: 2026-02-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "a10_activity_logs"
down_revision = "a9_formulation_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "activity_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(20), nullable=False, server_default="info"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
    )

    op.create_index("ix_activity_logs_event_type", "activity_logs", ["event_type"])
    op.create_index("ix_activity_logs_entity", "activity_logs", ["entity_type", "entity_id"])
    op.create_index("ix_activity_logs_created", "activity_logs", ["created_at"])
    op.create_index("ix_activity_logs_user_created", "activity_logs", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_activity_logs_user_created")
    op.drop_index("ix_activity_logs_created")
    op.drop_index("ix_activity_logs_entity")
    op.drop_index("ix_activity_logs_event_type")
    op.drop_table("activity_logs")
