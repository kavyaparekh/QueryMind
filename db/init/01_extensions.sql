-- Enable pgvector for semantic schema retrieval (Phase 2).
-- This must run before any table using the vector type is created.
CREATE EXTENSION IF NOT EXISTS vector;
