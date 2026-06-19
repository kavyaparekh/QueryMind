-- Vector store for semantic schema retrieval (Phase 2).
-- Populated by backend/scripts/embed_schema.py after Chinook is seeded.
--
-- Design note: embedding dim = 1024 targets Voyage AI voyage-3.
-- If you switch to a different model, drop and recreate this table with
-- the correct dimension before running embed_schema.py.

CREATE TABLE IF NOT EXISTS schema_embeddings (
    id          SERIAL PRIMARY KEY,
    object_type TEXT NOT NULL,        -- 'table' or 'column'
    object_name TEXT NOT NULL,        -- e.g. 'Artist' or 'Artist.Name'
    description TEXT NOT NULL,        -- human-readable text sent to embedding model
    embedding   vector(1024),         -- NULL until embed_schema.py runs
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- IVFFlat index for fast approximate nearest-neighbour search.
-- lists=10 is reasonable for < 10k rows; tune upward as corpus grows.
CREATE INDEX IF NOT EXISTS schema_embeddings_vec_idx
    ON schema_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 10);

-- Read-only role needs SELECT here too (for schema_retriever node).
GRANT SELECT ON schema_embeddings TO querymind_ro;
