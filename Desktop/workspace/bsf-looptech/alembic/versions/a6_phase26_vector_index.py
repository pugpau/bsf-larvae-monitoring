"""Phase 2-6: HNSW vector index on substrate_knowledge.embedding

Revision ID: a6_phase26_vec_idx
Revises: a5_phase4_rag
Create Date: 2026-02-12
"""
from alembic import op

revision = "a6_phase26_vec_idx"
down_revision = "a5_phase4_rag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_substrate_knowledge_embedding_hnsw "
        "ON substrate_knowledge USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_substrate_knowledge_embedding_hnsw")
