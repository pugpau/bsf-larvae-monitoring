-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- HNSW index on substrate_knowledge.embedding is managed by
-- Alembic migration a6_phase26_vector_index (not here, as this
-- file only runs during Docker initdb on first container creation).
