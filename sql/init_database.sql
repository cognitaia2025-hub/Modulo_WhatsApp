-- =====================================================================
-- Script Maestro de Inicialización de Base de Datos
-- Agente WhatsApp con Memoria Infinita
-- =====================================================================
-- Base de datos: agente_whatsapp
-- Puerto: 5434 (externo) → 5432 (interno)
-- Usuario: admin / password123
-- =====================================================================

-- 1. EXTENSIÓN PGVECTOR (Búsqueda semántica de vectores)
-- =====================================================================
CREATE EXTENSION IF NOT EXISTS vector;

COMMENT ON EXTENSION vector IS 
'Extensión para almacenar y buscar embeddings (vectores de 384 dimensiones)';


-- =====================================================================
-- 2. MEMORIA PROCEDIMENTAL: Herramientas Disponibles
-- =====================================================================
-- Almacena las herramientas de Google Calendar que el agente puede usar
-- Esta tabla define las capacidades del agente

CREATE TABLE IF NOT EXISTS herramientas_disponibles (
    id_tool SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    descripcion TEXT NOT NULL,
    parametros JSONB DEFAULT '{}'::jsonb,
    activa BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_herramientas_activas 
ON herramientas_disponibles(activa) 
WHERE activa = true;

COMMENT ON TABLE herramientas_disponibles IS 
'Memoria Procedimental: Catálogo de herramientas que el agente puede ejecutar';

-- Insertar las 5 herramientas de Google Calendar
INSERT INTO herramientas_disponibles (nombre, descripcion, parametros) VALUES
(
    'list_calendar_events',
    'Lista eventos del calendario de Google Calendar en un rango de fechas específico',
    '{"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}'::jsonb
),
(
    'create_calendar_event',
    'Crea un nuevo evento en Google Calendar con título, fecha, hora de inicio y duración',
    '{"title": "string", "date": "YYYY-MM-DD", "time": "HH:MM", "duration_minutes": 60}'::jsonb
),
(
    'update_calendar_event',
    'Actualiza un evento existente en Google Calendar (título, fecha u hora)',
    '{"event_id": "string", "title": "string", "date": "YYYY-MM-DD", "time": "HH:MM"}'::jsonb
),
(
    'delete_calendar_event',
    'Elimina un evento del calendario de Google Calendar por su ID',
    '{"event_id": "string"}'::jsonb
),
(
    'get_event_details',
    'Obtiene los detalles completos de un evento específico de Google Calendar',
    '{"event_id": "string"}'::jsonb
)
ON CONFLICT (nombre) DO NOTHING;


-- =====================================================================
-- 3. MEMORIA EPISÓDICA: Recuerdos a Largo Plazo
-- =====================================================================
-- Almacena resúmenes de conversaciones con embeddings para búsqueda semántica
-- El agente puede recordar interacciones pasadas y aprender patrones del usuario

CREATE TABLE IF NOT EXISTS memoria_episodica (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    resumen TEXT NOT NULL,
    embedding vector(384) NOT NULL,  -- Embeddings de 384 dimensiones
    metadata JSONB DEFAULT '{}'::jsonb,  -- {fecha, session_id, tipo, timezone}
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT user_id_not_empty CHECK (user_id != ''),
    CONSTRAINT resumen_not_empty CHECK (resumen != '')
);

-- Índice para búsqueda por usuario
CREATE INDEX IF NOT EXISTS idx_memoria_user_id 
ON memoria_episodica(user_id);

-- Índice para búsqueda temporal (ordenar por fecha)
CREATE INDEX IF NOT EXISTS idx_memoria_timestamp 
ON memoria_episodica(timestamp DESC);

-- Índice HNSW para búsqueda semántica ultra-rápida con pgvector
-- Usa distancia coseno (óptima para embeddings normalizados)
CREATE INDEX IF NOT EXISTS idx_memoria_embedding_hnsw 
ON memoria_episodica 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Índice GIN para búsqueda en metadata JSON
CREATE INDEX IF NOT EXISTS idx_memoria_metadata 
ON memoria_episodica USING gin(metadata);

COMMENT ON TABLE memoria_episodica IS 
'Memoria Episódica: Resúmenes de conversaciones con embeddings para búsqueda semántica';

COMMENT ON COLUMN memoria_episodica.embedding IS 
'Vector de 384 dimensiones generado con paraphrase-multilingual-MiniLM-L12-v2';

COMMENT ON COLUMN memoria_episodica.metadata IS 
'JSON con: fecha (Pendulum), session_id, tipo (normal/cierre_expiracion), timezone';


-- =====================================================================
-- Función Helper: Buscar Memorias Similares (Búsqueda Semántica)
-- =====================================================================
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
    ORDER BY m.embedding <=> p_embedding  -- Ordena por distancia (menor = más similar)
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION buscar_memorias_similares IS 
'Busca las N memorias más similares semánticamente para un usuario dado';


-- =====================================================================
-- 4. AUDITORÍA PLANA: Logs de Conversaciones (Retención 6 meses)
-- =====================================================================
-- Almacena TODOS los mensajes de usuario y asistente para auditoría
-- Sin TTL automático, pero con índice temporal para limpieza manual

CREATE TABLE IF NOT EXISTS auditoria_conversaciones (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    session_id VARCHAR(200) NOT NULL,
    rol VARCHAR(20) NOT NULL,  -- 'user', 'assistant', 'system'
    contenido TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT rol_valido CHECK (rol IN ('user', 'assistant', 'system'))
);

-- Índice compuesto para consultas por usuario + fecha
CREATE INDEX IF NOT EXISTS idx_auditoria_user_timestamp 
ON auditoria_conversaciones(user_id, timestamp DESC);

-- Índice para consultas por sesión
CREATE INDEX IF NOT EXISTS idx_auditoria_session 
ON auditoria_conversaciones(session_id);

COMMENT ON TABLE auditoria_conversaciones IS 
'Auditoría: Logs planos de todas las conversaciones (retención 6 meses)';

-- Vista para limpieza de registros antiguos (>6 meses)
CREATE OR REPLACE VIEW auditoria_para_limpiar AS
SELECT id, user_id, timestamp
FROM auditoria_conversaciones
WHERE timestamp < NOW() - INTERVAL '6 months';

COMMENT ON VIEW auditoria_para_limpiar IS 
'Registros de auditoría con más de 6 meses para limpieza manual';


-- =====================================================================
-- 5. TABLAS INTERNAS DE LANGGRAPH (Checkpoint Automático)
-- =====================================================================
-- LangGraph creará automáticamente estas tablas al ejecutar setup():
-- - checkpoints: Estado de cada sesión (TTL 24h)
-- - checkpoint_writes: Escrituras pendientes
-- - checkpoint_blobs: Datos grandes serializados

-- Estas tablas se crean automáticamente con PostgresSaver.setup()
-- Ver: langgraph-checkpoint-postgres


-- =====================================================================
-- 6. FUNCIÓN DE MANTENIMIENTO: Limpieza Automática de Auditoría
-- =====================================================================
CREATE OR REPLACE FUNCTION limpiar_auditoria_antigua()
RETURNS INTEGER AS $$
DECLARE
    registros_eliminados INTEGER;
BEGIN
    DELETE FROM auditoria_conversaciones
    WHERE timestamp < NOW() - INTERVAL '6 months';
    
    GET DIAGNOSTICS registros_eliminados = ROW_COUNT;
    
    RAISE NOTICE 'Eliminados % registros de auditoría antiguos', registros_eliminados;
    RETURN registros_eliminados;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION limpiar_auditoria_antigua IS 
'Elimina registros de auditoría con más de 6 meses de antigüedad';

-- Job programado (ejecutar manualmente o con pg_cron)
-- SELECT cron.schedule('limpiar-auditoria', '0 2 1 * *', 'SELECT limpiar_auditoria_antigua();');


-- =====================================================================
-- 7. VERIFICACIÓN FINAL
-- =====================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Base de datos inicializada correctamente';
    RAISE NOTICE '📊 Extensión pgvector: Instalada';
    RAISE NOTICE '🛠️  Herramientas disponibles: % registros', (SELECT COUNT(*) FROM herramientas_disponibles);
    RAISE NOTICE '🧠 Memoria episódica: Lista para embeddings de 384 dims';
    RAISE NOTICE '📝 Auditoría de conversaciones: Retención 6 meses';
    RAISE NOTICE '💾 Tablas de LangGraph: Se crearán al ejecutar checkpointer.setup()';
    RAISE NOTICE '🎯 Puerto: 5434 (externo) → 5432 (interno)';
END $$;

-- Consultar estado de las tablas creadas
SELECT 
    'herramientas_disponibles' AS tabla,
    COUNT(*) AS registros,
    pg_size_pretty(pg_total_relation_size('herramientas_disponibles')) AS tamaño
FROM herramientas_disponibles
UNION ALL
SELECT 
    'memoria_episodica' AS tabla,
    COUNT(*) AS registros,
    pg_size_pretty(pg_total_relation_size('memoria_episodica')) AS tamaño
FROM memoria_episodica
UNION ALL
SELECT 
    'auditoria_conversaciones' AS tabla,
    COUNT(*) AS registros,
    pg_size_pretty(pg_total_relation_size('auditoria_conversaciones')) AS tamaño
FROM auditoria_conversaciones;
