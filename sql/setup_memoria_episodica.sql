-- Tabla para memoria episódica (largo plazo) con pgvector
-- Almacena resúmenes de conversaciones con embeddings para búsqueda semántica

-- Crear extensión pgvector si no existe
CREATE EXTENSION IF NOT EXISTS vector;

-- Tabla principal
CREATE TABLE IF NOT EXISTS memoria_episodica (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    resumen TEXT NOT NULL,
    embedding vector(384) NOT NULL,  -- Embeddings de 384 dimensiones
    metadata JSONB DEFAULT '{}'::jsonb,  -- Fecha, session_id, tipo
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Índices para optimización
    CONSTRAINT user_id_not_empty CHECK (user_id != ''),
    CONSTRAINT resumen_not_empty CHECK (resumen != '')
);

-- Índice para búsqueda por usuario
CREATE INDEX IF NOT EXISTS idx_memoria_user_id 
ON memoria_episodica(user_id);

-- Índice para búsqueda por timestamp
CREATE INDEX IF NOT EXISTS idx_memoria_timestamp 
ON memoria_episodica(timestamp DESC);

-- Índice HNSW para búsqueda semántica ultra-rápida (pgvector)
-- Usa distancia coseno (mejor para embeddings normalizados)
CREATE INDEX IF NOT EXISTS idx_memoria_embedding_cosine 
ON memoria_episodica 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Índice GIN para búsqueda en metadata JSON
CREATE INDEX IF NOT EXISTS idx_memoria_metadata 
ON memoria_episodica USING gin(metadata);

-- Comentarios explicativos
COMMENT ON TABLE memoria_episodica IS 
'Almacena resúmenes de conversaciones con embeddings para memoria a largo plazo';

COMMENT ON COLUMN memoria_episodica.embedding IS 
'Vector de 384 dimensiones generado con paraphrase-multilingual-MiniLM-L12-v2';

COMMENT ON COLUMN memoria_episodica.metadata IS 
'JSON con: fecha, session_id, tipo (normal/cierre_expiracion), timezone';

-- Función helper para búsqueda semántica
CREATE OR REPLACE FUNCTION buscar_memorias_similares(
    p_user_id VARCHAR(100),
    p_embedding vector(384),
    p_limit INT DEFAULT 5
)
RETURNS TABLE(
    id INT,
    resumen TEXT,
    similarity FLOAT,
    metadata JSONB,
    timestamp TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id,
        m.resumen,
        1 - (m.embedding <=> p_embedding) AS similarity,  -- Cosine similarity
        m.metadata,
        m.timestamp
    FROM memoria_episodica m
    WHERE m.user_id = p_user_id
    ORDER BY m.embedding <=> p_embedding  -- Ordena por distancia
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION buscar_memorias_similares IS 
'Busca las N memorias más similares semánticamente para un usuario';

-- Datos de ejemplo (opcional, comentar si no quieres seed data)
-- INSERT INTO memoria_episodica (user_id, resumen, embedding, metadata) VALUES
-- ('test_user', 
--  '[24/01/2026 12:00] Usuario agendó cita para mañana 15:00. Estado: Completada.', 
--  '[0.1, 0.2, ...]'::vector(384),  -- Embedding de ejemplo
--  '{"tipo": "normal", "session_id": "test_001"}'::jsonb
-- );

-- Verificar instalación
SELECT 'Tabla memoria_episodica creada exitosamente' AS status;
SELECT COUNT(*) AS registros_actuales FROM memoria_episodica;
