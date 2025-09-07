-- Enable vector extension (pgvector)
CREATE EXTENSION IF NOT EXISTS vector;

-- Main table
CREATE TABLE IF NOT EXISTS images (
  id UUID PRIMARY KEY,
  source TEXT NOT NULL,                -- 'instagram' | 'user'
  source_id TEXT,                      -- ig media id or upload id
  url TEXT,                            -- canonical or CDN/permalink
  hashtags TEXT[] DEFAULT '{}',
  width INT,
  height INT,
  created_at TIMESTAMPTZ DEFAULT now(),
  embedding VECTOR(512)                -- CLIP ViT-B/32 dim
);

-- Avoid duplicates from same source
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'uniq_source_source_id'
  ) THEN
    ALTER TABLE images ADD CONSTRAINT uniq_source_source_id UNIQUE (source, source_id);
  END IF;
END$$;

-- ANN index for fast similarity (cosine)
CREATE INDEX IF NOT EXISTS idx_images_embedding
ON images USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Hashtag index
CREATE INDEX IF NOT EXISTS idx_images_hashtags ON images USING GIN (hashtags);
