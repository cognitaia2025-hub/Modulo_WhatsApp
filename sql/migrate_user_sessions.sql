-- =============================================
-- Migración: Tabla user_sessions para Cache
-- =============================================

-- Crear tabla si no existe
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,           -- Phone number del usuario
    thread_id VARCHAR(100) UNIQUE NOT NULL,  -- ID único de sesión LangGraph
    phone_number VARCHAR(50),
    last_activity TIMESTAMP DEFAULT NOW(),   -- Última actividad
    messages_count INTEGER DEFAULT 0,        -- Contador de mensajes
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_user_sessions_user FOREIGN KEY (user_id) 
        REFERENCES usuarios(phone_number) ON DELETE CASCADE
);

-- Índices para búsquedas rápidas
CREATE INDEX IF NOT EXISTS idx_sessions_user_activity 
    ON user_sessions(user_id, last_activity DESC);

CREATE INDEX IF NOT EXISTS idx_sessions_thread 
    ON user_sessions(thread_id);

CREATE INDEX IF NOT EXISTS idx_sessions_cleanup 
    ON user_sessions(last_activity) 
    WHERE last_activity < NOW() - INTERVAL '24 hours';

-- Comentarios
COMMENT ON TABLE user_sessions IS 
    'Gestión de sesiones activas con rolling window de 24 horas';

COMMENT ON COLUMN user_sessions.last_activity IS 
    'Timestamp de última actividad. Sesiones > 24h se consideran expiradas';

COMMENT ON COLUMN user_sessions.messages_count IS 
    'Contador incremental de mensajes en la sesión';

-- Vista para monitoreo
CREATE OR REPLACE VIEW sesiones_activas AS
SELECT 
    us.user_id,
    us.thread_id,
    us.last_activity,
    EXTRACT(EPOCH FROM (NOW() - us.last_activity))/3600 as hours_inactive,
    us.messages_count,
    u.display_name,
    u.tipo_usuario
FROM user_sessions us
LEFT JOIN usuarios u ON u.phone_number = us.user_id
WHERE us.last_activity > NOW() - INTERVAL '24 hours'
ORDER BY us.last_activity DESC;

-- Función de limpieza automática
CREATE OR REPLACE FUNCTION cleanup_old_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM user_sessions
    WHERE last_activity < NOW() - INTERVAL '30 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON user_sessions TO postgres;
GRANT USAGE, SELECT ON SEQUENCE user_sessions_id_seq TO postgres;
