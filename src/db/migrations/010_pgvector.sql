-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column to insights table
ALTER TABLE insights ADD COLUMN IF NOT EXISTS embedding vector(384);

-- Create HNSW index for fast similarity search
CREATE INDEX IF NOT EXISTS idx_insights_embedding
ON insights USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- RPC function for similarity search
CREATE OR REPLACE FUNCTION match_insights(
    query_embedding vector(384),
    match_count int DEFAULT 10,
    match_threshold float DEFAULT 0.7
)
RETURNS TABLE (
    id uuid,
    org_id uuid,
    category text,
    title text,
    description text,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        i.id,
        i.org_id,
        i.category,
        i.title,
        i.description,
        1 - (i.embedding <=> query_embedding) AS similarity
    FROM insights i
    WHERE i.embedding IS NOT NULL
      AND 1 - (i.embedding <=> query_embedding) > match_threshold
    ORDER BY i.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
