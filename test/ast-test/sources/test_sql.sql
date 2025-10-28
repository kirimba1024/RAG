-- RAG Assistant Database Schema
-- PostgreSQL database schema for RAG Assistant

-- Create database
CREATE DATABASE rag_assistant;
\c rag_assistant;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Projects table
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    language VARCHAR(50),
    framework VARCHAR(100),
    repository_url VARCHAR(500),
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Documents table (for indexed files)
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    file_path VARCHAR(1000) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_extension VARCHAR(10),
    file_size BIGINT,
    language VARCHAR(50),
    content_hash VARCHAR(64) UNIQUE NOT NULL,
    is_indexed BOOLEAN DEFAULT FALSE,
    indexed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Chunks table (for text chunks)
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    start_line INTEGER,
    end_line INTEGER,
    token_count INTEGER,
    embedding VECTOR(1536), -- For vector similarity search
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Search queries table
CREATE TABLE search_queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    query_text TEXT NOT NULL,
    query_type VARCHAR(50) NOT NULL, -- 'semantic', 'exact', 'regex'
    language_filter VARCHAR(50),
    results_count INTEGER,
    execution_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Search results table
CREATE TABLE search_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_id UUID NOT NULL REFERENCES search_queries(id) ON DELETE CASCADE,
    chunk_id UUID NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
    relevance_score FLOAT NOT NULL,
    rank INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Knowledge graph entities table
CREATE TABLE kg_entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    entity_name VARCHAR(255) NOT NULL,
    entity_type VARCHAR(100) NOT NULL, -- 'class', 'function', 'variable', 'module'
    file_path VARCHAR(1000),
    start_line INTEGER,
    end_line INTEGER,
    properties JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Knowledge graph relationships table
CREATE TABLE kg_relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source_entity_id UUID NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
    target_entity_id UUID NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL, -- 'uses', 'extends', 'implements', 'calls'
    properties JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_documents_project_id ON documents(project_id);
CREATE INDEX idx_documents_file_path ON documents(file_path);
CREATE INDEX idx_documents_language ON documents(language);
CREATE INDEX idx_documents_content_hash ON documents(content_hash);

CREATE INDEX idx_chunks_document_id ON chunks(document_id);
CREATE INDEX idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops);

CREATE INDEX idx_search_queries_user_id ON search_queries(user_id);
CREATE INDEX idx_search_queries_project_id ON search_queries(project_id);
CREATE INDEX idx_search_queries_created_at ON search_queries(created_at);

CREATE INDEX idx_search_results_query_id ON search_results(query_id);
CREATE INDEX idx_search_results_chunk_id ON search_results(chunk_id);

CREATE INDEX idx_kg_entities_project_id ON kg_entities(project_id);
CREATE INDEX idx_kg_entities_entity_name ON kg_entities(entity_name);
CREATE INDEX idx_kg_entities_entity_type ON kg_entities(entity_type);

CREATE INDEX idx_kg_relationships_project_id ON kg_relationships(project_id);
CREATE INDEX idx_kg_relationships_source_entity ON kg_relationships(source_entity_id);
CREATE INDEX idx_kg_relationships_target_entity ON kg_relationships(target_entity_id);
CREATE INDEX idx_kg_relationships_type ON kg_relationships(relationship_type);

-- Functions
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Views
CREATE VIEW project_stats AS
SELECT 
    p.id,
    p.name,
    p.language,
    COUNT(DISTINCT d.id) as document_count,
    COUNT(DISTINCT c.id) as chunk_count,
    COUNT(DISTINCT e.id) as entity_count,
    COUNT(DISTINCT r.id) as relationship_count,
    p.created_at
FROM projects p
LEFT JOIN documents d ON p.id = d.project_id
LEFT JOIN chunks c ON d.id = c.document_id
LEFT JOIN kg_entities e ON p.id = e.project_id
LEFT JOIN kg_relationships r ON p.id = r.project_id
GROUP BY p.id, p.name, p.language, p.created_at;

-- Sample data
INSERT INTO users (username, email, password_hash, first_name, last_name, is_admin) VALUES
('admin', 'admin@example.com', '$2b$10$example_hash', 'Admin', 'User', TRUE),
('developer', 'dev@example.com', '$2b$10$example_hash', 'John', 'Doe', FALSE);

INSERT INTO projects (name, description, owner_id, language, framework) VALUES
('RAG Assistant', 'Multi-language code analysis tool', (SELECT id FROM users WHERE username = 'admin'), 'Python', 'FastAPI'),
('Web App', 'Sample web application', (SELECT id FROM users WHERE username = 'developer'), 'JavaScript', 'React');
