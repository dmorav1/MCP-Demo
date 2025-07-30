-- Enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    scenario_title TEXT,
    original_title TEXT,
    url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create the conversation_chunks table
CREATE TABLE IF NOT EXISTS conversation_chunks (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
    order_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding VECTOR(1536), -- Dimension for text-embedding-ada-002
    author_name TEXT,
    author_type VARCHAR(10),
    timestamp TIMESTAMP WITH TIME ZONE,
    CONSTRAINT conversation_order_unique UNIQUE (conversation_id, order_index)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS ix_conversation_chunks_conversation_id ON conversation_chunks(conversation_id);
CREATE INDEX IF NOT EXISTS ix_conversation_chunks_embedding ON conversation_chunks USING hnsw (embedding vector_l2_ops);
CREATE INDEX IF NOT EXISTS ix_conversations_created_at ON conversations(created_at);
CREATE INDEX IF NOT EXISTS ix_conversation_chunks_timestamp ON conversation_chunks(timestamp);
