"""Phase 2-6: HNSW vector index on substrate_knowledge.embedding

Revision ID: a6_phase26_vec_idx
Revises: a5_phase4_rag
Create Date: 2026-02-12
"""
from alembic import op
import sqlalchemy as sa

revision = "a6_phase26_vec_idx"
down_revision = "a6_phase5_batch"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    try:
        conn.execute(sa.text("SAVEPOINT hnsw_idx"))
        conn.execute(sa.text(
            "CREATE INDEX IF NOT EXISTS ix_substrate_knowledge_embedding_hnsw "
            "ON substrate_knowledge USING hnsw (embedding vector_cosine_ops)"
        ))
        conn.execute(sa.text("RELEASE SAVEPOINT hnsw_idx"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT hnsw_idx"))
        # pgvector not installed — skip HNSW index (dev environment)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_substrate_knowledge_embedding_hnsw")
