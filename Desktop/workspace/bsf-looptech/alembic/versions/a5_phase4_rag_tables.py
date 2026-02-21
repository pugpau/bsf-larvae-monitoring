"""Phase 4 Migration: substrate_knowledge + chat_sessions + chat_messages

Revision ID: a5_phase4_rag
Revises: a4_phase3_ml
Create Date: 2026-02-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a5_phase4_rag"
down_revision = "a4_phase3_ml"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # substrate_knowledge — pgvector embedding column
    op.create_table(
        "substrate_knowledge",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False, server_default="manual"),
        sa.Column("metadata_json", postgresql.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_substrate_knowledge_title", "substrate_knowledge", ["title"])
    # Add vector column via raw SQL (pgvector extension required)
    conn = op.get_bind()
    try:
        conn.execute(sa.text("SAVEPOINT vector_col"))
        conn.execute(sa.text("ALTER TABLE substrate_knowledge ADD COLUMN embedding vector(768)"))
        conn.execute(sa.text("RELEASE SAVEPOINT vector_col"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT vector_col"))
        # pgvector not installed — skip embedding column (dev environment)

    op.create_table(
        "chat_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(200), nullable=False, server_default="New Chat"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("context_chunks", postgresql.JSON, nullable=True),
        sa.Column("token_count", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])
    op.create_index("ix_chat_messages_created", "chat_messages", ["created_at"])


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("substrate_knowledge")
