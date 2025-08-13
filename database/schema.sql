-- Inside LM Database Schema
-- This schema creates all necessary tables for the RAG-based book analysis platform

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create enum types
CREATE TYPE genre_type AS ENUM (
    'history',
    'science', 
    'literature',
    'philosophy',
    'technology',
    'other'
);

-- Books table
CREATE TABLE books (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    author VARCHAR(200) NOT NULL,
    genre genre_type NOT NULL DEFAULT 'other',
    file_path TEXT NOT NULL,
    total_pages INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Document chunks table (for storing text chunks with embeddings)
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    page_start INTEGER NOT NULL,
    page_end INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    embedding vector(384), -- FastEmbed BGE-small dimension
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Users table (for Supabase auth integration)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Notebooks table
CREATE TABLE notebooks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    selected_books UUID[] DEFAULT '{}',
    selected_genres genre_type[] DEFAULT '{}',
    memory_summary TEXT DEFAULT '',
    key_facts TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Chat messages table
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    notebook_id UUID NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
    user_message TEXT NOT NULL,
    assistant_response TEXT NOT NULL,
    citations JSONB DEFAULT '[]',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Notes table (for user notes per notebook)
CREATE TABLE notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    notebook_id UUID NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX idx_books_genre ON books(genre);
CREATE INDEX idx_books_author ON books(author);
CREATE INDEX idx_document_chunks_book_id ON document_chunks(book_id);
CREATE INDEX idx_document_chunks_pages ON document_chunks(page_start, page_end);
CREATE INDEX idx_notebooks_user_id ON notebooks(user_id);
CREATE INDEX idx_chat_messages_notebook_id ON chat_messages(notebook_id);
CREATE INDEX idx_chat_messages_timestamp ON chat_messages(timestamp);
CREATE INDEX idx_notes_notebook_id ON notes(notebook_id);

-- Create vector similarity search index (requires pgvector extension)
-- CREATE INDEX idx_document_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_books_updated_at BEFORE UPDATE ON books FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_notebooks_updated_at BEFORE UPDATE ON notebooks FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_notes_updated_at BEFORE UPDATE ON notes FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert sample data for testing
INSERT INTO users (email, full_name) VALUES 
    ('test@example.com', 'Test User');

-- Insert sample books
INSERT INTO books (title, author, genre, file_path, total_pages) VALUES 
    ('Sample History Book', 'John Doe', 'history', '/sample/history.pdf', 300),
    ('Sample Science Book', 'Jane Smith', 'science', '/sample/science.pdf', 250);

-- Create RLS (Row Level Security) policies
ALTER TABLE books ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE notebooks ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE notes ENABLE ROW LEVEL SECURITY;

-- Books: Public read access
CREATE POLICY "Books are viewable by everyone" ON books FOR SELECT USING (true);

-- Document chunks: Public read access
CREATE POLICY "Document chunks are viewable by everyone" ON document_chunks FOR SELECT USING (true);

-- Notebooks: Users can only see their own notebooks
CREATE POLICY "Users can view own notebooks" ON notebooks FOR SELECT USING (auth.uid()::text = user_id::text);
CREATE POLICY "Users can insert own notebooks" ON notebooks FOR INSERT WITH CHECK (auth.uid()::text = user_id::text);
CREATE POLICY "Users can update own notebooks" ON notebooks FOR UPDATE USING (auth.uid()::text = user_id::text);
CREATE POLICY "Users can delete own notebooks" ON notebooks FOR DELETE USING (auth.uid()::text = user_id::text);

-- Chat messages: Users can only see messages from their notebooks
CREATE POLICY "Users can view chat messages from own notebooks" ON chat_messages FOR SELECT USING (
    EXISTS (
        SELECT 1 FROM notebooks WHERE notebooks.id = chat_messages.notebook_id AND notebooks.user_id::text = auth.uid()::text
    )
);
CREATE POLICY "Users can insert chat messages to own notebooks" ON chat_messages FOR INSERT WITH CHECK (
    EXISTS (
        SELECT 1 FROM notebooks WHERE notebooks.id = chat_messages.notebook_id AND notebooks.user_id::text = auth.uid()::text
    )
);

-- Notes: Users can only see notes from their notebooks
CREATE POLICY "Users can view notes from own notebooks" ON notes FOR SELECT USING (
    EXISTS (
        SELECT 1 FROM notebooks WHERE notebooks.id = notes.notebook_id AND notebooks.user_id::text = auth.uid()::text
    )
);
CREATE POLICY "Users can insert notes to own notebooks" ON notes FOR INSERT WITH CHECK (
    EXISTS (
        SELECT 1 FROM notebooks WHERE notebooks.id = notes.notebook_id AND notebooks.user_id::text = auth.uid()::text
    )
);
CREATE POLICY "Users can update own notes" ON notes FOR UPDATE USING (
    EXISTS (
        SELECT 1 FROM notebooks WHERE notebooks.id = notes.notebook_id AND notebooks.user_id::text = auth.uid()::text
    )
);
CREATE POLICY "Users can delete own notes" ON notes FOR DELETE USING (
    EXISTS (
        SELECT 1 FROM notebooks WHERE notebooks.id = notes.notebook_id AND notebooks.user_id::text = auth.uid()::text
    )
);
